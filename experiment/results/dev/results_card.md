# EP-SKEL results card: dev corpus

Posts 622, authors 32, target arcs 2 (1 concentrated, 1 distributed), decoys 0, signal posts 6, bystander authors 30.
Budgets [0.01, 0.05, 0.2]; tie seeds [0, 1, 2]; aggregation {'kind': 'top_k_sum', 'k': 3}; S3-open `deepseek/deepseek-v4.1-flash`, S3-com `anthropic/claude-sonnet-5.5`, S1 `qwen/qwen3-embedding-8b`. Scoring cost $13.56.

## Measurement points (means over tie seeds; absolute numbers)

| selector     | access_variant   | budget   |   n_retained |   detected |   detected_min |   detected_max |   conc |   dist |   detected_loose |   decoy_hits |   bystanders |    bpd |   profile_depth |   review_load |   signal_posts |
|:-------------|:-----------------|:---------|-------------:|-----------:|---------------:|---------------:|-------:|-------:|-----------------:|-------------:|-------------:|-------:|----------------:|--------------:|---------------:|
| S-rand       | D0               | 1 %      |            6 |       0    |              0 |              0 |      0 |   0    |              0   |            0 |         5.4  | nan    |            1.12 |      nan      |           0    |
| S-rand       | D0               | 5 %      |           31 |       0.2  |              0 |              1 |      0 |   0.2  |              0.8 |            0 |        18.2  |  91    |            1.64 |       31      |           0.2  |
| S-rand       | D0               | 20 %     |          124 |       0.6  |              0 |              1 |      0 |   0.6  |              1.4 |            0 |        28.4  |  47.33 |            4.23 |      124      |           0.6  |
| S0-sub       | D0               | 1 %      |            6 |       1    |              1 |              1 |      1 |   0    |              1   |            0 |         4.67 |   4.67 |            1.08 |        6      |           1    |
| S0-sub       | D0               | 5 %      |           31 |       1.67 |              1 |              2 |      1 |   0.67 |              2   |            0 |        19    |  11.4  |            1.48 |       20.6667 |           1.67 |
| S0-sub       | D0               | 20 %     |          124 |       2    |              2 |              2 |      1 |   1    |              2   |            0 |        30    |  15    |            3.88 |       62      |           2    |
| S0-sub       | D3-agg           | 1 %      |            6 |       1    |              1 |              1 |      1 |   0    |              1   |            0 |         1    |   1    |            2    |        6      |           1    |
| S0-sub       | D3-agg           | 5 %      |           31 |       1    |              1 |              1 |      1 |   0    |              1   |            0 |         2.67 |   2.67 |           10.11 |       31      |           1    |
| S0-sub       | D3-agg           | 20 %     |          124 |       1    |              1 |              1 |      1 |   0    |              1   |            0 |        13.33 |  13.33 |            8.94 |      124      |           1    |
| S0-veto      | D0               | 1 %      |            6 |       1    |              1 |              1 |      1 |   0    |              1   |            0 |         4.67 |   4.67 |            1.08 |        6      |           1    |
| S0-veto      | D0               | 5 %      |           31 |       1.67 |              1 |              2 |      1 |   0.67 |              2   |            0 |        19    |  11.4  |            1.48 |       20.6667 |           1.67 |
| S0-veto      | D0               | 20 %     |          124 |       2    |              2 |              2 |      1 |   1    |              2   |            0 |        30    |  15    |            3.88 |       62      |           2    |
| S0-veto      | D3-agg           | 1 %      |            6 |       1    |              1 |              1 |      1 |   0    |              1   |            0 |         1    |   1    |            2    |        6      |           1    |
| S0-veto      | D3-agg           | 5 %      |           31 |       1    |              1 |              1 |      1 |   0    |              1   |            0 |         2.67 |   2.67 |           10.11 |       31      |           1    |
| S0-veto      | D3-agg           | 20 %     |          124 |       1    |              1 |              1 |      1 |   0    |              1   |            0 |        13    |  13    |            9.15 |      124      |           1    |
| S1           | D0               | 1 %      |            6 |       0    |              0 |              0 |      0 |   0    |              0   |            0 |         6    | nan    |            1    |      nan      |           0    |
| S1           | D0               | 5 %      |           31 |       1    |              1 |              1 |      0 |   1    |              1   |            0 |        15    |  15    |            2    |       31      |           1    |
| S1           | D0               | 20 %     |          124 |       1    |              1 |              1 |      0 |   1    |              1   |            0 |        25    |  25    |            4.92 |      124      |           1    |
| S1           | D3-agg           | 1 %      |            6 |       0    |              0 |              0 |      0 |   0    |              0   |            0 |         2    | nan    |            3    |      nan      |           0    |
| S1           | D3-agg           | 5 %      |           31 |       0    |              0 |              0 |      0 |   0    |              0   |            0 |         5    | nan    |            6.2  |      nan      |           0    |
| S1           | D3-agg           | 20 %     |          124 |       0    |              0 |              0 |      0 |   0    |              0   |            0 |        11    | nan    |           11.27 |      nan      |           0    |
| S1           | D3-txt           | 1 %      |            6 |       0    |              0 |              0 |      0 |   0    |              0   |            0 |         5    | nan    |            1.2  |      nan      |           0    |
| S1           | D3-txt           | 5 %      |           31 |       0    |              0 |              0 |      0 |   0    |              0   |            0 |        13    | nan    |            2.38 |      nan      |           0    |
| S1           | D3-txt           | 20 %     |          124 |       0    |              0 |              0 |      0 |   0    |              0   |            0 |        20    | nan    |            6.2  |      nan      |           0    |
| S1           | D3-vec           | 1 %      |            6 |       0    |              0 |              0 |      0 |   0    |              0   |            0 |         6    | nan    |            1    |      nan      |           0    |
| S1           | D3-vec           | 5 %      |           31 |       0    |              0 |              0 |      0 |   0    |              0   |            0 |        14    | nan    |            2.21 |      nan      |           0    |
| S1           | D3-vec           | 20 %     |          124 |       0    |              0 |              0 |      0 |   0    |              0   |            0 |        25    | nan    |            4.96 |      nan      |           0    |
| S1-shuffled0 | D0               | 1 %      |            6 |       0    |              0 |              0 |      0 |   0    |              1   |            0 |         4    | nan    |            1.25 |      nan      |           0    |
| S1-shuffled0 | D0               | 5 %      |           31 |       1    |              1 |              1 |      0 |   1    |              1   |            0 |        15    |  15    |            1.87 |       31      |           1    |
| S1-shuffled0 | D0               | 20 %     |          124 |       1    |              1 |              1 |      0 |   1    |              1   |            0 |        27    |  27    |            4.33 |      124      |           3    |
| S3-open      | D0               | 1 %      |            6 |       1    |              1 |              1 |      1 |   0    |              1   |            0 |         5    |   5    |            1    |        6      |           1    |
| S3-open      | D0               | 5 %      |           31 |       2    |              2 |              2 |      1 |   1    |              2   |            0 |        12    |   6    |            2.33 |       15.5    |           3    |
| S3-open      | D0               | 20 %     |          124 |       2    |              2 |              2 |      1 |   1    |              2   |            0 |        23    |  11.5  |            5    |       62      |           6    |
| S3-open      | D3-agg           | 1 %      |            6 |       1    |              1 |              1 |      1 |   0    |              1   |            0 |         1    |   1    |            1    |        6      |           1    |
| S3-open      | D3-agg           | 5 %      |           31 |       1    |              1 |              1 |      1 |   0    |              1   |            0 |         1    |   1    |           26    |       31      |           1    |
| S3-open      | D3-agg           | 20 %     |          124 |       1    |              1 |              1 |      1 |   0    |              1   |            0 |         9    |   9    |           13.22 |      124      |           1    |
| S3-open      | D3-nat           | 1 %      |            6 |       2    |              2 |              2 |      1 |   1    |              2   |            0 |         3    |   1.5  |            1.33 |        3      |           2    |
| S3-open      | D3-nat           | 5 %      |           31 |       2    |              2 |              2 |      1 |   1    |              2   |            0 |        10    |   5    |            2.6  |       15.5    |           4    |
| S3-open      | D3-nat           | 20 %     |          124 |       2    |              2 |              2 |      1 |   1    |              2   |            0 |        21.67 |  10.83 |            5.13 |       62      |           5    |

## Go / no-go criteria (plan section 19)

|   id | criterion                                                                   |   value | pass   |
|-----:|:----------------------------------------------------------------------------|--------:|:-------|
|    1 | at least one selector detects >= 6/10 arcs in D3 at 20 %                    |     2   | False  |
|    2 | at most 1/1 distributed arcs detected in D0 at 5 % (max over selectors)     |     1   | True   |
|    3 | at least 3/1 concentrated arcs detected by S0 in D0 at 20 %                 |     1   | False  |
|    4 | S-rand detects at most 1 arc at 20 %                                        |     0.6 | True   |
|    5 | for at least one selector, D3 - D0 for distributed arcs >= 3 arcs (at 20 %) |     0   | False  |
|    6 | duplicate_rate below the dev-corpus threshold                               |   nan   |        |

## S3 minus S3' (value of the explicit signal list)

(not run)

## Decision-based view (KEEP_FOR_REVIEW only, budget-independent)

| selector   | access_variant   |   n_scored |   n_keep |   arcs_keep_strict |   arcs_keep_loose |   dist_keep |   conc_keep |   decoy_keep |   bystander_authors_keep |   bystander_posts_keep |   hardneg_keep | detected_arcs   |
|:-----------|:-----------------|-----------:|---------:|-------------------:|------------------:|------------:|------------:|-------------:|-------------------------:|-----------------------:|---------------:|:----------------|
| S3-open    | D0               |        622 |        2 |                  1 |                 1 |           0 |           1 |            0 |                        1 |                      1 |              1 | TA-05           |
| S3-open    | D3-nat           |        622 |        4 |                  2 |                 2 |           1 |           1 |            0 |                        2 |                      2 |              2 | TA-05|TB-09     |

## Determinism, control model, declared vs internal score

```json
{
 "declared_vs_internal_D0": {
  "n": 621,
  "spearman": 0.5305772310809369,
  "logprob_available_share": 0.9983922829581994
 },
 "declared_vs_internal_D3-nat": {
  "n": 622,
  "spearman": 0.42527581405384424,
  "logprob_available_share": 1.0
 }
}
```

## Decisive posts named by S3-open in D3-nat vs the PI's signal posts

```json
{
 "n_signal_posts_kept": 2,
 "named_a_signal_post": 2,
 "by_arc": {
  "TA-05": [
   [
    "P00019"
   ]
  ],
  "TB-09": [
   [
    "P00606",
    "P00608",
    "P00609"
   ]
  ]
 }
}
```
