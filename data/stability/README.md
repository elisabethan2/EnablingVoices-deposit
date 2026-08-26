# Seed-stability check

Output of `code/06_stability/stability_check_round1.py`, run 2026-06-05 on the
UCloud GPU node. The Round 1 Llama 3.1 8B screening prompt was run five times
over the 120-record validation subset — one fixed seed per full pass (seeds
1–5), fixed record order — to test whether screening decisions depend on the
random seed. Round 1 sampled at temperature 0.1 with top-*p* 0.9, so repeated
runs are not deterministic by construction.

`stability_round1_20260605_222533.xlsx`

| Sheet | Contents |
|---|---|
| `Summary` | Headline counts: papers, seeds, papers stable across all runs, percentage stable, papers flipping at least once, mean pairwise agreement across runs |
| `PerRun` | One row per seed: counts of INCLUDE, EXCLUDE and UNCLEAR decisions |
| `PerPaper` | One row per record (120): decision counts across the five runs, a `stable` flag, the majority decision, and mean/SD of the model's confidence score |
| `Raw_paper_x_seed` | One row per record × seed (600): the decision, confidence, and processing status for every individual observation |

## Reading the results

`Summary` reports **109 of 120 records (90.8%) stable across all five seeds**, with
11 flipping at least once. That headline understates decision stability, because
of how `UNCLEAR` is recorded.

`UNCLEAR` is not a screening decision. It is the placeholder written whenever a
run produced no usable decision, and it occurs only alongside a failed status:

| Decision | Status | Observations |
|---|---|---|
| `EXCLUDE` | `success` | 429 |
| `INCLUDE` | `success` | 76 |
| `UNCLEAR` | `failed_json_extraction` | 50 |
| `UNCLEAR` | `failed_text_extraction` | 45 |

No `INCLUDE` or `EXCLUDE` decision is ever recorded with a failed status, and no
`UNCLEAR` is ever recorded with a successful one.

All 11 unstable records flip between a decision and `UNCLEAR` — never between
`INCLUDE` and `EXCLUDE`. **Restricted to the 505 observations that produced a
parseable response, no record carries two different decisions across seeds.**

The 120 records break down as:

| Category | Count |
|---|---|
| Stable `EXCLUDE` across all five seeds | 80 |
| Stable `INCLUDE` across all five seeds | 15 |
| Stable `UNCLEAR` — text-extraction failure in all five seeds | 9 |
| Stable `UNCLEAR` — JSON-parse failure in all five seeds | 5 |
| Flips between a decision and `UNCLEAR` | 11 |

The 9 permanent text-extraction failures are the same 9 records that failed in
the February production run (`_processing_status = failed_text_extraction` in
`data/screening/validation_sample.xlsx`).

So the seed affects **whether the model returns parseable output**, not **which
decision it returns**. The 50 JSON-parse failures spread over 16 records are
genuinely seed-dependent; the decisions themselves are not.

## Relationship to the February production run

This check ran in June 2026 under a newer software stack than the February
production screening. It is not a reproduction of that run and its totals differ
from it: `PerRun` shows 15–16 includes per seed across the subset, against the
28 Llama includes recorded for the same 120 records in February
(`data/screening/master_comparison.xlsx`). The February run also produced no
JSON-parse failures that survived recovery, whereas this one shows 50.

That divergence is the environment-sensitivity finding described in
`docs/ENVIRONMENT.md` and `docs/METHODS_REFERENCE.md`: screening decisions here
are stable to the random seed but sensitive to the dependency environment. The
deposited February outputs, not this re-run, are the authoritative record of the
reported results.
