# Full-text extraction — error log

**Status.** Discrepancies between the trialled LLM full-text extraction (Llama 3.1 8B, 14 March 2026) and the study characteristics charted **manually** for Section 4. The extraction was trialled and **not used** for the reported results; deposited only to document its failure modes (paper §3.6; Supplementary D.8). Verified values are the manually charted Section 4 / Table 4 characteristics; extracted values are read directly from the deposited workbook. The run processed 10 candidates as they stood in March 2026; this log covers the six studies in the final included set.

## Summary

- **Model misattribution (spurious GPT-4):** Bailey 2026, Obiorah 2021, Purohit 2023, Sheehy 2024, Stara 2021. Only Xygkou 2024 genuinely used GPT-4.
- **Participant miscount:** Obiorah 2021.
- **Setting misidentified / flattened:** Obiorah 2021, Purohit 2023.

## Per-field discrepancies

| COV ID | Study | Field | Extracted | Verified (Section 4) | Error type | Model confidence |
|---|---|---|---|---|---|---|
| COV2660 | Bailey 2026 | AI model | GPT-3.5_language_model  ·  Assembly.ai_ASR  ·  GPT-4_language_model  ·  Google_Cloud_ASR  ·  language_model | GPT-3.5 | Model misattribution (spurious GPT-4) | 3 |
| COV5607 | Obiorah 2021 | AI model | image_captioning  ·  OCR  ·  geographic_data  ·  Cloudsight's API  ·  Google Cloud Vision text API  ·  GPT-4_language_model  ·  image_recognition | rule-based AAC; image-captioning APIs, no LLM | Model misattribution (spurious GPT-4) | 3 |
| COV5607 | Obiorah 2021 | N (participants) | 7 | 11 | Participant miscount | 3 |
| COV5607 | Obiorah 2021 | Setting | hospital_clinic | multi-site: clinic, restaurants, community | Setting flattened (multi-site -> single) | 3 |
| COV5630 | Purohit 2023 | AI model | GPT-3.55 language model  ·  GPT-4_language_model | GPT-3.5 (ChatGPT) | Model misattribution (spurious GPT-4) | 4 |
| COV5630 | Purohit 2023 | Setting | university_lab | secondary analysis of AphasiaBank transcripts; no live deployment | Setting misidentified | 4 |
| COV510 | Sheehy 2024 | AI model | speech-to-text  ·  intent interpretation  ·  text-to-speech  ·  GPT-4_language_model  ·  Google_Cloud_ASR  ·  text_to_speech_TTS | GPT-3.5 (Stage 2) | Model misattribution (spurious GPT-4) | 4 |
| COV1113 | Stara 2021 | AI model | automated speech recognition  ·  text-to-speech functions  ·  GPT-4_language_model  ·  Google_Cloud_ASR | rule-based (Anne; ASR+TTS), no LLM | Model misattribution (spurious GPT-4) | 3 |
| COV5688 | Xygkou 2024 | AI model | GPT-4_language_model | GPT-4 | Correct (GPT-4 genuinely used) | 2 |

## Confidence pattern

Model-reported confidence did not track correctness. The two highest-confidence extractions (Sheehy 2024 and Purohit 2023, both confidence 4) are the two that carry a spurious GPT-4, while the one study that genuinely used GPT-4 (Xygkou 2024) carries the lowest confidence (2). Confidence was therefore highest where the extraction was wrong.

## Mechanism

The errors follow from the windowed extraction design. A memory-limited GPU (Tesla V100, 32 GB) could not hold the full schema and a long article in one pass, so each paper was split into overlapping token windows, the full schema run on each, then merged. List fields (AI components) merge by **union**, so a single window mentioning GPT-4 — in related work, a citation, or a hallucination — propagates to the final field; whole-document aggregates (Obiorah's N = 11 across phases) cannot be recovered because no single window holds them; scalar fields take the first non-empty value, so an early window's setting guess (Purohit's 'university lab') overrides later, more accurate windows. Confidence is the minimum across windows, computed independently of the union, which is why wrong fields ride through at moderate confidence.
