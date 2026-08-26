# File inventory

Maps each deposited artefact to its pipeline stage and the output it produces.
Run parameters (model, quantisation, seed, dates, I/O) are in `run_log.csv`.

## Code

| File | Stage / role |
|---|---|
| `code/01_corpus_assembly/ristocsvenablingvoices478-301025.ipynb` | RIS → CSV corpus assembly (Kaggle) |
| `code/02_screening_round1/enabling_voices_round1.py` | Round 1 Llama 3.1 8B high-recall screening |
| `code/02_screening_round1/fix_json_failures.py` | Round 1 JSON recovery (`status: success_recovered`) |
| `code/03_validation/enabling_voices_round1_filtering_v2.ipynb` | Validation-subset construction + κ / accuracy |
| `code/03_validation/generate_annotation_files.py` | Annotator assignment (seed 42) |
| `code/03_validation/compare_models.py` | Llama vs Qwen vs human comparison |
| `code/03_validation/firstanalysisofannotateddata385.ipynb` | Annotation analysis |
| `code/04_screening_round2/enabling_voices_qwen_screening_v3.py` | Round 1 Qwen validation + Round 2 Qwen 2.5 7B screening |
| `code/05_extraction/enabling_voices_extraction_fulltext.py` | Full-text extraction, **as run** (documented only; not used for results). `INCLUDED_PAPERS` holds the pre-adjudication candidate set of 10 — the provenance record of the 2026-03-14 run |
| `code/05_extraction/enabling_voices_extraction_fulltext_final6.py` | The same script with `INCLUDED_PAPERS` corrected to the final 6; not run |
| `code/06_stability/stability_check_round1.py` | Seed-stability check |
| `code/07_figures/enabling_voices_figures_RSM.py` | Figure generation (`Fig1`–`Fig4`); see `figures/README.md` for the function and data inputs behind each |

## Prompts

| File | Stage |
|---|---|
| `prompts/round1_filtering_prompt.md` | Round 1 Llama filtering prompt |
| `prompts/round2_qwen_prompt.md` | Round 1 Qwen validation + Round 2 screening prompt |
| `prompts/extraction_prompt.md` | Full-text extraction prompt (system + user template) |

## Data

| File | Contents |
|---|---|
| `data/corpus/corpus_metadata.csv` | 478 records, bibliographic metadata only (no abstracts, no PDFs; identify by DOI) |
| `data/screening/enabling_voices_round1_V2_20260206_170842.xlsx` | Round 1 Llama output, pre-recovery |
| `data/screening/enabling_voices_round1_V2_20260206_170842_1.xlsx` | Round 1 Llama output, canonical post-recovery |
| `data/screening/qwen_validation_20260206_222701.xlsx` | Qwen 2.5 7B cross-check on the 120-record subset |
| `data/screening/enabling_voices_qwen_v3_20260312_230707.xlsx` | Round 2 Qwen conservative full-pool pass |
| `data/screening/validation_sample.xlsx` | The 120-record stratified subset **as drawn**, before annotation: full Llama output, the blinded annotator sheet, and the four stratum sheets (28 / 58 / 25 / 9) |
| `data/screening/master_comparison.xlsx` | 120-record subset: both human annotations (anonymised) + Llama + Qwen |
| `data/stability/stability_round1_20260605_222533.xlsx` | Seed-stability check: Summary, PerRun (5 seeds), PerPaper (120), Raw_paper_x_seed (600 observations) |
| `data/screening/model_comparison_report.xlsx` | Llama-vs-Qwen agreement summary |
| `data/screening/adjudication_needed.xlsx` | Records flagged for PI adjudication (annotations anonymised) |
| `data/screening/inclusion_candidate_pool.xlsx` | 36-record include-candidate / adjudication pool |
| `data/screening/final_inclusion_record.xlsx` | Authoritative final record: 6 included + 9 full-text exclusions |
| `data/screening/enabling_voices_extraction_fulltextWholePaper_20260314_192132.xlsx` | Full-text extraction output (documents failure modes; not used for results) |
| `data/annotations/annotator_1.xlsx` … `annotator_8.xlsx` | Anonymised human annotations (`Annotator_1`–`Annotator_8`); name key held offline |
| `data/stability/README.md` | How to read the seed-stability output |
| `data/extraction/extraction_error_log.md` | Errors made by the trialled full-text extraction, per record and field |
| `data/extraction/extraction_errors.csv` | The same error log in tabular form |

Full-text PDFs of screened records and raw, name-bearing annotation files are not
included, by design (copyright and GDPR respectively); see the top-level `README.md`.

## Docs

| File | Contents |
|---|---|
| `docs/FILE_INVENTORY.md` | This inventory |
| `docs/METHODS_REFERENCE.md` | Stage-by-stage methods: model configurations, environments, preprocessing, record counts |
| `docs/ENVIRONMENT.md` | Hardware, software versions, and reproducibility notes |
| `requirements-inference.txt` | Pinned dependency versions for the GPU inference stack (screening, extraction, figures) |
| `requirements-analysis.txt` | Pinned dependency versions for the CPU analysis stack (statistics recomputation) |
| `run_log.csv` | One row per run: model, parameters, seed, date, and I/O |
