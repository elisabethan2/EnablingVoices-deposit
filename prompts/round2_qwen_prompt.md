# Round 2 / Qwen screening prompt (verbatim)

Used by `code/04_screening_round2/enabling_voices_qwen_screening_v3.py` (Qwen 2.5
7B-Instruct) for the Round 1 Qwen validation (`03_qwenval`) and the Round 2
conservative full-pool pass (`04_r2`). Reproduced here verbatim from the
`SCREENING_PROMPT` string in that script.

This is a Python `str.format` template: `{article_text}` is replaced with the
extracted article text at run time, and the doubled braces `{{` / `}}` are literal
single braces `{` / `}` in the text the model actually receives.

```text
You are screening a research paper for a scoping review. The review is titled
"Enabling Voices" and examines how artificial intelligence (AI) technologies
support communication for people with dementia and/or aphasia.

Your task is to assess the paper against four criteria and return a structured
JSON response. Read the article text carefully before answering.

═══════════════════════════════════════════════════════════════
CRITERION 1 – TARGET POPULATION
═══════════════════════════════════════════════════════════════
INCLUDE if the study involves people with a CONFIRMED clinical diagnosis of:
  • Dementia (any subtype: Alzheimer's disease, vascular dementia, Lewy body
    dementia, frontotemporal dementia, etc.)
  • Primary Progressive Aphasia (PPA) – count as both dementia and aphasia
  • Aphasia (acquired: post-stroke aphasia, non-progressive aphasia, etc.)

EXCLUDE if the study involves ONLY:
  • People with suspected or probable dementia (not confirmed)
  • Mild Cognitive Impairment (MCI) without a dementia diagnosis
  • Healthy older adults or at-risk populations
  • Caregivers or family members as the primary study population
  • Other communication disorders (autism, cerebral palsy, developmental disorders)

INCLUDE (with flag) if the study has a MIXED sample that includes people with
dementia or aphasia alongside others, AND the paper reports outcomes specifically
for the target group, OR the technology is designed primarily for their use.

═══════════════════════════════════════════════════════════════
CRITERION 2 – AI TECHNOLOGY
═══════════════════════════════════════════════════════════════
Definition adopted for this review (European Commission, 2018):
  "AI refers to systems that display intelligent behaviour by analysing their
  environment and taking action – with some degree of autonomy – to achieve
  specific goals."

This includes: machine learning, deep learning, neural networks, natural
language processing (NLP), automatic speech recognition (ASR), large language
models (LLMs, e.g. GPT-4, ChatGPT), dialogue systems, computer vision for
understanding, word prediction using language models, and social robots with
adaptive/learning dialogue capabilities.

TWO-TIER CLASSIFICATION:

  TIER A – Explicit AI: The paper uses AI terminology explicitly in relation
  to the communication technology. Keywords: artificial intelligence, AI,
  machine learning, deep learning, neural network, LLM, GPT, NLP, natural
  language processing, ASR, automatic speech recognition, computer vision,
  dialogue system, conversational AI, word prediction, transformer, BERT.
  → Include directly on AI criterion. Extract the exact term(s) found.

  TIER B – Implicit/Functional AI: No explicit AI terminology, but the
  technology behaves according to the EC definition: it perceives user input,
  processes it with some degree of autonomy beyond fixed rule-based lookup,
  and generates contextually variable responses. Examples: social robots with
  "speech recognition and dialogue capabilities"; AAC devices with "predictive
  text"; virtual agents that "respond adaptively to voice commands".
  → Flag for human verification (do not auto-include).

EXCLUDE on AI criterion if:
  • The technology is a basic digital tool: pre-programmed content, fixed
    scripts, simple touchscreen with pre-stored phrases, video calling software,
    digital photo albums, basic reminder apps with fixed schedules
  • AI is mentioned only in the background or future work, not as a feature
    of the technology studied in the paper
  • A social robot is described ONLY by brand name with no AI claim — the
    paper must explicitly describe AI, NLP, or adaptive/learning behaviour

THE FOLLOWING ARE NOT AI TERMS — do not list them as explicit_ai_terms or
use them alone to justify tier=A_explicit:
  Interface/hardware: touchscreen, touch screen, tablet, head-worn display,
    Google Glass, computer-based system, desktop computer, mobile app, screen
  Multimedia/content: hypermedia, multimedia, pre-recorded audio, storyboard,
    interactive icons, photo album, slideshow, digital stories
  Communication platforms: Skype, Zoom, FaceTime, video calling, telephone
  Design methodology: user-centered design, iterative design, participatory
    design, co-design, assistive technology (as a category)
  Generic digital infrastructure: cloud computing, programmed alert system,
    Bluetooth, WiFi, sensors (without ML processing)
  Robot names without AI claims: PARO, NAO (without NLP claim), Pepper
    (without NLP claim), teleoperated robot, wizard-of-oz robot
  AAC devices without generation/prediction: picture symbols, pre-stored
    phrases, symbol boards, static vocabulary sets

WHAT DOES COUNT as Tier A AI (explicit terms to look for):
  artificial intelligence, AI, machine learning, deep learning, neural network,
  large language model, LLM, GPT, ChatGPT, BERT, transformer model,
  natural language processing, NLP, natural language understanding,
  automatic speech recognition, ASR (when used for understanding/response),
  dialogue system, dialogue management, conversational agent (with NLP),
  word prediction (ML-based), emotion recognition (ML-based),
  computer vision (for understanding, not just display),
  adaptive/personalised responses (must describe the learning mechanism)

IMPORTANT: Do NOT require AI to be the sole component. Include if an AI
component plays a meaningful role in enabling communicative interaction.

═══════════════════════════════════════════════════════════════
CRITERION 3 – COMMUNICATION SUPPORT
═══════════════════════════════════════════════════════════════
INCLUDE if communication is a PRIMARY OUTCOME or PRIMARY MECHANISM:
  • Human–machine communication: the AI system is a conversational partner
    (chatbot, social robot with dialogue, voice assistant, ECA)
  • Human–human communication mediated by AI: AAC systems, real-time
    speech-to-text, AI-generated conversation prompts facilitating human
    interaction
  • Communication scaffolding: the AI helps the person initiate, sustain,
    repair, or augment communicative interaction

EXCLUDE if the primary focus is ONLY:
  • Indirect psychosocial outcomes: loneliness, depression, anxiety, general
    wellbeing – where communication is not a studied mechanism or outcome
  • Cognitive training/stimulation: memory exercises, quiz games, arithmetic
    tasks, cognitive rehabilitation exercises (these are not communication)
  • Clinical assessment or detection: using AI to diagnose or screen for
    dementia or aphasia, or to assess language impairment
  • Functional daily living (ADL) support: medication reminders, appointment
    management, safety monitoring, GPS tracking
  • SPEECH AND LANGUAGE THERAPY TRAINING APPS: structured exercises designed
    to rehabilitate language functions through drills (e.g. naming therapy apps
    that use ASR to score word-retrieval exercises). Rationale: these target
    communication-as-rehabilitation-target, not communication-as-practice.
    EXAMPLE OF EXCLUSION: "aphaDIGITAL – a mobile app for speech therapy
    with ASR-based feedback on naming exercises" → EXCLUDE on C3.
    EXAMPLE OF INCLUSION: "a voice assistant that helps people with aphasia
    communicate their daily needs to caregivers" → INCLUDE on C3.
  • COGNITIVE TRAINING OR STIMULATION: activities designed to exercise
    cognitive functions (memory games, quizzes, arithmetic, naming exercises,
    categorisation tasks) even when delivered by a robot or AI system. A robot
    leading structured cognitive stimulation sessions is doing therapy, not
    communication support. Ask: is the AI being a CONVERSATION PARTNER, or
    is it being a DRILL INSTRUCTOR?
    EXAMPLE OF EXCLUSION: "Pepper robot conducts cognitive and socio-cognitive
    training sessions with structured tasks and verbal instructions" → EXCLUDE.
    EXAMPLE OF INCLUSION: "Pepper robot engages residents in open-ended
    conversation and responds to their topics of interest" → INCLUDE.

BORDERLINE – flag for human review if:
  • Study has both detection AND communication support aspects
  • Social robot whose function mixes cognitive stimulation with conversation
  • Usability study of a system designed for communication (include unless the
    system itself fails C2 or C3)

═══════════════════════════════════════════════════════════════
CRITERION 4 – STUDY TYPE
═══════════════════════════════════════════════════════════════
EXCLUDE: review articles, systematic reviews, scoping reviews, meta-analyses,
theoretical or conceptual papers without empirical data.
INCLUDE: empirical studies of any design (experimental, observational,
qualitative, mixed methods, case study, pilot, feasibility, design study,
co-design, RCT).

═══════════════════════════════════════════════════════════════
ARTICLE TEXT:
{article_text}
═══════════════════════════════════════════════════════════════

Return ONLY a valid JSON object. No preamble, no explanation outside the JSON.

{{
  "C4_study_type": {{
    "is_review_article": true_or_false,
    "study_type": "empirical / review / theoretical / unclear",
    "evidence": "Brief quote or description supporting the study type classification"
  }},

  "C1_population": {{
    "has_dementia": true_or_false_or_null,
    "has_aphasia": true_or_false_or_null,
    "has_ppa": true_or_false_or_null,
    "diagnosis_confirmed": true_or_false_or_null,
    "population_notes": "Who are the participants? Quote any diagnosis terms used.",
    "confidence": 1_to_5
  }},

  "C2_ai_technology": {{
    "tier": "A_explicit / B_implicit / none",
    "explicit_ai_terms": ["list of AI terms found verbatim, e.g. 'machine learning', 'GPT-4'"],
    "implicit_ai_indicators": ["functional indicators if Tier B, e.g. 'adaptive dialogue', 'speech recognition that responds'"],
    "technology_name": "Name of the system/device studied",
    "ai_evidence_quote": "Best direct quote from paper showing AI use (max 200 chars)",
    "is_basic_digital_tool": true_or_false,
    "is_ai_only_in_background": true_or_false,
    "confidence": 1_to_5
  }},

  "C3_communication_support": {{
    "is_direct_communication_support": true_or_false_or_null,
    "is_therapy_training_app": true_or_false,
    "is_detection_assessment_only": true_or_false,
    "is_indirect_psychosocial_only": true_or_false,
    "is_cognitive_training_only": true_or_false,
    "communication_role": "Description of how the AI supports (or fails to support) communication",
    "confidence": 1_to_5
  }},

  "screening_decision": {{
    "include": true_or_false,
    "flag_for_human_review": true_or_false,
    "exclude_reason": "C1 / C2 / C3 / C4 / none (list all that apply, e.g. 'C2,C3')",
    "overall_confidence": 1_to_5,
    "decision_rationale": "Concise explanation of the decision (max 150 chars)"
  }}
}}

CONFIDENCE SCALE (use for each criterion AND overall):
  1 = Abstract only or very little text; major uncertainty
  2 = Some information but key details missing
  3 = Enough to decide but one or more criteria are ambiguous
  4 = Good evidence; decision is clear
  5 = Very clear; explicit statements for all relevant criteria

CRITICAL CONSISTENCY RULE — read before setting include:
  include = true  ONLY IF ALL of the following hold:
    • C4: is_review_article = false
    • C1: has_dementia OR has_aphasia OR has_ppa = true, AND diagnosis_confirmed = true
    • C2: tier = "A_explicit" OR "B_implicit"
          AND is_basic_digital_tool = false
          AND is_ai_only_in_background = false
    • C3: is_direct_communication_support = true
          AND is_therapy_training_app = false
          AND is_detection_assessment_only = false

  If C2.tier = "none" → include MUST be false. A paper with no AI technology
  cannot be included even if population and communication criteria are met.
  If C2.tier = "B_implicit" → set flag_for_human_review = true.

FLAG FOR HUMAN REVIEW if any of these apply:
  • Overall confidence ≤ 2
  • C2 tier = B_implicit (Tier B AI requires human verification)
  • C3 is borderline (detection AND communication aspects both present)
  • Any criterion confidence ≤ 2 on a paper you would otherwise include
```
