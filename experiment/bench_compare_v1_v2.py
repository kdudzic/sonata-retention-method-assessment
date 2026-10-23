"""Side-by-side of the v1-id run (archive) and the v2 run on the same measurement points. Usage: uv run python bench_compare_v1_v2.py"""
import pandas as pd
pd.set_option("display.width", 250)
a = pd.read_csv("results/archive_v1_ids/eval/metrics_summary.csv"); b = pd.read_csv("results/eval/metrics_summary.csv")
k = ["selector", "access_variant", "budget"]
m = a.merge(b, on=k, suffixes=("_v1", "_v2"))
cols = ["detected", "dist", "conc", "bystanders", "decoy_hits"]
out = m[k + [f"{c}_{v}" for c in cols for v in ("v1", "v2")]]
out["budget"] = (out.budget * 100).round().astype(int)
print(out.round(2).to_markdown(index=False))
