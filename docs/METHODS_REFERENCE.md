# Methods reference

A stage-by-stage description of how the deposited data were produced: the model
configuration, computational environment, and text preprocessing behind each
pipeline stage, and the record counts that connect them.

This document is self-contained. Every value in it is traceable to a deposited
artefact — `run_log.csv`, `requirements-inference.txt`,
`requirements-analysis.txt`, or the released scripts under `code/` — and each
section names the files it draws on. Where a value was not recorded at run time
and cannot be recovered, that is stated rather than estimated; those cases are
collected in the final section.

Two values in the model table, marked *(model card)*, are properties of the
published model checkpoints rather than of these runs.

---

## Computational environments

The pipeline runs in two separate environments, pinned independently.

| | Inference environment | Analysis environment |
|---|---|---|
| Pins | `requirements-inference.txt` | `requirements-analysis.txt` |
| Hardware | UCloud GPU node (DeiC Interactive HPC) | CPU-only; no GPU, no model weights |
| Stages | Rounds 1 and 2 screening, full-text extraction, seed-stability check, figure generation | Statistics recomputation (`code/08_validation_metrics/`) |
| Produces | screening decisions, confidences and rationales in `data/screening/`; `figures/` | `validation_metrics.xlsx` / `.json` |

`pandas`, `numpy` and `openpyxl` appear in both files at different versions. That
is deliberate: these are two distinct environments, not one stack split in half.

The separation matters for what each environment can support. The screening
decisions were produced in the inference environment, whose exact run-time
library versions are not recoverable (see below); they are backed by the
deposited output files rather than by a re-run. The reported statistics were
produced in the analysis environment, and have been reproduced from the
deposited inputs — `docs/ENVIRONMENT.md` records that verification run in full.

### Hardware

One NVIDIA Tesla V100-SXM2-32GB (≈31.7 GiB usable), reservation `u1-gpu-h-1`,
node `nodeab-45`, DeiC Interactive HPC (SDU, Kubernetes). Corpus assembly and
part of the annotation analysis ran on Kaggle; all LLM screening, validation and
extraction ran on UCloud. The statistics recomputation ran on CPU.

### Software at run time (February–March 2026)

UCloud JupyterLab 4.3.5 image, Python 3.12. Inference used Hugging Face
`transformers` with `torch`, `bitsandbytes` and `accelerate`. PDF text extraction
used `PyPDF2` and `PyMuPDF`. Analysis used `pandas`, `numpy`, `openpyxl`,
`scikit-learn` and `matplotlib`. Neither vLLM nor llama.cpp was used at any
stage.

### Why the exact run-time versions are not recoverable

Dependencies in the production runs were installed unpinned at run time from a
notebook cell (`pip install … -q`). The `-q` flag suppressed pip's version
output, the install resolved to whatever was current on PyPI on the run date, and
the container was ephemeral. No artefact records the resolved versions: the job
logs were quiet, the notebook cells captured no install output, and the container
no longer exists.

**The exact February–March 2026 library versions, and the CUDA toolkit and driver
versions, are therefore not recoverable.** The released code pins exact, tested
versions instead, and those pins are what a reproduction should use. They are
*not* claimed to equal the versions that produced the deposited results, and the
CUDA version is not inferable from the `+cu130` build tag, which is a June 2026
artefact. The authoritative record of the original screening results is the
deposited output files.

This is also the concrete basis for the environment-sensitivity finding described
under "Seed-stability check" below.

**Version numbers are not reproduced in this document.** The authoritative record
is the requirements files themselves:

- `requirements-inference.txt` — the GPU stack, applying to Rounds 1 and 2
  screening, full-text extraction, the seed-stability check, and figure
  generation. Re-pinned in June 2026; see the caveat above.
- `requirements-analysis.txt` — the CPU stack, applying to the statistics
  recomputation only. Captured by `pip freeze` from a clean environment in which
  the script was then run against the deposited inputs and its output compared
  against the deposited results, rather than reconstructed after the fact.

`docs/ENVIRONMENT.md` records the provenance of each set and the verification run
in full.

---

## Model configurations

All four model-driven stages at a glance. Sources: `run_log.csv`, and the
configuration constants and `generate()` calls in the released scripts.

| | **Round 1 screening** | **Round 1 cross-check + Round 2 screening** | **Full-text extraction** *(not used for results)* | **Seed-stability check** |
|---|---|---|---|---|
| Checkpoint | `meta-llama/Llama-3.1-8B-Instruct` | `Qwen/Qwen2.5-7B-Instruct` | `meta-llama/Llama-3.1-8B-Instruct` | `meta-llama/Llama-3.1-8B-Instruct` |
| Quantisation | 4-bit NF4, double quantisation, compute dtype `float16` (bitsandbytes) | 4-bit NF4, double quantisation, compute dtype `bfloat16` | 4-bit NF4, double quantisation, compute dtype `float16` | as Round 1 |
| Decoding | sampling (`do_sample=True`) | sampling (`do_sample=True`) | greedy (`do_sample=False`) | sampling (`do_sample=True`) |
| Temperature | 0.1 | 0.1 | not applied (greedy decoding) | 0.1 |
| Top-*p* | 0.9 | 0.9 | not applied (greedy decoding) | 0.9 |
| Repetition penalty | 1.1 | 1.05 | 1.05 | 1.1 |
| Max input | 4,000 tokens (hard truncation) | 6,000 characters (≈1,500 tokens) | 8,000 tokens per chunk, 200-token overlap | 4,000 tokens |
| Max new tokens | 1,000 | 1,200 | 3,000 | 1,000 |
| Context window *(model card)* | 128,000 tokens | 32,768 tokens | 128,000 tokens | 128,000 tokens |
| Inference backend | Hugging Face `transformers` (`AutoModelForCausalLM.generate`), `device_map="auto"`, bitsandbytes 4-bit | same | same | same |
| Batch size | 1 (records processed sequentially) | 1 | 1 chunk at a time | 1 |
| Seed | unseeded | unseeded | unseeded | 1, 2, 3, 4, 5 (`transformers.set_seed`, one full pass per seed) |
| Run date | 2026-02-06 | 2026-02-06 (validation subset); 2026-03-12 (Round 2, full pool) | 2026-03-14 | 2026-06-05 |
| GPU | Tesla V100-SXM2-32GB | Tesla V100-SXM2-32GB | Tesla V100-SXM2-32GB | Tesla V100-SXM2-32GB |

Two points the table compresses:

- The **context window** row is the published capacity of each checkpoint, not a
  setting of these runs. Effective input was bounded by the truncation limits in
  the "Max input" row, which are far below those capacities.
- Records were processed **one at a time**, with a checkpoint written every 10
  records. No batching was used at any stage.

---

## Text preprocessing

PDF text extraction differs by stage, and the library and version are recorded
explicitly because extraction backend is a known source of variance in text
recovered from PDFs.

| Stage | Extraction path |
|---|---|
| Round 1 screening; seed-stability check | `PyPDF2` (`PdfReader`, per-page `extract_text()`) |
| Round 1 Qwen cross-check; Round 2 screening | embedded plain-text streams from the record container where present, falling back to `PyPDF2` |
| Full-text extraction | `PyMuPDF` (`fitz`) as primary extractor, `PyPDF2` as fallback |

Extracted text was then truncated before being passed to the model: to the first
**4,000 tokens** for Round 1 and the stability check, and to the first **6,000
characters (≈1,500 tokens)** for the Qwen passes. These are two different limits
expressed in two different units, and are not interchangeable.

The full-text extraction stage did not truncate. It instead ran a sliding window
over the whole article: chunks of up to 8,000 input tokens with a 200-token
overlap, where the per-chunk budget is 8,000 minus the prompt-template length,
floored at 500 tokens. Each chunk was parsed independently, with a
truncation-repair step that closes unterminated JSON.

The `PyPDF2` and `PyMuPDF` versions resolved at run time were not recorded, for
the reasons given under "Why the exact run-time versions are not recoverable".
The versions in `requirements-inference.txt` are those of the released code.

### JSON recovery

54 of the 470 Round 1 records returned syntactically malformed JSON — an unquoted
`unclear` literal in the decision field. `fix_json_failures.py` repairs the
literal and re-parses the stored model response **without re-querying the
model**; these records carry the status `success_recovered`. Both the pre-recovery
and post-recovery workbooks are deposited so the effect of this step is visible.

---

## Pipeline stages

### 1. Corpus assembly

`code/01_corpus_assembly/`, Kaggle, 2025-10-30. A database export (RIS) was
parsed into `data/corpus/corpus_metadata.csv`: 478 records of bibliographic
metadata only. Abstracts were removed for copyright reasons and full-text PDFs
are not deposited; records are identifiable by DOI. 470 of the 478 records had
machine-readable PDF text.

### 2. Round 1 screening — Llama 3.1 8B

`code/02_screening_round1/`, UCloud, 2026-02-06. A high-recall first pass over
the 470 records submitted to LLM screening, using
`prompts/round1_filtering_prompt.md`.

Outcome: 28 include, 408 exclude, 25 flagged for manual review, and 9 records
that yielded no usable text. Final record statuses are 407 `success`, 54
`success_recovered` and 9 `failed_text_extraction`, totalling 470. The 461
records with a valid Round 1 decision are the 470 submitted minus the 9
text-extraction failures.

Outputs: `enabling_voices_round1_V2_20260206_170842.xlsx` (pre-recovery) and
`…_170842_1.xlsx` (canonical, post-recovery), both under `data/screening/`.

### 3. Validation — human annotation and cross-model check

`code/03_validation/`, 2026-02.

A stratified 120-record subset was drawn: all 28 Llama includes, all 25
manual-review records, and 67 sampled excludes. The draw was unseeded, so it is
not reproducible from the code; subset membership is deposited instead, in
`data/screening/master_comparison.xlsx`.

The subset was double-annotated by eight annotators, 30 records each, so every
record carries two independent human decisions. Annotator assignment used a fixed
seed of 42 and is reproducible. Annotations are deposited as
`data/annotations/annotator_1.xlsx` … `annotator_8.xlsx`; annotators appear only
as `Annotator_1`–`Annotator_8` and the name key is held offline.

Human double annotation is the reference standard against which model screening
performance is measured. Two reference standards are used across the deposit and
are kept distinct: human consensus (annotator A == B) for the diagnostic metrics,
and the final included set for the descriptive retrospective comparison.

In parallel, Qwen 2.5 7B screened the same 120 records as a cross-model check
(`qwen_validation_20260206_222701.xlsx`), and `compare_models.py` produced
`model_comparison_report.xlsx` and `master_comparison.xlsx`.

### 4. Round 2 screening — Qwen 2.5 7B

`code/04_screening_round2/`, UCloud, 2026-03-12. A conservative pass over the
full 470-record pool using `prompts/round2_qwen_prompt.md`, following criteria
refinement informed by the human–model disagreement analysis.

Outcome: 41 includes (38 Tier A, 3 Tier B), 278 flagged, 151 exclude. Of the 41
includes, 8 were also human includes, 13 were also human excludes, and 20 were
new records for adjudication. Output:
`enabling_voices_qwen_v3_20260312_230707.xlsx`.

### 5. Adjudication and final inclusion

Final inclusion was decided by human adjudication, not by model recall. 12
records were validated as includes in the subset stage — 9 by annotator
consensus, 2 by tiebreaker, 1 by adjudication — and full-text review reduced
these to 6.

`data/screening/final_inclusion_record.xlsx` is the authoritative record: the 6
included studies, plus the 9 records excluded at full text with reasons. It also
documents two author-name corrections applied after LLM-truncated initials were
identified (COV5183 → Favela; COV5169 → Mowri).

### 6. Full-text extraction — documented, not used for results

`code/05_extraction/`, UCloud, 2026-03-14. Full-text extraction was attempted but
**not relied upon for any reported result**. It is deposited to document its
failure modes. The deposited output workbook reflects the pre-adjudication
candidate set rather than the final 6, and should be read accordingly.

### 7. Seed-stability check

`code/06_stability/`, UCloud, 2026-06-05. Round 1 was re-run over the 120-record
subset five times, one fixed seed per pass (1–5) with a fixed record order.

Include/exclude decisions were identical across all five seeds within a single
software environment. Re-running the same code under a newer software stack,
however, produced systematic divergence on borderline records, including two
records in the final included set. Screening decisions are therefore stable to
the random seed but sensitive to library versions — which is why the inference
environment is pinned explicitly and why the deposited outputs, not a re-run, are
treated as authoritative. The comparison is confounded by elapsed time as well as
environment, and is reported as most-likely environment drift.

This sensitivity is a property of the inference stage: quantised generative
decoding over text recovered from PDFs. The analysis stage behaves differently —
see below.

### 8. Figures

`code/07_figures/`, 2026-06-09. `enabling_voices_figures_RSM.py` generates
`Fig1`–`Fig4` as 600-dpi PNG plus vector PDF. Rendering is deterministic and no
seed applies. `figures/README.md` maps each figure to its generating function and
data inputs.

Figure 1 plots the 461 records that received a valid Round 1 decision. Figure 3
is a flow diagram whose values are encoded as static constants in the script.

### 9. Statistics recomputation

`code/08_validation_metrics/`, CPU, 2026-06-08. `compute_review_statistics.py`
recomputes every reported screening and validation statistic from the deposited
screening and annotation outputs, so all reported figures trace to a single
computation. It reads three deposited workbooks and writes
`validation_metrics.xlsx` and `validation_metrics.json`.

All operations are deterministic counts and agreement statistics. No sampling or
stochastic step is involved, so no random seed applies.

Re-running this script on the deposited inputs in a clean environment reproduced
all 68 metric values exactly, across a pandas and numpy version change — the
opposite behaviour to the inference stage. `docs/ENVIRONMENT.md` records that
verification run, its scope, and the headline values reproduced.

Note that the script's output directory defaults to the working directory, so it
writes beside the deposited copies when run from the repository root.

---

## Record counts through the pipeline

| Stage | Count |
|---|---|
| Identified via database searching | 7,147 |
| Duplicates removed | −2,495 |
| Screened at title/abstract | 4,652 |
| Excluded at title/abstract | −4,174 |
| Assessed for eligibility | 478 |
| No retrievable PDF (reviewed manually, all excluded) | −8 |
| Submitted to LLM screening | 470 |
| Text-extraction failures (human-reviewed, all excluded) | −9 |
| Valid Round 1 decision | 461 (28 include, 408 exclude, 25 manual review) |
| Stratified validation subset | 120 (28 + 25 + 67 sampled excludes) |
| Included after full-text adjudication | 6 |

Database sources for the 7,147: Scopus, ComDisDome, LLBA and MLA combined
(2,113); Web of Science (1,780); MEDLINE (1,298); PsycINFO (543); CINAHL (488);
IEEE Xplore (374); ACM Digital Library (263); Google Scholar (200); Sociological
Abstracts (88).

---

## Values not recorded in the deposit

| Value | Status |
|---|---|
| Exact library versions used in the February–March 2026 production runs | Not recoverable. Installed unpinned; `-q` suppressed pip output; the container was ephemeral. |
| CUDA toolkit and driver versions at run time | Not recorded. Not inferable from the `+cu130` build tag, which is a June 2026 artefact. |
| PDF-extraction library versions at run time | Not recorded. The versions in `requirements-inference.txt` are pins of the released code, not the versions used. |
| Identification-stage counts (7,147 / 2,495 / 4,652 / 4,174) | Held as static constants in the figure script and sourced from the reference-manager log; no deposited export backs them, unlike the 478 → 470 → 461 → 120 → 6 stages. |
| Wall-clock runtime and throughput per stage | Not recorded. |
| Validation-subset draw | Unseeded and not reproducible from code; membership is deposited in `master_comparison.xlsx` instead. |
| Model generation seeds (Rounds 1 and 2, extraction) | Unseeded in the original runs. The released code sets explicit seeds for future runs. |
