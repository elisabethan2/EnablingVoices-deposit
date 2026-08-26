# Updated Filtering Prompt for Enabling Voices Round 1

## Key Changes Made:
1. Added explicit detection/diagnosis exclusion in EXCLUSION EXAMPLES
2. Clarified COMMUNICATION FOCUS criterion to emphasize "support" vs "detect"
3. Added `is_detection_study` field to JSON output for flagging
4. Added clarifying note about the distinction

---

## Updated Prompt (copy this into Cell 7 of the notebook)

```python
FILTERING_PROMPT = '''You are screening research papers for a systematic review on AI technologies that SUPPORT communication for people with dementia and/or aphasia.

CRITICAL DISTINCTION:
This review focuses on AI that HELPS people communicate (assistive/supportive), NOT AI that DETECTS or DIAGNOSES conditions through speech/language analysis.

SCREENING CRITERIA - A paper should be INCLUDED if it meets ALL THREE:
1. POPULATION: Involves people with dementia OR aphasia (including primary progressive aphasia, post-stroke aphasia, or communication difficulties in dementia)
2. TECHNOLOGY: Involves artificial intelligence (machine learning, deep learning, NLP, LLMs, chatbots, computer vision, speech recognition, intelligent/adaptive systems, social robots with AI capabilities)
3. COMMUNICATION SUPPORT: The AI is used to SUPPORT, ASSIST, ENABLE, or ENHANCE communication, language, speech, conversation, or social interaction for the target population

EXCLUSION CRITERIA (do NOT include):
- DETECTION/DIAGNOSIS STUDIES: AI used to detect, diagnose, screen for, or assess dementia or aphasia through speech, language, or cognitive markers (e.g., "detecting MCI from speech patterns", "automatic aphasia severity assessment", "ML classification of dementia subtypes")
- Digital tools WITHOUT AI (e.g., simple video calling, photo albums, basic reminder apps)
- Studies only on healthy older adults or other populations without dementia/aphasia
- Pure theoretical/ethical discussions without technology implementation or evaluation
- Studies on caregivers only without patient involvement
- Non-intelligent assistive devices
- Outcome measurement tools that only ASSESS communication but don't SUPPORT it

INCLUDE EXAMPLES (AI that SUPPORTS communication):
- Social robots that facilitate conversation or social interaction
- Chatbots or virtual agents that help users communicate or practice language
- AI-powered AAC (augmentative and alternative communication) devices
- Speech recognition systems that assist with communication
- NLP-based tools that simplify or augment language for users
- AI systems that prompt, cue, or scaffold conversation
- Intelligent reminiscence systems that support meaningful interaction
- Adaptive communication interfaces

EXCLUDE EXAMPLES (AI that DETECTS/DIAGNOSES):
- ML models that classify dementia vs healthy from speech features
- Automatic detection of aphasia severity from language samples
- AI screening tools for cognitive impairment
- Speech biomarker analysis for early dementia detection
- NLP analysis to predict disease progression
- Diagnostic decision support systems (unless they also include communication support)

ARTICLE TEXT:
{article_text}

Analyze this article and return ONLY a JSON object with your screening decision:

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
    "is_detection_study": true/false
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

AI_TYPE OPTIONS: speech_recognition, NLP, machine_learning, deep_learning, computer_vision, chatbot, social_robot_AI, emotion_detection, LLM, intelligent_agent, adaptive_system, AAC, other_AI, none, unclear

SUPPORT_VS_DETECT:
- "support" = AI helps users communicate (INCLUDE)
- "detect" = AI detects/diagnoses condition from speech/language (EXCLUDE)
- "both" = Paper includes both aspects (flag for MANUAL REVIEW)
- "unclear" = Cannot determine (flag for MANUAL REVIEW)

Return ONLY the JSON object, no other text.'''

print("✓ Filtering prompt loaded (with detection exclusion)")
print(f"  Prompt length: {len(FILTERING_PROMPT)} characters")
```

---

## Summary of Changes

| Section | Original | Updated |
|---------|----------|---------|
| Title/intro | "supporting communication" | Added "CRITICAL DISTINCTION" box |
| Criterion 3 | "COMMUNICATION FOCUS" | "COMMUNICATION SUPPORT" (emphasizes assistive) |
| Exclusions | 5 bullet points | 7 bullet points (added detection + assessment tools) |
| Include examples | AI technology list | Renamed "INCLUDE EXAMPLES" with support focus |
| Exclude examples | (none specific) | New "EXCLUDE EXAMPLES" section with detection examples |
| JSON: technology | - | Added `is_detection_study` field |
| JSON: communication | `has_communication_focus` | Changed to `has_communication_support` |
| JSON: communication | - | Added `support_vs_detect` field |

---

## Also Update the Annotation Function (Cell 9)

Add these lines to extract the new fields in the `screen_article` function:

```python
# In the technology assessment section, add:
result['is_detection_study'] = ta.get('is_detection_study', None)

# In the communication assessment section, change and add:
result['has_communication_support'] = ca.get('has_communication_support', None)
result['support_vs_detect'] = ca.get('support_vs_detect', '')
```
