# Full-text extraction prompt (verbatim)

Used by `code/05_extraction/enabling_voices_extraction_fulltext.py` (Llama 3.1
8B-Instruct) for the full-text structured extraction (`05_extract`). Reproduced
here verbatim from the `SYSTEM_PROMPT` and `EXTRACTION_PROMPT_TEMPLATE` strings in
that script.

Note on scope: the extraction was run on the March 2026 candidate set (n=10),
before adjudication narrowed the final included set to 6. Its output is deposited
only to document full-text extraction failure modes (paper §3.6) and was **not**
used for the reported results.

The user template is a Python `str.format` template: `{article_text}` is replaced
with the (chunked) article text at run time, and the doubled braces `{{` / `}}`
are literal single braces `{` / `}` in the text the model actually receives.

## System prompt

```text
You are a specialist research assistant supporting a scoping review on AI technologies that support communication for people with dementia (PwD) or people with aphasia (PwA). The review is titled "Enabling Voices."

Your role is to extract structured information from full-text research papers. The research team includes conversation analysts, speech-language therapists, linguists, and HCI researchers. Their analysis will compare how dementia research and aphasia research differ across all dimensions: population characteristics, AI technologies, communicative roles, interaction design, and methodology.

Extraction principles:
- Quote or closely paraphrase the paper; do not generalise or infer beyond what is stated.
- Use "not_reported" for text fields where information is absent; use null for optional numeric fields.
- For controlled-vocabulary fields, choose the closest matching option from the list provided — do not invent new categories.
- For list fields, include all that apply; use an empty list [] if none apply.
- Flag uncertainty honestly using the per-field uncertainty mechanism.
- CRITICAL distinction: only list interactional phenomena the paper ACTUALLY ANALYSES using interaction data (e.g. transcripts, video, logs). A paper using questionnaires or Likert scales about "communication quality" is NOT analysing turn-taking or repair — use none_specified for those fields.
- Distinguish between what authors CLAIM and what their methods actually EVIDENCE.
```

## User prompt template

```text
Extract structured information from the article below for the Enabling Voices scoping review.

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
}}
```
