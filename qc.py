"""Quality control for a built corpus (plan stage 5). Usage: uv run python qc.py corpus/epskel_v1 [v1]

Produces in the corpus dir:
  qc_<v>.json           - per-layer diversity metrics, duplicate stats, refusal/empty counts, length stats
  qc_neardups_<v>.csv   - pairs of posts with embedding cosine > threshold (for manual removal decisions)
  qc_flags_<v>.csv      - posts flagged: refusal-like, empty/short, forbidden-topic words in the background layer,
                          English leakage, placeholder brackets
  sample_pi_200_<v>.csv - 200-post stratified sample for the PI's uniformity review
  sample_blind_30_<v>.csv - 30-post blind sample for the external reviewer (no labels)
  signal_posts_<v>.csv  - all arc posts with signal status, for the PI's approval of signal posts
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from epskel import metrics
from epskel.llm import looks_like_refusal

# words that must not appear in the mundane background layer (plan Annex A hard exclusions)
BG_FORBIDDEN = [
    r"\bzabij", r"\bzabić", r"\bnóż", r"\bnoż[ae]\b", r"\bbroń", r"\bpistol", r"\bstrzel", r"\bpobij", r"\bpobić", r"\bgroż", r"\bgroźb",
    r"\bpolicj", r"\bprokurat", r"\bsąd\b", r"\bsądz", r"\bwięzien", r"\bareszt", r"\bprzestęp", r"\bkradzie", r"\bnapad",
    r"\bbomb", r"\bwybuch", r"\bterror", r"\bzamach", r"\bprotest", r"\bdemonstr", r"\bpartia", r"\bwybor", r"\bminist", r"\brząd\b",
    r"\bimigran", r"\buchodź", r"\bukrai", r"\bkości[óo]ł", r"\bksiądz", r"\bmsz[ay]\b", r"\bgej\b", r"\blgbt",
]
_BG_RE = [re.compile(p, re.I) for p in BG_FORBIDDEN]


def main(d: str, version: str = "v1", dup_threshold: float = 0.90) -> None:
    D = Path(d)
    posts = pd.read_csv(D / f"posts_{version}.csv", dtype=str).fillna("")
    authors = pd.read_csv(D / f"authors_{version}.csv", dtype=str).fillna("")
    texts = posts.text.tolist()
    report: dict = {"n_posts": len(posts), "n_authors": len(authors), "layers": posts.layer.value_counts().to_dict()}

    # ---- flags
    flags = []
    for i, r in posts.iterrows():
        t = r.text
        why = []
        if not t.strip():
            why.append("empty")
        elif len(t.split()) < 4:
            why.append("too_short")
        if looks_like_refusal(t):
            why.append("refusal_like")
        if re.search(r"\[[A-Za-z ]+\]|\{[a-z_]+\}", t):
            why.append("placeholder")
        if len(t) > 120 and not re.search(r"[ąćęłńóśźż]", t.lower()) and re.search(r"\b(the|and|this|with)\b", t):
            why.append("english_leak")
        if r.layer == "background":
            hits = [p.pattern for p in _BG_RE if p.search(t)]
            if hits:
                why.append("bg_forbidden:" + "|".join(hits[:3]))
        if r.layer == "background" and len(t.split()) > 70:
            why.append("too_long")
        if why:
            flags.append({"post_id": r.post_id, "author_id": r.author_id, "layer": r.layer, "flags": ";".join(why), "text": t})
    pd.DataFrame(flags).to_csv(D / f"qc_flags_{version}.csv", index=False)
    report["n_flagged"] = len(flags)
    report["flag_counts"] = pd.Series([f["flags"].split(":")[0].split(";")[0] for f in flags]).value_counts().to_dict() if flags else {}

    # ---- duplicates
    norm = [re.sub(r"\W+", " ", t.lower()).strip() for t in texts]
    exact = pd.Series(norm).duplicated(keep=False)
    report["exact_dup_posts"] = int(exact.sum())
    E = metrics.embed(texts, batch_size=64)
    S = E @ E.T
    np.fill_diagonal(S, -1)
    iu = np.triu_indices(len(texts), 1)
    sims = S[iu]
    hi = np.where(sims > dup_threshold)[0]
    pairs = [{"post_a": posts.post_id[iu[0][k]], "post_b": posts.post_id[iu[1][k]], "cos": float(sims[k]),
              "same_author": posts.author_id[iu[0][k]] == posts.author_id[iu[1][k]],
              "text_a": texts[iu[0][k]], "text_b": texts[iu[1][k]]} for k in hi]
    pd.DataFrame(pairs).sort_values("cos", ascending=False).to_csv(D / f"qc_neardups_{version}.csv", index=False) if pairs else pd.DataFrame(columns=["post_a"]).to_csv(D / f"qc_neardups_{version}.csv", index=False)
    report["near_dup_pairs"] = len(pairs)
    report["near_dup_rate_posts"] = float((S.max(axis=1) > dup_threshold).mean())
    report["dup_threshold"] = dup_threshold

    # ---- per-layer metrics
    per_layer = {}
    for layer, sub in posts.groupby("layer"):
        idx = sub.index.to_numpy()
        rep = metrics.report_set(layer, sub.text.tolist(), E=E[idx], with_bleu=len(sub) <= 600)
        per_layer[layer] = rep.flat()
        per_layer[layer]["ai_ism_top"] = rep.surface.get("ai_ism_top")
    report["per_layer"] = per_layer
    # within-author similarity (how samey is one author's stream)
    wa = []
    for aid, sub in posts.groupby("author_id"):
        if len(sub) >= 3:
            idx = sub.index.to_numpy()
            M = E[idx] @ E[idx].T
            wa.append(M[np.triu_indices(len(idx), 1)].mean())
    report["within_author_mean_cos"] = float(np.mean(wa))
    report["posts_per_author"] = {"mean": float(posts.groupby("author_id").size().mean()), "min": int(posts.groupby("author_id").size().min()), "max": int(posts.groupby("author_id").size().max())}
    report["len_words"] = {"mean": float(np.mean([len(t.split()) for t in texts])), "p10": float(np.percentile([len(t.split()) for t in texts], 10)), "p90": float(np.percentile([len(t.split()) for t in texts], 90))}

    # ---- samples for review
    rng = np.random.default_rng(0)
    bg = posts[posts.layer == "background"].sample(n=min(140, (posts.layer == "background").sum()), random_state=0)
    hn = posts[posts.layer == "hardneg"].sample(n=min(40, (posts.layer == "hardneg").sum()), random_state=0)
    arc = posts[posts.layer == "arc"].sample(n=min(20, (posts.layer == "arc").sum()), random_state=0)
    s200 = pd.concat([bg, hn, arc]).sample(frac=1, random_state=1)
    s200[["post_id", "author_id", "layer", "timestamp", "text", "post_level_profile", "arc_id", "arc_role"]].to_csv(D / f"sample_pi_200_{version}.csv", index=False)
    s30 = posts.sample(n=min(30, len(posts)), random_state=2)[["post_id", "text"]]
    s30.to_csv(D / f"sample_blind_30_{version}.csv", index=False)
    if (posts.layer == "arc").any():
        key = pd.read_csv(D / f"arc_key_{version}.csv", dtype=str)
        arcp = posts[posts.layer == "arc"].merge(key, on=["arc_id", "arc_position"], how="left")
        arcp[["arc_id", "arc_type", "arc_position", "arc_role", "post_level_profile", "is_signal", "timestamp", "text"]].sort_values(["arc_id", "arc_position"]).to_csv(D / f"signal_posts_{version}.csv", index=False)

    (D / f"qc_{version}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "per_layer"}, indent=1, ensure_ascii=False, default=float))
    for layer, m in per_layer.items():
        print(layer, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items() if k in ("lex_compression_ratio", "lex_self_rep4", "lex_self_bleu4", "lex_distinct2", "sem_mean_cos", "sem_near_dup_rate", "sem_vendi_norm", "surf_len_mean", "surf_ai_ism_per_post", "surf_first_lower", "surf_emoji")})


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "v1")
