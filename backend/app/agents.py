import json
import re
from typing import Dict, Any, List

from groq import AsyncGroq

from app.config import settings


EMERGENCY_KEYWORDS = [
    "chest pain",
    "breathing difficulty",
    "shortness of breath",
    "unconscious",
    "fainted",
    "seizure",
    "heavy bleeding",
    "stroke",
    "paralysis",
    "confusion",
    "severe allergic",
    "swelling face",
    "suicidal",
    "poison",
    "severe dehydration",
    "pregnancy bleeding",
]


def detect_emergency(symptoms: str, additional_info: str = "") -> bool:
    text = f"{symptoms} {additional_info}".lower()
    return any(keyword in text for keyword in EMERGENCY_KEYWORDS)

def build_ai_medicine_suggestions(patient_data: Dict[str, Any], emergency: bool) -> List[Dict[str, str]]:
    symptoms = f"{patient_data.get('symptoms', '')} {patient_data.get('additional_info', '')}".lower()

    if emergency:
        return [
            {
                "medicine_name": "Emergency care required",
                "dose": "Immediate emergency medical evaluation",
                "frequency": "Now",
                "duration": "Until assessed by emergency care",
                "note": "Do not delay emergency medical care."
            }
        ]

    if any(word in symptoms for word in ["stomach", "abdominal", "vomit", "vomiting", "diarrhea", "food", "loose motion"]):
        return [
            {
                "medicine_name": "ORS / Oral Rehydration Solution",
                "dose": "Prepare as per packet instruction",
                "frequency": "Small frequent sips after vomiting or loose stool",
                "duration": "1-2 days",
                "note": "Maintain hydration."
            },
            {
                "medicine_name": "Ondansetron 4 mg",
                "dose": "1 tablet",
                "frequency": "Every 8 hours if vomiting occurs",
                "duration": "1 day",
                "note": "Avoid unnecessary use if vomiting stops."
            },
            {
                "medicine_name": "Probiotic capsule",
                "dose": "1 capsule",
                "frequency": "Once or twice daily",
                "duration": "3 days",
                "note": "For diarrhea support."
            }
        ]

    if any(word in symptoms for word in ["rash", "itchy", "itching", "allergy", "skin"]):
        return [
            {
                "medicine_name": "Cetirizine 10 mg",
                "dose": "1 tablet",
                "frequency": "At night",
                "duration": "3 days",
                "note": "May cause sleepiness."
            },
            {
                "medicine_name": "Calamine lotion",
                "dose": "Apply thin layer",
                "frequency": "2-3 times daily",
                "duration": "3 days",
                "note": "For itching and irritation."
            }
        ]

    if any(word in symptoms for word in ["urination", "urine", "burning", "uti", "frequent urination"]):
        return [
            {
                "medicine_name": "Urinary alkalinizer sachet",
                "dose": "1 sachet in water",
                "frequency": "2 times daily",
                "duration": "2 days",
                "note": "Drink enough water if not medically restricted."
            },
            {
                "medicine_name": "Paracetamol 500 mg",
                "dose": "1 tablet",
                "frequency": "Every 6-8 hours if pain occurs",
                "duration": "1-2 days",
                "note": "Do not exceed safe daily limit."
            }
        ]

    if any(word in symptoms for word in ["back pain", "lower back", "muscle", "lifting"]):
        return [
            {
                "medicine_name": "Paracetamol 500 mg",
                "dose": "1 tablet",
                "frequency": "Every 6-8 hours if pain occurs",
                "duration": "2 days",
                "note": "Avoid overdose."
            },
            {
                "medicine_name": "Pain relief gel",
                "dose": "Apply thin layer",
                "frequency": "2-3 times daily",
                "duration": "3 days",
                "note": "Apply externally only."
            }
        ]

    if any(word in symptoms for word in ["headache", "migraine", "nausea", "light"]):
        return [
            {
                "medicine_name": "Paracetamol 500 mg",
                "dose": "1 tablet",
                "frequency": "Every 6-8 hours if headache occurs",
                "duration": "1-2 days",
                "note": "Avoid overdose."
            },
            {
                "medicine_name": "ORS / fluids",
                "dose": "As needed",
                "frequency": "Frequently",
                "duration": "1 day",
                "note": "Useful if dehydration or nausea is present."
            }
        ]

    if any(word in symptoms for word in ["cough", "chest tightness", "asthma", "wheezing"]):
        return [
            {
                "medicine_name": "Antihistamine option",
                "dose": "1 tablet",
                "frequency": "At night",
                "duration": "3 days",
                "note": "For allergic cough symptoms."
            },
            {
                "medicine_name": "Steam inhalation",
                "dose": "5-10 minutes",
                "frequency": "1-2 times daily",
                "duration": "3 days",
                "note": "Stop if breathing discomfort increases."
            }
        ]

    return [
        {
            "medicine_name": "Paracetamol 500 mg",
            "dose": "1 tablet",
            "frequency": "Every 6-8 hours if pain/discomfort occurs",
            "duration": "1-2 days",
            "note": "General symptom relief."
        }
    ]


def ensure_ai_medicine_section(result: Dict[str, Any], patient_data: Dict[str, Any], emergency: bool) -> Dict[str, Any]:
    meds = result.get("medicine_section")

    should_replace = False

    if not isinstance(meds, list) or len(meds) == 0:
        should_replace = True
    else:
        joined = json.dumps(meds).lower()
        bad_terms = [
            "doctor to verify",
            "doctor to determine",
            "medicine to be selected",
            "for doctor review only"
        ]
        if any(term in joined for term in bad_terms):
            should_replace = True

    if should_replace:
        result["medicine_section"] = build_ai_medicine_suggestions(patient_data, emergency)

    return result

def extract_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return {}


async def call_groq_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "your_groq_api_key_here":
        return {}

    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    try:
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return extract_json(content)
    except Exception as e:
        print("Groq error:", str(e))
        return {}


def fallback_questions(symptoms: str) -> List[Dict[str, Any]]:
    text = symptoms.lower()
    questions = []

    if "fever" in text or "temperature" in text:
        questions.extend([
            {
                "question": "What is your current body temperature?",
                "reason": "The patient reported fever, so temperature helps assess severity.",
                "related_to": "fever",
                "priority": "high",
                "can_skip": True,
            },
            {
                "question": "Do you have rash, bleeding, or severe weakness?",
                "reason": "Fever with body pain may need warning-sign screening.",
                "related_to": "fever/body pain",
                "priority": "high",
                "can_skip": True,
            },
        ])

    if "cough" in text or "cold" in text or "throat" in text:
        questions.extend([
            {
                "question": "Is your cough dry or with phlegm?",
                "reason": "Cough type helps understand respiratory symptoms.",
                "related_to": "cough",
                "priority": "medium",
                "can_skip": True,
            },
            {
                "question": "Do you have breathing difficulty or chest pain?",
                "reason": "These may be emergency warning signs in respiratory illness.",
                "related_to": "cough/breathing",
                "priority": "emergency",
                "can_skip": True,
            },
        ])

    if "stomach" in text or "abdominal" in text or "diarrhea" in text or "vomit" in text:
        questions.extend([
            {
                "question": "Do you have vomiting, diarrhea, or blood in stool?",
                "reason": "These symptoms help assess digestive illness severity.",
                "related_to": "stomach problem",
                "priority": "high",
                "can_skip": True,
            },
            {
                "question": "Where exactly is the abdominal pain located?",
                "reason": "Pain location helps the doctor understand possible causes.",
                "related_to": "abdominal pain",
                "priority": "medium",
                "can_skip": True,
            },
        ])

    if "headache" in text:
        questions.append(
            {
                "question": "Is the headache severe, sudden, or associated with vomiting/confusion?",
                "reason": "Certain headache patterns may need urgent medical evaluation.",
                "related_to": "headache",
                "priority": "high",
                "can_skip": True,
            }
        )

    if not questions:
        questions = [
            {
                "question": "When did the main symptom start and is it getting worse?",
                "reason": "Duration and progression help understand illness severity.",
                "related_to": "main symptoms",
                "priority": "medium",
                "can_skip": True,
            },
            {
                "question": "Do you have fever, severe pain, breathing difficulty, or weakness?",
                "reason": "These are common severity indicators.",
                "related_to": "overall condition",
                "priority": "high",
                "can_skip": True,
            },
            {
                "question": "Are you currently taking any medicine for this problem?",
                "reason": "Current medicine helps avoid unsafe duplication.",
                "related_to": "treatment history",
                "priority": "medium",
                "can_skip": True,
            },
        ]

    return questions[:5]


async def agent1_generate_questions(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    emergency = detect_emergency(
        patient_data.get("symptoms", ""),
        patient_data.get("additional_info", "") or "",
    )

    system_prompt = """
You are Agent 1 of MediGuard AI.
Your task is to ask only relevant follow-up questions based on the patient's given symptoms.

Rules:
- Required fields are already collected: name, age, sex, blood_group, symptoms, duration.
- Ask maximum 5 questions.
- Every question must be related to the symptoms.
- Do not ask random unrelated questions.
- User can skip all follow-up questions.
- Every question must include: question, reason, related_to, priority, can_skip.
- priority must be one of: low, medium, high, emergency.
- Return only valid JSON.

JSON format:
{
  "questions": [
    {
      "question": "string",
      "reason": "string",
      "related_to": "string",
      "priority": "low | medium | high | emergency",
      "can_skip": true
    }
  ],
  "emergency_detected": true
}
"""

    user_prompt = json.dumps(patient_data, indent=2)

    result = await call_groq_json(system_prompt, user_prompt)

    questions = result.get("questions") if result else None

    if not questions:
        questions = fallback_questions(patient_data.get("symptoms", ""))

    return {
        "questions": questions[:5],
        "emergency_detected": emergency,
    }


async def agent1_initial_review(patient_data: Dict[str, Any], followup_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    emergency = detect_emergency(
        patient_data.get("symptoms", ""),
        patient_data.get("additional_info", "") or "",
    )

    system_prompt = """
You are Agent 1: Patient Intake + Simple Clinical Review Assistant.

Tasks:
1. Structure the patient information.
2. Analyze symptoms lightly.
3. Create a simple initial clinical review.
4. Mention possible conditions using cautious language.
5. Do not confirm final diagnosis.
6. Do not prescribe medicine.
7. Mention skipped/unknown information if any.
8. If emergency signs exist, include: "Please seek emergency medical care immediately."
9. Return only valid JSON.

JSON format:
{
  "patient_profile": {
    "name": "string",
    "age": number,
    "sex": "string",
    "blood_group": "string"
  },
  "structured_symptoms": [
    {
      "symptom": "string",
      "duration": "string",
      "severity": "unknown | mild | moderate | severe",
      "note": "string"
    }
  ],
  "skipped_or_unknown": ["string"],
  "initial_clinical_review": {
    "summary": "string",
    "possible_conditions": ["string"],
    "reasoning": "string",
    "urgency_level": "low | moderate | urgent | emergency",
    "confidence": "low | medium | high"
  },
  "emergency_warning": "string or empty"
}
"""

    payload = {
        "patient_data": patient_data,
        "followup_answers": followup_answers,
        "emergency_detected": emergency,
    }

    result = await call_groq_json(system_prompt, json.dumps(payload, indent=2))

    if result:
        return result

    return {
        "patient_profile": {
            "name": patient_data.get("name"),
            "age": patient_data.get("age"),
            "sex": patient_data.get("sex"),
            "blood_group": patient_data.get("blood_group"),
        },
        "structured_symptoms": [
            {
                "symptom": patient_data.get("symptoms"),
                "duration": patient_data.get("duration"),
                "severity": "unknown",
                "note": "Generated by fallback because AI response was unavailable.",
            }
        ],
        "skipped_or_unknown": [
            item["question"] for item in followup_answers if not item.get("answer") or item.get("answer") == "Skipped"
        ],
        "initial_clinical_review": {
            "summary": f"The patient reports {patient_data.get('symptoms')} for {patient_data.get('duration')}.",
            "possible_conditions": ["Needs doctor review", "Common illness related to reported symptoms"],
            "reasoning": "The symptoms need professional evaluation. More details may improve accuracy.",
            "urgency_level": "emergency" if emergency else "moderate",
            "confidence": "low",
        },
        "emergency_warning": "Please seek emergency medical care immediately." if emergency else "",
    }


async def agent2_deep_analysis(patient_data: Dict[str, Any], agent1_review: Dict[str, Any]) -> Dict[str, Any]:
    emergency = detect_emergency(
        patient_data.get("symptoms", ""),
        patient_data.get("additional_info", "") or "",
    )

    system_prompt = """
You are Agent 2: Deep Clinical Analysis Assistant.

Tasks:
1. Analyze original patient data and Agent 1 review.
2. Create deeper clinical reasoning.
3. List possible sickness names cautiously.
4. Explain why the sickness may have happened.
5. Mention missing/skipped information.
6. Suggest doctor type and possible tests for doctor consideration.
7. Do not confirm final diagnosis.
8. Do not prescribe medicine.
9. If emergency signs exist, clearly mention emergency risk.
10. Return only valid JSON.

JSON format:
{
  "case_summary": "string",
  "deep_analysis": [
    {
      "possible_condition": "string",
      "likelihood": "low | moderate | high | cannot rule out",
      "supporting_points": ["string"],
      "limitations": ["string"]
    }
  ],
  "why_it_may_have_happened": ["string"],
  "missing_information": ["string"],
  "emergency_risk": "low | moderate | high | emergency",
  "recommended_doctor": "string",
  "doctor_consideration_tests": ["string"],
  "confidence": "low | medium | high"
}
"""

    payload = {
        "patient_data": patient_data,
        "agent1_review": agent1_review,
        "emergency_detected": emergency,
    }

    result = await call_groq_json(system_prompt, json.dumps(payload, indent=2))

    if result:
        return result

    return {
        "case_summary": f"{patient_data.get('age')}-year-old {patient_data.get('sex')} patient reports {patient_data.get('symptoms')} for {patient_data.get('duration')}.",
        "deep_analysis": [
            {
                "possible_condition": "Condition requires doctor review",
                "likelihood": "cannot rule out",
                "supporting_points": ["Symptoms were provided by patient"],
                "limitations": ["AI fallback used", "Doctor evaluation required"],
            }
        ],
        "why_it_may_have_happened": [
            "May be related to infection, lifestyle, exposure, or another medical condition depending on doctor assessment."
        ],
        "missing_information": ["Physical examination", "Vital signs", "Lab tests if needed"],
        "emergency_risk": "emergency" if emergency else "moderate",
        "recommended_doctor": "General physician / Medicine specialist",
        "doctor_consideration_tests": ["CBC or other tests if doctor thinks necessary"],
        "confidence": "low",
    }
def build_doctor_only_medicine_suggestions(patient_data: Dict[str, Any], emergency: bool) -> List[Dict[str, str]]:
    symptoms = f"{patient_data.get('symptoms', '')} {patient_data.get('additional_info', '')}".lower()

    if emergency:
        return [
            {
                "medicine_name": "Emergency treatment plan to be decided by doctor/emergency team",
                "dose": "Doctor to determine",
                "frequency": "Doctor to determine",
                "duration": "Doctor to determine",
                "note": "Emergency case. Patient should seek immediate medical care. Do not delay hospital evaluation."
            }
        ]

    if any(word in symptoms for word in ["stomach", "abdominal", "vomit", "vomiting", "diarrhea", "food", "loose motion"]):
        return [
            {
                "medicine_name": "ORS / Oral Rehydration Solution",
                "dose": "Doctor to confirm based on dehydration level",
                "frequency": "After each loose stool/vomiting episode as clinically appropriate",
                "duration": "Until hydration improves or as advised by doctor",
                "note": "Supportive rehydration option. Doctor should verify patient condition first."
            },
            {
                "medicine_name": "Antiemetic option, e.g., Ondansetron",
                "dose": "Doctor to determine",
                "frequency": "Doctor to determine",
                "duration": "Doctor to determine",
                "note": "For vomiting control only if doctor considers appropriate."
            },
            {
                "medicine_name": "Antispasmodic option, e.g., Hyoscine Butylbromide",
                "dose": "Doctor to determine",
                "frequency": "Doctor to determine",
                "duration": "Doctor to determine",
                "note": "For abdominal cramp only if doctor considers appropriate and no contraindication exists."
            },
            {
                "medicine_name": "Probiotic / Zinc option",
                "dose": "Doctor to determine",
                "frequency": "Doctor to determine",
                "duration": "Doctor to determine",
                "note": "May be considered for diarrhea depending on age, severity, and doctor judgement."
            }
        ]

    if any(word in symptoms for word in ["rash", "itchy", "itching", "allergy", "skin"]):
        return [
            {
                "medicine_name": "Antihistamine option, e.g., Cetirizine or Fexofenadine",
                "dose": "Doctor to determine",
                "frequency": "Doctor to determine",
                "duration": "Doctor to determine",
                "note": "For allergic itching/rash if doctor considers appropriate."
            },
            {
                "medicine_name": "Topical soothing/calamine option",
                "dose": "Doctor to determine",
                "frequency": "Doctor to determine",
                "duration": "Doctor to determine",
                "note": "For local skin irritation. Avoid if open wound or severe reaction unless doctor approves."
            }
        ]

    if any(word in symptoms for word in ["urination", "urine", "burning", "uti", "frequent urination"]):
        return [
            {
                "medicine_name": "Urinary alkalinizer / symptomatic urinary relief option",
                "dose": "Doctor to determine",
                "frequency": "Doctor to determine",
                "duration": "Doctor to determine",
                "note": "Only if doctor considers appropriate."
            },
            {
                "medicine_name": "Antibiotic option if UTI is confirmed/suspected by doctor",
                "dose": "Doctor to determine",
                "frequency": "Doctor to determine",
                "duration": "Doctor to determine",
                "note": "Antibiotics must be selected only by doctor after history, pregnancy status, allergy, and urine test consideration."
            }
        ]

    if any(word in symptoms for word in ["back pain", "lower back", "muscle", "lifting"]):
        return [
            {
                "medicine_name": "Pain reliever option, e.g., Paracetamol",
                "dose": "Doctor to determine",
                "frequency": "Doctor to determine",
                "duration": "Doctor to determine",
                "note": "For pain relief if doctor considers appropriate."
            },
            {
                "medicine_name": "Topical pain relief gel option",
                "dose": "Doctor to determine",
                "frequency": "Doctor to determine",
                "duration": "Doctor to determine",
                "note": "For local muscle pain if doctor approves."
            }
        ]

    if any(word in symptoms for word in ["cough", "chest tightness", "asthma", "wheezing"]):
        return [
            {
                "medicine_name": "Cough medicine / bronchodilator plan based on doctor assessment",
                "dose": "Doctor to determine",
                "frequency": "Doctor to determine",
                "duration": "Doctor to determine",
                "note": "Respiratory medicines must be selected by doctor, especially if asthma or breathing difficulty exists."
            }
        ]

    if any(word in symptoms for word in ["headache", "migraine", "nausea", "light"]):
        return [
            {
                "medicine_name": "Pain reliever option, e.g., Paracetamol",
                "dose": "Doctor to determine",
                "frequency": "Doctor to determine",
                "duration": "Doctor to determine",
                "note": "For headache relief if doctor considers appropriate."
            },
            {
                "medicine_name": "Anti-nausea option if needed",
                "dose": "Doctor to determine",
                "frequency": "Doctor to determine",
                "duration": "Doctor to determine",
                "note": "Only if doctor approves after checking red flags."
            }
        ]

    return [
        {
            "medicine_name": "Symptom-based medicine plan",
            "dose": "Doctor to determine",
            "frequency": "Doctor to determine",
            "duration": "Doctor to determine",
            "note": "Doctor should choose medicine after reviewing the patient condition."
        }
    ]


def ensure_doctor_only_medicine_section(result: Dict[str, Any], patient_data: Dict[str, Any], emergency: bool) -> Dict[str, Any]:
    current_meds = result.get("medicine_section")

    invalid = False

    if not isinstance(current_meds, list) or len(current_meds) == 0:
        invalid = True
    else:
        joined = json.dumps(current_meds).lower()
        if "doctor to verify" in joined and len(current_meds) <= 1:
            invalid = True

    if invalid:
        result["medicine_section"] = build_doctor_only_medicine_suggestions(patient_data, emergency)

    return result

async def agent3_prescription_generator(
    patient_data: Dict[str, Any],
    agent1_review: Dict[str, Any],
    agent2_review: Dict[str, Any],
) -> Dict[str, Any]:
    emergency = detect_emergency(
        patient_data.get("symptoms", ""),
        patient_data.get("additional_info", "") or "",
    )

    system_prompt = """
You are Agent 3: AI Prescription Content Generator for a project demo.

Important:
- Generate a complete AI-generated prescription content.
- This is for a project/demo system.
- Do not write "Pending Doctor Review".
- Do not write "Doctor to determine".
- Do not write "Doctor to verify".
- Do not write "For doctor review only".
- Include medicine name, dose, frequency, duration, and note.
- Use practical prescription-style formatting.
- If emergency risk exists, put this exact warning at the top:
  "Please seek emergency medical care immediately."
- Keep the prescription short and realistic.
- Do not write long clinical essay.
- Return only valid JSON.

JSON format:
{
  "document_title": "AI Generated Prescription",
  "top_warning": "string",
  "patient_information": {
    "name": "string",
    "age": number,
    "sex": "string",
    "blood_group": "string"
  },
  "chief_complaints": ["string"],
  "clinical_summary": "short string",
  "possible_diagnosis": ["string"],
  "investigation_advice": ["string"],
  "medicine_section": [
    {
      "medicine_name": "string",
      "dose": "string",
      "frequency": "string",
      "duration": "string",
      "note": "string"
    }
  ],
  "healthcare_advice": ["string"],
  "follow_up_advice": "string",
  "status": "AI Generated"
}
"""

    payload = {
        "patient_data": patient_data,
        "agent1_review": agent1_review,
        "agent2_review": agent2_review,
        "emergency_detected": emergency,
    }

    result = await call_groq_json(system_prompt, json.dumps(payload, indent=2))

    if result:
        if emergency and not result.get("top_warning"):
            result["top_warning"] = "Please seek emergency medical care immediately."

        result = ensure_ai_medicine_section(result, patient_data, emergency)
        result["status"] = "AI Generated"
        return result

    return {
        "document_title": "AI-Generated Prescription for Doctor Review",
        "top_warning": "Please seek emergency medical care immediately." if emergency else "",
        "patient_information": {
            "name": patient_data.get("name"),
            "age": patient_data.get("age"),
            "sex": patient_data.get("sex"),
            "blood_group": patient_data.get("blood_group"),
        },
        "chief_complaints": [patient_data.get("symptoms")],
        "clinical_summary": f"The patient reports {patient_data.get('symptoms')} for {patient_data.get('duration')}.",
        "possible_diagnosis": ["Doctor review required"],
        "reason_of_sickness": ["Reason needs clinical evaluation."],
        "investigation_advice": ["Doctor may suggest tests after examination."],
                "medicine_section": build_ai_medicine_suggestions(patient_data, emergency),
        "healthcare_advice": [
            "Take rest.",
            "Drink adequate fluid if not restricted.",
            "Seek medical help if symptoms worsen.",
        ],
        "follow_up_advice": "Follow up with a registered doctor.",
        "doctor_review_note": "This prescription must be reviewed and approved by a doctor before patient use.",
        "status": "Pending Doctor Review",
    }


def prescription_json_to_text(data: Dict[str, Any]) -> str:
    lines = []

    if data.get("top_warning"):
        lines.append(data.get("top_warning"))
        lines.append("")

    patient = data.get("patient_information", {})

    lines.append("Patient Details:")
    lines.append(f"Name: {patient.get('name', '')}")
    lines.append(f"Age: {patient.get('age', '')}")
    lines.append(f"Sex: {patient.get('sex', '')}")
    lines.append(f"Blood Group: {patient.get('blood_group', '')}")
    lines.append("")

    complaints = data.get("chief_complaints", [])
    if complaints:
        lines.append("Chief Complaints:")
        for item in complaints[:5]:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("Provisional Diagnosis:")
    diagnosis = data.get("possible_diagnosis", [])
    if diagnosis:
        for item in diagnosis[:3]:
            lines.append(f"- {item}")
    else:
        lines.append("- Symptom-based clinical impression")
    lines.append("")

    lines.append("Rx:")
    meds = data.get("medicine_section", [])

    if meds:
        for index, med in enumerate(meds, start=1):
            lines.append(f"{index}. {med.get('medicine_name', '')}")
            lines.append(f"   Dose: {med.get('dose', '')}")
            lines.append(f"   Frequency: {med.get('frequency', '')}")
            lines.append(f"   Duration: {med.get('duration', '')}")
            if med.get("note"):
                lines.append(f"   Note: {med.get('note')}")
            lines.append("")
    else:
        lines.append("1. Symptomatic treatment")
        lines.append("   Dose: As appropriate")
        lines.append("   Frequency: As appropriate")
        lines.append("   Duration: Short course")
        lines.append("")

    advice = data.get("healthcare_advice", [])
    if advice:
        lines.append("Advice:")
        for item in advice[:6]:
            lines.append(f"- {item}")
        lines.append("")

    investigations = data.get("investigation_advice", [])
    if investigations:
        lines.append("Investigations:")
        for item in investigations[:4]:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("Follow-up:")
    lines.append(data.get("follow_up_advice", "Follow up if symptoms persist or worsen."))
    lines.append("")

    return "\n".join(lines)