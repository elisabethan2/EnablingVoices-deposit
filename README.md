# Enabling Voices — LLM-Assisted Screening Pipeline

Code, prompts, and derived data for the scoping review *"Enabling Voices:
AI-Assisted Communication Support for People with Dementia and Aphasia"* and its
methodological contribution on locally hosted, open-source LLM-assisted screening.

> Manuscript: [citation / DOI — to add on acceptance]
> This repository is the deposited code and data referenced by the paper's Data
> Availability Statement.

**This repository is the archived deposit accompanying the manuscript.** It is
published as a single commit representing the state of the work at deposit, and
is not a development repository: there are no feature branches and no
development history here. The working history — drafts, review iterations, and
intermediate states — is retained privately by the authors and is not part of
the archived record.

Document metadata has been removed uniformly from every workbook in this
deposit: author and last-modified-by fields, application and locale
identifiers, and the saved-folder path Excel records inside the file. This is
applied to all workbooks alike, so that neither the presence nor the absence of
metadata carries information about who prepared a given file. Cell contents,
sheet structure and every reported statistic are unaffected: re-running
`code/08_validation_metrics/compute_review_statistics.py` on these files
reproduces all 68 reported values exactly.

## What is and is not here

**Included:** all analysis code, the screening/extraction prompts, the model
screening decisions (with confidences and rationales), the anonymised human
annotations, and record-level corpus metadata (titles, DOIs, identifiers).

**Not included, by design:**
- **Full-text PDFs of screened records** — not redistributable for copyright
  reasons. Records are identified by DOI so they can be retrieved independently.
- **Raw human-annotation files carrying annotator names** — excluded for data
  protection (GDPR). Annotators appear only as `Annotator_1`–`Annotator_8`; the
  name key is held offline and is not in this repository.

## Repository structure

```
code/
  01_corpus_assembly/   RIS -> CSV parsing of the database export
  02_screening_round1/  Round 1 Llama 3.1 8B screening + JSON-recovery step
  03_validation/        validation-subset construction, annotator assignment,
                        model comparison, inter-rater + agreement analysis
  04_screening_round2/  Round 2 Qwen 2.5 7B screening
  05_extraction/        full-text extraction (documented; NOT used for results)
  06_stability/         seed-stability check
  07_figures/           figure generation
  08_validation_metrics/   validation-metrics recomputation
prompts/                Round 1, Round 2, and extraction prompts (verbatim)
data/
  corpus/               record metadata (no PDFs)
  screening/            model decisions, confidences, rationales, comparisons
  annotations/          anonymised human annotations + consensus
  stability/            seed-stability check output
  extraction/           error log for the trialled full-text extraction
docs/
  FILE_INVENTORY.md     every file mapped to its pipeline stage, run, and output
  METHODS_REFERENCE.md  stage-by-stage methods: model configs, environments,
                        preprocessing, and record counts
  ENVIRONMENT.md        hardware, software versions, and reproducibility notes
figures/                generated figures
requirements-inference.txt   GPU stack: screening, extraction, figures
requirements-analysis.txt    CPU stack: statistics recomputation
run_log.csv             one row per run: model, parameters, seed, date, I/O
```

## Pipeline

1. **Corpus assembly** — database export (RIS) parsed to a single CSV (470
   machine-readable of 478 records).
2. **Round 1 screening** — Llama 3.1 8B, high-recall first pass over 470 records.
   A separate post-processing step recovers records whose JSON output was
   malformed (status `success_recovered`).
3. **Validation** — a 120-record subset, double-annotated by eight annotators;
   inter-rater reliability and model–human agreement computed.
4. **Round 2 screening** — Qwen 2.5 7B, conservative cross-check over the pool.
5. **Adjudication** — PI review of disagreements; final inclusion by human
   adjudication, not model recall.
6. **Extraction** — full-text extraction was attempted but **not relied upon**;
   it is included to document its failure modes (see the paper, §3.6).

## Reproducing

1. Recreate the relevant environment: `requirements-inference.txt` for the GPU
   screening/extraction/figure stages, `requirements-analysis.txt` for the
   statistics recomputation in `code/08_validation_metrics/` (exact versions matter —
   see the note below).
2. Place the PDFs (retrieved via DOI) where the scripts expect them.
3. Run the stages in numbered order; parameters and I/O paths are in `run_log.csv`.

**Reproducibility notes.**
- *Seeds.* The annotator assignment used a fixed seed (42). The model-generation
  steps and the validation-subset draw in the original runs were **not** seeded,
  so those runs are not bit-for-bit reproducible; the released code sets explicit
  seeds for future runs. The exact subset membership is deposited regardless.
- *Environment sensitivity.* Screening decisions were stable across random seeds
  within one software environment, but re-running identical code under updated
  library versions produced systematic divergence on borderline records.
  Reproduce with the pinned versions in `requirements-inference.txt`; treat the
  deposited outputs as the authoritative record. This sensitivity is specific to
  the inference stage: the statistics recomputation reproduced every reported
  metric exactly across a pandas/numpy version change (see `docs/ENVIRONMENT.md`).

## Licence

This repository is dual-licensed:

- **Code** — MIT Licence (`LICENSE`). Applies to everything under `code/`, except
  the deposited output files `code/08_validation_metrics/validation_metrics.xlsx`
  and `validation_metrics.json`, which are data.
- **Data and documentation** — Creative Commons Attribution 4.0 International
  (`LICENSE-DATA.txt`). Applies to `data/`, `figures/`, `prompts/`, `docs/`,
  `README.md`, `run_log.csv`, and the deposited output files noted above.

Attribution should cite the associated publication; see `CITATION.cff`.

Note that the licences cover this repository's own contents. They do not extend
to the screened publications themselves, whose full texts are not redistributed
here (see "What is and is not here").

## Contact

Elisabeth Muth Andersen, Department of Culture and Language, University of
Southern Denmark, Odense, Denmark (corresponding author).

For access queries relating to this deposit: open-access@bib.sdu.dk
