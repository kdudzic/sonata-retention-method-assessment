"""EP-SKEL selection experiment CLI.

  uv run python experiment.py describe                 corpora after the arc split
  uv run python experiment.py build-lexicon            LLM draft of the S0 lexicon from category definitions -> artifacts/s0_lexicon_draft.yaml
  uv run python experiment.py leak-check               rare terms of signal posts vs S0 lexicon / S1 seeds (plan 11.2)
  uv run python experiment.py model-trial [--n 200]    S3 D0 on a dev sample for each open candidate (plan M2 model choice)
  uv run python experiment.py freeze [--note ...]      hash and freeze selector artifacts (stage 0)
  uv run python experiment.py score --corpus dev|eval --selectors s0,s1,s3open,s3blind,s3com,srand [--repeat]
  uv run python experiment.py metrics --corpus dev|eval
  uv run python experiment.py report --corpus dev|eval
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter

import pandas as pd
import yaml

from selex import config, corpus, freeze, report, runner
from selex.llm import LLM
from selex.s0_lexical import Lexicon, S0Selector, norm
from selex.s1_semantic import Seeds
from selex.s3_llm import S3Selector, build_messages


def cmd_describe(cfg, a):
    ev, dv = corpus.load_split(cfg)
    print(json.dumps({"eval": corpus.describe(ev), "dev": corpus.describe(dv)}, ensure_ascii=False, indent=1))


def cmd_build_lexicon(cfg, a):
    llm = LLM(a.model, run_name="lexicon_build", temperature=0.3, max_tokens=8000)
    tmpl = config.read_prompt("lexicon_expand_v1")
    body = re.sub(r"<!--.*?-->\s*", "", tmpl, flags=re.S)
    m = re.search(r"^SYSTEM\s*\n(.*?)^USER\s*\n(.*)$", body, flags=re.S | re.M)
    r = llm.chat([{"role": "system", "content": m.group(1).strip()}, {"role": "user", "content": m.group(2).strip()}], tag="lexicon")
    t = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", r.text.strip())
    d = json.loads(t[t.find("{"): t.rfind("}") + 1])
    d = {k: sorted(set(str(x).strip().lower() for x in v if str(x).strip())) for k, v in d.items()}
    d["version"] = "s0_lexicon_draft"
    d["_source"] = f"LLM expansion from category definitions only (model {a.model}, prompt lexicon_expand_v1); to be pruned by hand"
    out = config.ARTIFACTS / "s0_lexicon_draft.yaml"
    out.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
    print({k: len(v) for k, v in d.items() if isinstance(v, list)}, llm.summary(), "->", out)


def cmd_leak_check(cfg, a):
    """Plan 11.2: which lexicon entries / seed words occur in the signal posts (term overlap), and which rare signal-post
    terms are in the lexicon. Reported, not acted on automatically."""
    ev, dv = corpus.load_split(cfg)
    lex = Lexicon.load(config.resolve(cfg["selectors"]["s0"]["lexicon"]))
    sel = S0Selector(lex, cfg["selectors"]["s0"]["weights"], cfg["selectors"]["s0"]["proximity_tokens"])
    seeds = Seeds.load(config.resolve(cfg["selectors"]["s1"]["seeds"]))
    seed_vocab = set(w for s in seeds.plus for w in norm(s).split() if len(w) > 4)
    bg_vocab = Counter(w for t in ev.posts[ev.posts.layer == "background"].text for w in norm(t).split())
    rows = []
    for c in (ev, dv):
        for arc_id in c.target_arcs:
            for pid in c.arcs[arc_id]["signal_post_ids"]:
                txt = c.posts.loc[c.posts.post_id == pid, "text"].iloc[0]
                f = sel.features(txt)
                rare = [w for w in set(norm(txt).split()) if len(w) > 4 and bg_vocab[w] <= 2]
                rows.append({"corpus": c.name, "arc": arc_id, "post_id": pid, "S0_cats": "".join(k for k in "ABCDE" if f[k]),
                             "rare_terms_in_seeds": sorted(set(rare) & seed_vocab), "n_rare": len(rare), "text": txt[:90]})
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    df.to_csv(cfg["results_dir"] / "leak_check.csv", index=False)


def cmd_model_trial(cfg, a):
    """S3 D0 on a dev sample (all dev arc posts + random background/hard negatives) for each open candidate."""
    ev, dv = corpus.load_split(cfg)
    rng = pd.Series(dv.posts.post_id.tolist()).sample(frac=1, random_state=0).tolist()
    arc_ids = [p for arc in dv.arcs.values() for p in arc["post_ids"]]
    sample = arc_ids + [p for p in rng if p not in set(arc_ids)][: max(0, a.n - len(arc_ids))]
    text_of = dict(zip(dv.posts.post_id, dv.posts.text))
    out = []
    for model in cfg["selectors"]["s3"]["open_candidates"]:
        sel = S3Selector(model, cfg["selectors"]["s3"]["prompt_d0"], run_name=f"trial_{model.replace('/', '_')}", temperature=0.0, workers=6)
        res = sel.score_many([(p, text_of[p], None) for p in sample], desc=model)
        ok = [r for r in res if not isinstance(r, Exception)]
        sc = pd.Series({r.post_id: r.raw_score for r in ok})
        sub = corpus.Corpus("devtrial", dv.posts[dv.posts.post_id.isin(sc.index)].copy(), dv.authors, dv.arc_key, dv.arcs)
        from selex.metrics import evaluate_budget
        row = {"model": model, "n": len(ok), "errors": len(res) - len(ok), "cost": sel.llm.total_cost,
               "logprob_share": float(pd.Series([r.p_keep is not None for r in ok]).mean()) if ok else 0,
               "parse_ok": float(pd.Series([r.parse_ok for r in ok]).mean()) if ok else 0,
               "keep_rate": float(pd.Series([r.decision == "KEEP_FOR_REVIEW" for r in ok]).mean()) if ok else 0}
        for b in (0.05, 0.20):
            m = evaluate_budget(sub, sc, b, 0)
            row[f"detected@{int(b*100)}"] = m.detected_arcs; row[f"bystanders@{int(b*100)}"] = m.bystander_authors
        # mean rank of signal posts (lower = better)
        from selex.metrics import rank_with_ties
        r = rank_with_ties(sc, 0)
        row["mean_signal_rank_pct"] = float(r[[p for p in dv.signal_post_ids if p in r.index]].mean() / len(r) * 100)
        out.append(row); print(row, flush=True)
    df = pd.DataFrame(out)
    df.to_csv(cfg["results_dir"] / "model_trial.csv", index=False)
    print(df.round(3).to_markdown(index=False))


def cmd_freeze(cfg, a):
    man = freeze.freeze(cfg, note=a.note or "")
    print(json.dumps(man, indent=1, ensure_ascii=False))


def _corpus(cfg, name):
    ev, dv = corpus.load_split(cfg)
    return ev if name == "eval" else dv


def cmd_score(cfg, a):
    c = _corpus(cfg, a.corpus)
    if c.name == "eval" and not a.post_hoc:
        ok, problems = freeze.check(cfg)
        if not ok:
            raise SystemExit("evaluation corpus is locked until artifacts are frozen and unchanged: " + "; ".join(problems))
    if a.s1_seeds:
        # post-hoc S1 variant with a different seed file; selector is labelled so it is never mixed with protocol runs
        cfg = json.loads(json.dumps(cfg, default=str)); cfg["results_dir"] = config.resolve(cfg["results_dir"])
        cfg["selectors"]["s1"]["seeds"] = a.s1_seeds
        frames = runner.run_s1(c, cfg, shuffled_seeds=[], include_d3=True)
        for f in frames:
            f["selector"] = f["selector"].str.replace("S1", f"S1-{a.label}", regex=False)
            runner.save_scores(f, c, cfg, f"{f.selector.iloc[0]}_{f.access_variant.iloc[0]}_{f.run_id.iloc[0]}")
            print("saved post-hoc", f.selector.iloc[0], f.access_variant.iloc[0])
        return
    sels = a.selectors.split(",")
    frames = []
    if "s0" in sels:
        frames += runner.run_s0(c, cfg)
    if "s1" in sels:
        frames += runner.run_s1(c, cfg, shuffled_seeds=[0, 1, 2] if c.name == "eval" else [0])
    if "s3open" in sels:
        frames += runner.run_s3_open(c, cfg, repeat=1 if a.repeat else 0)
    if "s3blind" in sels:
        frames += runner.run_s3_blind(c, cfg)
    if "s3com" in sels:
        frames += runner.run_s3_control(c, cfg)
    if "srand" in sels:
        frames += runner.run_srand(c, cfg)
    for f in frames:
        name = f"{f.selector.iloc[0]}_{f.access_variant.iloc[0]}_{f.run_id.iloc[0]}"
        p = runner.save_scores(f, c, cfg, name)
        print("saved", p, len(f))


def cmd_metrics(cfg, a):
    c = _corpus(cfg, a.corpus)
    per_seed, summ = report.compute_metrics(c, cfg)
    pd.set_option("display.width", 250)
    print(summ.round(2).to_string(index=False))


def cmd_report(cfg, a):
    c = _corpus(cfg, a.corpus)
    per_seed, summ = report.compute_metrics(c, cfg)
    crit = report.go_no_go(summ, c)
    agree = report.agreement(c, cfg)
    blind = report.blind_difference(summ)
    decisive = report.decisive_posts_check(c, cfg)
    report.curves(summ, cfg["results_dir"] / c.name / "curves.png", title=f"EP-SKEL {c.name}")
    ledger = cfg["results_dir"] / "raw" / "ledger.jsonl"
    cost = sum(json.loads(l).get("cost", 0) for l in ledger.read_text().splitlines() if l.strip()) if ledger.exists() else 0.0
    text = report.results_card(c, cfg, summ, crit, agree, blind, decisive, cost)
    print(text[:6000])


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("describe")
    p = sub.add_parser("build-lexicon"); p.add_argument("--model", default="openai/gpt-6-sol")
    sub.add_parser("leak-check")
    p = sub.add_parser("model-trial"); p.add_argument("--n", type=int, default=200)
    p = sub.add_parser("freeze"); p.add_argument("--note", default="")
    p = sub.add_parser("score"); p.add_argument("--corpus", default="dev"); p.add_argument("--selectors", default="s0,s1,srand"); p.add_argument("--repeat", action="store_true"); p.add_argument("--post-hoc", action="store_true"); p.add_argument("--s1-seeds", default=None); p.add_argument("--label", default="posthoc")
    p = sub.add_parser("metrics"); p.add_argument("--corpus", default="dev")
    p = sub.add_parser("report"); p.add_argument("--corpus", default="dev")
    a = ap.parse_args()
    cfg = config.load()
    {"describe": cmd_describe, "build-lexicon": cmd_build_lexicon, "leak-check": cmd_leak_check, "model-trial": cmd_model_trial,
     "freeze": cmd_freeze, "score": cmd_score, "metrics": cmd_metrics, "report": cmd_report}[a.cmd](cfg, a)


if __name__ == "__main__":
    main()
