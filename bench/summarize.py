"""Build markdown comparison tables from stage A / B result JSONs. Usage: uv run python bench/summarize.py"""
import json, glob, sys
import pandas as pd
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 60)
def table(rows, cols, sort=None):
    df = pd.DataFrame(rows)
    cols = [c for c in cols if c in df.columns]
    df = df[cols]
    if sort and sort in df.columns: df = df.sort_values(sort)
    return df
A_COLS = ["model", "cost_usd", "refusal_arc", "refusal_hn", "arc_brief_refusal_rate", "arc_brief_sanitised_rate", "arc_brief_full_rate",
          "arc_brief_profile_match", "arc_brief_keep_leak", "arc_brief_keep_miss", "hn_brief_full_rate", "hn_brief_profile_match",
          "judge_auc", "judge_p_ai_mean", "judge_polish_mean", "det_auc_char", "det_auc_word",
          "sem_mean_cos", "sem_near_dup_rate", "sem_vendi_norm", "lex_compression_ratio", "lex_self_rep4", "lex_self_bleu4", "lex_distinct2",
          "surf_len_mean", "surf_first_lower", "surf_ends_no_punct", "surf_em_dash", "surf_ellipsis", "surf_ai_ism_per_post",
          "persona_consistency", "persona_tic_overuse", "persona_repetitive", "persona_natural", "arc_brief_natural", "hn_brief_natural"]
B_COLS = ["model", "method", "n", "cost_usd", "calls", "judge_auc", "judge_p_ai_mean", "judge_polish_mean", "det_auc_char", "det_auc_word",
          "sem_mean_cos", "sem_near_dup_rate", "sem_vendi_norm", "lex_compression_ratio", "lex_self_rep4", "lex_self_bleu4", "lex_distinct2",
          "surf_len_mean", "surf_len_std", "surf_first_lower", "surf_ends_no_punct", "surf_ai_ism_per_post",
          "persona_consistency", "persona_tic_overuse", "persona_repetitive", "persona_natural"]
for f in sorted(glob.glob("bench/stageA_results__*.json")):
    rows = json.load(open(f)); print("\n##", f); df = table(rows, A_COLS)
    print(df.round(3).to_markdown(index=False))
    ref = {k.replace("ref_", ""): v for k, v in rows[0].items() if k.startswith("ref_surf_") or k.startswith("ref_lex_") or k.startswith("ref_sem_")}
    print("\nreference (length-matched real tweets):", {k: round(v, 3) for k, v in ref.items() if isinstance(v, float)})
for f in sorted(glob.glob("bench/stageA_natural__*.json")):
    rows = json.load(open(f)); print("\n##", f); print(table(rows, ["model", "judge_auc", "judge_p_ai_mean", "judge_p_ai_ref_mean", "judge_polish_mean"]).round(3).to_markdown(index=False))
for f in sorted(glob.glob("bench/stageB_results__*.json")):
    rows = json.load(open(f)); print("\n##", f); print(table(rows, B_COLS).round(3).to_markdown(index=False))
