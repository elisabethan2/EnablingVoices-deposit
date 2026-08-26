#!/usr/bin/env python3
"""
Fix JSON parsing failures in Enabling Voices Round 1 results.

This script:
1. Loads the checkpoint JSON
2. Fixes entries where JSON parsing failed due to unquoted 'unclear' values
3. Re-extracts screening decisions from raw responses
4. Updates both the checkpoint JSON and Excel file

Usage:
    python fix_json_failures.py
"""

import json
import re
import pandas as pd
from pathlib import Path
from datetime import datetime

# =============================================================================
# CONFIGURATION - UPDATE THESE PATHS
# =============================================================================

CHECKPOINT_PATH = "/work/EnablingPapers150126/outputs/enabling_voices_round1_V2_checkpoint.json"
EXCEL_PATH = "/work/EnablingPapers150126/outputs/enabling_voices_round1_V2_20260206_170842.xlsx"

# Backup suffix
BACKUP_SUFFIX = "_backup"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def fix_json_string(text):
    """Fix common JSON issues like unquoted 'unclear' values."""
    if not text or not isinstance(text, str):
        return text
    
    # Fix unquoted boolean-like values
    text = re.sub(r':\s*unclear\s*([,}\]])', r': "unclear"\1', text)
    text = re.sub(r':\s*True\s*([,}\]])', r': true\1', text)
    text = re.sub(r':\s*False\s*([,}\]])', r': false\1', text)
    
    # Fix trailing commas
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)
    
    return text


def extract_json_from_text(text):
    """Extract the first complete JSON object from text."""
    if not text:
        return None
    
    text = fix_json_string(str(text))
    
    start_idx = text.find('{')
    if start_idx == -1:
        return None
    
    depth = 0
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text[start_idx:], start=start_idx):
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                json_str = text[start_idx:i+1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    return None
    
    return None


def extract_fields_from_screening(screening):
    """Extract flat fields from nested screening JSON."""
    result = {}
    
    if not screening:
        return result
    
    # Screening decision
    sd = screening.get('screening_decision', {})
    result['include'] = sd.get('include', None)
    result['confidence'] = sd.get('confidence', None)
    result['decision_rationale'] = sd.get('decision_rationale', '')
    
    # Population assessment
    pa = screening.get('population_assessment', {})
    result['has_dementia'] = pa.get('has_dementia_focus', None)
    result['has_aphasia'] = pa.get('has_aphasia_focus', None)
    result['population_details'] = pa.get('population_details', '')
    
    # Technology assessment
    ta = screening.get('technology_assessment', {})
    result['has_ai'] = ta.get('has_ai_technology', None)
    ai_type = ta.get('ai_type', [])
    result['ai_types'] = ','.join(ai_type) if isinstance(ai_type, list) else str(ai_type)
    result['technology_details'] = ta.get('technology_details', '')
    result['technology_confidence'] = ta.get('technology_confidence', None)
    result['is_detection_study'] = ta.get('is_detection_study', None)
    result['is_basic_digital_tool'] = ta.get('is_basic_digital_tool', None)
    result['ai_evidence'] = ta.get('ai_evidence', '')
    
    # Communication assessment
    ca = screening.get('communication_assessment', {})
    result['has_communication_support'] = ca.get('has_communication_support', None)
    comm_type = ca.get('communication_type', [])
    result['communication_types'] = ','.join(comm_type) if isinstance(comm_type, list) else str(comm_type)
    result['communication_details'] = ca.get('communication_details', '')
    result['support_vs_detect'] = ca.get('support_vs_detect', '')
    
    # Study metadata
    sm = screening.get('study_metadata', {})
    result['study_type'] = sm.get('study_type', '')
    result['publication_type'] = sm.get('publication_type', '')
    
    # Manual review flag
    mrf = screening.get('manual_review_flag', {})
    result['needs_manual_review'] = mrf.get('needs_review', False)
    result['review_reason'] = mrf.get('review_reason', '')
    
    # Key quote
    result['key_quote'] = screening.get('key_quote', '')
    
    return result


def try_recover_from_preview(preview):
    """Try to extract at least the include decision from a partial response."""
    if not preview:
        return None
    
    preview = str(preview)
    
    # Try full JSON extraction first
    screening = extract_json_from_text(preview)
    if screening:
        return screening
    
    # If that fails, try to extract just the screening_decision
    include_match = re.search(r'"include":\s*(true|false)', preview, re.IGNORECASE)
    confidence_match = re.search(r'"confidence":\s*(\d)', preview)
    rationale_match = re.search(r'"decision_rationale":\s*"([^"]*)"', preview)
    
    if include_match:
        return {
            'screening_decision': {
                'include': include_match.group(1).lower() == 'true',
                'confidence': int(confidence_match.group(1)) if confidence_match else None,
                'decision_rationale': rationale_match.group(1) if rationale_match else 'Recovered from partial response'
            },
            '_recovered': True,
            '_recovery_note': 'Extracted from partial response preview'
        }
    
    return None


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    print("="*60)
    print("FIXING JSON PARSING FAILURES")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Check files exist
    if not Path(CHECKPOINT_PATH).exists():
        print(f"ERROR: Checkpoint file not found: {CHECKPOINT_PATH}")
        return
    
    if not Path(EXCEL_PATH).exists():
        print(f"ERROR: Excel file not found: {EXCEL_PATH}")
        return
    
    # ==========================================================================
    # STEP 1: Load and backup checkpoint
    # ==========================================================================
    print("\n[1/4] Loading checkpoint...")
    
    with open(CHECKPOINT_PATH, 'r') as f:
        checkpoint = json.load(f)
    
    results = checkpoint.get('results', [])
    print(f"  Loaded {len(results)} results")
    
    # Backup
    backup_path = CHECKPOINT_PATH.replace('.json', f'{BACKUP_SUFFIX}.json')
    with open(backup_path, 'w') as f:
        json.dump(checkpoint, f, indent=2, default=str)
    print(f"  Backup saved: {backup_path}")
    
    # ==========================================================================
    # STEP 2: Fix JSON parsing failures
    # ==========================================================================
    print("\n[2/4] Fixing JSON parsing failures...")
    
    fixed_count = 0
    still_failed = 0
    
    for result in results:
        status = result.get('_processing_status', '')
        
        if status == 'failed_json_extraction':
            # Try to recover from raw response preview
            preview = result.get('_raw_response_preview', '')
            
            screening = try_recover_from_preview(preview)
            
            if screening:
                # Update the result with recovered data
                result['_raw_screening'] = screening
                
                # Extract fields
                fields = extract_fields_from_screening(screening)
                result.update(fields)
                
                result['_processing_status'] = 'success_recovered'
                result['_recovery_note'] = 'JSON parsing fixed - unquoted unclear values'
                
                # Remove error fields
                if '_error' in result:
                    del result['_error']
                
                fixed_count += 1
            else:
                still_failed += 1
    
    print(f"  Fixed: {fixed_count}")
    print(f"  Still failed: {still_failed}")
    
    # ==========================================================================
    # STEP 3: Update checkpoint statistics and save
    # ==========================================================================
    print("\n[3/4] Updating checkpoint...")
    
    # Recalculate stats
    success_count = sum(1 for r in results if r.get('_processing_status') in ['success', 'success_recovered'])
    include_count = sum(1 for r in results if r.get('include') == True)
    exclude_count = sum(1 for r in results if r.get('include') == False)
    failed_count = sum(1 for r in results if r.get('_processing_status') not in ['success', 'success_recovered'])
    
    checkpoint['stats'] = {
        'total_processed': len(results),
        'success': success_count,
        'include': include_count,
        'exclude': exclude_count,
        'failed': failed_count,
        'fixed_in_recovery': fixed_count
    }
    checkpoint['last_fixed'] = datetime.now().isoformat()
    
    # Save updated checkpoint
    with open(CHECKPOINT_PATH, 'w') as f:
        json.dump(checkpoint, f, indent=2, default=str)
    print(f"  Checkpoint updated: {CHECKPOINT_PATH}")
    
    # ==========================================================================
    # STEP 4: Regenerate Excel file
    # ==========================================================================
    print("\n[4/4] Regenerating Excel file...")
    
    # Backup Excel
    backup_excel = EXCEL_PATH.replace('.xlsx', f'{BACKUP_SUFFIX}.xlsx')
    import shutil
    shutil.copy(EXCEL_PATH, backup_excel)
    print(f"  Backup saved: {backup_excel}")
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Categorize
    def categorize(row):
        status = row.get('_processing_status', '')
        if status not in ['success', 'success_recovered']:
            return 'Failed'
        if row.get('needs_manual_review'):
            return 'Manual Review'
        if row.get('include') == True:
            return 'Include'
        return 'Exclude'
    
    df['_category'] = df.apply(categorize, axis=1)
    
    # Key columns for summary sheets
    key_cols = [
        '_filename', 'include', 'confidence', 'decision_rationale',
        'has_dementia', 'has_aphasia', 'has_ai', 'ai_types',
        'technology_confidence', 'is_detection_study', 'is_basic_digital_tool',
        'ai_evidence', 'has_communication_support', 'support_vs_detect',
        'study_type', 'needs_manual_review', 'review_reason', 'key_quote', 
        '_category', '_processing_status'
    ]
    key_cols = [c for c in key_cols if c in df.columns]
    
    # Save to Excel with multiple sheets
    with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
        # Summary sheet (all records)
        df[key_cols].to_excel(writer, sheet_name='Summary', index=False)
        
        # Include sheet
        include_df = df[df['_category'] == 'Include']
        if len(include_df) > 0:
            include_df[key_cols].to_excel(writer, sheet_name='Include', index=False)
        
        # Exclude sheet
        exclude_df = df[df['_category'] == 'Exclude']
        if len(exclude_df) > 0:
            exclude_df[key_cols].to_excel(writer, sheet_name='Exclude', index=False)
        
        # Manual Review sheet
        review_df = df[df['_category'] == 'Manual Review']
        if len(review_df) > 0:
            review_df[key_cols].to_excel(writer, sheet_name='Manual Review', index=False)
        
        # Failed sheet
        failed_df = df[df['_category'] == 'Failed']
        if len(failed_df) > 0:
            # Include more columns for debugging
            fail_cols = key_cols + ['_error', '_total_pages', '_extracted_chars']
            fail_cols = [c for c in fail_cols if c in df.columns]
            failed_df[fail_cols].to_excel(writer, sheet_name='Failed', index=False)
    
    print(f"  Excel updated: {EXCEL_PATH}")
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    stats = df['_category'].value_counts()
    print(f"\nUpdated statistics:")
    print(f"  Total processed: {len(results)}")
    for cat in ['Include', 'Exclude', 'Manual Review', 'Failed']:
        count = stats.get(cat, 0)
        print(f"  {cat}: {count}")
    
    print(f"\nRecovery stats:")
    print(f"  JSON parsing failures fixed: {fixed_count}")
    print(f"  Remaining failures (text extraction): {still_failed}")
    
    # List remaining failures
    if still_failed > 0:
        print(f"\nRemaining failed files (need manual review):")
        for r in results:
            if r.get('_processing_status') not in ['success', 'success_recovered']:
                print(f"  - {r.get('_filename')}: {r.get('_error', 'Unknown error')}")
    
    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
