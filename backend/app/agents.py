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

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}

    try:
        return json.loads(match.group(0))
    except Exception:
        return {}


async def call_groq_json(system_prompt: str, user_payload: Dict[str, Any]) -> Dict[str, Any]:
    client = get_groq_client()
    if not client:
        return {}

    try:
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
            ],
            temperature=0.2,
            max_tokens=3200,
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
    parts = re.split(r"[,;\n]+", str(value))
    return [part.strip() for part in parts if part.strip()]


def detect_emergency(symptoms: str, additional_info: str = "") -> bool:
    text = f"{symptoms or ''} {additional_info or ''}".lower()
    emergency_keywords = [
        "chest pain", "severe chest pain", "stroke", "unconscious", "fainting",
        "severe breathing problem", "shortness of breath", "oxygen low", "spo2 low",
        "seizure", "convulsion", "severe bleeding", "blood vomiting", "black stool",
        "severe dehydration", "confusion", "suicidal", "pregnant severe pain",
        "high fever with stiff neck", "severe allergic reaction", "anaphylaxis",
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
            "Use all fields, not only symptoms. This is a doctor-facing AI prescription draft. "
            "Never use vague medicine category names such as Antibiotic. Use specific generic names only when clinically supported."
        ),
    }


def fallback_followup_questions(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    symptoms = (patient_data.get("symptoms") or "").lower()
    additional = (patient_data.get("additional_info") or "").lower()
    text = f"{symptoms} {additional}"
    questions: List[Dict[str, str]] = []

    if any(word in text for word in ["diarrhea", "vomiting", "stomach", "loose stool", "পেট", "ডায়রিয়া", "বমি"]):
        questions.extend([
            {"question": "How many times did vomiting or loose stool happen today?", "reason": "To understand dehydration risk and severity.", "related_to": "stomach/vomiting/diarrhea", "priority": "high"},
            {"question": "Did you notice blood in stool or vomit?", "reason": "Blood may indicate a serious condition.", "related_to": "gastrointestinal warning sign", "priority": "high"},
            {"question": "Can you drink water or ORS without vomiting?", "reason": "To assess hydration status.", "related_to": "dehydration", "priority": "high"},
        ])

    if any(word in text for word in ["fever", "temperature", "জ্বর"]):
        questions.extend([
            {"question": "What is the highest recorded temperature?", "reason": "Fever level helps estimate severity.", "related_to": "fever", "priority": "medium"},
            {"question": "Do you have rash, severe headache, severe body pain, or bleeding?", "reason": "These can be relevant in Bangladesh fever cases.", "related_to": "fever pattern", "priority": "high"},
        ])

    if any(word in text for word in ["cough", "cold", "sore throat", "throat", "কাশি", "গলা"]):
        questions.extend([
            {"question": "Do you have fever, breathing difficulty, chest pain, or thick yellow/green phlegm?", "reason": "To identify respiratory red flags or possible bacterial features.", "related_to": "respiratory symptoms", "priority": "high"},
            {"question": "How many days have you had the cough?", "reason": "Duration helps separate viral cough from persistent illness.", "related_to": "cough duration", "priority": "medium"},
        ])

    if any(word in text for word in ["urine", "burning urination", "uti", "প্রস্রাব"]):
        questions.extend([
            {"question": "Do you feel burning during urination or lower abdominal pain?", "reason": "To assess possible urinary tract infection.", "related_to": "urinary symptoms", "priority": "high"},
            {"question": "Do you have fever or back/flank pain?", "reason": "Fever or flank pain may suggest complicated infection.", "related_to": "urinary red flags", "priority": "high"},
        ])

    if not questions:
        questions = [
            {"question": "Is the problem getting better, worse, or staying the same?", "reason": "Symptom progression helps assess urgency.", "related_to": "overall condition", "priority": "medium"},
            {"question": "Do you have any known allergy to medicine?", "reason": "Allergy information is important before prescription drafting.", "related_to": "medicine safety", "priority": "high"},
            {"question": "Are you currently taking any medicine?", "reason": "Current medicine may interact with new medicine.", "related_to": "current medication", "priority": "high"},
        ]

    seen = set()
    unique_questions = []
    for item in questions:
        key = item["question"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique_questions.append(item)

    return {
        "questions": unique_questions[:7],
        "emergency_detected": detect_emergency(patient_data.get("symptoms", ""), patient_data.get("additional_info", "")),
    }


async def agent1_generate_questions(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = """
You are Agent 1 in a medical consultation demo system for Bangladesh.
Generate 3 to 7 patient-friendly follow-up questions.
Use ALL fields: symptoms, duration, age, sex, vitals, existing disease, current medicine, allergies, additional info.
Do not focus only on main symptoms. Detect emergency signals.
Return only valid JSON:
{"questions":[{"question":"string","reason":"string","related_to":"string","priority":"high|medium|low"}],"emergency_detected":true}
"""
    result = await call_groq_json(system_prompt, build_full_patient_context(patient_data))
    if not result or not isinstance(result.get("questions"), list):
        return fallback_followup_questions(patient_data)
    result["emergency_detected"] = bool(result.get("emergency_detected") or detect_emergency(patient_data.get("symptoms", ""), patient_data.get("additional_info", "")))
    return result


def fallback_agent1_review(patient_data: Dict[str, Any], followup_answers: List[Dict[str, str]]) -> Dict[str, Any]:
    symptoms = patient_data.get("symptoms", "")
    duration = patient_data.get("duration", "")
    emergency = detect_emergency(symptoms, patient_data.get("additional_info", ""))
    return {
        "emergency_warning": "Please seek emergency medical care immediately." if emergency else "",
        "structured_symptoms": [{"symptom": symptoms, "severity": "unknown", "note": f"Duration: {duration}"}],
        "initial_clinical_review": {
            "summary": f"Patient reports {symptoms} for {duration}. Additional context: {patient_data.get('additional_info', '') or 'none'}.",
            "possible_conditions": ["Needs clinical review based on complete patient history."],
            "reasoning": "This review considered symptoms, duration, vitals, existing disease, current medicines, allergies, additional information, and follow-up answers.",
            "urgency_level": "high" if emergency else "medium",
            "confidence": "limited without physical examination",
        },
        "followup_answers_used": followup_answers,
    }


async def agent1_initial_review(patient_data: Dict[str, Any], followup_answers: List[Dict[str, str]]) -> Dict[str, Any]:
    system_prompt = """
You are Agent 1 in a medical consultation demo system for Bangladesh.
Create an initial clinical review. Use ALL fields and follow-up answers.
Return only valid JSON:
{
 "emergency_warning":"string or empty",
 "structured_symptoms":[{"symptom":"string","severity":"string","note":"string"}],
 "initial_clinical_review":{"summary":"string","possible_conditions":["string"],"reasoning":"string","urgency_level":"low|medium|high","confidence":"string"},
 "followup_answers_used":[{"question":"string","answer":"string"}]
}
"""
    result = await call_groq_json(system_prompt, build_full_patient_context(patient_data, followup_answers=followup_answers))
    if not result or not isinstance(result, dict):
        return fallback_agent1_review(patient_data, followup_answers)
    if detect_emergency(patient_data.get("symptoms", ""), patient_data.get("additional_info", "")):
        result["emergency_warning"] = "Please seek emergency medical care immediately."
    result["followup_answers_used"] = followup_answers
    return result


def fallback_agent2_analysis(patient_data: Dict[str, Any], agent1_review: Dict[str, Any]) -> Dict[str, Any]:
    symptoms = (patient_data.get("symptoms") or "").lower()
    additional = (patient_data.get("additional_info") or "").lower()
    text = f"{symptoms} {additional}"
    possible = []

    if any(word in text for word in ["diarrhea", "vomiting", "stomach", "loose stool"]):
        possible = [{"possible_condition": "Acute gastroenteritis or food/water-related stomach upset", "likelihood": "possible", "reason": "Relevant to stomach pain, vomiting, diarrhea, food exposure, and hydration status."}]
    elif any(word in text for word in ["fever", "cough", "cold", "sore throat"]):
        possible = [{"possible_condition": "Viral upper respiratory infection or seasonal respiratory illness", "likelihood": "possible", "reason": "Relevant to fever/cough/cold symptoms in Bangladesh context."}]
    elif any(word in text for word in ["urine", "burning urination", "uti"]):
        possible = [{"possible_condition": "Possible urinary tract infection", "likelihood": "possible", "reason": "Urinary symptoms need urine R/E and doctor assessment."}]
    else:
        possible = [{"possible_condition": "Non-specific clinical condition requiring doctor review", "likelihood": "uncertain", "reason": "Insufficient details for strong differential analysis."}]

    return {
        "case_summary": (
            f"Symptoms: {patient_data.get('symptoms', '')}. Duration: {patient_data.get('duration', '')}. "
            f"Vitals: temperature {patient_data.get('temperature', 'unknown')}, BP {patient_data.get('blood_pressure', 'unknown')}, oxygen {patient_data.get('oxygen_level', 'unknown')}. "
            f"Additional info: {patient_data.get('additional_info', '') or 'none'}."
        ),
        "deep_analysis": possible,
        "why_it_may_have_happened": [patient_data.get("additional_info") or "Cause needs clinical correlation."],
        "doctor_consideration_tests": ["CBC if fever, infection signs, weakness, or persistent symptoms are present", "Relevant test based on symptoms and doctor assessment"],
        "emergency_risk": "high" if detect_emergency(patient_data.get("symptoms", ""), patient_data.get("additional_info", "")) else "not obvious",
        "confidence": "limited without physical examination",
        "all_fields_considered": True,
    }


async def agent2_deep_analysis(patient_data: Dict[str, Any], agent1_review: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = """
You are Agent 2 in a medical consultation demo system for Bangladesh.
Perform deeper clinical analysis using ALL patient fields and Agent 1 review.
Bangladesh context: food/water hygiene, seasonal fever, dengue/viral fever, dehydration, heat, dust/air pollution, local illness patterns.
Return only valid JSON:
{"case_summary":"string","deep_analysis":[{"possible_condition":"string","likelihood":"high|medium|low|possible|uncertain","reason":"string"}],"why_it_may_have_happened":["string"],"doctor_consideration_tests":["string"],"emergency_risk":"low|medium|high|not obvious","confidence":"string","all_fields_considered":true}
"""
    context = build_full_patient_context(patient_data, followup_answers=agent1_review.get("followup_answers_used", []), agent1_review=agent1_review)
    result = await call_groq_json(system_prompt, context)
    if not result or not isinstance(result, dict):
        return fallback_agent2_analysis(patient_data, agent1_review)
    result["all_fields_considered"] = True
    return result


def is_vague_medicine_name(name: str) -> bool:
    clean = (name or "").strip().lower()
    vague_names = {
        "medicine", "drug", "tablet", "capsule", "syrup", "antibiotic", "antibiotics", "an antibiotic",
        "oral antibiotic", "broad spectrum antibiotic", "broad-spectrum antibiotic", "appropriate antibiotic",
        "empirical antibiotic", "empiric antibiotic", "antibiotic therapy", "painkiller", "analgesic",
        "antihistamine", "cough syrup", "vitamin", "multivitamin",
    }
    return clean in vague_names


def looks_like_specific_antibiotic(name: str) -> bool:
    clean = (name or "").strip().lower()
    specific_antibiotics = [
        "amoxicillin", "clavulanic", "co-amoxiclav", "azithromycin", "cefixime", "cefuroxime",
        "cephalexin", "flucloxacillin", "doxycycline", "metronidazole", "ciprofloxacin",
        "levofloxacin", "nitrofurantoin", "ceftriaxone", "cefpodoxime", "clindamycin",
    ]
    return any(item in clean for item in specific_antibiotics)


def condition_supports_antibiotic(patient_data: Dict[str, Any]) -> bool:
    symptoms = (patient_data.get("symptoms") or "").lower()
    additional = (patient_data.get("additional_info") or "").lower()
    temperature = (patient_data.get("temperature") or "").lower()
    duration = (patient_data.get("duration") or "").lower()
    text = f"{symptoms} {additional} {temperature} {duration}"

    supportive_keywords = [
        "pus", "wound infection", "cellulitis", "boil", "abscess", "burning urination",
        "urine burning", "uti", "tonsil pus", "productive cough with fever", "pneumonia",
        "dysentery", "blood in stool", "dental infection", "ear discharge", "high fever for 3 days",
        "fever more than 3 days",
    ]
    return any(keyword in text for keyword in supportive_keywords)


def clean_medicine_suggestions(medicines: List[Dict[str, str]], patient_data: Dict[str, Any]) -> List[Dict[str, str]]:
    allergies = (patient_data.get("allergies") or "").lower()
    existing = (patient_data.get("existing_disease") or "").lower()
    full_text = f"{patient_data.get('symptoms', '')} {patient_data.get('additional_info', '')} {allergies} {existing}".lower()
    antibiotic_supported = condition_supports_antibiotic(patient_data)
    cleaned: List[Dict[str, str]] = []

    for med in medicines:
        if not isinstance(med, dict):
            continue
        name = str(med.get("medicine_name", "")).strip()
        name_lower = name.lower()
        if not name or is_vague_medicine_name(name):
            continue

        if "antibiotic" in name_lower and not looks_like_specific_antibiotic(name):
            continue
        if looks_like_specific_antibiotic(name) and not antibiotic_supported:
            continue

        if "vitamin" in name_lower and not any(clue in full_text for clue in ["vitamin d low", "vitamin b12 low", "deficiency confirmed", "lab confirmed", "doctor advised vitamin"]):
            continue
        if "paracetamol" in name_lower and "liver" in existing:
            continue

        for key in ["dose", "frequency", "duration", "note"]:
            if key not in med or not str(med.get(key, "")).strip():
                med[key] = "Doctor to confirm" if key != "note" else "Doctor should confirm suitability before approval."

        if looks_like_specific_antibiotic(name):
            med["note"] = (
                str(med.get("note", "")).strip()
                + " Doctor must confirm bacterial indication, allergy status, pregnancy status, renal/liver status, local resistance pattern, and suitability before approval."
            ).strip()

        cleaned.append(med)

    return cleaned[:5]


def is_broad_non_specific_case(patient_data: Dict[str, Any]) -> bool:
    symptoms = (patient_data.get("symptoms") or "").lower()
    additional = (patient_data.get("additional_info") or "").lower()
    duration = (patient_data.get("duration") or "").lower()
    text = f"{symptoms} {additional} {duration}"
    broad_keywords = [
        "hair fall", "hair loss", "tired", "fatigue", "weak", "weakness", "over sleeping",
        "oversleeping", "sleepy", "headache", "neck pain", "body pain", "stress", "depression", "low energy",
    ]
    acute_keywords = ["diarrhea", "vomiting", "loose stool", "high fever", "chest pain", "shortness of breath", "bleeding", "severe pain", "burning urination", "blood in stool"]
    broad_count = sum(1 for word in broad_keywords if word in text)
    has_clear_acute = any(word in text for word in acute_keywords)
    long_duration = any(word in duration for word in ["week", "weeks", "month", "months", "long", "many days", "অনেকদিন"])
    return (broad_count >= 3 and not has_clear_acute) or (broad_count >= 2 and long_duration)


def build_dynamic_fallback_medicines(patient_data: Dict[str, Any]) -> List[Dict[str, str]]:
    symptoms = (patient_data.get("symptoms") or "").lower()
    additional = (patient_data.get("additional_info") or "").lower()
    allergies = (patient_data.get("allergies") or "").lower()
    existing = (patient_data.get("existing_disease") or "").lower()
    text = f"{symptoms} {additional}"
    medicines: List[Dict[str, str]] = []

    if detect_emergency(symptoms, additional) or is_broad_non_specific_case(patient_data):
        return []

    if any(word in text for word in ["diarrhea", "loose stool", "vomiting", "stomach", "পেট", "ডায়রিয়া", "বমি"]):
        medicines.append({"medicine_name": "Oral Rehydration Solution (ORS)", "dose": "Prepare according to packet instruction", "frequency": "Small frequent sips after vomiting or loose stool", "duration": "Until dehydration risk improves", "note": "Important for fluid and salt replacement in Bangladesh context."})
        if "vomiting" in text or "বমি" in text:
            medicines.append({"medicine_name": "Ondansetron", "dose": "4 mg", "frequency": "If vomiting continues, as directed by doctor", "duration": "Short course", "note": "Doctor should confirm suitability before final approval."})
        if any(word in text for word in ["fever", "জ্বর", "pain", "ব্যথা"]) and "paracetamol" not in allergies and "liver" not in existing:
            medicines.append({"medicine_name": "Paracetamol", "dose": "500 mg", "frequency": "If fever or pain occurs, as directed by doctor", "duration": "Short course", "note": "Avoid overdose and avoid if significant liver disease is present."})

    elif any(word in text for word in ["fever", "জ্বর", "body pain", "headache", "মাথা ব্যথা"]):
        if "paracetamol" not in allergies and "liver" not in existing:
            medicines.append({"medicine_name": "Paracetamol", "dose": "500 mg", "frequency": "If fever or body pain occurs, as directed by doctor", "duration": "Short course", "note": "Doctor should review temperature pattern and risk factors."})
        medicines.append({"medicine_name": "ORS / Fluid support", "dose": "As needed", "frequency": "Frequent fluids", "duration": "During fever period", "note": "Hydration is important in Bangladesh heat and fever context."})

    elif any(word in text for word in ["cough", "cold", "sore throat", "কাশি", "ঠান্ডা", "গলা"]):
        if "cetirizine" not in allergies:
            medicines.append({"medicine_name": "Cetirizine", "dose": "10 mg", "frequency": "Once at night if allergy/runny nose is present, as directed by doctor", "duration": "Short course", "note": "May cause drowsiness."})
        medicines.append({"medicine_name": "Normal saline gargle / steam inhalation", "dose": "Supportive care", "frequency": "As needed", "duration": "Few days", "note": "Supportive care for throat/nasal symptoms."})

    elif any(word in text for word in ["acidity", "gas", "heartburn", "gastric", "অ্যাসিডিটি"]):
        medicines.append({"medicine_name": "Antacid", "dose": "As directed by doctor", "frequency": "After meal if acidity occurs", "duration": "Short course", "note": "Diet and meal timing should also be reviewed."})

    return clean_medicine_suggestions(medicines, patient_data)


def fallback_agent3_prescription(patient_data: Dict[str, Any], agent1_review: Dict[str, Any], agent2_review: Dict[str, Any]) -> Dict[str, Any]:
    emergency = detect_emergency(patient_data.get("symptoms", ""), patient_data.get("additional_info", ""))
    symptoms_list = list_from_text(patient_data.get("symptoms", ""))
    diagnosis: List[str] = []
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
        "top_warning": "Please seek emergency medical care immediately." if emergency else "",
        "patient_information": {"name": patient_data.get("name", ""), "age": patient_data.get("age", ""), "sex": patient_data.get("sex", ""), "blood_group": patient_data.get("blood_group", "")},
        "chief_complaints": symptoms_list or [patient_data.get("symptoms", "")],
        "possible_diagnosis": diagnosis[:3],
        "medicine_section": [] if emergency else build_dynamic_fallback_medicines(patient_data),
        "healthcare_advice": ["Drink safe water and maintain hydration.", "Avoid self-medicating with antibiotics.", "Take rest and monitor symptoms.", "Seek urgent care if symptoms worsen or red flag signs appear."],
        "investigation_advice": agent2_review.get("doctor_consideration_tests", []) or ["CBC if fever or infection signs persist", "Relevant test based on doctor review"],
        "follow_up_advice": "Follow up with a registered doctor if symptoms persist or worsen.",
        "all_patient_fields_considered": True,
        "country_context": "Bangladesh",
    }


def enforce_prescription_quality(result: Dict[str, Any], patient_data: Dict[str, Any], agent1_review: Dict[str, Any], agent2_review: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        result = {}

    result["document_title"] = result.get("document_title") or "AI Prescription Draft"
    result["status"] = "AI Generated"
    result["country_context"] = "Bangladesh"
    result["all_patient_fields_considered"] = True
    result.setdefault("patient_information", {"name": patient_data.get("name", ""), "age": patient_data.get("age", ""), "sex": patient_data.get("sex", ""), "blood_group": patient_data.get("blood_group", "")})

    if not isinstance(result.get("chief_complaints"), list):
        result["chief_complaints"] = list_from_text(patient_data.get("symptoms", ""))
    if not isinstance(result.get("possible_diagnosis"), list):
        result["possible_diagnosis"] = ["Requires doctor review based on complete history"]
    if not isinstance(result.get("medicine_section"), list):
        result["medicine_section"] = []
    if not isinstance(result.get("healthcare_advice"), list):
        result["healthcare_advice"] = []
    if not isinstance(result.get("investigation_advice"), list):
        result["investigation_advice"] = []

    emergency = detect_emergency(patient_data.get("symptoms", ""), patient_data.get("additional_info", ""))
    if emergency:
        result["top_warning"] = "Please seek emergency medical care immediately."
        result["medicine_section"] = []
        result["healthcare_advice"] = ["Seek emergency medical care immediately.", "Do not delay care while waiting for online prescription review."]
        result["investigation_advice"] = ["Emergency doctor assessment required."]
        result["follow_up_advice"] = "Go to the nearest emergency department immediately."
        return result

    if is_broad_non_specific_case(patient_data):
        result["possible_diagnosis"] = [
            "Broad symptoms requiring clinical evaluation",
            "Possible thyroid imbalance, anemia, nutritional deficiency, sleep/stress-related issue, respiratory infection, or musculoskeletal strain should be assessed by a doctor",
        ]
        result["medicine_section"] = []
        result["healthcare_advice"] = [
            "Maintain regular sleep schedule and hydration.",
            "Take balanced Bangladeshi diet with protein, vegetables, fruits, and safe drinking water.",
            "Avoid self-medicating with antibiotics or vitamins without doctor advice.",
            "For neck pain, avoid prolonged bad posture and use gentle rest or heat therapy if comfortable.",
            "Monitor cough, fever, breathing difficulty, and worsening headache.",
        ]
        result["investigation_advice"] = [
            "CBC with hemoglobin percentage",
            "TSH and FT4 for thyroid evaluation",
            "Serum ferritin / iron profile if hair fall and tiredness persist",
            "Vitamin D and Vitamin B12 level if clinically indicated",
            "Fasting blood glucose or random blood glucose",
            "Doctor physical examination for cough and neck pain",
        ]
        result["follow_up_advice"] = "Consult a registered doctor within 2-3 days for proper evaluation. Seek urgent care if breathing difficulty, high fever, severe headache, weakness, confusion, or worsening symptoms occur."
        result["quality_note"] = "Medicine section intentionally left empty because symptoms are broad/non-specific. Investigation and doctor assessment are more appropriate before medication."
        return result

    result["medicine_section"] = clean_medicine_suggestions(result.get("medicine_section", []), patient_data)
    if not result["medicine_section"]:
        result["medicine_section"] = build_dynamic_fallback_medicines(patient_data)
    if not result["healthcare_advice"]:
        result["healthcare_advice"] = ["Drink safe water and maintain hydration.", "Take rest and monitor symptoms.", "Seek medical care if symptoms worsen."]
    if not result["investigation_advice"]:
        result["investigation_advice"] = ["Relevant investigations based on doctor assessment"]
    if not result.get("follow_up_advice"):
        result["follow_up_advice"] = "Follow up with a doctor if symptoms persist or worsen."
    return result


async def agent3_prescription_generator(patient_data: Dict[str, Any], agent1_review: Dict[str, Any], agent2_review: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = """
You are Agent 3 in a medical consultation demo system for Bangladesh.
Generate a structured prescription draft for DOCTOR REVIEW.

Rules:
- This is only an AI-generated draft. A registered doctor will review and approve it.
- Do NOT always give 2 medicines. Medicine count must be case-specific: 0, 1, 2, 3, 4, or 5.
- Never prescribe medicine just to fill Rx.
- Never write vague medicine/category names: Antibiotic, Painkiller, Antihistamine, Vitamin, Multivitamin, Cough syrup, Tablet.
- If an antibiotic is clinically reasonable, medicine_name must be a specific generic antibiotic name such as Amoxicillin + Clavulanic Acid, Azithromycin, Cefixime, Metronidazole, Nitrofurantoin, Doxycycline, Cephalexin, Cefuroxime, or Ciprofloxacin.
- Do not give antibiotics randomly. Only suggest a specific antibiotic candidate when symptoms/context supports bacterial infection: urinary symptoms, wound/pus, dysentery/blood in stool, dental infection, ear discharge, tonsillar pus, pneumonia features, or prolonged high fever with bacterial features.
- If bacterial indication is unclear, do not add antibiotic; add investigations and follow-up advice instead.
- For every antibiotic candidate, include dose, frequency, duration, and doctor verification note.
- Antibiotic dose/frequency/duration must not be blank.
- Hair fall + tiredness + oversleeping + headache type cases should NOT automatically receive multivitamin or paracetamol; prefer investigations first.
- Consider all patient information, not only the main symptom text.
- Use Bangladesh context: heat, dehydration, food/water hygiene, seasonal fever, dengue/viral fever, dust/air pollution, common lifestyle/nutrition issues.
- Prefer generic names, not brand names.

Return only valid JSON with this exact shape:
{
  "document_title": "AI Prescription Draft",
  "status": "AI Generated",
  "top_warning": "string or empty",
  "patient_information": {"name":"string","age":"string or number","sex":"string","blood_group":"string"},
  "chief_complaints": ["string"],
  "possible_diagnosis": ["string"],
  "medicine_section": [{"medicine_name":"specific generic medicine name","dose":"string","frequency":"string","duration":"string","note":"string"}],
  "healthcare_advice": ["string"],
  "investigation_advice": ["string"],
  "follow_up_advice": "string",
  "all_patient_fields_considered": true,
  "country_context": "Bangladesh"
}
"""
    context = build_full_patient_context(patient_data, followup_answers=agent1_review.get("followup_answers_used", []), agent1_review=agent1_review, agent2_review=agent2_review)
    result = await call_groq_json(system_prompt, context)
    if not result or not isinstance(result, dict):
        result = fallback_agent3_prescription(patient_data, agent1_review, agent2_review)
    return enforce_prescription_quality(result, patient_data, agent1_review, agent2_review)


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
        lines.append("- No routine medicine selected in this draft.")
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
    return "\n".join(lines)
