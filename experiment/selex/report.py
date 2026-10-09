"""Metrics over all score files, detectability / invasiveness curves, go/no-go checks and the results card."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .corpus import Corpus
from .metrics import evaluate_grid, summarize
from .runner import load_all_scores


def compute_metrics(c: Corpus, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (per-seed metrics, summary over tie seeds). S-rand seeds are collapsed into one selector 'S-rand'."""
    S = load_all_scores(c, cfg)
    rows = []
    for (sel, var, run_id), g in S.groupby(["selector", "access_variant", "run_id"]):
        sc = g.set_index("post_id")["raw_score"].astype(float)
        # scores restricted to a subsample (S3-com) are evaluated on the subsample corpus
        sub = c if len(sc) == len(c.posts) else Corpus(c.name, c.posts[c.posts.post_id.isin(sc.index)].copy(), c.authors, c.arc_key,
                                                      {a: v for a, v in c.arcs.items()})
        rep = int(g.run_id.iloc[0][-1]) if False else 0
        m = evaluate_grid(sub, sc, cfg["budgets"], cfg["tie_seeds"],
                          meta={"selector": sel.split("S-rand")[0] + "S-rand" if sel.startswith("S-rand") else sel,
                                "access_variant": var, "run_id": run_id, "n_scored": len(sc), "model_id": g.model_id.iloc[0]})
        rows.append(m)
    per_seed = pd.concat(rows, ignore_index=True)
    summ = summarize(per_seed)
    d = cfg["results_dir"] / c.name
    per_seed.to_csv(d / "metrics_per_seed.csv", index=False)
    summ.to_csv(d / "metrics_summary.csv", index=False)
    return per_seed, summ


def go_no_go(summ: pd.DataFrame, c: Corpus, dup_rate: float | None = None, dup_threshold: float | None = None) -> list[dict]:
    """Plan section 19 criteria, evaluated on the summary table (means over tie seeds)."""
    def get(sel, var, b, col):
        r = summ[(summ.selector == sel) & (summ.access_variant == var) & (np.isclose(summ.budget, b))]
        return float(r[col].iloc[0]) if len(r) else np.nan
    n_dist = sum(1 for a in c.target_arcs if c.arcs[a]["arc_type"] == "distributed")
    n_conc = sum(1 for a in c.target_arcs if c.arcs[a]["arc_type"] == "concentrated")
    d3_variants = {"S0-sub": "D3-agg", "S0-veto": "D3-agg", "S1": "D3-txt", "S3-open": "D3-nat", "S3-blind": "D3-nat"}
    best_d3_20 = max((get(s, v, 0.20, "detected") for s, v in d3_variants.items()), default=np.nan)
    dist_d0_5 = max((get(s, "D0", 0.05, "dist") for s in ("S0-sub", "S0-veto", "S1", "S3-open", "S3-blind")), default=np.nan)
    conc_s0_20 = max(get("S0-sub", "D0", 0.20, "conc"), get("S0-veto", "D0", 0.20, "conc"))
    rand_20 = get("S-rand", "D0", 0.20, "detected")
    gain = max(((get(s, v, 0.20, "dist") - get(s, "D0", 0.20, "dist")) for s, v in d3_variants.items()), default=np.nan)
    crit = [
        {"id": 1, "criterion": "at least one selector detects >= 6/10 arcs in D3 at 20 %", "value": best_d3_20, "pass": bool(best_d3_20 >= 6)},
        {"id": 2, "criterion": f"at most 1/{n_dist} distributed arcs detected in D0 at 5 % (max over selectors)", "value": dist_d0_5, "pass": bool(dist_d0_5 <= 1)},
        {"id": 3, "criterion": f"at least 3/{n_conc} concentrated arcs detected by S0 in D0 at 20 %", "value": conc_s0_20, "pass": bool(conc_s0_20 >= 3)},
        {"id": 4, "criterion": "S-rand detects at most 1 arc at 20 %", "value": rand_20, "pass": bool(rand_20 <= 1)},
        {"id": 5, "criterion": "for at least one selector, D3 - D0 for distributed arcs >= 3 arcs (at 20 %)", "value": gain, "pass": bool(gain >= 3)},
        {"id": 6, "criterion": "duplicate_rate below the dev-corpus threshold", "value": dup_rate, "pass": (None if dup_rate is None else bool(dup_rate <= (dup_threshold or 0.01)))},
    ]
    return crit


def blind_difference(summ: pd.DataFrame) -> pd.DataFrame:
    a = summ[summ.selector == "S3-open"][["access_variant", "budget", "detected", "dist", "conc", "bystanders"]]
    b = summ[summ.selector == "S3-blind"][["access_variant", "budget", "detected", "dist", "conc", "bystanders"]]
    m = a.merge(b, on=["access_variant", "budget"], suffixes=("_S3", "_S3blind"))
    for col in ("detected", "dist", "conc", "bystanders"):
        m[f"{col}_diff"] = m[f"{col}_S3"] - m[f"{col}_S3blind"]
    return m


def agreement(c: Corpus, cfg: dict) -> dict:
    """Determinism (S3-open rep0 vs rep1), control transfer (S3-com vs S3-open on the subsample), declared vs internal score."""
    from scipy.stats import spearmanr

    S = load_all_scores(c, cfg)
    out = {}
    for var in ("D0", "D3-nat"):
        runs = S[(S.selector == "S3-open") & (S.access_variant == var)].groupby("run_id")
        frames = [g.set_index("post_id") for _, g in runs]
        if len(frames) >= 2:
            a, b = frames[0], frames[1]
            j = a.join(b, lsuffix="_a", rsuffix="_b", how="inner")
            out[f"determinism_{var}"] = {"n": int(len(j)), "decision_agreement": float((j.decision_a == j.decision_b).mean()),
                                        "score_spearman": float(spearmanr(j.raw_score_a, j.raw_score_b).correlation),
                                        "retention_score_mean_abs_diff": float((j.retention_score_a - j.retention_score_b).abs().mean())}
        o = S[(S.selector == "S3-open") & (S.access_variant == var)]
        cm = S[(S.selector == "S3-com") & (S.access_variant == var)]
        if len(o) and len(cm):
            o1 = o.drop_duplicates("post_id").set_index("post_id"); c1 = cm.drop_duplicates("post_id").set_index("post_id")
            j = o1.join(c1, lsuffix="_open", rsuffix="_com", how="inner")
            out[f"control_{var}"] = {"n": int(len(j)), "decision_agreement": float((j.decision_open == j.decision_com).mean()),
                                     "retention_spearman": float(spearmanr(j.retention_score_open, j.retention_score_com, nan_policy="omit").correlation)}
        if len(o):
            o1 = o.drop_duplicates("post_id")
            ok = o1.logprob_decision.notna() & o1.retention_score.notna()
            if ok.sum() > 10:
                out[f"declared_vs_internal_{var}"] = {"n": int(ok.sum()),
                                                      "spearman": float(spearmanr(np.exp(o1.logprob_decision[ok]), o1.retention_score[ok]).correlation),
                                                      "logprob_available_share": float(o1.logprob_decision.notna().mean())}
    (cfg["results_dir"] / c.name / "agreement.json").write_text(json.dumps(out, indent=1))
    return out


def decisive_posts_check(c: Corpus, cfg: dict) -> dict:
    """D3-nat: do the posts the model names as decisive coincide with the PI's signal posts? (Annex F note)"""
    S = load_all_scores(c, cfg)
    d = S[(S.selector == "S3-open") & (S.access_variant == "D3-nat")].drop_duplicates("post_id")
    sig = c.signal_post_ids
    hits = tot = 0
    arcs_named = {}
    for _, r in d.iterrows():
        if r.post_id not in sig or r.decision != "KEEP_FOR_REVIEW":
            continue
        try:
            dp = set(json.loads(r.decisive_posts_json or "[]"))
        except Exception:
            dp = set()
        tot += 1
        if dp & sig:
            hits += 1
        arc = c.posts.loc[c.posts.post_id == r.post_id, "arc_id"].iloc[0]
        arcs_named.setdefault(arc, []).append(sorted(dp))
    return {"n_signal_posts_kept": tot, "named_a_signal_post": hits, "by_arc": arcs_named}


def decision_detection(c: Corpus, cfg: dict) -> pd.DataFrame:
    """Auxiliary, decision-based view (plan: DISCARD / KEEP_FOR_REVIEW classes kept as a secondary measure):
    an arc counts as detected when at least one of its signal posts received KEEP_FOR_REVIEW; bystanders = authors
    without an arc with at least one KEEP post. Independent of the retention budget."""
    S = load_all_scores(c, cfg)
    rows = []
    for (sel, var, run_id), g in S.groupby(["selector", "access_variant", "run_id"]):
        if not sel.startswith("S3") or var == "D3-agg":
            continue
        keep = set(g.loc[g.decision == "KEEP_FOR_REVIEW", "post_id"])
        det = [a for a in c.target_arcs if set(c.arcs[a]["signal_post_ids"]) & keep]
        loose = [a for a in c.target_arcs if set(c.arcs[a]["post_ids"]) & keep]
        by = c.posts[c.posts.post_id.isin(keep) & c.posts.author_id.isin(c.bystander_authors)]
        rows.append({"selector": sel, "access_variant": var, "run_id": run_id, "n_scored": len(g), "n_keep": len(keep),
                     "arcs_keep_strict": len(det), "arcs_keep_loose": len(loose),
                     "dist_keep": sum(1 for a in det if c.arcs[a]["arc_type"] == "distributed"),
                     "conc_keep": sum(1 for a in det if c.arcs[a]["arc_type"] == "concentrated"),
                     "decoy_keep": sum(1 for a in c.decoy_arcs if set(c.arcs[a]["post_ids"]) & keep),
                     "bystander_authors_keep": int(by.author_id.nunique()), "bystander_posts_keep": int(len(by)),
                     "hardneg_keep": int(c.posts[c.posts.post_id.isin(keep) & (c.posts.layer == "hardneg")].shape[0]),
                     "detected_arcs": "|".join(det)})
    df = pd.DataFrame(rows)
    df.to_csv(cfg["results_dir"] / c.name / "decision_detection.csv", index=False)
    return df


def curves(summ: pd.DataFrame, out: Path, title: str = "") -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for (sel, var), g in summ.groupby(["selector", "access_variant"]):
        if sel.startswith("S3-com"):
            continue
        g = g.sort_values("budget")
        style = "-" if var == "D0" else "--"
        axes[0].plot(g.budget * 100, g.detected, style, marker="o", label=f"{sel} {var}")
        axes[1].plot(g.budget * 100, g.bystanders, style, marker="o", label=f"{sel} {var}")
    axes[0].set_xlabel("retention budget (% of posts)"); axes[0].set_ylabel("detected arcs (strict)"); axes[0].set_title("Detectability")
    axes[1].set_xlabel("retention budget (% of posts)"); axes[1].set_ylabel("bystander authors retained"); axes[1].set_title("Invasiveness")
    axes[0].set_xscale("log"); axes[1].set_xscale("log")
    axes[1].legend(fontsize=6, ncol=2)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def results_card(c: Corpus, cfg: dict, summ: pd.DataFrame, crit: list[dict], agree: dict, blind: pd.DataFrame, decisive: dict,
                 cost: float, notes: str = "") -> str:
    md = [f"# EP-SKEL results card: {c.name} corpus", "",
          f"Posts {len(c.posts)}, authors {len(c.authors)}, target arcs {len(c.target_arcs)} ({sum(1 for a in c.target_arcs if c.arcs[a]['arc_type']=='concentrated')} concentrated, "
          f"{sum(1 for a in c.target_arcs if c.arcs[a]['arc_type']=='distributed')} distributed), decoys {len(c.decoy_arcs)}, signal posts {len(c.signal_post_ids)}, bystander authors {len(c.bystander_authors)}.",
          f"Budgets {cfg['budgets']}; tie seeds {cfg['tie_seeds']}; aggregation {cfg['aggregation']}; S3-open `{cfg['selectors']['s3']['open_model']}`, S3-com `{cfg['selectors']['s3']['control_model']}`, S1 `{cfg['selectors']['s1']['embedding_model']}`. Scoring cost ${cost:.2f}.", ""]
    md += ["## Measurement points (means over tie seeds; absolute numbers)", ""]
    t = summ.copy()
    t["budget"] = (t.budget * 100).round(0).astype(int).astype(str) + " %"
    cols = ["selector", "access_variant", "budget", "n_retained", "detected", "detected_min", "detected_max", "conc", "dist", "detected_loose", "decoy_hits", "bystanders", "bpd", "profile_depth", "review_load", "signal_posts"]
    md.append(t[cols].round(2).to_markdown(index=False))
    md += ["", "## Go / no-go criteria (plan section 19)", "", pd.DataFrame(crit).to_markdown(index=False), ""]
    md += ["## S3 minus S3' (value of the explicit signal list)", "", blind.round(2).to_markdown(index=False) if len(blind) else "(not run)", ""]
    md += ["## Determinism, control model, declared vs internal score", "", "```json", json.dumps(agree, indent=1), "```", ""]
    md += ["## Decisive posts named by S3-open in D3-nat vs the PI's signal posts", "", "```json", json.dumps(decisive, ensure_ascii=False, indent=1)[:3000], "```", ""]
    if notes:
        md += ["## Notes", "", notes, ""]
    text = "\n".join(md)
    (cfg["results_dir"] / c.name / "results_card.md").write_text(text, encoding="utf-8")
    return text
