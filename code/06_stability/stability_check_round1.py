#!/usr/bin/env python3
"""
Stability check for Llama 3.1 8B Round 1 screening on the FIXED 120-paper subset.

Purpose
-------
Quantify how much the include/exclude decisions vary from run to run due to random
chance (sampling during generation). This addresses the RSM requirement to report
"sensitivity to ... random chance". It is an ADDITIONAL analysis: it does NOT replace
the original Round 1 run and does not touch the human-annotation chain. The original
run is simply one realisation of the same stochastic process characterised here.

What it does
------------
Reuses the exact prompt and screening logic from enabling_voices_round1.py, runs it
over the 120 subset N times (one fixed seed per pass, fixed paper order), and reports:
  - per-paper decision stability (does the paper get the same decision every run?)
  - mean pairwise agreement across runs
  - confidence spread per paper
  - per-run agreement with human consensus (accuracy / sensitivity / specificity /
    Cohen's kappa), IF a human-consensus file is supplied.

Note on sampling: screen_article uses do_sample=True (temperature 0.1, top_p 0.9),
which is what creates the run-to-run variability we are measuring, so we keep it.
(For a *determinism* demonstration you would instead set do_sample=False / greedy and
run once -- a different question from this one.)

Run on UCloud, in the same folder as enabling_voices_round1.py:
    python stability_check_round1.py
    # or, to keep a log:
    nohup python stability_check_round1.py > stability_round1.log 2>&1 &
"""

import gc
import itertools
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, set_seed

# Reuse the ORIGINAL prompt + screening function so this matches the real pipeline.
import enabling_voices_round1 as ev1

# =============================================================================
# CONFIGURATION
# =============================================================================
SEEDS = [1, 2, 3, 4, 5]                       # one full pass over the 120 per seed

# The fixed 120-paper validation subset (output of generate_annotation_files input)
VALIDATION_SAMPLE = "/work/EnablingPapers150126/outputs/validation_sample.xlsx"
VALIDATION_SHEET  = "Full_Sample_LLM_Visible"  # sheet used by generate_annotation_files.py
FILENAME_COL      = "_filename"

# Optional: human consensus labels to measure accuracy variation across runs.
# Provide a .xlsx or .csv with columns: _filename, human_include  (human_include = True/False).
# Leave as None to compute stability only.
HUMAN_CONSENSUS   = None

PDF_FOLDER  = ev1.PDF_FOLDER
OUTPUT_DIR  = ev1.OUTPUT_DIR
MODEL_NAME  = ev1.MODEL_NAME
MAX_TOKENS  = ev1.MAX_TOKENS_PER_ARTICLE
HF_TOKEN    = getattr(ev1, "HF_TOKEN", None)
TEST_LIMIT  = None                            # set to e.g. 5 for a quick smoke test

_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_XLSX = f"{OUTPUT_DIR}/stability_round1_{_TS}.xlsx"


# =============================================================================
# HELPERS
# =============================================================================
def load_model():
    """Load Llama 3.1 8B with the SAME 4-bit config as the original Round 1 run."""
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,   # matches enabling_voices_round1.py
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    tok = AutoTokenizer.from_pretrained(MODEL_NAME, token=HF_TOKEN)
    mdl = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, quantization_config=bnb, device_map="auto", token=HF_TOKEN
    )
    print(f"  Model loaded: {MODEL_NAME}")
    return mdl, tok


def load_subset_filenames():
    df = pd.read_excel(VALIDATION_SAMPLE, sheet_name=VALIDATION_SHEET)
    files = df[FILENAME_COL].dropna().astype(str).tolist()
    if TEST_LIMIT:
        files = files[:TEST_LIMIT]
    print(f"  Subset loaded: {len(files)} papers")
    return files


def load_human_consensus():
    if not HUMAN_CONSENSUS:
        return None
    p = Path(HUMAN_CONSENSUS)
    df = pd.read_csv(p) if p.suffix.lower() == ".csv" else pd.read_excel(p)
    df = df[[FILENAME_COL, "human_include"]].dropna()
    df["human_decision"] = df["human_include"].map(
        lambda v: "INCLUDE" if bool(v) else "EXCLUDE"
    )
    return dict(zip(df[FILENAME_COL].astype(str), df["human_decision"]))


def norm_decision(include_value):
    if include_value is True:
        return "INCLUDE"
    if include_value is False:
        return "EXCLUDE"
    return "UNCLEAR"


# =============================================================================
# RUN
# =============================================================================
def run_screening(model, tokenizer, files):
    rows = []
    for seed in SEEDS:
        set_seed(seed)  # one seed per full pass; fixed order -> each run is reproducible
        print(f"\n=== Seed {seed} ===")
        for i, fname in enumerate(files, 1):
            pdf_path = str(Path(PDF_FOLDER) / fname)
            res = ev1.screen_article(pdf_path, model, tokenizer, MAX_TOKENS)
            rows.append({
                "filename": fname,
                "seed": seed,
                "decision": norm_decision(res.get("include")),
                "confidence": res.get("confidence"),
                "status": res.get("_processing_status"),
            })
            if i % 20 == 0:
                print(f"  seed {seed}: {i}/{len(files)}")
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
    return pd.DataFrame(rows)


def per_paper_table(long_df):
    out = []
    for fname, g in long_df.groupby("filename"):
        decisions = g["decision"].tolist()
        confs = pd.to_numeric(g["confidence"], errors="coerce")
        n_inc = sum(d == "INCLUDE" for d in decisions)
        n_exc = sum(d == "EXCLUDE" for d in decisions)
        n_unc = sum(d == "UNCLEAR" for d in decisions)
        stable = len(set(decisions)) == 1
        majority = max(set(decisions), key=decisions.count)
        out.append({
            "filename": fname,
            "n_runs": len(decisions),
            "n_INCLUDE": n_inc,
            "n_EXCLUDE": n_exc,
            "n_UNCLEAR": n_unc,
            "stable": stable,                      # same decision in every run?
            "majority_decision": majority,
            "confidence_mean": round(confs.mean(), 3) if confs.notna().any() else None,
            "confidence_sd": round(confs.std(ddof=0), 3) if confs.notna().any() else None,
        })
    return pd.DataFrame(out).sort_values(["stable", "filename"])


def mean_pairwise_agreement(long_df):
    """Average, over all seed-pairs, of the % of papers with matching decisions."""
    pivot = long_df.pivot_table(index="filename", columns="seed",
                                values="decision", aggfunc="first")
    seeds = list(pivot.columns)
    if len(seeds) < 2:
        return None
    agreements = []
    for a, b in itertools.combinations(seeds, 2):
        mask = pivot[a].notna() & pivot[b].notna()
        agreements.append((pivot.loc[mask, a] == pivot.loc[mask, b]).mean())
    return float(np.mean(agreements))


def per_run_table(long_df, human):
    try:
        from sklearn.metrics import cohen_kappa_score
        have_sklearn = True
    except Exception:
        have_sklearn = False

    out = []
    for seed, g in long_df.groupby("seed"):
        row = {"seed": seed,
               "n_INCLUDE": int((g["decision"] == "INCLUDE").sum()),
               "n_EXCLUDE": int((g["decision"] == "EXCLUDE").sum()),
               "n_UNCLEAR": int((g["decision"] == "UNCLEAR").sum())}
        if human:
            m = g[g["filename"].isin(human)].copy()
            m["human"] = m["filename"].map(human)
            # binary: INCLUDE vs not-INCLUDE, against human INCLUDE/EXCLUDE
            pred = (m["decision"] == "INCLUDE")
            truth = (m["human"] == "INCLUDE")
            tp = int((pred & truth).sum()); tn = int((~pred & ~truth).sum())
            fp = int((pred & ~truth).sum()); fn = int((~pred & truth).sum())
            row["accuracy"]    = round((tp + tn) / max(len(m), 1), 3)
            row["sensitivity"] = round(tp / max(tp + fn, 1), 3)
            row["specificity"] = round(tn / max(tn + fp, 1), 3)
            row["precision"]   = round(tp / max(tp + fp, 1), 3)
            if have_sklearn and len(m) > 1:
                row["cohen_kappa_vs_human"] = round(
                    cohen_kappa_score(pred.astype(int), truth.astype(int)), 3)
        out.append(row)
    return pd.DataFrame(out)


def main():
    print("=" * 60)
    print("ROUND 1 STABILITY CHECK")
    print(f"Seeds: {SEEDS}")
    print("=" * 60)

    model, tokenizer = load_model()
    files = load_subset_filenames()
    human = load_human_consensus()

    long_df = run_screening(model, tokenizer, files)

    per_paper = per_paper_table(long_df)
    per_run = per_run_table(long_df, human)
    mpa = mean_pairwise_agreement(long_df)

    n_papers = long_df["filename"].nunique()
    n_stable = int(per_paper["stable"].sum())
    summary = pd.DataFrame([
        {"metric": "papers", "value": n_papers},
        {"metric": "seeds (runs)", "value": len(SEEDS)},
        {"metric": "papers stable across all runs", "value": n_stable},
        {"metric": "papers stable (%)", "value": round(100 * n_stable / max(n_papers, 1), 1)},
        {"metric": "papers that flip at least once", "value": n_papers - n_stable},
        {"metric": "mean pairwise agreement across runs (%)",
         "value": round(100 * mpa, 1) if mpa is not None else None},
    ])

    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as w:
        summary.to_excel(w, sheet_name="Summary", index=False)
        per_run.to_excel(w, sheet_name="PerRun", index=False)
        per_paper.to_excel(w, sheet_name="PerPaper", index=False)
        long_df.to_excel(w, sheet_name="Raw_paper_x_seed", index=False)

    print("\n" + "=" * 60)
    print("DONE")
    print(summary.to_string(index=False))
    print(f"\nSaved: {OUTPUT_XLSX}")


if __name__ == "__main__":
    main()
