#!/usr/bin/env python3
"""
Compare Llama 3.1 8B and Qwen 2.5 7B Results on Validation Sample

This script compares the screening decisions of both models and calculates
inter-rater agreement metrics.

Usage:
    python compare_models.py
"""

import pandas as pd
import json
import numpy as np
from pathlib import Path
from datetime import datetime

# =============================================================================
# CONFIGURATION - UPDATE THESE PATHS
# =============================================================================

# Llama results (the updated one with JSON fixes)
LLAMA_EXCEL = "/work/EnablingPapers150126/outputs/enabling_voices_round1_V2_20260206_170842_1.xlsx"
LLAMA_JSON = "/work/EnablingPapers150126/outputs/enabling_voices_round1_V2_checkpoint__1_.json"

# Qwen results
QWEN_EXCEL = "/work/EnablingPapers150126/outputs/qwen_validation_20260206_222716.xlsx"
QWEN_JSON = "/work/EnablingPapers150126/outputs/qwen_validation_checkpoint.json"

# Output
OUTPUT_DIR = "/work/EnablingPapers150126/outputs"
OUTPUT_FILE = f"{OUTPUT_DIR}/model_comparison_report.xlsx"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_cohens_kappa(y1, y2):
    """Calculate Cohen's Kappa for two binary arrays."""
    # Confusion matrix
    both_yes = sum((y1 == True) & (y2 == True))
    both_no = sum((y1 == False) & (y2 == False))
    y1_yes_y2_no = sum((y1 == True) & (y2 == False))
    y1_no_y2_yes = sum((y1 == False) & (y2 == True))
    
    total = both_yes + both_no + y1_yes_y2_no + y1_no_y2_yes
    
    if total == 0:
        return 0, 0, {}
    
    # Observed agreement
    p_o = (both_yes + both_no) / total
    
    # Expected agreement
    p_y1_yes = (both_yes + y1_yes_y2_no) / total
    p_y2_yes = (both_yes + y1_no_y2_yes) / total
    p_e = (p_y1_yes * p_y2_yes) + ((1 - p_y1_yes) * (1 - p_y2_yes))
    
    # Kappa
    kappa = (p_o - p_e) / (1 - p_e) if (1 - p_e) != 0 else 0
    
    confusion = {
        'both_yes': both_yes,
        'both_no': both_no,
        'y1_yes_y2_no': y1_yes_y2_no,
        'y1_no_y2_yes': y1_no_y2_yes,
        'total': total
    }
    
    return kappa, p_o, confusion


def interpret_kappa(kappa):
    """Interpret Cohen's Kappa value."""
    if kappa < 0:
        return "Poor (worse than chance)"
    elif kappa < 0.20:
        return "Slight"
    elif kappa < 0.40:
        return "Fair"
    elif kappa < 0.60:
        return "Moderate"
    elif kappa < 0.80:
        return "Substantial"
    else:
        return "Almost Perfect"


# =============================================================================
# MAIN SCRIPT
# =============================================================================

def main():
    print("="*70)
    print("LLAMA vs QWEN MODEL COMPARISON")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # =========================================================================
    # Load Data
    # =========================================================================
    print("\n[1/5] Loading data...")
    
    # Load Qwen results
    qwen_df = pd.read_excel(QWEN_EXCEL, sheet_name='Summary')
    print(f"  Qwen results: {len(qwen_df)} papers")
    
    # Load Llama results (full dataset)
    llama_full = pd.read_excel(LLAMA_EXCEL, sheet_name='Summary')
    print(f"  Llama results (full): {len(llama_full)} papers")
    
    # Filter Llama to only validation sample papers
    validation_files = set(qwen_df['_filename'].tolist())
    llama_df = llama_full[llama_full['_filename'].isin(validation_files)].copy()
    print(f"  Llama filtered to validation: {len(llama_df)} papers")
    
    # Check coverage
    llama_files = set(llama_df['_filename'].tolist())
    qwen_files = set(qwen_df['_filename'].tolist())
    
    missing_in_llama = qwen_files - llama_files
    missing_in_qwen = llama_files - qwen_files
    
    if missing_in_llama:
        print(f"  ⚠ Missing in Llama: {len(missing_in_llama)} papers")
    if missing_in_qwen:
        print(f"  ⚠ Missing in Qwen: {len(missing_in_qwen)} papers")
    
    # =========================================================================
    # Merge Datasets
    # =========================================================================
    print("\n[2/5] Merging datasets...")
    
    # Select columns for comparison
    llama_cols = ['_filename', '_category', 'include', 'confidence', 'decision_rationale',
                  'has_ai', 'has_dementia', 'has_aphasia', 'is_detection_study', 
                  'is_basic_digital_tool', 'has_communication_support', 
                  'needs_manual_review', 'key_quote', '_processing_status']
    llama_cols = [c for c in llama_cols if c in llama_df.columns]
    
    qwen_cols = ['_filename', '_category', 'include', 'confidence', 'decision_rationale',
                 'has_ai', 'has_dementia', 'has_aphasia', 'is_detection_study',
                 'is_basic_digital_tool', 'has_communication_support',
                 'needs_manual_review', 'key_quote', '_processing_status']
    qwen_cols = [c for c in qwen_cols if c in qwen_df.columns]
    
    merged = pd.merge(
        llama_df[llama_cols],
        qwen_df[qwen_cols],
        on='_filename',
        suffixes=('_llama', '_qwen'),
        how='outer'
    )
    print(f"  Merged dataset: {len(merged)} papers")
    
    # =========================================================================
    # Calculate Agreement Metrics
    # =========================================================================
    print("\n[3/5] Calculating agreement metrics...")
    
    # Exclude failed papers from agreement calculation
    valid_mask = (
        (merged['_processing_status_llama'].isin(['success', 'success_recovered'])) &
        (merged['_processing_status_qwen'] == 'success')
    )
    valid = merged[valid_mask].copy()
    print(f"  Valid comparisons (excluding failed): {len(valid)}")
    
    # Convert include to boolean
    valid['llama_include'] = valid['include_llama'].fillna(False).astype(bool)
    valid['qwen_include'] = valid['include_qwen'].fillna(False).astype(bool)
    
    # Calculate Kappa for INCLUDE decision
    kappa, percent_agree, confusion = calculate_cohens_kappa(
        valid['llama_include'].values,
        valid['qwen_include'].values
    )
    
    print(f"\n  INCLUDE Decision Agreement:")
    print(f"    Raw agreement: {percent_agree*100:.1f}%")
    print(f"    Cohen's Kappa: {kappa:.3f} ({interpret_kappa(kappa)})")
    
    # =========================================================================
    # Detailed Analysis
    # =========================================================================
    print("\n[4/5] Detailed analysis...")
    
    # Category distribution
    print("\n  Category Distribution:")
    print(f"  {'Category':<20} {'Llama':>10} {'Qwen':>10}")
    print(f"  {'-'*40}")
    
    llama_cats = merged['_category_llama'].value_counts()
    qwen_cats = merged['_category_qwen'].value_counts()
    all_cats = set(llama_cats.index) | set(qwen_cats.index)
    
    for cat in ['Include', 'Exclude', 'Manual Review', 'Failed']:
        if cat in all_cats:
            l_count = llama_cats.get(cat, 0)
            q_count = qwen_cats.get(cat, 0)
            print(f"  {cat:<20} {l_count:>10} {q_count:>10}")
    
    # Confusion matrix
    print(f"\n  Confusion Matrix (Include Decision):")
    print(f"                        Qwen INCLUDE    Qwen EXCLUDE")
    print(f"  Llama INCLUDE              {confusion['both_yes']:3d}              {confusion['y1_yes_y2_no']:3d}")
    print(f"  Llama EXCLUDE              {confusion['y1_no_y2_yes']:3d}              {confusion['both_no']:3d}")
    
    # Disagreement details
    llama_yes_qwen_no = valid[
        (valid['llama_include'] == True) & (valid['qwen_include'] == False)
    ]
    qwen_yes_llama_no = valid[
        (valid['llama_include'] == False) & (valid['qwen_include'] == True)
    ]
    
    print(f"\n  Disagreements:")
    print(f"    Llama INCLUDE, Qwen EXCLUDE: {len(llama_yes_qwen_no)} papers")
    print(f"    Qwen INCLUDE, Llama EXCLUDE: {len(qwen_yes_llama_no)} papers")
    
    # Confidence comparison
    llama_conf = valid['confidence_llama'].dropna()
    qwen_conf = valid['confidence_qwen'].dropna()
    
    print(f"\n  Confidence Scores:")
    print(f"    Llama: mean={llama_conf.mean():.2f}, median={llama_conf.median():.1f}, std={llama_conf.std():.2f}")
    print(f"    Qwen:  mean={qwen_conf.mean():.2f}, median={qwen_conf.median():.1f}, std={qwen_conf.std():.2f}")
    
    # Manual review comparison
    llama_mr = sum(valid['needs_manual_review_llama'] == True)
    qwen_mr = sum(valid['needs_manual_review_qwen'] == True)
    
    print(f"\n  Manual Review Flags:")
    print(f"    Llama: {llama_mr} papers")
    print(f"    Qwen:  {qwen_mr} papers")
    
    # =========================================================================
    # Save Results
    # =========================================================================
    print("\n[5/5] Saving results...")
    
    # Create summary statistics
    summary_stats = pd.DataFrame({
        'Metric': [
            'Total papers compared',
            'Valid comparisons (non-failed)',
            'Raw Agreement (%)',
            "Cohen's Kappa",
            'Kappa Interpretation',
            'Llama INCLUDE count',
            'Qwen INCLUDE count',
            'Both INCLUDE',
            'Llama only INCLUDE',
            'Qwen only INCLUDE',
            'Both EXCLUDE',
            'Llama Manual Review',
            'Qwen Manual Review',
            'Llama Avg Confidence',
            'Qwen Avg Confidence'
        ],
        'Value': [
            len(merged),
            len(valid),
            f"{percent_agree*100:.1f}%",
            f"{kappa:.3f}",
            interpret_kappa(kappa),
            int(confusion['both_yes'] + confusion['y1_yes_y2_no']),
            int(confusion['both_yes'] + confusion['y1_no_y2_yes']),
            confusion['both_yes'],
            confusion['y1_yes_y2_no'],
            confusion['y1_no_y2_yes'],
            confusion['both_no'],
            llama_mr,
            qwen_mr,
            f"{llama_conf.mean():.2f}",
            f"{qwen_conf.mean():.2f}"
        ]
    })
    
    # Prepare disagreement details
    disagreements = pd.concat([
        llama_yes_qwen_no.assign(disagreement_type='Llama_INCLUDE_Qwen_EXCLUDE'),
        qwen_yes_llama_no.assign(disagreement_type='Qwen_INCLUDE_Llama_EXCLUDE')
    ])
    
    # Save to Excel
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        summary_stats.to_excel(writer, sheet_name='Summary', index=False)
        merged.to_excel(writer, sheet_name='All_Comparisons', index=False)
        
        if len(disagreements) > 0:
            disagreements.to_excel(writer, sheet_name='Disagreements', index=False)
        
        # Papers both included
        both_include = valid[
            (valid['llama_include'] == True) & (valid['qwen_include'] == True)
        ]
        if len(both_include) > 0:
            both_include.to_excel(writer, sheet_name='Both_Include', index=False)
        
        # Papers both excluded
        both_exclude = valid[
            (valid['llama_include'] == False) & (valid['qwen_include'] == False)
        ]
        if len(both_exclude) > 0:
            both_exclude.to_excel(writer, sheet_name='Both_Exclude', index=False)
    
    print(f"  ✓ Report saved to: {OUTPUT_FILE}")
    
    # =========================================================================
    # Print Summary
    # =========================================================================
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    print(f"""
┌─────────────────────────────────────────────────────────────────────┐
│                    MODEL COMPARISON SUMMARY                         │
├─────────────────────────────────────────────────────────────────────┤
│                           Llama 3.1 8B      Qwen 2.5 7B             │
│  Include                      {confusion['both_yes'] + confusion['y1_yes_y2_no']:3d}               {confusion['both_yes'] + confusion['y1_no_y2_yes']:3d}                │
│  Exclude                      {confusion['y1_no_y2_yes'] + confusion['both_no']:3d}               {confusion['y1_yes_y2_no'] + confusion['both_no']:3d}                │
│  Manual Review flagged        {llama_mr:3d}               {qwen_mr:3d}                │
│  Avg Confidence              {llama_conf.mean():.2f}              {qwen_conf.mean():.2f}               │
├─────────────────────────────────────────────────────────────────────┤
│  AGREEMENT METRICS                                                  │
│  Raw Agreement:        {percent_agree*100:.1f}%                                       │
│  Cohen's Kappa:        {kappa:.3f} ({interpret_kappa(kappa):<20})        │
├─────────────────────────────────────────────────────────────────────┤
│  DISAGREEMENTS                                                      │
│  Llama YES, Qwen NO:   {confusion['y1_yes_y2_no']:3d} papers                                   │
│  Qwen YES, Llama NO:   {confusion['y1_no_y2_yes']:3d} papers                                   │
└─────────────────────────────────────────────────────────────────────┘
""")

    # Print disagreement details
    if len(llama_yes_qwen_no) > 0:
        print("\nPapers where Llama=INCLUDE, Qwen=EXCLUDE:")
        for _, row in llama_yes_qwen_no.iterrows():
            print(f"  • {row['_filename']}")
            print(f"    Llama rationale: {str(row.get('decision_rationale_llama', 'N/A'))[:60]}")
            print(f"    Qwen rationale:  {str(row.get('decision_rationale_qwen', 'N/A'))[:60]}")
    
    if len(qwen_yes_llama_no) > 0:
        print("\nPapers where Qwen=INCLUDE, Llama=EXCLUDE:")
        for _, row in qwen_yes_llama_no.iterrows():
            print(f"  • {row['_filename']}")
            print(f"    Llama rationale: {str(row.get('decision_rationale_llama', 'N/A'))[:60]}")
            print(f"    Qwen rationale:  {str(row.get('decision_rationale_qwen', 'N/A'))[:60]}")
    
    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
