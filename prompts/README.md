# Prompts

Verbatim prompts used in the screening and extraction pipeline.

| File | Stage | Model | Source script |
|---|---|---|---|
| `round1_filtering_prompt.md` | Round 1 high-recall screening | Llama 3.1 8B-Instruct | `code/02_screening_round1/enabling_voices_round1.py` |
| `round2_qwen_prompt.md` | Round 1 Qwen validation + Round 2 screening | Qwen 2.5 7B-Instruct | `code/04_screening_round2/enabling_voices_qwen_screening_v3.py` |
| `extraction_prompt.md` | Full-text structured extraction (documented only; not used for results) | Llama 3.1 8B-Instruct | `code/05_extraction/enabling_voices_extraction_fulltext.py` |

Each prompt is also embedded in its source script; the files here reproduce that
text verbatim. Where a prompt is a Python `str.format` template, `{article_text}`
is the substituted article text and doubled braces `{{` / `}}` are literal single
braces in the text the model receives.
