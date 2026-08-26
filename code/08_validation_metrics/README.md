# Validation metrics (`code/08_validation_metrics/`)

`compute_review_statistics.py` recomputes every screening and validation statistic
reported in Sections 3.2–3.5 from the deposited screening and annotation outputs, so
all reported figures trace to a single computation.

## Inputs

The script reads three files (paths set in the `CONFIGURATION` block at the top):

| Role | File / sheet |
|------|--------------|
| Annotator-level 120-paper subset (annotator A/B, Llama, Qwen R1) | `master_comparison.xlsx`, sheet `All120Papers` |
| Llama vs Qwen R1 comparison report | `model_comparison_report.xlsx`, sheet `All_Comparisons` |
| Qwen Round 2, full 470-record run | `enabling_voices_qwen_v3_20260312_230707.xlsx`, sheet `Screening` |

The paths in the script point to the UCloud run locations. **On a clone of this
repository, edit the `CONFIGURATION` block to point at the deposited copies** (e.g. under
`data/screening/`). All three input files must be deposited for the script to be re-runnable.

The final included set (N=6) and the four final-narrowing exclusions are documented
constants in the script; their provenance is `enabling_voices_master_inclusion.xlsx`
(Master Inclusion Tracker) and Section 3.5. That tracker is deposited separately and is
not read by this script.

## Outputs

- `validation_metrics.xlsx` — `Metrics`, `Confusion_matrices`, and `Run_info` sheets
- `validation_metrics.json` — the same content plus run metadata and integrity checks

The deposited copies of both files sit in this directory and were generated from the
input files above. Re-running the script regenerates the metrics identically; the
`Run_info` block will differ, because it records the run's own timestamp, library
versions, and input paths.

**The deposited copies are the provenance record of the original run and should not be
replaced.** Their `Run_info` reports the 2026-06-08 run — the timestamp, the library
versions in use then, and the UCloud input paths — none of which a later re-run can
reconstruct.

## Run

From the repository root (input paths are repo-relative):

```bash
python compute_review_statistics.py
```

Outputs go to `code/08_validation_metrics/outputs/`, a separate directory that is
gitignored. The deposited copies are left alone.

The script **refuses to overwrite an existing `validation_metrics.xlsx` or `.json`**
and exits non-zero, naming the files it declined to touch. The check runs before any
computation, so a refusal never leaves one output rewritten and the other stale.

```bash
python compute_review_statistics.py --output-dir DIR   # write somewhere else
python compute_review_statistics.py --overwrite        # deliberately replace outputs
```

`--overwrite` also lifts the guard on the deposited copies, so use it only when
replacing them is genuinely what you intend.

## Notes

- **Determinism:** counts and agreement statistics only; no sampling or stochastic step, so
  no random seed applies.
- **Two reference standards, kept distinct:** human consensus (annotator A==B) for the
  diagnostic metrics (sensitivity/specificity/precision/kappa), and the final included set
  (N=6) for the descriptive, post-hoc retrospective comparison. They are not interchangeable.
- **Caveat on the diagnostic metrics:** they rest on 9 positive cases in an include-enriched
  subset, so the sensitivity and precision estimates are imprecise and are not
  corpus-representative prevalence estimates.
- **Environment:** CPU-only; pins are in the repository `requirements-analysis.txt`
  (`numpy`, `pandas`, `openpyxl`; no GPU, model weights, or PDF handling involved).
  The script records its Python, pandas, and numpy versions in the JSON metadata and
  the `Run_info` sheet.
- **Verified:** re-running this script on the deposited inputs on 2026-08-26 reproduced
  all 68 reported metric values exactly; the only differences in the outputs were the
  run timestamp, the recorded library versions, and the input paths. See
  `docs/ENVIRONMENT.md`, "Verification run".
