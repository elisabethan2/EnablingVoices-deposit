#!/usr/bin/env python3
"""
Enabling Voices — Full-Text Structured Extraction (Section 4 Analysis)
=======================================================================
Runs Llama 3.1 8B over the March 2026 candidate set (n=10), extracting
structured data for all Section 4 analysis dimensions.

SCOPE / PROVENANCE NOTE
-----------------------
This script ran on the pre-final candidate set of 10 records as it stood in
March 2026, BEFORE adjudication narrowed the final included set to 6 studies.
Four of these candidates were subsequently excluded at full text and are NOT
in the final 6: COV5183 (Favela), COV11296 (Rudzicz), COV342 (Faisal), and
COV5639 (Rass). The final included set is recorded in
data/screening/final_inclusion_record.xlsx (N=6).

The extraction output is deposited ONLY to document full-text extraction
failure modes (see paper §3.6); it was NOT used for the reported results. The
n=10 candidate list below is therefore left intact as the historical record of
exactly what this run processed.

Input:  .txt full-text files (one per paper)
Output: Excel workbook with one row per paper across multiple thematic sheets

Run:          python enabling_voices_extraction_fulltext.py
Background:   nohup python enabling_voices_extraction_fulltext.py > extraction.log 2>&1 &
Progress:     tail -f extraction.log
"""

# =============================================================================
# VERSION NOTE -- read before using this file
# =============================================================================
# This is the CORRECTED companion to enabling_voices_extraction_fulltext.py.
#
# The as-run script is preserved unchanged in this directory. It is the code
# that actually produced the deposited extraction output, and its
# INCLUDED_PAPERS reflects the PRE-ADJUDICATION candidate set of ten records as
# it stood on 2026-03-14. It is the provenance record of that run and is not
# edited to match the final set.
#
# This file differs from it in exactly one respect: INCLUDED_PAPERS lists the
# six studies in the authoritative final record
# (data/screening/final_inclusion_record.xlsx). Nothing else is changed.
#
# This corrected version has NOT been run. Full-text extraction was trialled
# and abandoned; it contributed nothing to the reported results, and the
# deposited output is retained only to document its failure modes. This file
# exists so the deposit does not contain a script asserting an included set
# that contradicts the final record -- not to invite a re-run.
# =============================================================================

import os
import json
import re
import gc
from pathlib import Path
from datetime import datetime
import pandas as pd

# =============================================================================
# CONFIGURATION — UPDATE PATHS FOR YOUR UCLOUD SETUP
# =============================================================================

PDF_FOLDER  = "/work/EnablingPapers150126"   # UPDATE: folder containing COV*.pdf files
OUTPUT_DIR  = "/work/EnablingPapers150126/outputs"  # UPDATE: mounted storage output folder
OUTPUT_PREFIX   = "enabling_voices_extraction_fulltext"

MODEL_NAME  = "meta-llama/Llama-3.1-8B-Instruct"

# Reduces KV-cache memory fragmentation on V100 / A100
os.environ.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")
HF_TOKEN    = None                           # Set to your HF token string if needed
TEMPERATURE = 0.05                           # Very low: extraction should be deterministic
MAX_NEW_TOKENS = 3000                        # JSON schema ~1800-2500 tokens when fully populated

TEST_MODE_LIMIT   = None    # Set to e.g. 2 for a quick test run
MAX_INPUT_TOKENS  = 8000    # Hard ceiling on input tokens fed to the model.
                            # The V100 (32 GB) with 4-bit model needs input+output
                            # KV cache to fit in ~24 GB. At fp16, 10k input +
                            # 2k output ~ 10 GB KV cache — safely within budget.
                            # Priority: keep abstract + intro + methods + results.

# The March 2026 candidate set (n=10) — see the scope/provenance note in the
# module docstring. Four of these were later excluded at full text; the dict is
# kept intact as the historical record of what this run processed (not the final 6).
# Keys = COV ID (used to locate the .txt file); values = short label for logging.
# NOTE: this list differs from the as-run script. See the VERSION NOTE above.
# Removed: COV5183 Favela (labelled "J. 2023" there, from an LLM-truncated
# author initial), COV11296 Rudzicz, COV342 Faisal, COV5639 Rass -- all four
# excluded on final full-text review. Bailey is 2026 here (Aphasiology
# 2026;40(1):150-165); the as-run script and its outputs carry the 2025
# online-first date.
INCLUDED_PAPERS = {
    "COV2660":  "Bailey 2026     — Aphasia-GPT",
    "COV510":   "Sheehy 2024     — VR virtual partner (PwD)",
    "COV5607":  "Obiorah 2021    — AI-AAC prototypes for PwA",
    "COV5630":  "Purohit 2023    — ChatGPT word retrieval (PwA)",
    "COV1113":  "Stara 2021      — Anne virtual agent (PwD)",
    "COV5688":  "Xygkou 2024     — MindTalker GPT-4 (PwD)",
}

# =============================================================================
# EXTRACTION PROMPT
# =============================================================================
# Design notes:
#   - System prompt frames the research context and the comparative PWA/PWD lens.
#   - User prompt carries the article text and the full schema.
#   - All categorical fields use controlled vocabularies so output can be
#     used directly for charts without post-hoc recoding.
#   - Per-field uncertainty flags allow the team to prioritise what to
#     verify on first reading, without treating all AI output as equally reliable.
#   - EMCA/interactional gap detection is built into interactional_aspects
#     and transcription_approach — key for the review's methodological argument.
#   - AI communicative role uses the four-category taxonomy from Section 4.3.

SYSTEM_PROMPT = """You are a specialist research assistant supporting a scoping review on AI technologies that support communication for people with dementia (PwD) or people with aphasia (PwA). The review is titled "Enabling Voices."

Your role is to extract structured information from full-text research papers. The research team includes conversation analysts, speech-language therapists, linguists, and HCI researchers. Their analysis will compare how dementia research and aphasia research differ across all dimensions: population characteristics, AI technologies, communicative roles, interaction design, and methodology.

Extraction principles:
- Quote or closely paraphrase the paper; do not generalise or infer beyond what is stated.
- Use "not_reported" for text fields where information is absent; use null for optional numeric fields.
- For controlled-vocabulary fields, choose the closest matching option from the list provided — do not invent new categories.
- For list fields, include all that apply; use an empty list [] if none apply.
- Flag uncertainty honestly using the per-field uncertainty mechanism.
- CRITICAL distinction: only list interactional phenomena the paper ACTUALLY ANALYSES using interaction data (e.g. transcripts, video, logs). A paper using questionnaires or Likert scales about "communication quality" is NOT analysing turn-taking or repair — use none_specified for those fields.
- Distinguish between what authors CLAIM and what their methods actually EVIDENCE.
"""

EXTRACTION_PROMPT_TEMPLATE = """Extract structured information from the article below for the Enabling Voices scoping review.

ARTICLE TEXT:
{article_text}

Return ONLY a single valid JSON object matching the schema below.
Do NOT write any text before the opening { or after the closing }.
Do NOT use markdown code fences (no ```json).
Do NOT add comments inside the JSON.
Start your response with { and end it with }.

{{
  "bibliographic": {{
    "cov_id": "COV identifier if visible in text, else not_reported",
    "title": "Full title of the paper",
    "first_author_surname": "First author surname only",
    "year": 2024,
    "journal_or_venue": "Journal name or conference/book title",
    "country_of_study": "Country where the study was conducted (not where published). If multiple countries, list all.",
    "doi": "DOI if present, else not_reported"
  }},

  "population": {{
    "target_group": "dementia / aphasia / both",
    "diagnosis_details": "Specific diagnosis(es), e.g. 'mild-to-moderate Alzheimer\\'s disease', 'chronic post-stroke aphasia (Broca\\'s type)', 'primary progressive aphasia'",
    "diagnosis_criteria": "How diagnosis was confirmed, e.g. 'MMSE score ≤24', 'clinical diagnosis by neurologist', 'WAB-R aphasia quotient', 'not_reported'",
    "severity": "Severity level if reported, e.g. 'mild-to-moderate', 'advanced', 'WAB-R AQ range 25-75', 'not_reported'",
    "n_with_condition": "Integer: number of participants WITH the diagnosis who used the technology. Do not include caregivers, raters, or healthy controls here.",
    "total_n_in_study": "Integer: all participants in the study including caregivers, controls, raters",
    "age_info": "Age details, e.g. 'mean 74.3 (SD 6.2)', 'range 65–89', 'not_reported'",
    "gender_info": "Gender breakdown, e.g. '8 female, 4 male', 'not_reported'",
    "language_background": "Participants' language(s), e.g. 'English-speaking', 'Dutch', 'bilingual Spanish-English', 'not_reported'",
    "other_participants": "Others in the study, e.g. 'caregivers (n=12)', 'SLTs (n=3)', 'healthy controls', 'none'",
    "recruitment_method": "How participants were recruited, e.g. 'via care home', 'clinical referral', 'convenience sample', 'not_reported'",
    "consent_capacity_notes": "Any reported considerations around consent or decision-making capacity, or 'not_reported'",
    "uncertainty_flags": ["List any population fields where the paper is ambiguous or information was inferred rather than stated"]
  }},

  "study_design": {{
    "study_type": "One of: RCT / quasi_experimental / pre_post / pilot_study / feasibility_study / case_study / ethnographic / design_study / co_design / participatory_design / mixed_methods / qualitative / descriptive / review / theoretical / other",
    "study_type_detail": "More specific label, e.g. 'single-arm pre-post feasibility study', 'multi-session ethnographic case study'",
    "study_aim": "The stated aim or research question(s), max 250 characters",
    "duration_of_data_collection": "e.g. '6 weeks', 'single 30-minute session', 'not_reported'",
    "number_of_sessions": "e.g. '3 sessions', 'single session', 'not_reported'",
    "theoretical_framework": ["Named theories, models, or frameworks explicitly cited, e.g. 'person_centered_care', 'scaffolding_theory', 'participatory_design', 'ICF_framework', 'social_model_of_disability', 'HCI_usability_framework', 'conversation_analysis', 'none_stated'"],
    "framework_detail": "How the theory/framework is actually used in the study, or 'not_reported'"
  }},

  "setting": {{
    "setting_type": "One of: home / care_facility / hospital_clinic / rehabilitation_centre / university_lab / community / online_remote / multiple / not_reported",
    "setting_detail": "More specific description, e.g. 'memory care unit in assisted living facility', 'participants\\' own homes via telehealth'",
    "deployment_context": "How technology was deployed: 'researcher_present', 'unsupervised_home_use', 'clinician_supervised', 'group_session', 'not_reported'"
  }},

  "ai_technology": {{
    "technology_name": "Specific system/device/platform name, e.g. 'MindTalker', 'Pepper robot with GPT-4', 'Aphasia-GPT prototype'",
    "technology_type": "One of: social_robot / chatbot_text / virtual_conversational_agent / smart_speaker_VUI / AAC_device / mobile_app / web_platform / mixed / other",
    "physical_form": "One of: embodied_robot / screen_based_avatar / screen_text_only / smartphone_tablet / smart_speaker_no_screen / wearable / mixed / not_applicable",
    "anthropomorphisation": "How human-like is the system? One of: humanoid_robot / non_humanoid_robot / human_avatar / cartoon_avatar / voice_only / text_only / not_applicable",
    "ai_components": ["Specific AI components, e.g. 'GPT-4_language_model', 'Google_Cloud_ASR', 'emotion_recognition_CNN', 'custom_dialogue_manager', 'text_to_speech_TTS', 'intent_classification', 'word_prediction_model', 'reinforcement_learning'"],
    "ai_component_details": "How the AI components work together — brief system architecture, max 350 characters",
    "commercial_or_custom": "One of: commercial_off_the_shelf / custom_built / modified_commercial / research_prototype / not_reported",
    "named_commercial_systems": "Any commercial AI systems named, e.g. 'ChatGPT', 'GPT-4', 'Amazon Alexa', 'Google ASR', or 'none'",
    "input_modalities": ["How the USER communicates TO the technology: 'speech', 'text_typing', 'touchscreen_symbols', 'gesture', 'eye_gaze', 'physical_buttons', 'other'"],
    "output_modalities": ["How the technology responds TO the user: 'synthesised_speech', 'text_display', 'static_images', 'video', 'robot_movement', 'robot_facial_expression', 'haptic_feedback', 'sound_effects', 'other'"],
    "language_of_system": "Language(s) the system operates in, e.g. 'English', 'Spanish and English', 'not_reported'",
    "adaptivity": "Does the system adapt to the individual user over time or in real-time? Describe specifically, or 'none' / 'not_reported'",
    "autonomy_level": "One of: fully_autonomous / semi_autonomous_with_prompts / wizard_of_oz / human_operated / not_clear",
    "development_stage": "One of: early_prototype / developed_prototype / pilot_system / commercial_product / not_reported"
  }},

  "communicative_role": {{
    "primary_role": "Choose the SINGLE best fit: conversation_partner / facilitator_of_human_human_interaction / communication_scaffold_prompter / language_simplifier_translator",
    "primary_role_justification": "One sentence quoting or closely paraphrasing the paper to justify this classification, max 200 characters",
    "secondary_roles": ["Any additional roles the AI plays, using same vocabulary as primary_role, or empty list []"],
    "communication_functions_targeted": ["Which communicative functions the technology targets: 'turn_taking', 'topic_management_initiation', 'word_finding_support', 'narrative_production', 'social_engagement', 'emotional_expression', 'caregiver_mediation', 'daily_communication_needs', 'speech_production', 'language_comprehension', 'other'"],
    "communication_modalities_in_focus": ["Modalities the HUMANS use that are studied/supported: 'spoken_language', 'written_language', 'gesture', 'facial_expression', 'prosody', 'gaze', 'body_posture', 'symbol_based_communication', 'multimodal'"],
    "interaction_partner_role": "Who interacts with the technology: 'person_with_condition_directly' / 'person_with_condition_via_caregiver_support' / 'caregiver_only' / 'group' / 'dyadic_peer' / 'therapist_mediated'",
    "ai_replaces_or_augments": "Does the AI replace human interaction or augment/support human-human interaction? One of: replaces_human_interaction / augments_human_interaction / both / not_clear",
    "uncertainty_flags": ["Any fields in this block where classification was uncertain or based on inference"]
  }},

  "interaction_analysis": {{
    "data_collection_methods": ["Methods used: 'video_recording', 'audio_recording', 'interaction_log_data', 'screen_recording', 'interview', 'questionnaire_survey', 'standardised_test', 'observation_field_notes', 'think_aloud', 'physiological_measures', 'other'"],
    "analysis_approaches": ["All analytical approaches used. CRITICAL RULES for conversation_analysis_CA: ONLY assign this if the paper uses FORMAL CA methodology — meaning sequential analysis of turns using actual interaction data (audio/video recordings or transcripts), with attention to turn design, sequence organisation, or repair. A paper that uses questionnaires, Likert scales, rating scales, or surveys about communication quality is NOT doing CA — use descriptive_statistics or thematic_analysis instead. A paper that codes interaction data using a predefined scheme is interaction_coding_scheme, NOT CA. If transcription_approach is not_applicable or not_reported, do NOT assign conversation_analysis_CA. Options: 'conversation_analysis_CA', 'multimodal_interaction_analysis', 'discourse_analysis', 'thematic_analysis', 'content_analysis', 'descriptive_statistics', 'inferential_statistics', 'usability_metrics_SUS_etc', 'standardised_language_assessment', 'acoustic_analysis', 'NLP_automated_metrics', 'interaction_coding_scheme', 'grounded_theory', 'framework_analysis', 'narrative_analysis', 'other'"],
    "analysis_detail": "Describe the analysis approach in more detail, max 300 characters",
    "interactional_aspects_studied": ["ONLY list if paper ACTUALLY ANALYSES using interaction data (transcripts/video/logs), NOT if assessed via questionnaire: 'turn_taking', 'repair_sequences', 'topic_management', 'initiative_and_response', 'response_latency', 'overlapping_talk', 'word_finding', 'circumlocution', 'perseveration', 'comprehension_breakdown', 'engagement_behaviours', 'none_specified'"],
    "transcription_approach": "One of: Jefferson_notation / CHAT_CLAN / orthographic_transcription / automatic_ASR_transcript / interaction_coding_only / not_applicable / not_reported",
    "outcome_measures": ["Specific measures: 'WAB_R', 'ASHA_FACS', 'CIU_count', 'MLU', 'turn_count', 'topic_initiation_rate', 'engagement_rating_scale', 'conversation_duration', 'word_retrieval_accuracy', 'SUS_score', 'custom_Likert', 'qualitative_themes', 'MMSE', 'other'"],
    "emca_gap_flag": "Does the paper study communication outcomes WITHOUT analysing the interactional process itself? LOGIC RULES — apply these in order: (1) If analysis_approaches contains conversation_analysis_CA or multimodal_interaction_analysis AND transcription_approach is not not_applicable/not_reported → use no_gap_process_analysed. (2) If analysis_approaches contains only descriptive_statistics, inferential_statistics, usability_metrics_SUS_etc, thematic_analysis, or questionnaire-based methods → use yes_outcome_only. (3) If the paper analyses some interaction data but primarily reports outcome measures → use partial. (4) If not applicable (e.g. design paper with no interaction data) → use not_applicable. One of: yes_outcome_only / no_gap_process_analysed / partial / not_applicable",
    "emca_gap_note": "Brief note on what interactional detail is absent that an EMCA researcher would want, or 'none', max 200 characters"
  }},

  "key_findings": {{
    "main_findings": "Summary of key findings on AI-supported communication, max 400 characters",
    "communication_outcomes": "Specific findings about communication or interaction, max 300 characters",
    "user_experience": "Findings on usability, acceptability, or satisfaction (including caregiver perspective if relevant), max 200 characters",
    "challenges_reported": "Technical, interactional, or implementation challenges, max 250 characters",
    "authors_conclusions": "Authors' own stated conclusions, closely paraphrased, max 300 characters",
    "pwa_pwd_comparative_note": "If this paper compares PwA and PwD, OR if findings have implications for the other population not studied, note this here. Otherwise 'not_applicable'."
  }},

  "extraction_quality": {{
    "overall_confidence": "Integer 1–5: (1=very limited info, 2=major gaps, 3=most fields covered, 4=good coverage minor gaps, 5=comprehensive)",
    "fields_with_low_confidence": ["List field names where extraction confidence is low"],
    "general_notes": "Any issues, ambiguities, or notes for the research team, max 250 characters"
  }}
}}"""


# =============================================================================
# SETUP
# =============================================================================

print("=" * 65)
print("ENABLING VOICES — FULL-TEXT STRUCTURED EXTRACTION")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 65)

os.makedirs(OUTPUT_DIR, exist_ok=True)
timestamp   = datetime.now().strftime('%Y%m%d_%H%M%S')
OUTPUT_FILE = f"{OUTPUT_DIR}/{OUTPUT_PREFIX}_{timestamp}.xlsx"
CHECKPOINT_FILE = f"{OUTPUT_DIR}/{OUTPUT_PREFIX}_checkpoint.json"

print(f"PDF folder       : {PDF_FOLDER}")
print(f"Output file      : {OUTPUT_FILE}")
print(f"Checkpoint       : {CHECKPOINT_FILE}")
print(f"Papers to process: {len(INCLUDED_PAPERS)}")


# =============================================================================
# DEPENDENCIES
# =============================================================================

print("\n[1/5] Checking dependencies...")
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    print("  ✓ Core ML packages available")
except ImportError:
    print("  Installing core ML packages...")
    import subprocess
    subprocess.run([
        "pip", "install", "-q",
        "transformers", "torch", "bitsandbytes", "accelerate",
        "pandas", "openpyxl", "--break-system-packages"
    ])
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# PyMuPDF is the primary PDF extractor; PyPDF2 is the fallback.
# PyMuPDF handles two-column layouts and extracts table content in reading order.
try:
    import fitz  # PyMuPDF
    PDF_BACKEND = "pymupdf"
    print("  ✓ PDF backend: PyMuPDF (fitz)")
except ImportError:
    print("  Installing PyMuPDF...")
    import subprocess
    subprocess.run(["pip", "install", "-q", "pymupdf", "--break-system-packages"])
    try:
        import fitz
        PDF_BACKEND = "pymupdf"
        print("  ✓ PDF backend: PyMuPDF — just installed")
    except ImportError:
        PDF_BACKEND = "pypdf2"
        print("  ⚠ PyMuPDF unavailable — falling back to PyPDF2 (lower quality)")
        try:
            import PyPDF2
        except ImportError:
            subprocess.run(["pip", "install", "-q", "PyPDF2", "--break-system-packages"])
            import PyPDF2

print("✓ All dependencies ready")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_pdf_pymupdf(pdf_path: Path) -> str:
    """
    Extract text from a PDF using PyMuPDF (fitz).

    Uses reading-order sort for correct two-column layout handling.
    Strips repeated page headers/footers heuristically (short lines
    appearing on 3+ pages).
    """
    doc = fitz.open(str(pdf_path))
    pages_text = []
    for page in doc:
        page_text = page.get_text("text", sort=True)
        pages_text.append(page_text)
    doc.close()

    # Identify running headers/footers: short lines appearing on 3+ pages
    from collections import Counter
    all_lines = []
    for pt in pages_text:
        all_lines.extend(pt.splitlines())
    short_line_counts = Counter(
        ln.strip() for ln in all_lines if 0 < len(ln.strip()) < 80
    )
    repeated_chrome = {ln for ln, cnt in short_line_counts.items() if cnt >= 3}

    cleaned_pages = []
    for pt in pages_text:
        lines = [ln for ln in pt.splitlines() if ln.strip() not in repeated_chrome]
        cleaned_pages.append("\n".join(lines))

    full_text = "\n\n".join(cleaned_pages)
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)
    return full_text.strip()


def extract_pdf_pypdf2(pdf_path: Path) -> str:
    """Fallback PDF extractor using PyPDF2."""
    import PyPDF2
    text_parts = []
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts).strip()


def load_fulltext(cov_id: str, folder: str) -> str | None:
    """
    Locate and extract the full text for a given COV ID.

    Search order:
      1. COV*.pdf  — preferred; extracted with PyMuPDF (or PyPDF2 fallback)
      2. COV*.txt  — accepted as a fallback if no PDF is present
         (copy-pasted .txt files may be missing table content)
    """
    folder_path = Path(folder)

    # 1. Try PDF first
    # Match COV510_*.pdf but not COV5105_*.pdf: require _ after the ID
    pdf_matches = sorted(folder_path.glob(f"{cov_id}_*.pdf"))
    if not pdf_matches:  # fallback for IDs without underscore separator
        pdf_matches = sorted(folder_path.glob(f"{cov_id}.pdf"))
    if pdf_matches:
        pdf_path = pdf_matches[0]
        print(f"    Source: PDF ({pdf_path.name}) — backend: {PDF_BACKEND}")
        try:
            if PDF_BACKEND == "pymupdf":
                return extract_pdf_pymupdf(pdf_path)
            else:
                return extract_pdf_pypdf2(pdf_path)
        except Exception as e:
            print(f"    WARNING: PDF extraction failed ({e}) — trying txt fallback")

    # 2. Fall back to .txt
    txt_matches = sorted(folder_path.glob(f"{cov_id}_*.txt"))
    if not txt_matches:
        txt_matches = sorted(folder_path.glob(f"{cov_id}.txt"))
    if txt_matches:
        print(f"    WARNING: No PDF found — using .txt (tables may be incomplete)")
        try:
            return txt_matches[0].read_text(encoding="utf-8", errors="replace").strip()
        except Exception as e:
            print(f"    ERROR reading txt: {e}")
            return None

    print(f"    WARNING: No PDF or txt found for {cov_id} in {folder}")
    return None


def parse_json_response(text: str) -> dict | None:
    """
    Extract a JSON object from the model response, handling common Llama artefacts:
      - Text preamble before the opening brace
      - Markdown code fences (```json ... ```)
      - Trailing commas before } or ]
      - Truncated output (generation cut off mid-object) — repair by
        closing all open braces/brackets and retrying parse
    """
    if not text:
        return None

    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)
    text = text.strip()

    # Find the first { — everything before it is preamble
    start = text.find("{")
    if start == -1:
        return None
    text = text[start:]

    # Fix trailing commas
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # Attempt 1: clean parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2: truncation repair
    # Walk the string tracking brace/bracket depth; cut at the last point
    # where depth returns to 0 (i.e. the outermost object closed cleanly).
    # If it never closes (truncated output), add the missing closers.
    depth = 0
    in_string = False
    escape = False
    last_zero_close = -1
    stack = []   # track { vs [

    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append(ch)
            depth += 1
        elif ch in "}]":
            if stack:
                stack.pop()
            depth -= 1
            if depth == 0:
                last_zero_close = i + 1

    if last_zero_close > 0:
        # The object closed cleanly somewhere — use up to that point
        candidate = text[:last_zero_close]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Attempt 3: close truncated output by appending missing closers
    # stack now contains unclosed openers in order; close them in reverse
    closers = {"{": "}", "[": "]"}
    suffix = "".join(closers[ch] for ch in reversed(stack))
    repaired = text.rstrip().rstrip(",") + "\n" + suffix
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None


def merge_chunk_results(chunks: list) -> dict:
    """
    Merge extraction dicts from multiple chunks into one.

    Rules:
    - Scalars:  first non-empty, non-"not_reported", non-null value wins.
                Later chunks can still fill fields left empty by earlier ones.
    - Lists:    union across all chunks, deduplicate, preserve order.
    - Numeric:  prefer the largest value (e.g. n_with_condition from the
                methods section is more reliable than a passing mention).
    - extraction_quality.overall_confidence: take the minimum (most conservative).
    """
    EMPTY = {"not_reported", "not_applicable", "none_stated", "none", "",
             "not_clear", "not_reported.", "N/A", "n/a"}

    def is_empty(v):
        if v is None:
            return True
        if isinstance(v, list):
            return len(v) == 0
        return str(v).strip() in EMPTY

    merged = {}

    def _merge_level(base, overlay, path=""):
        for key, val in overlay.items():
            full_path = f"{path}.{key}" if path else key
            if key not in base or is_empty(base[key]):
                base[key] = val
            elif isinstance(val, list) and isinstance(base[key], list):
                # Union lists, preserving order, deduplicating
                seen = set(str(x) for x in base[key])
                for item in val:
                    if str(item) not in seen and not is_empty(item):
                        base[key].append(item)
                        seen.add(str(item))
            elif isinstance(val, dict) and isinstance(base[key], dict):
                _merge_level(base[key], val, full_path)
            elif full_path == "extraction_quality.overall_confidence":
                # Take minimum confidence across chunks
                try:
                    base[key] = min(int(base[key]), int(val))
                except (ValueError, TypeError):
                    pass  # keep existing
            elif isinstance(val, (int, float)) and isinstance(base[key], (int, float)):
                # For counts like n_with_condition, take the larger value
                try:
                    if float(val) > float(base[key]):
                        base[key] = val
                except (ValueError, TypeError):
                    pass
            # For strings: keep existing non-empty value (first wins)

    for chunk in chunks:
        _merge_level(merged, chunk)

    return merged


def flatten_to_row(data: dict, cov_id: str, label: str) -> dict:
    """
    Flatten nested JSON into a single dict row for DataFrame.
    Lists are joined with ' | '. Nested keys use dot notation.
    """
    row = {"_cov_id": cov_id, "_label": label}

    def _recurse(obj, prefix=""):
        for key, val in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(val, dict):
                _recurse(val, full_key)
            elif isinstance(val, list):
                row[full_key] = " | ".join(str(v) for v in val)
            else:
                row[full_key] = val

    if isinstance(data, dict):
        _recurse(data)
    return row


def save_checkpoint(results: list, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  ✓ Checkpoint saved ({len(results)} papers processed)")


def load_checkpoint(path: str) -> list:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"  ✓ Loaded checkpoint ({len(data)} papers previously processed)")
        return data
    return []


# =============================================================================
# LOAD MODEL
# =============================================================================

print("\n[2/5] Checking GPU and loading model...")

if torch.cuda.is_available():
    print(f"  ✓ GPU: {torch.cuda.get_device_name(0)}")
    print(f"  ✓ VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
else:
    print("  ⚠ No GPU detected — inference will be slow")

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True
)

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    token=HF_TOKEN,
    trust_remote_code=True
)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    quantization_config=quantization_config,
    device_map="auto",
    token=HF_TOKEN,
    trust_remote_code=True
)

print(f"  ✓ Model loaded: {MODEL_NAME}")


# =============================================================================
# PROCESS PAPERS
# =============================================================================

print(f"\n[3/5] Processing {len(INCLUDED_PAPERS)} papers...")

results        = load_checkpoint(CHECKPOINT_FILE)
processed_ids  = {r["_cov_id"] for r in results
                   if r.get("_processing_status") == "success"}

papers = list(INCLUDED_PAPERS.items())
if TEST_MODE_LIMIT:
    papers = papers[:TEST_MODE_LIMIT]
    print(f"  ⚠ TEST MODE: limited to {TEST_MODE_LIMIT} papers")

for i, (cov_id, label) in enumerate(papers):

    if cov_id in processed_ids:
        print(f"  [{i+1:02d}/{len(papers)}] SKIP (done): {cov_id} — {label}")
        continue

    print(f"\n  [{i+1:02d}/{len(papers)}] {cov_id} — {label}")

    # ── Load full text ──────────────────────────────────────────────────────
    text = load_fulltext(cov_id, PDF_FOLDER)
    if not text:
        results.append({
            "_cov_id": cov_id,
            "_label": label,
            "_processing_status": "failed_no_text"
        })
        save_checkpoint(results, CHECKPOINT_FILE)
        continue

    word_count = len(text.split())
    token_estimate = word_count * 1.35   # rough tokens-per-word for academic English
    print(f"    Words: {word_count:,}  (~{token_estimate:,.0f} tokens)")

    # ── Chunked extraction: split article into overlapping windows ──────────
    # The V100 (32 GB) cannot fit the full schema + a long article in one pass.
    # Solution: split the article into overlapping token windows; run the full
    # schema on each chunk; merge by preferring non-empty values and unioning
    # list fields. Short papers get one chunk; Rass 2025 gets ~5.

    # Measure template overhead once
    template_tokens = tokenizer(
        EXTRACTION_PROMPT_TEMPLATE.format(article_text=""),
        return_tensors="pt"
    )["input_ids"].shape[1]

    CHUNK_SIZE    = MAX_INPUT_TOKENS - template_tokens - 100  # article tokens per chunk
    CHUNK_OVERLAP = 200   # token overlap between consecutive chunks

    if CHUNK_SIZE < 500:
        CHUNK_SIZE = 500

    # Tokenise full article
    article_token_ids = tokenizer(
        text, return_tensors="pt", truncation=False
    )["input_ids"][0]
    total_article_tokens = len(article_token_ids)

    # Build non-overlapping start positions, then add overlap
    stride = CHUNK_SIZE - CHUNK_OVERLAP
    starts = list(range(0, total_article_tokens, stride))
    # Ensure final window always reaches the end
    if total_article_tokens > CHUNK_SIZE and starts[-1] + CHUNK_SIZE < total_article_tokens:
        starts.append(max(0, total_article_tokens - CHUNK_SIZE))
    # Deduplicate preserving order
    seen_s = set()
    starts = [s for s in starts if not (s in seen_s or seen_s.add(s))]
    n_chunks = len(starts)

    print(f"    Article tokens: {total_article_tokens:,} "
          f"(template: {template_tokens:,}, chunk budget: {CHUNK_SIZE:,}) "
          f"→ {n_chunks} chunk(s)")

    chunk_results = []

    for chunk_idx, start in enumerate(starts):
        end        = min(start + CHUNK_SIZE, total_article_tokens)
        chunk_ids  = article_token_ids[start:end]
        chunk_text = tokenizer.decode(chunk_ids, skip_special_tokens=True)

        print(f"    Chunk {chunk_idx+1}/{n_chunks}: tokens {start:,}–{end:,}")

        user_message = EXTRACTION_PROMPT_TEMPLATE.format(article_text=chunk_text)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message}
        ]
        formatted = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(formatted, return_tensors="pt")
        inputs = {k: v.to(model.device) for k, v in inputs.items()}

        torch.cuda.empty_cache()
        gc.collect()

        outputs = None
        try:
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=MAX_NEW_TOKENS,
                    do_sample=False,
                    repetition_penalty=1.05,
                    pad_token_id=tokenizer.eos_token_id
                )
            response = tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True
            )
            parsed = parse_json_response(response)
            if parsed:
                chunk_results.append(parsed)
                print(f"      ✓ chunk {chunk_idx+1} OK")
            else:
                print(f"      ✗ chunk {chunk_idx+1} parse failed — skipped")

        except torch.cuda.OutOfMemoryError as e:
            print(f"      ✗ chunk {chunk_idx+1} OOM — skipped")
        except Exception as e:
            print(f"      ✗ chunk {chunk_idx+1} error: {str(e)[:100]}")
        finally:
            if outputs is not None:
                del outputs
            del inputs
            torch.cuda.empty_cache()
            gc.collect()

    # ── Merge chunks ──────────────────────────────────────────────────────────
    if not chunk_results:
        results.append({
            "_cov_id": cov_id,
            "_label": label,
            "_processing_status": "all_chunks_failed",
        })
        print(f"    ✗ All chunks failed")
    else:
        merged = merge_chunk_results(chunk_results)
        row = flatten_to_row(merged, cov_id, label)
        row["_processing_status"]    = "success"
        row["_n_chunks"]             = n_chunks
        row["_chunks_succeeded"]     = len(chunk_results)
        row["_total_article_tokens"] = total_article_tokens
        results.append(row)

        pop  = merged.get("population", {}).get("target_group", "?")
        tech = merged.get("ai_technology", {}).get("technology_name", "?")[:50]
        role = merged.get("communicative_role", {}).get("primary_role", "?")
        conf = merged.get("extraction_quality", {}).get("overall_confidence", "?")
        print(f"    ✓ Merged {len(chunk_results)}/{n_chunks} chunks | "
              f"pop={pop} | role={role} | conf={conf}")
        print(f"    Tech: {tech}")


    # ── Checkpoint after every paper (only 10 total, so always save) ────────
    save_checkpoint(results, CHECKPOINT_FILE)



def apply_emca_corrections(results: list) -> list:
    """
    Post-processing rule-based corrections for the two systematic errors:

    Error A — CA over-assignment:
      If analysis_approaches contains conversation_analysis_CA but
      transcription_approach is not_applicable or not_reported,
      remove CA and replace with interaction_coding_scheme if there is
      interaction data, otherwise leave the other approaches unchanged.
      Log each correction.

    Error B — emca_gap_flag contradiction:
      If emca_gap_flag is no_process_analysis_present (old value) or
      yes_outcome_only but analysis_approaches contains
      conversation_analysis_CA or multimodal_interaction_analysis,
      correct to no_gap_process_analysed.
      Conversely, if emca_gap_flag is no_gap_process_analysed but
      analysis_approaches contains no process-level methods,
      correct to yes_outcome_only.
    """
    PROCESS_METHODS = {"conversation_analysis_CA", "multimodal_interaction_analysis",
                       "discourse_analysis"}
    OUTCOME_ONLY    = {"descriptive_statistics", "inferential_statistics",
                       "usability_metrics_SUS_etc", "thematic_analysis",
                       "content_analysis", "framework_analysis", "grounded_theory",
                       "narrative_analysis", "standardised_language_assessment",
                       "NLP_automated_metrics"}
    NO_TRANSCRIPT   = {"not_applicable", "not_reported", ""}

    corrected = []
    for r in results:
        if r.get("_processing_status") != "success":
            corrected.append(r)
            continue

        r = dict(r)  # shallow copy
        cov = r.get("_cov_id", "?")
        corrections = []

        # Read current values (stored as pipe-joined strings after flatten)
        analysis_raw   = r.get("interaction_analysis.analysis_approaches", "")
        transcript_raw = r.get("interaction_analysis.transcription_approach", "")
        emca_flag      = r.get("interaction_analysis.emca_gap_flag", "")

        analysis_set = {a.strip() for a in analysis_raw.split("|") if a.strip()}
        transcript   = transcript_raw.strip()

        # ── Error A: CA without transcript ───────────────────────────────────
        if "conversation_analysis_CA" in analysis_set and transcript in NO_TRANSCRIPT:
            analysis_set.discard("conversation_analysis_CA")
            corrections.append(
                f"Removed conversation_analysis_CA (transcription='{transcript}')"
            )
            r["interaction_analysis.analysis_approaches"] = " | ".join(sorted(analysis_set))

        # Refresh after possible CA removal
        has_process = bool(analysis_set & PROCESS_METHODS)
        has_outcome = bool(analysis_set & OUTCOME_ONLY)

        # ── Error B: emca_gap_flag contradiction ─────────────────────────────
        if has_process and emca_flag in ("no_process_analysis_present", "yes_outcome_only"):
            r["interaction_analysis.emca_gap_flag"] = "no_gap_process_analysed"
            corrections.append(
                f"emca_gap_flag: '{emca_flag}' → 'no_gap_process_analysed' "
                f"(process methods present: {analysis_set & PROCESS_METHODS})"
            )
        elif not has_process and emca_flag == "no_gap_process_analysed":
            r["interaction_analysis.emca_gap_flag"] = "yes_outcome_only"
            corrections.append(
                f"emca_gap_flag: 'no_gap_process_analysed' → 'yes_outcome_only' "
                f"(no process methods in: {analysis_set})"
            )

        if corrections:
            r["_emca_corrections"] = " | ".join(corrections)
            print(f"  Corrected {cov}: {' | '.join(corrections)}")

        corrected.append(r)

    return corrected

# =============================================================================
# BUILD OUTPUT EXCEL
# =============================================================================

print(f"\n[4/5] Building output Excel: {OUTPUT_FILE}")

print("\n  Applying EMCA/CA post-processing corrections...")
results = apply_emca_corrections(results)

successful = [r for r in results if r.get("_processing_status") == "success"]
failed     = [r for r in results if r.get("_processing_status") != "success"]

df = pd.DataFrame(successful)

# Helper: pull existing columns from a list, in order
def cols(col_list):
    return [c for c in col_list if c in df.columns]


with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:

    # ── Sheet 1: Overview ────────────────────────────────────────────────────
    # One row per paper, the 12 fields most useful for a first team read-through
    overview = cols([
        "_cov_id", "_label",
        "bibliographic.first_author_surname", "bibliographic.year",
        "bibliographic.country_of_study",
        "population.target_group",
        "population.diagnosis_details",
        "population.n_with_condition",
        "ai_technology.technology_name",
        "ai_technology.technology_type",
        "communicative_role.primary_role",
        "study_design.study_type",
        "key_findings.main_findings",
        "extraction_quality.overall_confidence",
    ])
    df[overview].to_excel(writer, sheet_name="Overview", index=False)

    # ── Sheet 2: Population (Section 4.1) ────────────────────────────────────
    population = cols([
        "_cov_id", "_label",
        "population.target_group",
        "population.diagnosis_details",
        "population.diagnosis_criteria",
        "population.severity",
        "population.n_with_condition",
        "population.total_n_in_study",
        "population.age_info",
        "population.gender_info",
        "population.language_background",
        "population.other_participants",
        "population.recruitment_method",
        "population.consent_capacity_notes",
        "population.uncertainty_flags",
    ])
    df[population].to_excel(writer, sheet_name="Population", index=False)

    # ── Sheet 3: AI Technology (Section 4.2) ─────────────────────────────────
    technology = cols([
        "_cov_id", "_label",
        "population.target_group",           # keep for cross-referencing
        "ai_technology.technology_name",
        "ai_technology.technology_type",
        "ai_technology.physical_form",
        "ai_technology.anthropomorphisation",
        "ai_technology.ai_components",
        "ai_technology.ai_component_details",
        "ai_technology.commercial_or_custom",
        "ai_technology.named_commercial_systems",
        "ai_technology.input_modalities",
        "ai_technology.output_modalities",
        "ai_technology.language_of_system",
        "ai_technology.adaptivity",
        "ai_technology.autonomy_level",
        "ai_technology.development_stage",
    ])
    df[technology].to_excel(writer, sheet_name="AI_Technology", index=False)

    # ── Sheet 4: Communicative Role (Section 4.3) ─────────────────────────────
    comm_role = cols([
        "_cov_id", "_label",
        "population.target_group",
        "communicative_role.primary_role",
        "communicative_role.primary_role_justification",
        "communicative_role.secondary_roles",
        "communicative_role.communication_functions_targeted",
        "communicative_role.communication_modalities_in_focus",
        "communicative_role.interaction_partner_role",
        "communicative_role.ai_replaces_or_augments",
        "communicative_role.uncertainty_flags",
    ])
    df[comm_role].to_excel(writer, sheet_name="Communicative_Role", index=False)

    # ── Sheet 5: Methodology & Interaction Analysis (Sections 4.4–4.5) ────────
    methodology = cols([
        "_cov_id", "_label",
        "population.target_group",
        "study_design.study_type",
        "study_design.study_type_detail",
        "study_design.study_aim",
        "study_design.duration_of_data_collection",
        "study_design.number_of_sessions",
        "study_design.theoretical_framework",
        "study_design.framework_detail",
        "setting.setting_type",
        "setting.setting_detail",
        "setting.deployment_context",
        "interaction_analysis.data_collection_methods",
        "interaction_analysis.analysis_approaches",
        "interaction_analysis.analysis_detail",
        "interaction_analysis.interactional_aspects_studied",
        "interaction_analysis.transcription_approach",
        "interaction_analysis.outcome_measures",
        "interaction_analysis.emca_gap_flag",
        "interaction_analysis.emca_gap_note",
        "_emca_corrections",
    ])
    df[methodology].to_excel(writer, sheet_name="Methodology", index=False)

    # ── Sheet 6: Key Findings ─────────────────────────────────────────────────
    findings = cols([
        "_cov_id", "_label",
        "population.target_group",
        "key_findings.main_findings",
        "key_findings.communication_outcomes",
        "key_findings.user_experience",
        "key_findings.challenges_reported",
        "key_findings.authors_conclusions",
        "key_findings.pwa_pwd_comparative_note",
    ])
    df[findings].to_excel(writer, sheet_name="Key_Findings", index=False)

    # ── Sheet 7: Visualisation-ready (for charts / heatmaps) ─────────────────
    # Narrow schema: one controlled-vocab field per dimension, for direct plotting
    viz = cols([
        "_cov_id", "_label",
        "bibliographic.first_author_surname",
        "bibliographic.year",
        "bibliographic.country_of_study",
        "population.target_group",
        "population.n_with_condition",
        "ai_technology.technology_type",
        "ai_technology.physical_form",
        "ai_technology.anthropomorphisation",
        "ai_technology.autonomy_level",
        "ai_technology.development_stage",
        "communicative_role.primary_role",
        "communicative_role.ai_replaces_or_augments",
        "study_design.study_type",
        "setting.setting_type",
        "interaction_analysis.emca_gap_flag",
        "interaction_analysis.transcription_approach",
        "extraction_quality.overall_confidence",
    ])
    df[viz].to_excel(writer, sheet_name="Visualisation_Data", index=False)

    # ── Sheet 8: Full raw extraction ──────────────────────────────────────────
    df.to_excel(writer, sheet_name="Full_Extraction", index=False)

    # ── Sheet 9: Failed / errors ──────────────────────────────────────────────
    if failed:
        pd.DataFrame(failed).to_excel(writer, sheet_name="Failed", index=False)

print(f"  ✓ Saved: {OUTPUT_FILE}")


# =============================================================================
# SUMMARY
# =============================================================================

print(f"\n[5/5] Summary")
print("=" * 65)
print(f"  Total papers:      {len(INCLUDED_PAPERS)}")
print(f"  Successfully done: {len(successful)}")
print(f"  Failed:            {len(failed)}")
if failed:
    for r in failed:
        print(f"    - {r['_cov_id']}: {r.get('_processing_status')} | {r.get('_error','')[:80]}")
print(f"\n  Output:     {OUTPUT_FILE}")
print(f"  Checkpoint: {CHECKPOINT_FILE}")
print(f"\n  Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
