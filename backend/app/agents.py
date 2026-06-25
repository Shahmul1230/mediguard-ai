import json
import re
from typing import Any, Dict, List

from groq import Groq

from app.config import settings


def get_groq_client():
    if not settings.GROQ_API_KEY:
        return None

    return Groq(api_key=settings.GROQ_API_KEY)


def extract_json_from_text(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text or "", re.DOTALL)

    if not match:
        return {}

    try:
        return json.loads(match.group(0))
    except Exception:
        return {}


async def call_groq_json(
    system_prompt: str,
    user_payload: Dict[str, Any],
    temperature: float = 0.25,
    max_tokens: int = 3000,
) -> Dict[str, Any]:
    client = get_groq_client()

    if not client:
        return {}

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
                },
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content or ""
        return extract_json_from_text(content)

    except Exception:
        return {}


def list_from_text(value: Any) -> List[str]:
    if not value:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value)
    parts = re.split(r"[,;\n]+", text)

    return [part.strip() for part in parts if part.strip()]


def text_has_any(text: str, keywords: List[str]) -> bool:
    text = (text or "").lower()
    return any(keyword.lower() in text for keyword in keywords)


def get_case_text(patient_data: Dict[str, Any]) -> str:
    return " ".join(
        [
            str(patient_data.get("symptoms") or ""),
            str(patient_data.get("duration") or ""),
            str(patient_data.get("temperature") or ""),
            str(patient_data.get("blood_pressure") or ""),
            str(patient_data.get("oxygen_level") or ""),
            str(patient_data.get("existing_disease") or ""),
            str(patient_data.get("current_medicine") or ""),
            str(patient_data.get("allergies") or ""),
            str(patient_data.get("additional_info") or ""),
        ]
    ).lower()


def detect_emergency(symptoms: str, additional_info: str = "") -> bool:
    text = f"{symptoms or ''} {additional_info or ''}".lower()

    emergency_keywords = [
        "chest pain",
        "severe chest pain",
        "stroke",
        "unconscious",
        "fainting",
        "severe breathing problem",
        "shortness of breath",
        "breathing difficulty",
        "oxygen low",
        "spo2 low",
        "seizure",
        "convulsion",
        "severe bleeding",
        "blood vomiting",
        "black stool",
        "severe dehydration",
        "confusion",
        "suicidal",
        "pregnant severe pain",
        "high fever with stiff neck",
        "severe allergic reaction",
        "anaphylaxis",
        "vision loss",
        "sudden vision loss",
        "one sided weakness",
        "facial droop",
        "severe headache with vomiting",
    ]

    return any(keyword in text for keyword in emergency_keywords)


def build_full_patient_context(
    patient_data: Dict[str, Any],
    followup_answers: List[Dict[str, str]] | None = None,
    agent1_review: Dict[str, Any] | None = None,
    agent2_review: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "patient_identity": {
            "name": patient_data.get("name", ""),
            "email": patient_data.get("email", ""),
            "age": patient_data.get("age", ""),
            "sex": patient_data.get("sex", ""),
            "blood_group": patient_data.get("blood_group", ""),
        },
        "main_problem": {
            "symptoms": patient_data.get("symptoms", ""),
            "duration": patient_data.get("duration", ""),
        },
        "vitals_and_measurements": {
            "temperature": patient_data.get("temperature", "unknown"),
            "blood_pressure": patient_data.get("blood_pressure", "unknown"),
            "oxygen_level": patient_data.get("oxygen_level", "unknown"),
        },
        "medical_background": {
            "existing_disease": patient_data.get("existing_disease", "unknown"),
            "current_medicine": patient_data.get("current_medicine", "unknown"),
            "allergies": patient_data.get("allergies", "unknown"),
            "additional_info": patient_data.get("additional_info", ""),
        },
        "followup_answers": followup_answers or [],
        "agent1_review": agent1_review or {},
        "agent2_review": agent2_review or {},
        "country_context": "Bangladesh",
        "important_instruction": (
            "Consider all fields, not only symptoms. Consider duration, vitals, existing disease, "
            "current medicines, allergies, additional information, follow-up answers, and Bangladesh context."
        ),
    }


def fallback_followup_questions(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    text = get_case_text(patient_data)
    questions: List[Dict[str, str]] = []

    if text_has_any(text, ["diarrhea", "vomiting", "stomach", "loose stool", "পেট", "বমি", "ডায়রিয়া"]):
        questions.extend(
            [
                {
                    "question": "How many times did vomiting or loose stool happen today?",
                    "reason": "To understand dehydration risk and severity.",
                    "related_to": "stomach/vomiting/diarrhea",
                    "priority": "high",
                },
                {
                    "question": "Did you notice blood in stool or vomit?",
                    "reason": "Blood may indicate a serious condition.",
                    "related_to": "gastrointestinal warning sign",
                    "priority": "high",
                },
                {
                    "question": "Can you drink water or ORS without vomiting?",
                    "reason": "To assess hydration status.",
                    "related_to": "dehydration",
                    "priority": "high",
                },
            ]
        )

    if text_has_any(text, ["fever", "temperature", "জ্বর"]):
        questions.extend(
            [
                {
                    "question": "What is the highest recorded temperature?",
                    "reason": "Fever level helps estimate severity.",
                    "related_to": "fever",
                    "priority": "medium",
                },
                {
                    "question": "Do you have rash, severe headache, eye pain, or body pain?",
                    "reason": "These may be relevant in Bangladesh fever cases.",
                    "related_to": "fever pattern",
                    "priority": "medium",
                },
            ]
        )

    if text_has_any(text, ["cough", "cold", "sore throat", "throat", "কাশি", "ঠান্ডা"]):
        questions.extend(
            [
                {
                    "question": "Do you have fever, breathing difficulty, chest pain, or wheezing with the cough?",
                    "reason": "To identify respiratory red flags.",
                    "related_to": "cough/respiratory symptoms",
                    "priority": "high",
                },
                {
                    "question": "Is the cough dry or with phlegm?",
                    "reason": "Cough type helps guide doctor review.",
                    "related_to": "cough type",
                    "priority": "medium",
                },
            ]
        )

    if text_has_any(text, ["urine", "burning urination", "uti", "প্রস্রাব"]):
        questions.extend(
            [
                {
                    "question": "Do you feel burning during urination or lower abdominal pain?",
                    "reason": "To assess possible urinary tract infection.",
                    "related_to": "urinary symptoms",
                    "priority": "high",
                },
                {
                    "question": "Do you have fever or back/flank pain?",
                    "reason": "Fever or flank pain may suggest complicated infection.",
                    "related_to": "urinary red flags",
                    "priority": "high",
                },
            ]
        )

    if not questions:
        questions = [
            {
                "question": "Is the problem getting better, worse, or staying the same?",
                "reason": "Symptom progression helps assess urgency.",
                "related_to": "overall condition",
                "priority": "medium",
            },
            {
                "question": "Do you have any known allergy to medicine?",
                "reason": "Allergy information is important before prescription drafting.",
                "related_to": "medicine safety",
                "priority": "high",
            },
            {
                "question": "Are you currently taking any medicine?",
                "reason": "Current medicine may interact with new medicine.",
                "related_to": "current medication",
                "priority": "high",
            },
        ]

    seen = set()
    unique_questions = []

    for item in questions:
        q = item["question"].strip().lower()
        if q not in seen:
            seen.add(q)
            unique_questions.append(item)

    return {
        "questions": unique_questions[:7],
        "emergency_detected": detect_emergency(
            patient_data.get("symptoms", ""),
            patient_data.get("additional_info", ""),
        ),
    }


async def agent1_generate_questions(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = """
You are Agent 1 in a medical consultation demo system for Bangladesh.

Task:
Generate follow-up questions for the patient.

Rules:
- Consider ALL patient fields: symptoms, duration, age, sex, blood group, temperature, blood pressure, oxygen level, existing disease, current medicine, allergies, and additional info.
- Do not only focus on the main symptoms.
- Generate 3 to 7 useful follow-up questions.
- Keep questions patient-friendly and simple.
- Use Bangladesh context where relevant.
- Detect emergency signals.
- Return only valid JSON.

JSON format:
{
  "questions": [
    {
      "question": "string",
      "reason": "string",
      "related_to": "string",
      "priority": "high|medium|low"
    }
  ],
  "emergency_detected": true/false
}
"""

    context = build_full_patient_context(patient_data)
    result = await call_groq_json(system_prompt, context)

    if not result or not isinstance(result.get("questions"), list):
        return fallback_followup_questions(patient_data)

    result["emergency_detected"] = bool(
        result.get("emergency_detected")
        or detect_emergency(patient_data.get("symptoms", ""), patient_data.get("additional_info", ""))
    )

    return result


def fallback_agent1_review(
    patient_data: Dict[str, Any],
    followup_answers: List[Dict[str, str]],
) -> Dict[str, Any]:
    symptoms = patient_data.get("symptoms", "")
    duration = patient_data.get("duration", "")
    emergency = detect_emergency(symptoms, patient_data.get("additional_info", ""))

    return {
        "emergency_warning": (
            "Please seek emergency medical care immediately."
            if emergency
            else ""
        ),
        "structured_symptoms": [
            {
                "symptom": symptoms,
                "severity": "unknown",
                "note": f"Duration: {duration}",
            }
        ],
        "initial_clinical_review": {
            "summary": (
                f"Patient reports {symptoms} for {duration}. "
                f"Additional context: {patient_data.get('additional_info', '') or 'none'}."
            ),
            "possible_conditions": [
                "Needs clinical review based on complete patient history."
            ],
            "reasoning": (
                "This review considered symptoms, duration, vitals, existing disease, "
                "current medicines, allergies, additional information, and follow-up answers."
            ),
            "urgency_level": "high" if emergency else "medium",
            "confidence": "limited without physical examination",
        },
        "followup_answers_used": followup_answers,
    }


async def agent1_initial_review(
    patient_data: Dict[str, Any],
    followup_answers: List[Dict[str, str]],
) -> Dict[str, Any]:
    system_prompt = """
You are Agent 1 in a medical consultation demo system for Bangladesh.

Task:
Create an initial clinical review.

Rules:
- Use ALL patient fields and follow-up answers.
- Do not ignore existing disease, current medicine, allergies, vitals, or additional info.
- Mention how follow-up answers affect the review.
- Keep it structured.
- Return only valid JSON.

JSON format:
{
  "emergency_warning": "string or empty",
  "structured_symptoms": [
    {
      "symptom": "string",
      "severity": "string",
      "note": "string"
    }
  ],
  "initial_clinical_review": {
    "summary": "string",
    "possible_conditions": ["string"],
    "reasoning": "string",
    "urgency_level": "low|medium|high",
    "confidence": "string"
  },
  "followup_answers_used": [
    {
      "question": "string",
      "answer": "string"
    }
  ]
}
"""

    context = build_full_patient_context(patient_data, followup_answers=followup_answers)
    result = await call_groq_json(system_prompt, context)

    if not result or not isinstance(result, dict):
        return fallback_agent1_review(patient_data, followup_answers)

    if detect_emergency(patient_data.get("symptoms", ""), patient_data.get("additional_info", "")):
        result["emergency_warning"] = "Please seek emergency medical care immediately."

    result["followup_answers_used"] = followup_answers

    return result


def fallback_agent2_analysis(
    patient_data: Dict[str, Any],
    agent1_review: Dict[str, Any],
) -> Dict[str, Any]:
    text = get_case_text(patient_data)
    possible = []

    if text_has_any(text, ["diarrhea", "vomiting", "stomach", "loose stool"]):
        possible = [
            {
                "possible_condition": "Acute gastroenteritis or food/water-related stomach upset",
                "likelihood": "possible",
                "reason": "Relevant to stomach pain, vomiting, diarrhea, food exposure, and hydration status.",
            }
        ]
    elif text_has_any(text, ["fever", "cough", "cold", "sore throat"]):
        possible = [
            {
                "possible_condition": "Viral upper respiratory infection or seasonal respiratory illness",
                "likelihood": "possible",
                "reason": "Relevant to fever/cough/cold symptoms in Bangladesh local context.",
            }
        ]
    elif text_has_any(text, ["urine", "burning urination", "uti"]):
        possible = [
            {
                "possible_condition": "Possible urinary tract infection",
                "likelihood": "possible",
                "reason": "Urinary symptoms need urine R/E and doctor assessment.",
            }
        ]
    elif text_has_any(text, ["hair fall", "hair loss", "tired", "fatigue", "oversleeping", "over sleeping"]):
        possible = [
            {
                "possible_condition": "Broad symptoms requiring clinical evaluation",
                "likelihood": "possible",
                "reason": "Hair fall, tiredness, and sleep changes may relate to thyroid imbalance, anemia, stress/sleep disorder, or nutritional deficiency.",
            }
        ]
    else:
        possible = [
            {
                "possible_condition": "Non-specific clinical condition requiring doctor review",
                "likelihood": "uncertain",
                "reason": "Insufficient details for strong differential analysis.",
            }
        ]

    return {
        "case_summary": (
            f"Symptoms: {patient_data.get('symptoms', '')}. "
            f"Duration: {patient_data.get('duration', '')}. "
            f"Vitals: temperature {patient_data.get('temperature', 'unknown')}, "
            f"BP {patient_data.get('blood_pressure', 'unknown')}, "
            f"oxygen {patient_data.get('oxygen_level', 'unknown')}. "
            f"Additional info: {patient_data.get('additional_info', '') or 'none'}."
        ),
        "deep_analysis": possible,
        "why_it_may_have_happened": [
            patient_data.get("additional_info") or "Cause needs clinical correlation."
        ],
        "doctor_consideration_tests": [
            "CBC if fever, infection signs, weakness, or persistent symptoms are present",
            "Relevant test based on symptoms and doctor assessment",
        ],
        "emergency_risk": (
            "high"
            if detect_emergency(patient_data.get("symptoms", ""), patient_data.get("additional_info", ""))
            else "not obvious"
        ),
        "confidence": "limited without physical examination",
        "all_fields_considered": True,
    }


async def agent2_deep_analysis(
    patient_data: Dict[str, Any],
    agent1_review: Dict[str, Any],
) -> Dict[str, Any]:
    system_prompt = """
You are Agent 2 in a medical consultation demo system for Bangladesh.

Task:
Perform a deeper clinical analysis.

Rules:
- Consider ALL fields: symptoms, duration, age, sex, blood group, temperature, BP, oxygen, existing disease, current medicine, allergies, additional info, and Agent 1 review.
- Do not ignore additional info.
- Think about Bangladesh-relevant causes such as food/water hygiene, seasonal fever, dengue/viral fever, dehydration, heat exposure, dust/air pollution, and common local illness patterns when relevant.
- Do not overdiagnose.
- Return only valid JSON.

JSON format:
{
  "case_summary": "string",
  "deep_analysis": [
    {
      "possible_condition": "string",
      "likelihood": "high|medium|low|possible|uncertain",
      "reason": "string"
    }
  ],
  "why_it_may_have_happened": ["string"],
  "doctor_consideration_tests": ["string"],
  "emergency_risk": "low|medium|high|not obvious",
  "confidence": "string",
  "all_fields_considered": true
}
"""

    context = build_full_patient_context(
        patient_data,
        followup_answers=agent1_review.get("followup_answers_used", []),
        agent1_review=agent1_review,
    )

    result = await call_groq_json(system_prompt, context)

    if not result or not isinstance(result, dict):
        return fallback_agent2_analysis(patient_data, agent1_review)

    result["all_fields_considered"] = True

    return result


def is_vague_medicine_name(name: str) -> bool:
    clean_name = (name or "").strip().lower()

    vague_names = [
        "medicine",
        "tablet",
        "capsule",
        "syrup",
        "painkiller",
        "pain killer",
        "analgesic",
        "antibiotic",
        "antibiotics",
        "an antibiotic",
        "oral antibiotic",
        "broad spectrum antibiotic",
        "broad-spectrum antibiotic",
        "appropriate antibiotic",
        "empirical antibiotic",
        "empiric antibiotic",
        "antibiotic therapy",
        "antihistamine",
        "cough syrup",
        "vitamin",
        "multivitamin",
        "multi vitamin",
        "supplement",
    ]

    return clean_name in vague_names


def looks_like_specific_antibiotic(name: str) -> bool:
    clean_name = (name or "").strip().lower()

    specific_antibiotics = [
        "amoxicillin",
        "clavulanic",
        "co-amoxiclav",
        "azithromycin",
        "cefixime",
        "cefuroxime",
        "cephalexin",
        "flucloxacillin",
        "doxycycline",
        "metronidazole",
        "ciprofloxacin",
        "levofloxacin",
        "nitrofurantoin",
        "ceftriaxone",
        "cefpodoxime",
        "clindamycin",
        "linezolid",
        "meropenem",
        "piperacillin",
        "tazobactam",
    ]

    return any(item in clean_name for item in specific_antibiotics)


def condition_supports_antibiotic(patient_data: Dict[str, Any]) -> bool:
    text = get_case_text(patient_data)

    supportive_keywords = [
        "pus",
        "wound infection",
        "cellulitis",
        "boil",
        "abscess",
        "burning urination",
        "urine burning",
        "uti",
        "tonsil pus",
        "productive cough with fever",
        "pneumonia",
        "dysentery",
        "blood in stool",
        "dental infection",
        "ear discharge",
        "high fever for 3 days",
        "fever more than 3 days",
        "doctor suspects bacterial",
        "bacterial infection",
        "culture positive",
    ]

    return any(keyword in text for keyword in supportive_keywords)


def is_risky_emergency_medicine(name: str) -> bool:
    clean_name = (name or "").strip().lower()

    risky_keywords = [
        "aspirin",
        "nitroglycerin",
        "glyceryl trinitrate",
        "atenolol",
        "bisoprolol",
        "metoprolol",
        "propranolol",
        "amlodipine",
        "nifedipine",
        "losartan",
        "valsartan",
        "captopril",
        "enalapril",
        "furosemide",
        "frusemide",
        "prednisolone",
        "dexamethasone",
        "steroid",
        "diazepam",
        "clonazepam",
        "alprazolam",
        "sedative",
        "tramadol",
        "morphine",
        "pethidine",
        "insulin",
        "warfarin",
        "heparin",
        "rivaroxaban",
        "apixaban",
    ]

    return any(keyword in clean_name for keyword in risky_keywords)


def medicine_has_required_fields(med: Dict[str, Any]) -> bool:
    required = ["medicine_name", "dose", "frequency", "duration", "note"]

    return all(str(med.get(key) or "").strip() for key in required)


def clean_weak_medicine_suggestions(
    medicines: List[Dict[str, str]],
    patient_data: Dict[str, Any],
) -> List[Dict[str, str]]:
    allergies = (patient_data.get("allergies") or "").lower()
    existing = (patient_data.get("existing_disease") or "").lower()
    full_text = get_case_text(patient_data)

    emergency = detect_emergency(
        patient_data.get("symptoms", ""),
        patient_data.get("additional_info", ""),
    )

    cleaned = []
    seen_names = set()

    if not isinstance(medicines, list):
        return []

    for med in medicines:
        if not isinstance(med, dict):
            continue

        name = str(med.get("medicine_name", "")).strip()
        name_lower = name.lower()

        if not name:
            continue

        if name_lower in seen_names:
            continue

        if is_vague_medicine_name(name):
            continue

        if emergency and is_risky_emergency_medicine(name):
            continue

        if "antibiotic" in name_lower and not looks_like_specific_antibiotic(name):
            continue

        if looks_like_specific_antibiotic(name) and not condition_supports_antibiotic(patient_data):
            continue

        if "vitamin" in name_lower and not any(
            clue in full_text
            for clue in [
                "vitamin d low",
                "vitamin b12 low",
                "deficiency confirmed",
                "lab confirmed",
                "doctor advised vitamin",
                "known vitamin deficiency",
                "low vitamin",
            ]
        ):
            continue

        if "paracetamol" in name_lower and "liver" in existing:
            continue

        if "cetirizine" in name_lower and "cetirizine" in allergies:
            continue

        if "diclofenac" in name_lower and text_has_any(
            f"{allergies} {existing}",
            ["diclofenac", "nsaid allergy", "severe asthma", "stomach ulcer", "kidney disease"],
        ):
            continue

        med["medicine_name"] = name
        med["dose"] = str(med.get("dose") or "Doctor to confirm dose").strip()
        med["frequency"] = str(med.get("frequency") or "Doctor to confirm frequency").strip()
        med["duration"] = str(med.get("duration") or "Doctor to confirm duration").strip()

        note = str(med.get("note") or "").strip()

        if not note:
            note = (
                "Doctor must verify indication, contraindications, allergy, current medicines, "
                "and suitability before approval."
            )

        if "doctor" not in note.lower():
            note = f"{note} Doctor must verify suitability before approval."

        if looks_like_specific_antibiotic(name):
            if "bacterial" not in note.lower() and "infection" not in note.lower():
                note = (
                    f"{note} Confirm bacterial indication, allergy status, renal/liver status, "
                    "pregnancy status if relevant, and local guideline suitability before approval."
                )

        med["note"] = note

        if not medicine_has_required_fields(med):
            continue

        seen_names.add(name_lower)
        cleaned.append(med)

    return cleaned[:6]


def is_broad_non_specific_case(patient_data: Dict[str, Any]) -> bool:
    text = get_case_text(patient_data)
    duration = (patient_data.get("duration") or "").lower()

    broad_keywords = [
        "hair fall",
        "hair loss",
        "tired",
        "tiredness",
        "fatigue",
        "weak",
        "weakness",
        "over sleeping",
        "oversleeping",
        "sleepy",
        "headache",
        "neck pain",
        "body pain",
        "stress",
        "depression",
        "low energy",
    ]

    acute_clear_keywords = [
        "diarrhea",
        "vomiting",
        "loose stool",
        "high fever",
        "chest pain",
        "shortness of breath",
        "bleeding",
        "severe pain",
        "burning urination",
        "blood in stool",
    ]

    broad_count = sum(1 for word in broad_keywords if word in text)
    has_clear_acute = any(word in text for word in acute_clear_keywords)

    long_or_unclear_duration = any(
        word in duration
        for word in [
            "week",
            "weeks",
            "month",
            "months",
            "long",
            "many days",
            "অনেকদিন",
        ]
    )

    return (broad_count >= 3 and not has_clear_acute) or (broad_count >= 2 and long_or_unclear_duration)


def build_dynamic_fallback_medicines(patient_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Intentionally no hardcoded symptom-to-medicine mapping.

    This function exists only for backward compatibility with older code references.
    Medicines should be generated dynamically by Groq through:
    - agent3_prescription_generator()
    - repair_medicine_section_with_ai()
    """
    return []


async def repair_medicine_section_with_ai(
    patient_data: Dict[str, Any],
    current_result: Dict[str, Any],
    agent1_review: Dict[str, Any],
    agent2_review: Dict[str, Any],
    attempt: int = 1,
) -> List[Dict[str, str]]:
    system_prompt = """
You are a clinical prescription draft assistant for Bangladesh.

Task:
Generate ONLY the medicine_section array for doctor review.

Core goal:
- Best effort: try not to leave medicine_section empty.
- But never invent unsafe or unjustified medicines.
- Medicine must be generated dynamically from the full patient case.
- Do NOT use a fixed template.
- Do NOT give the same medicines for every case.
- Do NOT follow a simple symptom-to-medicine mapping.
- Think clinically from the full case context, Bangladesh context, age, sex, duration, vitals, allergies, current medicines, and red flags.

Safety and quality:
- This is NOT final medical advice.
- A registered doctor will review and approve.
- If emergency signs exist, medicines may still be listed only as doctor-review candidates when clinically justifiable.
- Do not provide definitive emergency treatment.
- Avoid heart medicine, blood pressure medicine, aspirin, nitroglycerin, sedatives, steroids, strong painkillers, anticoagulants, insulin, or antibiotics unless clearly justified for doctor review.
- Do not prescribe antibiotics randomly.
- Do not write vague category names like Painkiller, Antibiotic, Antihistamine, Vitamin, Multivitamin, Cough Syrup, Tablet, Capsule, Syrup.
- Use specific generic medicine names only.
- Every medicine must include medicine_name, dose, frequency, duration, and note.
- The note must explain why the medicine is being considered and what the doctor must verify.
- If no safe clinically justified medicine is possible, return an empty array.
- For broad/non-specific cases, do not randomly add multivitamin. Use medicine only if there is a case-specific reason.
- Respect allergies, existing diseases, current medicines, pregnancy possibility if relevant, and emergency risks.

Return only valid JSON:
{
  "medicine_section": [
    {
      "medicine_name": "specific generic medicine name",
      "dose": "string",
      "frequency": "string",
      "duration": "string",
      "note": "case-specific reason and doctor verification note"
    }
  ]
}
"""

    payload = {
        "attempt": attempt,
        "patient_data": build_full_patient_context(
            patient_data=patient_data,
            followup_answers=agent1_review.get("followup_answers_used", []),
            agent1_review=agent1_review,
            agent2_review=agent2_review,
        ),
        "current_prescription_draft": current_result,
        "instruction": (
            "Generate medicine dynamically from this exact case. "
            "Do not use fixed fallback medicines. "
            "Try your best to provide clinically justified doctor-review medicine candidates, "
            "but return empty if medicine is not safe or not clinically clear."
        ),
    }

    repaired = await call_groq_json(
        system_prompt=system_prompt,
        user_payload=payload,
        temperature=0.35 if attempt == 1 else 0.45,
        max_tokens=2000,
    )

    if not repaired or not isinstance(repaired.get("medicine_section"), list):
        return []

    return clean_weak_medicine_suggestions(repaired["medicine_section"], patient_data)


async def final_medicine_retry_with_ai(
    patient_data: Dict[str, Any],
    current_result: Dict[str, Any],
    agent1_review: Dict[str, Any],
    agent2_review: Dict[str, Any],
) -> List[Dict[str, str]]:
    """
    Final best-effort retry if Rx is empty.
    No hardcoded medicine names. AI must decide from case.
    """
    system_prompt = """
You are a cautious Bangladeshi clinical prescription draft assistant.

The previous draft has an empty medicine_section.

Task:
Make one final best-effort attempt to generate medicine_section dynamically for doctor review.

Rules:
- Do not use any fixed template.
- Do not copy common medicines mechanically.
- Medicine must be justified by the exact patient case.
- Medicine can be symptomatic, supportive, or disease-directed only if clinically reasonable.
- Emergency cases may still have doctor-review candidates, but no definitive emergency treatment.
- If no medicine is safe or clinically justified, return an empty medicine_section.
- Never use vague category names.
- Every item must have medicine_name, dose, frequency, duration, and note.
- The note must explain the case-specific reason and doctor verification requirements.
- Prefer Bangladesh-relevant generic medicine names.

Return only valid JSON:
{
  "medicine_section": [
    {
      "medicine_name": "specific generic medicine name",
      "dose": "string",
      "frequency": "string",
      "duration": "string",
      "note": "case-specific reason and doctor verification note"
    }
  ]
}
"""

    payload = {
        "patient_data": build_full_patient_context(
            patient_data=patient_data,
            followup_answers=agent1_review.get("followup_answers_used", []),
            agent1_review=agent1_review,
            agent2_review=agent2_review,
        ),
        "current_prescription_draft": current_result,
        "instruction": (
            "This is the final retry. Best effort to avoid empty Rx, but safety comes first. "
            "Do not hardcode or template. Use only case-specific medicine candidates."
        ),
    }

    repaired = await call_groq_json(
        system_prompt=system_prompt,
        user_payload=payload,
        temperature=0.5,
        max_tokens=2000,
    )

    if not repaired or not isinstance(repaired.get("medicine_section"), list):
        return []

    return clean_weak_medicine_suggestions(repaired["medicine_section"], patient_data)


def fallback_agent3_prescription(
    patient_data: Dict[str, Any],
    agent1_review: Dict[str, Any],
    agent2_review: Dict[str, Any],
) -> Dict[str, Any]:
    emergency = detect_emergency(
        patient_data.get("symptoms", ""),
        patient_data.get("additional_info", ""),
    )

    symptoms_list = list_from_text(patient_data.get("symptoms", ""))
    diagnosis = []

    deep_analysis = agent2_review.get("deep_analysis", [])

    if isinstance(deep_analysis, list):
        for item in deep_analysis:
            if isinstance(item, dict) and item.get("possible_condition"):
                diagnosis.append(item["possible_condition"])

    if not diagnosis:
        diagnosis = ["Clinical condition requiring doctor review"]

    return {
        "document_title": "AI Prescription Draft",
        "status": "AI Generated",
        "top_warning": (
            "Please seek emergency medical care immediately."
            if emergency
            else ""
        ),
        "patient_information": {
            "name": patient_data.get("name", ""),
            "age": patient_data.get("age", ""),
            "sex": patient_data.get("sex", ""),
            "blood_group": patient_data.get("blood_group", ""),
        },
        "chief_complaints": symptoms_list or [patient_data.get("symptoms", "")],
        "possible_diagnosis": diagnosis[:4],
        "medicine_section": [],
        "healthcare_advice": [
            "Drink safe water and maintain hydration.",
            "Avoid self-medicating with antibiotics or prescription medicines.",
            "Take rest and monitor symptoms.",
            "Seek urgent care if symptoms worsen or red flag signs appear.",
        ],
        "investigation_advice": agent2_review.get("doctor_consideration_tests", [])
        or [
            "Relevant tests based on doctor review",
            "Physical examination by a registered doctor",
        ],
        "follow_up_advice": "Follow up with a registered doctor if symptoms persist or worsen.",
        "all_patient_fields_considered": True,
        "country_context": "Bangladesh",
    }


def enforce_prescription_quality(
    result: Dict[str, Any],
    patient_data: Dict[str, Any],
    agent1_review: Dict[str, Any],
    agent2_review: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(result, dict):
        result = {}

    result["document_title"] = result.get("document_title") or "AI Prescription Draft"
    result["status"] = "AI Generated"
    result["country_context"] = "Bangladesh"
    result["all_patient_fields_considered"] = True

    result.setdefault(
        "patient_information",
        {
            "name": patient_data.get("name", ""),
            "age": patient_data.get("age", ""),
            "sex": patient_data.get("sex", ""),
            "blood_group": patient_data.get("blood_group", ""),
        },
    )

    if not isinstance(result.get("chief_complaints"), list):
        result["chief_complaints"] = list_from_text(patient_data.get("symptoms", ""))

    if not result.get("chief_complaints"):
        result["chief_complaints"] = [patient_data.get("symptoms", "") or "Not available"]

    if not isinstance(result.get("possible_diagnosis"), list):
        result["possible_diagnosis"] = ["Requires doctor review based on complete history"]

    if not result.get("possible_diagnosis"):
        result["possible_diagnosis"] = ["Requires doctor review based on complete history"]

    if not isinstance(result.get("medicine_section"), list):
        result["medicine_section"] = []

    if not isinstance(result.get("healthcare_advice"), list):
        result["healthcare_advice"] = []

    if not isinstance(result.get("investigation_advice"), list):
        result["investigation_advice"] = []

    result["medicine_section"] = clean_weak_medicine_suggestions(
        result.get("medicine_section", []),
        patient_data,
    )

    emergency = detect_emergency(
        patient_data.get("symptoms", ""),
        patient_data.get("additional_info", ""),
    )

    if emergency:
        result["top_warning"] = "Please seek emergency medical care immediately."

        result["healthcare_advice"] = [
            "Seek emergency medical care immediately.",
            "Do not delay care while waiting for online prescription review.",
            "The listed medicines, if any, are only doctor-review candidates and not definitive emergency treatment.",
            "Avoid self-medicating with antibiotics, heart medicines, blood pressure medicines, aspirin, nitroglycerin, steroids, sedatives, anticoagulants, insulin, or strong painkillers unless a doctor confirms.",
        ]

        result["investigation_advice"] = [
            "Emergency doctor assessment required.",
            "Blood pressure, pulse, oxygen saturation, and physical examination.",
            "ECG/troponin if chest pain or cardiac symptoms are present.",
            "Neurological and eye/vision assessment if headache with vision problem, weakness, confusion, or neurological symptoms is present.",
            "CBC, blood glucose, electrolytes, and other tests based on doctor assessment.",
        ]

        result["follow_up_advice"] = (
            "Go to the nearest emergency department immediately, especially if chest pain, fainting, "
            "breathing difficulty, severe weakness, confusion, vision problem, severe dehydration, or worsening symptoms occur."
        )

        return result

    if is_broad_non_specific_case(patient_data):
        result["possible_diagnosis"] = [
            "Broad symptoms requiring clinical evaluation",
            "Possible thyroid imbalance, anemia, nutritional deficiency, sleep/stress-related issue, respiratory infection, or musculoskeletal condition should be assessed by a doctor",
        ]

        if not result["healthcare_advice"]:
            result["healthcare_advice"] = [
                "Maintain regular sleep schedule and hydration.",
                "Take balanced Bangladeshi diet with protein, vegetables, fruits, and safe drinking water.",
                "Avoid self-medicating with antibiotics or vitamins without doctor advice.",
                "Monitor cough, fever, breathing difficulty, worsening headache, weakness, and general condition.",
            ]

        result["investigation_advice"] = [
            "CBC with hemoglobin percentage",
            "TSH and FT4 for thyroid evaluation",
            "Serum ferritin / iron profile if hair fall and tiredness persist",
            "Vitamin D and Vitamin B12 level if clinically indicated",
            "Fasting blood glucose or random blood glucose",
            "Doctor physical examination based on symptoms",
        ]

        result["follow_up_advice"] = (
            "Consult a registered doctor within 2–3 days for proper evaluation. "
            "Seek urgent care if breathing difficulty, high fever, severe headache, weakness, confusion, chest pain, or worsening symptoms occur."
        )

        result["quality_note"] = (
            "Broad/non-specific case: medicine candidates are generated dynamically and must be verified by doctor."
        )

        return result

    if not result["healthcare_advice"]:
        result["healthcare_advice"] = [
            "Drink safe water and maintain hydration.",
            "Take rest and monitor symptoms.",
            "Avoid self-medicating with antibiotics or prescription medicines.",
            "Seek medical care if symptoms worsen.",
        ]

    if not result["investigation_advice"]:
        result["investigation_advice"] = [
            "Relevant investigations based on doctor assessment",
            "Physical examination by a registered doctor if symptoms persist or worsen",
        ]

    if not result.get("follow_up_advice"):
        result["follow_up_advice"] = "Follow up with a doctor if symptoms persist or worsen."

    return result


async def agent3_prescription_generator(
    patient_data: Dict[str, Any],
    agent1_review: Dict[str, Any],
    agent2_review: Dict[str, Any],
) -> Dict[str, Any]:
    system_prompt = """
You are Agent 3 in a medical consultation demo system for Bangladesh.

Task:
Generate a structured prescription draft for doctor review.

VERY IMPORTANT RULES:
- This is an AI-generated draft only. A registered doctor will review and approve it.
- The goal is to reduce doctor workload, not to replace the doctor.
- Medicine must be generated dynamically from the full patient case, not from a fixed template.
- Do NOT give the same medicines for every case.
- Do NOT follow simple symptom-to-medicine mapping.
- Do NOT use a fixed number of medicines.
- Do NOT always give 1, 2, or 3 medicines.
- Do NOT prescribe medicine just to fill the Rx section.
- Best effort: try not to leave medicine_section empty, but safety and clinical justification come first.
- If no safe clinically justified medicine candidate is clear, medicine_section may be empty.
- Emergency warning and urgent doctor/emergency referral must remain visible when red flags exist.
- Emergency cases may include medicine candidates only if they are safe, case-specific, and clearly doctor-review candidates; do not provide definitive emergency treatment.
- Avoid heart medicine, blood pressure medicine, aspirin, nitroglycerin, sedatives, steroids, anticoagulants, insulin, strong painkillers, or antibiotics unless clearly justified for doctor review.
- Avoid unnecessary antibiotics.
- If an antibiotic is clinically indicated, medicine_name must be a specific generic antibiotic name, not just "Antibiotic".
- If bacterial indication is unclear, do not add an antibiotic in Rx. Instead add investigation_advice and follow_up_advice.
- Do NOT suggest vitamins unless deficiency is known, strongly suspected with proper context, or doctor review is needed.
- Never write vague medicine/category names: Antibiotic, Painkiller, Antihistamine, Vitamin, Multivitamin, Cough syrup, Tablet, Capsule, Syrup, Supplement.
- Use specific generic medicine names only.
- For every medicine, include dose, frequency, duration, and a note.
- For every medicine, the note must explain the case-specific reason and what the doctor must verify.
- Prefer generic names, not Bangladeshi brand names.
- Consider all patient information, not only the main symptom text.
- Do not invent patient history, disease, medicine use, pregnancy status, HIV/ART, TB, diabetes, hypertension, or allergy unless provided.

Bangladesh-specific context:
- This will be used for Bangladeshi patients.
- Consider Bangladesh common context: hot weather, dehydration risk, food/water hygiene, seasonal fever, dengue/viral fever context, respiratory infection, dust/air pollution, nutrition, and access to common generic medicines.
- Respect local safety: avoid random antibiotics, avoid random steroids, avoid random sedatives, avoid unnecessary injections.
- Use generic names suitable for doctor review in Bangladesh, not brand names.
- Prioritize practical investigations and doctor review when medicine choice is uncertain.

You must consider ALL of these:
- age
- sex
- blood group
- main symptoms
- duration
- temperature
- blood pressure
- oxygen level
- existing disease
- current medicine
- allergies
- additional information
- follow-up answers
- Agent 1 review
- Agent 2 analysis
- Bangladesh country context

Return only valid JSON.

JSON format:
{
  "document_title": "AI Prescription Draft",
  "status": "AI Generated",
  "top_warning": "string or empty",
  "patient_information": {
    "name": "string",
    "age": "string or number",
    "sex": "string",
    "blood_group": "string"
  },
  "chief_complaints": ["string"],
  "possible_diagnosis": ["string"],
  "medicine_section": [
    {
      "medicine_name": "specific generic medicine name, never vague category name",
      "dose": "string",
      "frequency": "string",
      "duration": "string",
      "note": "case-specific reason and doctor verification note"
    }
  ],
  "healthcare_advice": ["string"],
  "investigation_advice": ["string"],
  "follow_up_advice": "string",
  "all_patient_fields_considered": true,
  "country_context": "Bangladesh"
}
"""

    context = build_full_patient_context(
        patient_data,
        followup_answers=agent1_review.get("followup_answers_used", []),
        agent1_review=agent1_review,
        agent2_review=agent2_review,
    )

    result = await call_groq_json(
        system_prompt=system_prompt,
        user_payload=context,
        temperature=0.3,
        max_tokens=3500,
    )

    if not result or not isinstance(result, dict):
        result = fallback_agent3_prescription(patient_data, agent1_review, agent2_review)

    result = enforce_prescription_quality(
        result=result,
        patient_data=patient_data,
        agent1_review=agent1_review,
        agent2_review=agent2_review,
    )

    if not result.get("medicine_section"):
        repaired_medicines = await repair_medicine_section_with_ai(
            patient_data=patient_data,
            current_result=result,
            agent1_review=agent1_review,
            agent2_review=agent2_review,
            attempt=1,
        )

        if repaired_medicines:
            result["medicine_section"] = repaired_medicines
            result = enforce_prescription_quality(
                result=result,
                patient_data=patient_data,
                agent1_review=agent1_review,
                agent2_review=agent2_review,
            )

    if not result.get("medicine_section"):
        repaired_medicines = await repair_medicine_section_with_ai(
            patient_data=patient_data,
            current_result=result,
            agent1_review=agent1_review,
            agent2_review=agent2_review,
            attempt=2,
        )

        if repaired_medicines:
            result["medicine_section"] = repaired_medicines
            result = enforce_prescription_quality(
                result=result,
                patient_data=patient_data,
                agent1_review=agent1_review,
                agent2_review=agent2_review,
            )

    if not result.get("medicine_section"):
        final_retry_medicines = await final_medicine_retry_with_ai(
            patient_data=patient_data,
            current_result=result,
            agent1_review=agent1_review,
            agent2_review=agent2_review,
        )

        if final_retry_medicines:
            result["medicine_section"] = final_retry_medicines
            result = enforce_prescription_quality(
                result=result,
                patient_data=patient_data,
                agent1_review=agent1_review,
                agent2_review=agent2_review,
            )

    if not result.get("medicine_section"):
        result["quality_note"] = (
            "Medicine section is empty because the AI could not identify a safe, case-specific, "
            "doctor-review medicine candidate. Doctor assessment is required before medication."
        )

    return result


def prescription_json_to_text(data: Dict[str, Any]) -> str:
    patient = data.get("patient_information", {}) or {}

    lines: List[str] = []

    warning = data.get("top_warning", "")

    if warning:
        lines.append(warning)
        lines.append("")

    lines.append("Patient Details:")
    lines.append(f"Name: {patient.get('name', '-')}")
    lines.append(f"Age: {patient.get('age', '-')}")
    lines.append(f"Sex: {patient.get('sex', '-')}")
    lines.append(f"Blood Group: {patient.get('blood_group', '-')}")
    lines.append("")

    lines.append("Chief Complaints:")
    complaints = data.get("chief_complaints", [])

    if complaints:
        for item in complaints:
            lines.append(f"- {item}")
    else:
        lines.append("- Not available")

    lines.append("")

    lines.append("Provisional Diagnosis:")
    diagnosis = data.get("possible_diagnosis", [])

    if diagnosis:
        for item in diagnosis:
            lines.append(f"- {item}")
    else:
        lines.append("- Not available")

    lines.append("")

    lines.append("Rx:")
    medicines = data.get("medicine_section", [])

    if medicines:
        for index, med in enumerate(medicines, start=1):
            lines.append(f"{index}. {med.get('medicine_name', 'Medicine')}")
            lines.append(f"   Dose: {med.get('dose', '-')}")
            lines.append(f"   Frequency: {med.get('frequency', '-')}")
            lines.append(f"   Duration: {med.get('duration', '-')}")
            lines.append(f"   Note: {med.get('note', '-')}")
            lines.append("")
    else:
        lines.append("- No medicine candidate selected in this draft. Doctor review required.")
        lines.append("")

    lines.append("Advice:")
    advice = data.get("healthcare_advice", [])

    if advice:
        for item in advice:
            lines.append(f"- {item}")
    else:
        lines.append("- Not available")

    lines.append("")

    lines.append("Investigations:")
    investigations = data.get("investigation_advice", [])

    if investigations:
        for item in investigations:
            lines.append(f"- {item}")
    else:
        lines.append("- Not available")

    lines.append("")

    lines.append("Follow-up:")
    lines.append(data.get("follow_up_advice", "Follow up if symptoms persist or worsen."))

    quality_note = data.get("quality_note")
    if quality_note:
        lines.append("")
        lines.append("Quality Note:")
        lines.append(str(quality_note))

    return "\n".join(lines)