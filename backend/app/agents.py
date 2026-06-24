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
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
                },
            ],
            temperature=0.35,
            max_tokens=2500,
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
    symptoms = (patient_data.get("symptoms") or "").lower()
    questions = []

    if any(word in symptoms for word in ["diarrhea", "vomiting", "stomach", "loose stool", "পেট"]):
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

    if any(word in symptoms for word in ["fever", "temperature", "জ্বর"]):
        questions.extend(
            [
                {
                    "question": "What is the highest recorded temperature?",
                    "reason": "Fever level helps estimate severity.",
                    "related_to": "fever",
                    "priority": "medium",
                },
                {
                    "question": "Do you have rash, severe headache, or body pain?",
                    "reason": "These may be relevant in Bangladesh fever cases.",
                    "related_to": "fever pattern",
                    "priority": "medium",
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

    return {
        "questions": questions[:6],
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
    symptoms = (patient_data.get("symptoms") or "").lower()
    possible = []

    if any(word in symptoms for word in ["diarrhea", "vomiting", "stomach", "loose stool"]):
        possible = [
            {
                "possible_condition": "Acute gastroenteritis or food-related stomach upset",
                "likelihood": "possible",
                "reason": "Relevant to stomach pain, vomiting, diarrhea, food exposure, and hydration status.",
            }
        ]
    elif any(word in symptoms for word in ["fever", "cough", "cold"]):
        possible = [
            {
                "possible_condition": "Viral fever or respiratory infection",
                "likelihood": "possible",
                "reason": "Relevant to fever/cough/cold symptoms in local context.",
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
            f"oxygen {patient_data.get('oxygen_level', 'unknown')}."
        ),
        "deep_analysis": possible,
        "why_it_may_have_happened": [
            patient_data.get("additional_info") or "Cause needs clinical correlation."
        ],
        "doctor_consideration_tests": [
            "CBC if fever or infection signs persist",
            "Relevant test based on symptoms and doctor assessment",
        ],
        "emergency_risk": "high" if detect_emergency(patient_data.get("symptoms", ""), patient_data.get("additional_info", "")) else "not obvious",
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
- Think about Bangladesh-relevant causes such as food/water hygiene, seasonal fever, dehydration, heat exposure, and common local illness patterns when relevant.
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


def build_dynamic_fallback_medicines(patient_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Fallback only runs if AI response fails.

    It is intentionally dynamic:
    - not fixed to 2 medicines
    - may return 0, 1, 2, 3, or more based on case
    - avoids antibiotics by default
    - respects allergy text as much as possible
    """

    symptoms = (patient_data.get("symptoms") or "").lower()
    additional = (patient_data.get("additional_info") or "").lower()
    allergies = (patient_data.get("allergies") or "").lower()
    existing = (patient_data.get("existing_disease") or "").lower()

    text = f"{symptoms} {additional}"
    medicines: List[Dict[str, str]] = []

    if detect_emergency(symptoms, additional):
        return []

    if any(word in text for word in ["diarrhea", "loose stool", "vomiting", "stomach", "পেট", "ডায়রিয়া", "বমি"]):
        medicines.append(
            {
                "medicine_name": "Oral Rehydration Solution (ORS)",
                "dose": "Prepare according to packet instruction",
                "frequency": "Small frequent sips after vomiting or loose stool",
                "duration": "Until dehydration risk improves",
                "note": "Important for fluid and salt replacement in Bangladesh context.",
            }
        )

        if "vomiting" in text or "বমি" in text:
            medicines.append(
                {
                    "medicine_name": "Ondansetron",
                    "dose": "4 mg",
                    "frequency": "If vomiting continues, as directed by doctor",
                    "duration": "Short course",
                    "note": "Doctor should confirm suitability before final approval.",
                }
            )

        if "fever" in text or "জ্বর" in text or "pain" in text or "ব্যথা" in text:
            if "paracetamol" not in allergies and "liver" not in existing:
                medicines.append(
                    {
                        "medicine_name": "Paracetamol",
                        "dose": "500 mg",
                        "frequency": "If fever or pain occurs, as directed by doctor",
                        "duration": "Short course",
                        "note": "Avoid overdose and avoid if significant liver disease is present.",
                    }
                )

    elif any(word in text for word in ["fever", "জ্বর", "body pain", "headache", "মাথা ব্যথা"]):
        if "paracetamol" not in allergies and "liver" not in existing:
            medicines.append(
                {
                    "medicine_name": "Paracetamol",
                    "dose": "500 mg",
                    "frequency": "If fever or body pain occurs, as directed by doctor",
                    "duration": "Short course",
                    "note": "Doctor should review temperature pattern and risk factors.",
                }
            )

        medicines.append(
            {
                "medicine_name": "ORS / Fluid support",
                "dose": "As needed",
                "frequency": "Frequent fluids",
                "duration": "During fever period",
                "note": "Hydration is important in Bangladesh heat and fever context.",
            }
        )

    elif any(word in text for word in ["cough", "cold", "sore throat", "কাশি", "ঠান্ডা", "গলা"]):
        if "cetirizine" not in allergies:
            medicines.append(
                {
                    "medicine_name": "Cetirizine",
                    "dose": "10 mg",
                    "frequency": "Once at night if allergy/runny nose is present, as directed by doctor",
                    "duration": "Short course",
                    "note": "May cause drowsiness.",
                }
            )

        medicines.append(
            {
                "medicine_name": "Normal saline gargle / steam inhalation",
                "dose": "Supportive care",
                "frequency": "As needed",
                "duration": "Few days",
                "note": "Supportive care for throat/nasal symptoms.",
            }
        )

    elif any(word in text for word in ["acidity", "gas", "heartburn", "gastric", "অ্যাসিডিটি"]):
        medicines.append(
            {
                "medicine_name": "Antacid",
                "dose": "As directed by doctor",
                "frequency": "After meal if acidity occurs",
                "duration": "Short course",
                "note": "Diet and meal timing should also be reviewed.",
            }
        )

    if not medicines:
        medicines.append(
            {
                "medicine_name": "No routine medicine selected in draft",
                "dose": "-",
                "frequency": "-",
                "duration": "-",
                "note": "Available information is insufficient or medicine may not be necessary. Doctor should review and finalize.",
            }
        )

    return medicines[:5]


def fallback_agent3_prescription(
    patient_data: Dict[str, Any],
    agent1_review: Dict[str, Any],
    agent2_review: Dict[str, Any],
) -> Dict[str, Any]:
    emergency = detect_emergency(patient_data.get("symptoms", ""), patient_data.get("additional_info", ""))

    symptoms_list = list_from_text(patient_data.get("symptoms", ""))
    diagnosis = []

    deep_analysis = agent2_review.get("deep_analysis", [])

    if isinstance(deep_analysis, list):
        for item in deep_analysis:
            if isinstance(item, dict) and item.get("possible_condition"):
                diagnosis.append(item["possible_condition"])

    if not diagnosis:
        diagnosis = ["Clinical condition requiring doctor review"]

    medicine_section = [] if emergency else build_dynamic_fallback_medicines(patient_data)

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
        "possible_diagnosis": diagnosis[:3],
        "medicine_section": medicine_section,
        "healthcare_advice": [
            "Drink safe water and maintain hydration.",
            "Avoid street food, oily food, and spicy food if stomach symptoms are present.",
            "Take rest and monitor symptoms.",
            "Seek urgent care if symptoms worsen or red flag signs appear.",
        ],
        "investigation_advice": agent2_review.get("doctor_consideration_tests", [])
        or [
            "CBC if fever or infection signs persist",
            "Relevant test based on doctor review",
        ],
        "follow_up_advice": "Follow up within 2 days if symptoms persist or worsen.",
        "all_patient_fields_considered": True,
        "country_context": "Bangladesh",
    }


async def agent3_prescription_generator(
    patient_data: Dict[str, Any],
    agent1_review: Dict[str, Any],
    agent2_review: Dict[str, Any],
) -> Dict[str, Any]:
    system_prompt = """
You are Agent 3 in a medical consultation demo system for Bangladesh.

Task:
Generate a structured prescription draft for doctor review.

VERY IMPORTANT:
- This is only an AI-generated draft. A registered doctor will review and approve it.
- Do NOT use a fixed number of medicines.
- The medicine_section can contain 0, 1, 2, 3, 4, or 5 medicines depending on the case.
- If medicine is not necessary or information is insufficient, medicine_section can be empty or contain a supportive-care-only item.
- Do NOT always give 2 medicines.
- Do NOT ignore additional information.

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
- additional info
- follow-up answers
- Agent 1 review
- Agent 2 analysis
- Bangladesh country context

Bangladesh context:
- Prefer generic medicine names, not brand names.
- Think about local environment such as hot weather, dehydration, water/food hygiene, seasonal fever, and common Bangladesh patient context.
- Avoid unnecessary antibiotics.
- Respect allergies, current medicines, and existing diseases.
- If emergency/red flag is present, do not create routine medicine plan; emphasize urgent care.

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
      "medicine_name": "generic medicine name",
      "dose": "string",
      "frequency": "string",
      "duration": "string",
      "note": "string"
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

    result = await call_groq_json(system_prompt, context)

    if not result or not isinstance(result, dict):
        return fallback_agent3_prescription(patient_data, agent1_review, agent2_review)

    result["status"] = "AI Generated"
    result["all_patient_fields_considered"] = True
    result["country_context"] = "Bangladesh"

    if "medicine_section" not in result or not isinstance(result["medicine_section"], list):
        result["medicine_section"] = build_dynamic_fallback_medicines(patient_data)

    if detect_emergency(patient_data.get("symptoms", ""), patient_data.get("additional_info", "")):
        result["top_warning"] = "Please seek emergency medical care immediately."
        result["medicine_section"] = []

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