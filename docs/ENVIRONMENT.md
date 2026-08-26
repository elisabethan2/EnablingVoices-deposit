# Environment and reproducibility notes

The pipeline runs in **two distinct environments**, pinned separately:

| | Inference environment | Analysis environment |
|---|---|---|
| Pins | `requirements-inference.txt` | `requirements-analysis.txt` |
| Where | UCloud GPU node (DeiC Interactive HPC) | CPU-only; no GPU, no model weights |
| Stages | Round 1 Llama screening, Round 1 Qwen cross-check, Round 2 Qwen screening, full-text extraction, seed-stability check, figure generation | Statistics recomputation (`code/08_validation_metrics/`) |
| Backs | the screening decisions, confidences and rationales in `data/screening/`, and `figures/` | `validation_metrics.xlsx` / `.json` — every statistic reported in Sections 3.2-3.5 |
| Version provenance | re-pinned June 2026; **not** the versions that produced the results | captured by `pip freeze` from an environment in which the script was re-run and verified |

`pandas`, `numpy` and `openpyxl` appear in both files at different versions. That
is intentional — they are two separate environments, not one stack split in half.

The distinction matters for what each environment can support. The reported
**screening decisions** were produced in the inference environment, whose exact
run-time versions are not recoverable (below); they are backed by the deposited
output files, not by a re-run. The reported **statistics** were produced in the
analysis environment, and those *have* been reproduced from the deposited inputs
(see "Verification run").

---

## Inference environment

### Hardware (February-March 2026 production runs)
- GPU: **Tesla V100-SXM2-32GB** (~31.7 GiB usable)
- Reservation: **u1-gpu-h-1** (1x), DeiC Interactive HPC (SDU/K8s), node nodeab-45
- Corpus assembly and some analysis notebooks ran on Kaggle; the LLM screening,
  validation, and extraction ran on UCloud.

### Software (February-March 2026 production runs)
- Application image: **UCloud JupyterLab 4.3.5**
- Python: **3.12** (confirmed; a current relaunch of the same image reports 3.12.12)
- Inference used Hugging Face `transformers` with `bitsandbytes` 4-bit quantisation.
  Neither vLLM nor llama.cpp was used at any stage.
- Dependencies were installed **at run time, unpinned**, from a notebook cell:
  `pip install transformers torch accelerate pypdf2 pandas openpyxl bitsandbytes -q`
  (PyMuPDF / scikit-learn likewise installed where used). The `-q` flag suppressed
  pip's version output, the install resolved to whatever was current on PyPI on
  2026-02-06, and the container was ephemeral.

### Why the exact original versions are not recoverable
The packages above were not pinned and not preinstalled in the image, so no
artefact records the resolved versions: the job logs were quiet, the notebook
cells captured no install output, and the container no longer exists. Relaunching
JupyterLab 4.3.5 today returns a refreshed base image: it reports a different set
of base package versions, no longer includes
transformers/bitsandbytes/accelerate/PyPDF2/PyMuPDF/scikit-learn at all, and the
same refreshed torch build appears on newer nodes -- so even the surviving base
versions are not confirmed identical to February. The exact February software
stack is
therefore not reconstructable. The **CUDA toolkit and driver versions were not
recorded either**, and are not inferable from the `+cu130` pin, which is a June
2026 build.

This is the concrete basis for the environment-sensitivity finding reported in the
paper (see below) and the reason the released code pins versions explicitly.

### Released code
`requirements-inference.txt` pins exact, tested versions to make the released code
reproducible going forward. These are **not** claimed to equal the (unrecoverable)
February versions; the authoritative record of the original screening results is
the deposited output files, not a re-run.

---

## Analysis environment

`code/08_validation_metrics/compute_review_statistics.py` recomputes every
screening and validation statistic reported in Sections 3.2-3.5 from the
deposited `.xlsx` outputs. It reads spreadsheets and writes spreadsheets: no GPU,
no model weights, no PDF handling, and no network access are involved. Its only
direct dependencies are `numpy`, `pandas` and `openpyxl`.

Because this stage is cheap and deterministic, its pins are not a reconstruction:
`requirements-analysis.txt` was produced by `pip freeze` on a clean virtual
environment in which the script was then actually run against the deposited
inputs and its output compared against the deposited results.

### Verification run

- **Date:** 2026-08-26
- **Environment:** clean `venv`, Python 3.12.3, CPU-only container
- **Installed:** `numpy`, `pandas`, `openpyxl` (unpinned); the resolved versions
  were frozen into `requirements-analysis.txt`, which is the authoritative record
  of them
- **Inputs:** the deposited copies under `data/screening/` —
  `master_comparison.xlsx` (sheet `All120Papers`),
  `model_comparison_report.xlsx` (sheet `All_Comparisons`),
  `enabling_voices_qwen_v3_20260312_230707.xlsx` (sheet `Screening`)
- **Result:** **all 68 metric values reproduced exactly.** A leaf-by-leaf
  comparison of the regenerated `validation_metrics.json` against the deposited
  copy found 68 metric leaves on both sides, no key present in one and absent in
  the other, and zero differing values. A cell-by-cell comparison of
  `validation_metrics.xlsx` across all three sheets (`Metrics`,
  `Confusion_matrices`, `Run_info`) compared 219 cells, of which only 4 differ —
  all in `Run_info`, and all expected: the run timestamp, the recorded pandas and
  numpy versions, and the input paths (the deposited copy records the original
  UCloud paths; the verification run used the repo-relative paths).

Reproduced values include the headline statistics:

| Statistic | Value |
|---|---|
| Subset composition | 9 consensus-include / 85 consensus-exclude / 26 disagree (n = 120) |
| Inter-annotator agreement | 78.3%, kappa = 0.285 |
| Llama vs human consensus | sens 0.778, spec 0.882, prec 0.412, acc 0.872, kappa 0.472 (TP/FP/TN/FN = 7/10/75/2) |
| Qwen R1 vs human consensus | sens 0.667, spec 0.988, prec 0.857, acc 0.957, kappa 0.727 (TP/FP/TN/FN = 6/1/84/3) |
| Llama vs Qwen R1 | 84.2% over all 120 (kappa 0.421); 82.9% valid-only (n = 111) |
| Retrospective vs final 6 | Llama 5/6 (+23 FP); Qwen R1 4/6 (+5 FP, 2 FN); Qwen R2 5/6 (+16 FP in-subset) |
| Qwen R2 split | 8 + 13 + 20 = 41 |
| Inclusion chain | 12 validated - 6 removed = 6 final |

All four of the script's internal integrity checks passed
(`subset_parts_sum_to_n`, `human_validated_is_12`, `qwenR2_split_sums_to_total`,
`twelve_minus_removed_is_six`).

### Scope of this verification, stated plainly

The verification environment is **not** the machine that generated the deposited
`validation_metrics.*` files on 2026-06-08. That run recorded Python 3.12.3,
pandas 3.0.2 and numpy 2.4.4 in its own output metadata; the verification run used
the same Python version but pandas 3.0.5 and numpy 2.5.2. The reported statistics
are therefore shown to be **stable across those library versions**, which is a
stronger claim than a bit-for-bit re-run on identical pins would have been, but it
is not a reconstruction of the original machine.

This verification covers the statistics recomputation only. It does **not**
re-derive the screening decisions those statistics are computed over: the script
reads the deposited model outputs as given. The screening decisions remain backed
by the deposited output files, for the reasons in "Why the exact original versions
are not recoverable".

---

## Seeds
- Annotator assignment: fixed seed 42 (reproducible).
- Model generation and the validation-subset draw: unseeded in the original runs.
  Released code sets explicit seeds for future runs; the subset membership is
  deposited regardless.
- The statistics recomputation involves no sampling or stochastic step, so no
  random seed applies.

## Environment sensitivity
A five-seed stability check found Round 1 include/exclude decisions identical
across seeds within one environment. Re-running identical code under a newer
software stack produced systematic divergence on borderline records, including
two records in the final included set. Screening decisions here are thus stable
to the random seed but sensitive to library versions. Reproduce with the pinned
versions in `requirements-inference.txt`; treat the deposited outputs as
authoritative.
(The comparison is confounded by time as well as environment and is reported as
most-likely environment drift.)

Note that this sensitivity is a property of the **inference** stage — quantised
generative decoding over extracted PDF text. The **analysis** stage shows the
opposite behaviour: as recorded above, it reproduced every metric exactly across
a pandas and numpy version change. The two environments are pinned separately
partly so that this distinction stays visible.
