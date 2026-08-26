#!/usr/bin/env python3
"""
Generate Annotation Files for Validation Sample

This script:
1. Loads the validation sample (120 papers)
2. Assigns each paper to 2 different annotators (double annotation)
3. Creates 8 Excel files, one per annotator (30 papers each)
4. Annotations are BLIND - annotators don't see LLM decisions

Usage:
    python generate_annotation_files.py

Output:
    - annotator_1.xlsx through annotator_8.xlsx
    - annotation_assignments.xlsx (master file showing all assignments)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# =============================================================================
# CONFIGURATION - UPDATE THESE
# =============================================================================

# Input file
VALIDATION_SAMPLE_PATH = "/work/EnablingPapers150126/outputs/validation_sample.xlsx"

# Output directory (will create annotator files here)
OUTPUT_DIR = "/work/EnablingPapers150126/outputs/annotation_files"

# Annotator names (can be changed to real names or kept as numbers)
ANNOTATOR_NAMES = [
    "Annotator_1",
    "Annotator_2", 
    "Annotator_3",
    "Annotator_4",
    "Annotator_5",
    "Annotator_6",
    "Annotator_7",
    "Annotator_8"
]

# Random seed for reproducibility
RANDOM_SEED = 42

# =============================================================================
# MAIN SCRIPT
# =============================================================================

def main():
    print("="*60)
    print("GENERATING ANNOTATION FILES")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Create output directory
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")
    
    # Load validation sample
    print(f"\nLoading validation sample from: {VALIDATION_SAMPLE_PATH}")
    validation_df = pd.read_excel(VALIDATION_SAMPLE_PATH, sheet_name='Full_Sample_LLM_Visible')
    n_papers = len(validation_df)
    n_annotators = len(ANNOTATOR_NAMES)
    
    print(f"  Total papers: {n_papers}")
    print(f"  Annotators: {n_annotators}")
    print(f"  Papers per annotator: {n_papers * 2 // n_annotators}")
    
    # ==========================================================================
    # Create balanced assignment
    # Each paper needs 2 annotators, each annotator gets 30 papers
    # ==========================================================================
    print("\nCreating balanced assignments...")
    
    np.random.seed(RANDOM_SEED)
    
    # Shuffle papers
    papers = validation_df['_filename'].tolist()
    paper_indices = list(range(n_papers))
    np.random.shuffle(paper_indices)
    
    # Create assignment matrix
    # For 120 papers and 8 annotators, we need each annotator to get 30 papers
    # and each paper to get 2 annotators
    
    # Strategy: Create pairs of annotators that rotate
    # Papers 0-14: Annotators (1,2), Papers 15-29: Annotators (3,4), etc.
    # Then Papers 30-44: Annotators (1,3), Papers 45-59: Annotators (2,4), etc.
    
    # Better strategy: Latin square-like assignment
    assignments = {name: [] for name in ANNOTATOR_NAMES}
    paper_annotators = {papers[i]: [] for i in range(n_papers)}
    
    # Create annotator pairs - each pair reviews 15 papers
    # With 8 annotators, we have C(8,2) = 28 possible pairs
    # We need 120 papers * 2 ratings = 240 ratings
    # 240 / 8 annotators = 30 papers per annotator
    
    # Simple round-robin assignment
    annotator_counts = {name: 0 for name in ANNOTATOR_NAMES}
    target_per_annotator = (n_papers * 2) // n_annotators  # 30
    
    for idx in paper_indices:
        paper = papers[idx]
        
        # Find two annotators with lowest current count
        available = [(name, count) for name, count in annotator_counts.items() 
                     if count < target_per_annotator]
        available.sort(key=lambda x: (x[1], x[0]))  # Sort by count, then name
        
        # Assign to two annotators with lowest counts
        assigned = []
        for name, count in available[:2]:
            assignments[name].append(paper)
            annotator_counts[name] += 1
            assigned.append(name)
        
        paper_annotators[paper] = assigned
    
    # Verify assignment
    print("\nAssignment summary:")
    for name in ANNOTATOR_NAMES:
        print(f"  {name}: {len(assignments[name])} papers")
    
    # ==========================================================================
    # Create individual annotator Excel files
    # ==========================================================================
    print("\nCreating annotator Excel files...")
    
    # Columns for annotation (BLIND - no LLM decisions shown)
    annotation_instructions = """
ANNOTATION INSTRUCTIONS:
- Read the FIRST 4 PAGES of each PDF
- For each paper, provide:
  1. decision: INCLUDE / EXCLUDE / UNCERTAIN
  2. confidence: 1-5 (1=very uncertain, 5=very confident)
  3. population: dementia / aphasia / both / neither / unclear
  4. has_ai: yes / no / unclear
  5. communication_focus: yes / no / unclear
  6. is_detection_study: yes / no
  7. notes: Any relevant observations

INCLUDE if ALL THREE criteria are met:
  1. Population involves people WITH dementia or aphasia
  2. Uses actual AI (ML, NLP, speech recognition, chatbots, LLMs)
  3. AI supports/enables communication

EXCLUDE if ANY of these apply:
  - Detection/diagnosis study (AI detects condition from speech)
  - No actual AI (just basic digital tools, pre-recorded content)
  - Wrong population (healthy elderly only, prevention focus)
  - No communication support focus
"""
    
    for annotator_name in ANNOTATOR_NAMES:
        annotator_papers = assignments[annotator_name]
        
        # Create dataframe for this annotator
        annotator_df = pd.DataFrame({
            'paper_id': range(1, len(annotator_papers) + 1),
            'filename': annotator_papers,
            'decision': '',  # INCLUDE / EXCLUDE / UNCERTAIN
            'confidence': '',  # 1-5
            'population': '',  # dementia / aphasia / both / neither / unclear
            'has_ai': '',  # yes / no / unclear
            'communication_focus': '',  # yes / no / unclear
            'is_detection_study': '',  # yes / no
            'notes': ''  # Free text
        })
        
        # Save to Excel
        output_path = output_dir / f"{annotator_name.lower().replace(' ', '_')}.xlsx"
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Instructions sheet
            instructions_df = pd.DataFrame({'Instructions': [annotation_instructions]})
            instructions_df.to_excel(writer, sheet_name='Instructions', index=False)
            
            # Annotation sheet
            annotator_df.to_excel(writer, sheet_name='Annotation', index=False)
        
        print(f"  Created: {output_path}")
    
    # ==========================================================================
    # Create master assignment file (for your reference)
    # ==========================================================================
    print("\nCreating master assignment file...")
    
    # Create master dataframe showing which annotators are assigned to each paper
    master_data = []
    for paper in papers:
        annotators = paper_annotators[paper]
        # Get LLM category for reference
        llm_category = validation_df[validation_df['_filename'] == paper]['_category'].values[0]
        master_data.append({
            'filename': paper,
            'llm_category': llm_category,
            'annotator_1': annotators[0] if len(annotators) > 0 else '',
            'annotator_2': annotators[1] if len(annotators) > 1 else ''
        })
    
    master_df = pd.DataFrame(master_data)
    
    # Also create a summary by annotator pair
    pair_counts = {}
    for paper, annotators in paper_annotators.items():
        pair = tuple(sorted(annotators))
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
    
    pairs_df = pd.DataFrame([
        {'annotator_pair': f"{p[0]} & {p[1]}", 'papers_shared': count}
        for p, count in sorted(pair_counts.items())
    ])
    
    master_path = output_dir / "annotation_assignments_master.xlsx"
    with pd.ExcelWriter(master_path, engine='openpyxl') as writer:
        master_df.to_excel(writer, sheet_name='Paper_Assignments', index=False)
        pairs_df.to_excel(writer, sheet_name='Annotator_Pairs', index=False)
        
        # Also include full validation sample with LLM decisions for later comparison
        validation_df.to_excel(writer, sheet_name='LLM_Decisions', index=False)
    
    print(f"  Created: {master_path}")
    
    # ==========================================================================
    # Summary
    # ==========================================================================
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"\nCreated {n_annotators} annotation files in: {output_dir}")
    print(f"Each annotator has 30 papers to review")
    print(f"Each paper will be reviewed by 2 annotators")
    print(f"\nFiles created:")
    for name in ANNOTATOR_NAMES:
        print(f"  - {name.lower().replace(' ', '_')}.xlsx")
    print(f"  - annotation_assignments_master.xlsx (for your reference)")
    
    print(f"\nAnnotator pair distribution:")
    for pair, count in sorted(pair_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {pair[0]} & {pair[1]}: {count} papers")
    if len(pair_counts) > 10:
        print(f"  ... and {len(pair_counts) - 10} more pairs")
    
    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
