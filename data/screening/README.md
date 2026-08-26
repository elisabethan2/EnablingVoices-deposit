# Screening outputs

Annotator identities are anonymised throughout (`Annotator_1`–`Annotator_8`);
the name key is held offline and is not in this repository.

## Round 1 (Llama 3.1 8B)
- `enabling_voices_round1_V2_20260206_170842_1.xlsx` — **canonical, post-recovery**
  output (status: success 407 / success_recovered 54 / failed_text_extraction 9).
  Per-record decision, confidence, rationale, and short key quote.
- `enabling_voices_round1_V2_20260206_170842.xlsx` — the **pre-recovery** version of
  the same run (before `fix_json_failures.py`), kept to show the recovery step's effect.

## Validation (120-record subset)
- `validation_sample.xlsx` — **the subset as drawn**, before any annotation. The
  stratified sample of 120 records taken from the Round 1 output, together with the
  blinded sheet the annotators worked from. Six sheets:

  | Sheet | Rows | Contents |
  |---|---|---|
  | `Full_Sample_LLM_Visible` | 120 | All 120 records with the full Llama Round 1 output visible: decision, confidence, per-criterion judgements and evidence, key quote, `_category` (stratum) and `_processing_status` |
  | `Annotation_Blind` | 120 | The blinded version annotators received: filename and stratum only, with empty `human_decision` / `human_confidence` / `human_notes` columns |
  | `LLM_Include` | 28 | The include stratum |
  | `LLM_Exclude` | 58 | The sampled-exclude stratum |
  | `LLM_Manual_Review` | 25 | The manual-review stratum |
  | `LLM_Failed` | 9 | The text-extraction-failure stratum |

  The three `human_*` columns are empty throughout: this is the sample as drawn, not
  the completed annotations. Completed annotations are in `data/annotations/` and
  `master_comparison.xlsx`. The file contains no annotator names and no email
  addresses. `_processing_status` across the 120 is 102 `success`, 9
  `success_recovered`, 9 `failed_text_extraction`.

  **Stratum labels and decision columns are not the same thing.** The four strata
  (28 / 58 / 25 / 9) record what Llama Round 1 actually returned. In
  `master_comparison.xlsx` the `llama_decision` column holds only `INCLUDE` (28) and
  `EXCLUDE` (92): the manual-review and text-extraction-failure records were folded
  into `EXCLUDE` when that comparison file was built. See "Decision coding" below.

- `master_comparison.xlsx` — the 120 records with both human annotations (anonymised)
  plus Llama and Qwen decisions; source of the reported validation metrics.
- `qwen_validation_20260206_222701.xlsx` — Qwen 2.5 7B cross-check on the subset.
- `model_comparison_report.xlsx` — Llama-vs-Qwen agreement summary.

## Round 2 (Qwen 2.5 7B)
- `enabling_voices_qwen_v3_20260312_230707.xlsx` — conservative full-pool pass.
  (Split outputs `_includes` / `_flagged` / `_partial` available on request.)

## Adjudication and inclusion
- `adjudication_needed.xlsx` — records flagged for PI adjudication (annotations anonymised).
- `inclusion_candidate_pool.xlsx` — the 36-record include-candidate / adjudication pool:
  both annotators (anonymised), model decisions, vote tallies, and decision-tree flags.
  This is the candidate pool, **not** the final set.
- `final_inclusion_record.xlsx` — **authoritative final record**: the 6 included studies
  plus the 9 records excluded at full text, with reasons. Supersedes the earlier
  "Final: 10" tracker (removed). Author names corrected from LLM-truncated initials
  (COV5183 → Favela; COV5169 → Mowri).

## Extraction (not used for results)
- `enabling_voices_extraction_fulltextWholePaper_20260314_192132.xlsx` — full-text
  LLM extraction output. **Not used for results**; deposited to document the
  extraction failure modes discussed in the paper (§3.6).

## Decision coding in the comparison files

`master_comparison.xlsx` stores `llama_decision` and `qwen_decision` as a binary
`INCLUDE` / `EXCLUDE` pair. The mapping from the four Round 1 outcomes is:

| Round 1 outcome (`_category` in `validation_sample.xlsx`) | n | `llama_decision` |
|---|---|---|
| Include | 28 | `INCLUDE` |
| Exclude | 58 | `EXCLUDE` |
| Manual Review | 25 | `EXCLUDE` |
| Failed (text extraction) | 9 | `EXCLUDE` |

The same 9 text-extraction failures are also recorded as `EXCLUDE` in
`qwen_decision`, even though the Qwen passes used a different PDF-text path.

This binarisation is applied **when `master_comparison.xlsx` is built**, not by
`code/08_validation_metrics/compute_review_statistics.py`, which reads the column
as it finds it. Consequences worth knowing when reading the reported metrics:

- Records the model declined to decide (`Manual Review`) and records it could not
  read (`Failed`) both count as model exclusions in the model-versus-human-consensus
  statistics.
- One of the six final included studies, COV5607 (Obiorah 2021), is in the
  manual-review stratum, so this coding makes it a Llama false negative.
- `model_comparison_report.xlsx` is coded differently: it keeps the 9
  text-extraction failures as blank (`NaN`) rather than as exclusions, which is why
  the Llama-versus-Qwen agreement statistic is reported on two denominators —
  all 120 (failures counted as exclude) and valid-only (n = 111, failures dropped).
