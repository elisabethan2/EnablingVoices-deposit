#!/usr/bin/env python3
"""
Enabling Voices Round 1 Filtering Script
Run from command line: python enabling_voices_round1.py

For background execution:
    nohup python enabling_voices_round1.py > output.log 2>&1 &

Check progress:
    tail -f output.log
"""

import os
import json
import re
import gc
from pathlib import Path
from datetime import datetime
import pandas as pd

# =============================================================================
# CONFIGURATION - UPDATE THESE PATHS FOR YOUR UCLOUD SETUP
# =============================================================================

# Input/Output paths
PDF_FOLDER = "/work/EnablingPapers150126"  # UPDATE: Path to your PDF folder
OUTPUT_DIR = "/work/EnablingPapers150126/outputs"  # UPDATE: Should be in mounted storage!
OUTPUT_PREFIX = "enabling_voices_round1"

# Model configuration
MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"
MAX_TOKENS_PER_ARTICLE = 4000  # Reduced for memory
TEMPERATURE = 0.1

# Processing options
TEST_MODE_LIMIT = None  # Set to e.g. 10 for testing, None for full processing
CHECKPOINT_EVERY = 10  # Save checkpoint every N papers

# Hugging Face token (if needed for gated models)
HF_TOKEN = None  # Or set to your token string

# =============================================================================
# SETUP
# =============================================================================

print("="*60)
print("ENABLING VOICES ROUND 1 FILTERING")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Derived paths
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
OUTPUT_FILE = f"{OUTPUT_DIR}/{OUTPUT_PREFIX}_{timestamp}.xlsx"
CHECKPOINT_FILE = f"{OUTPUT_DIR}/{OUTPUT_PREFIX}_checkpoint.json"

print(f"PDF Folder: {PDF_FOLDER}")
print(f"Output File: {OUTPUT_FILE}")
print(f"Checkpoint: {CHECKPOINT_FILE}")

# =============================================================================
# INSTALL DEPENDENCIES (if needed)
# =============================================================================

print("\n[1/6] Checking dependencies...")

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    import PyPDF2
    print("✓ All dependencies available")
except ImportError as e:
    print(f"Installing missing dependencies...")
    import subprocess
    subprocess.run(["pip", "install", "-q", "transformers", "torch", "bitsandbytes", 
                    "accelerate", "PyPDF2", "pandas", "openpyxl", "--break-system-packages"])
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    import PyPDF2
    print("✓ Dependencies installed")

# =============================================================================
# FILTERING PROMPT (v3 - with improved AI classification)
# =============================================================================

FILTERING_PROMPT = """You are screening research papers for a systematic review on AI technologies that SUPPORT communication for people with dementia and/or aphasia.

CRITICAL DISTINCTIONS:
1. This review focuses on AI that HELPS people communicate (assistive/supportive), NOT AI that DETECTS or DIAGNOSES conditions
2. The technology must involve ACTUAL AI (machine learning, neural networks, NLP, adaptive algorithms) - NOT just digital/electronic tools

=== WHAT COUNTS AS AI TECHNOLOGY ===
TRUE AI includes systems that:
- Learn from data or adapt to users (machine learning, deep learning)
- Process and understand natural language (NLP, speech recognition that transcribes/understands)
- Generate responses or content (chatbots, LLMs, text generation)
- Recognize patterns (emotion detection, computer vision for understanding)
- Make intelligent decisions or predictions
- Have adaptive/personalized behavior based on user interaction

Examples of TRUE AI:
- ChatGPT, GPT-4, LLMs for conversation
- Speech recognition systems that understand and respond (Google Assistant, Alexa)
- Social robots with NLP and adaptive dialogue (not just pre-programmed responses)
- Machine learning for personalization
- Emotion recognition systems
- Intelligent AAC that predicts/generates language

=== WHAT IS NOT AI TECHNOLOGY ===
These are DIGITAL TOOLS but NOT AI:
- Basic multimedia interfaces (camera, audio recorder, drawing tools)
- Pre-recorded or pre-programmed content playback
- Simple touchscreen interfaces without learning/adaptation
- Video calling software (Skype, Zoom)
- Digital photo albums or slideshow apps
- Basic reminder apps with fixed schedules
- AAC devices with only pre-stored phrases/images (no prediction or generation)
- Devices that simply record and playback audio
- Text-to-speech that only reads pre-written text (without NLP/generation)

=== SCREENING CRITERIA ===
A paper should be INCLUDED if it meets ALL THREE:
1. POPULATION: Involves people with dementia OR aphasia (not just prevention in healthy elderly)
2. TECHNOLOGY: Involves ACTUAL artificial intelligence (see above)
3. COMMUNICATION SUPPORT: The AI is used to SUPPORT, ASSIST, ENABLE, or ENHANCE communication

=== EXCLUSION CRITERIA ===
EXCLUDE if ANY of these apply:
- DETECTION/DIAGNOSIS STUDIES: AI used to detect, diagnose, or assess dementia/aphasia from speech/language
- NO ACTUAL AI: Study uses digital technology but without machine learning, NLP, or adaptive algorithms
- BASIC MULTIMEDIA TOOLS: Touchscreen apps for photos, drawings, audio recording without AI
- BASIC AAC: Communication devices with only pre-stored content, no prediction/generation
- PRE-PROGRAMMED ONLY: Robots or devices with fixed scripts, no adaptive behavior
- PREVENTION FOCUS: Technology for preventing dementia in healthy elderly (vs. supporting those WITH dementia)
- NO DEMENTIA/APHASIA PARTICIPANTS: Technology developed FOR but not tested WITH target population
- NO DEMENTIA/APHASIA: Only healthy older adults or other populations
- CAREGIVERS ONLY: No involvement of people with dementia/aphasia
- PURE THEORY: No technology implementation or evaluation

=== FALSE POSITIVE EXAMPLES (DO NOT INCLUDE) ===
These might SEEM like AI but are NOT:
- "Multimedia storytelling app with camera, drawing tools, and audio recording for aphasia" → NO AI, just basic multimedia
- "Desktop-PDA system where users create content with images and pre-recorded audio" → NO AI, pre-recorded content
- "Touchscreen interface for reminiscence with photos and music" → NO AI unless it has ML/NLP
- "AAC device with picture symbols that users tap to produce speech" → NO AI, pre-programmed output
- "Video conferencing tool adapted for dementia" → NO AI, basic digital tool
- "Robot to prevent dementia in healthy elderly through conversation" → Wrong population (prevention, not support)

=== TRUE POSITIVE EXAMPLES (DO INCLUDE) ===
- "ChatGPT-integrated smart home for dementia communication" → YES, LLM
- "Social robot with speech recognition and adaptive dialogue for dementia" → YES, NLP + adaptive
- "AI-powered AAC that uses GPT to generate sentence suggestions for aphasia" → YES, LLM generation
- "Emotionally intelligent robot that recognizes facial expressions and adapts responses" → YES, ML + adaptive

ARTICLE TEXT:
{article_text}

Analyze this article and return ONLY a JSON object:

{{
  "screening_decision": {{
    "include": true/false,
    "confidence": 1-5,
    "decision_rationale": "Brief explanation (max 100 chars)"
  }},
  "population_assessment": {{
    "has_dementia_focus": true/false/unclear,
    "has_aphasia_focus": true/false/unclear,
    "population_details": "Brief description (max 100 chars)",
    "population_confidence": 1-5
  }},
  "technology_assessment": {{
    "has_ai_technology": true/false/unclear,
    "ai_type": ["list", "of", "AI", "types"],
    "technology_details": "Brief description (max 100 chars)",
    "technology_confidence": 1-5,
    "is_detection_study": true/false,
    "is_basic_digital_tool": true/false,
    "ai_evidence": "Quote or evidence of actual AI (max 150 chars)"
  }},
  "communication_assessment": {{
    "has_communication_support": true/false/unclear,
    "communication_type": ["verbal", "nonverbal", "social_interaction"],
    "communication_details": "Brief description (max 100 chars)",
    "communication_confidence": 1-5,
    "support_vs_detect": "support/detect/both/unclear"
  }},
  "study_metadata": {{
    "study_type": "empirical/review/theoretical/development/other",
    "publication_type": "journal_article/conference/thesis/book_chapter/other"
  }},
  "manual_review_flag": {{
    "needs_review": true/false,
    "review_reason": "Why manual review needed (if applicable)"
  }},
  "key_quote": "One sentence from text supporting AI involvement (max 150 chars)"
}}

CONFIDENCE SCALE:
1 = Very uncertain, limited information
2 = Somewhat uncertain  
3 = Moderately confident
4 = Confident
5 = Very confident, clear evidence

AI_TYPE OPTIONS: speech_recognition, NLP, machine_learning, deep_learning, computer_vision, chatbot, social_robot_AI, emotion_detection, LLM, intelligent_agent, adaptive_system, AAC_with_AI, other_AI, none, unclear

FLAG FOR MANUAL REVIEW if:
- Technology might be AI but evidence is unclear
- Paper describes "intelligent" or "smart" system but doesn't specify how
- AAC device that might have prediction/learning features
- Social robot where AI capabilities are not clearly described

Return ONLY the JSON object, no other text."""

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file."""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip(), len(reader.pages)
    except Exception as e:
        return "", 0


def extract_first_json(text):
    """Extract the FIRST complete JSON object from text."""
    if not text:
        return None
    
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
                    json_str = json_str.replace('True', 'true').replace('False', 'false')
                    json_str = json_str.replace("'", '"')
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    try:
                        return json.loads(json_str)
                    except:
                        return None
    
    return None


def screen_article(pdf_path, model, tokenizer, max_tokens=4000):
    """Screen a single article and return structured filtering decision."""
    filename = pdf_path.name if hasattr(pdf_path, 'name') else str(pdf_path)
    result = {
        '_filename': filename,
        '_pdf_path': str(pdf_path)
    }
    
    # Extract text
    text, total_pages = extract_text_from_pdf(pdf_path)
    result['_total_pages'] = total_pages
    
    if not text:
        result['_processing_status'] = 'failed_text_extraction'
        result['_error'] = 'Could not extract text from PDF'
        return result
    
    result['_extracted_chars'] = len(text)
    
    # Truncate text if needed
    tokens = tokenizer.encode(text)
    original_tokens = len(tokens)
    if len(tokens) > max_tokens:
        text = tokenizer.decode(tokens[:max_tokens])
        result['_truncated'] = True
        result['_original_tokens'] = original_tokens
    else:
        result['_truncated'] = False
    
    result['_tokens_used'] = min(len(tokens), max_tokens)
    
    # Create prompt
    prompt = FILTERING_PROMPT.format(article_text=text)
    
    # Format for chat
    messages = [
        {"role": "system", "content": "You are a research assistant screening academic articles for a systematic review. Return ONLY valid JSON, no other text."},
        {"role": "user", "content": prompt}
    ]
    
    formatted_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(formatted_prompt, return_tensors="pt").to(model.device)
    
    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=1000,
            temperature=TEMPERATURE,
            top_p=0.9,
            repetition_penalty=1.1,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    # Extract response
    response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    
    # Clear GPU memory
    del inputs, outputs
    gc.collect()
    torch.cuda.empty_cache()
    
    # Extract JSON
    screening = extract_first_json(response)
    
    if screening:
        result['_raw_screening'] = screening
        
        sd = screening.get('screening_decision', {})
        result['include'] = sd.get('include', None)
        result['confidence'] = sd.get('confidence', None)
        result['decision_rationale'] = sd.get('decision_rationale', '')
        
        pa = screening.get('population_assessment', {})
        result['has_dementia'] = pa.get('has_dementia_focus', None)
        result['has_aphasia'] = pa.get('has_aphasia_focus', None)
        result['population_details'] = pa.get('population_details', '')
        
        ta = screening.get('technology_assessment', {})
        result['has_ai'] = ta.get('has_ai_technology', None)
        result['ai_types'] = ','.join(ta.get('ai_type', [])) if isinstance(ta.get('ai_type'), list) else str(ta.get('ai_type', ''))
        result['technology_details'] = ta.get('technology_details', '')
        result['technology_confidence'] = ta.get('technology_confidence', None)
        result['is_detection_study'] = ta.get('is_detection_study', None)
        result['is_basic_digital_tool'] = ta.get('is_basic_digital_tool', None)
        result['ai_evidence'] = ta.get('ai_evidence', '')
        
        ca = screening.get('communication_assessment', {})
        result['has_communication_support'] = ca.get('has_communication_support', None)
        result['communication_types'] = ','.join(ca.get('communication_type', [])) if isinstance(ca.get('communication_type'), list) else str(ca.get('communication_type', ''))
        result['communication_details'] = ca.get('communication_details', '')
        result['support_vs_detect'] = ca.get('support_vs_detect', '')
        
        sm = screening.get('study_metadata', {})
        result['study_type'] = sm.get('study_type', '')
        result['publication_type'] = sm.get('publication_type', '')
        
        mrf = screening.get('manual_review_flag', {})
        result['needs_manual_review'] = mrf.get('needs_review', False)
        result['review_reason'] = mrf.get('review_reason', '')
        
        result['key_quote'] = screening.get('key_quote', '')
        result['_processing_status'] = 'success'
    else:
        result['_processing_status'] = 'failed_json_extraction'
        result['_error'] = 'Could not extract valid JSON from response'
        result['_raw_response_preview'] = response[:500] if response else 'No response'
    
    return result


def save_checkpoint(results, processed_files, checkpoint_path):
    """Save checkpoint to JSON file."""
    checkpoint = {
        'results': results,
        'processed_files': list(processed_files),
        'timestamp': datetime.now().isoformat(),
        'stats': {
            'total_processed': len(results),
            'success': sum(1 for r in results if r.get('_processing_status') == 'success'),
            'include': sum(1 for r in results if r.get('include') == True),
            'exclude': sum(1 for r in results if r.get('include') == False),
            'failed': sum(1 for r in results if r.get('_processing_status') != 'success')
        }
    }
    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint, f, indent=2, default=str)


def load_checkpoint(checkpoint_path):
    """Load checkpoint from JSON file."""
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, 'r') as f:
            checkpoint = json.load(f)
        return checkpoint.get('results', []), set(checkpoint.get('processed_files', []))
    return [], set()


def save_results(results, output_path):
    """Save results to Excel file with multiple sheets."""
    df = pd.DataFrame(results)
    
    # Categorize
    def categorize(row):
        if row.get('_processing_status') != 'success':
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
        'study_type', 'needs_manual_review', 'review_reason', 'key_quote', '_category'
    ]
    key_cols = [c for c in key_cols if c in df.columns]
    
    # Save to Excel
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df[key_cols].to_excel(writer, sheet_name='Summary', index=False)
        
        if len(df[df['_category'] == 'Include']) > 0:
            df[df['_category'] == 'Include'][key_cols].to_excel(writer, sheet_name='Include', index=False)
        
        if len(df[df['_category'] == 'Exclude']) > 0:
            df[df['_category'] == 'Exclude'][key_cols].to_excel(writer, sheet_name='Exclude', index=False)
        
        if len(df[df['_category'] == 'Manual Review']) > 0:
            df[df['_category'] == 'Manual Review'][key_cols].to_excel(writer, sheet_name='Manual Review', index=False)
        
        if len(df[df['_category'] == 'Failed']) > 0:
            df[df['_category'] == 'Failed'].to_excel(writer, sheet_name='Failed', index=False)
    
    return df


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    
    # Check GPU
    print("\n[2/6] Checking GPU...")
    if torch.cuda.is_available():
        print(f"✓ GPU available: {torch.cuda.get_device_name(0)}")
        print(f"  Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    else:
        print("⚠ No GPU detected - this will be slow!")
    
    # Load model
    print("\n[3/6] Loading model...")
    print(f"  Model: {MODEL_NAME}")
    
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True
    )
    
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        token=HF_TOKEN
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=quantization_config,
        device_map="auto",
        token=HF_TOKEN
    )
    
    print("✓ Model loaded")
    
    # Find PDFs
    print("\n[4/6] Finding PDFs...")
    pdf_folder = Path(PDF_FOLDER)
    pdf_files = sorted(pdf_folder.glob("*.pdf"))
    
    if TEST_MODE_LIMIT:
        pdf_files = pdf_files[:TEST_MODE_LIMIT]
        print(f"⚠ TEST MODE: Limited to {TEST_MODE_LIMIT} files")
    
    print(f"✓ Found {len(pdf_files)} PDF files")
    
    # Load checkpoint
    print("\n[5/6] Loading checkpoint...")
    results, processed_files = load_checkpoint(CHECKPOINT_FILE)
    print(f"  Previously processed: {len(processed_files)} files")
    
    # Process articles
    print("\n[6/6] Processing articles...")
    print("-" * 60)
    
    from tqdm import tqdm
    
    for i, pdf_path in enumerate(tqdm(pdf_files, desc="Screening articles")):
        filename = pdf_path.name
        
        # Skip if already processed
        if filename in processed_files:
            continue
        
        # Screen article
        result = screen_article(pdf_path, model, tokenizer, MAX_TOKENS_PER_ARTICLE)
        results.append(result)
        processed_files.add(filename)
        
        # Progress update
        status = result.get('_processing_status', 'unknown')
        include = result.get('include', None)
        status_str = "INCLUDE" if include else ("EXCLUDE" if include == False else "FAILED")
        
        # Checkpoint
        if len(results) % CHECKPOINT_EVERY == 0:
            save_checkpoint(results, processed_files, CHECKPOINT_FILE)
            tqdm.write(f"  [Checkpoint saved: {len(results)} processed]")
    
    # Final save
    print("\n" + "=" * 60)
    print("SAVING RESULTS")
    print("=" * 60)
    
    save_checkpoint(results, processed_files, CHECKPOINT_FILE)
    df = save_results(results, OUTPUT_FILE)
    
    # Statistics
    stats = df['_category'].value_counts()
    print(f"\n✓ Processing complete!")
    print(f"\nResults saved to: {OUTPUT_FILE}")
    print(f"\nStatistics:")
    print(f"  Total processed: {len(results)}")
    for cat in ['Include', 'Exclude', 'Manual Review', 'Failed']:
        count = stats.get(cat, 0)
        print(f"  {cat}: {count}")
    
    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
