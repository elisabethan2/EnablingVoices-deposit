# Corpus

- `corpus_metadata.csv` — 478 records, bibliographic metadata only (title,
  authors, year, journal, DOI, volume/issue/pages, country, type).
  **Abstracts removed** for copyright; records are identifiable by DOI.
  Full-text PDFs are not included (copyright) — retrieve via DOI.

## Relationship to the corpus-assembly notebook

`code/01_corpus_assembly/ristocsvenablingvoices478-301025.ipynb` writes its output
as `complete_review_data.csv`. That file is **not** deposited and is not missing:
it is the pre-redaction working file, and it carries an `Abstract` column holding
the full abstract text of all 478 records.

`corpus_metadata.csv` is that same file with the `Abstract` column removed and
nothing else changed — same 478 records, same 11 remaining columns, in the same
order. The abstracts were removed for copyright before deposit, which is why the
notebook's filename does not appear anywhere under `data/`. The `Has_Abstract`
boolean is retained so the 385 records that had an abstract remain identifiable
without the text itself.

The notebook is left as it ran, so it still names the working file.

Bibliographic fields are preserved **as harvested** from the database export of
2025-10-30 and are deliberately not back-corrected. Where a record was retrieved
at its online-first stage, the `Year` field carries the online-first year rather
than the later issue year: COV2660 (Bailey, *Aphasia-GPT*) appears here as 2025
and is cited in the manuscript and in `final_inclusion_record.xlsx` as
*Aphasiology* 2026;40(1):150–165. The PDF filenames used as record identifiers
throughout the deposited workbooks (e.g. `COV2660_Bailey2025.pdf`) likewise keep
the harvest-time year; they are identifiers, not citations.
