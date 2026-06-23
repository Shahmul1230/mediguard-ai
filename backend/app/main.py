import json
import os
from typing import Any, Dict, List

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth_service import create_auth_token, hash_password, verify_password
from app.config import settings
from app.database import Base, engine, get_db
from app.email_service import send_prescription_email
from app.models import Consultation, User
from app.report_service import create_docx, create_pdf
from app.schemas import (
    AuthResponse,
    ConsultationResponse,
    DoctorApproveRequest,
    DoctorRejectRequest,
    FollowUpSubmitRequest,
    LoginRequest,
    PatientIntakeRequest,
    RegisterRequest,
    UserOut,
)
from app.agents import (
    agent1_generate_questions,
    agent1_initial_review,
    agent2_deep_analysis,
    agent3_prescription_generator,
    prescription_json_to_text,
    detect_emergency,
)


Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def json_loads_safe(value: str | None, fallback):
    if not value:
        return fallback

    try:
        return json.loads(value)
    except Exception:
        return fallback


def get_token_from_header(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Login required")

    parts = authorization.split(" ")

    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    return parts[1]


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = get_token_from_header(authorization)

    user = db.query(User).filter(User.auth_token == token).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user


def consultation_to_response(item: Consultation) -> ConsultationResponse:
    return ConsultationResponse(
        id=item.id,
        user_id=item.user_id,
        name=item.name,
        email=item.email,
        age=item.age,
        sex=item.sex,
        blood_group=item.blood_group,
        symptoms=item.symptoms,
        duration=item.duration,
        status=item.status,
        emergency_detected=item.emergency_detected,
        follow_up_questions=json_loads_safe(item.follow_up_questions_json, None),
        follow_up_answers=json_loads_safe(item.follow_up_answers_json, None),
        agent1_review=json_loads_safe(item.agent1_review_json, None),
        agent2_review=json_loads_safe(item.agent2_review_json, None),
        agent3_prescription=json_loads_safe(item.agent3_prescription_json, None),
        prescription_text=item.prescription_text,
        doctor_name=item.doctor_name,
        doctor_registration=item.doctor_registration,
        doctor_notes=item.doctor_notes,
        doctor_decision=item.doctor_decision,
        rejection_reason=item.rejection_reason,
        email_sent=item.email_sent,
        email_error=item.email_error,
        can_patient_download=item.status == "doctor_approved",
    )


def require_doctor_key(x_doctor_key: str | None):
    if not x_doctor_key or x_doctor_key != settings.DOCTOR_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid doctor secret key")


def build_patient_data(item: Consultation) -> Dict[str, Any]:
    return {
        "name": item.name,
        "email": item.email,
        "age": item.age,
        "sex": item.sex,
        "blood_group": item.blood_group,
        "symptoms": item.symptoms,
        "duration": item.duration,
        "temperature": item.temperature or "unknown",
        "blood_pressure": item.blood_pressure or "unknown",
        "oxygen_level": item.oxygen_level or "unknown",
        "existing_disease": item.existing_disease or "unknown",
        "current_medicine": item.current_medicine or "unknown",
        "allergies": item.allergies or "unknown",
        "additional_info": item.additional_info or "",
    }


@app.get("/")
def root():
    return {
        "message": "MediGuard AI backend is running",
        "docs": "/docs",
    }


@app.post("/api/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == str(payload.email).lower()).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    token = create_auth_token()

    user = User(
        name=payload.name,
        email=str(payload.email).lower(),
        password_hash=hash_password(payload.password),
        auth_token=token,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return AuthResponse(
        token=token,
        user=UserOut(id=user.id, name=user.name, email=user.email),
    )


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == str(payload.email).lower()).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_auth_token()
    user.auth_token = token

    db.commit()
    db.refresh(user)

    return AuthResponse(
        token=token,
        user=UserOut(id=user.id, name=user.name, email=user.email),
    )


@app.get("/api/patient/me", response_model=UserOut)
def patient_me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
    )


@app.get("/api/patient/consultations", response_model=List[ConsultationResponse])
def patient_consultation_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(Consultation)
        .filter(Consultation.user_id == current_user.id)
        .order_by(Consultation.id.desc())
        .all()
    )

    return [consultation_to_response(item) for item in items]


@app.get("/api/patient/consultations/{consultation_id}", response_model=ConsultationResponse)
def patient_get_consultation(
    consultation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = (
        db.query(Consultation)
        .filter(
            Consultation.id == consultation_id,
            Consultation.user_id == current_user.id,
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Consultation not found")

    return consultation_to_response(item)


@app.post("/api/consultations", response_model=ConsultationResponse)
async def create_consultation(
    payload: PatientIntakeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    emergency = detect_emergency(payload.symptoms, payload.additional_info or "")

    item = Consultation(
        user_id=current_user.id,
        name=payload.name,
        email=current_user.email,
        age=payload.age,
        sex=payload.sex,
        blood_group=payload.blood_group,
        symptoms=payload.symptoms,
        duration=payload.duration,
        temperature=payload.temperature,
        blood_pressure=payload.blood_pressure,
        oxygen_level=payload.oxygen_level,
        existing_disease=payload.existing_disease,
        current_medicine=payload.current_medicine,
        allergies=payload.allergies,
        additional_info=payload.additional_info,
        emergency_detected="yes" if emergency else "no",
        status="follow_up_questions_generated",
        doctor_decision=None,
        rejection_reason=None,
        email_sent="no",
        email_error=None,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    patient_data = build_patient_data(item)
    q_result = await agent1_generate_questions(patient_data)

    item.follow_up_questions_json = json.dumps(q_result.get("questions", []))

    if q_result.get("emergency_detected"):
        item.emergency_detected = "yes"

    db.commit()
    db.refresh(item)

    return consultation_to_response(item)


@app.post("/api/consultations/{consultation_id}/submit-followups", response_model=ConsultationResponse)
async def submit_followups(
    consultation_id: int,
    payload: FollowUpSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = (
        db.query(Consultation)
        .filter(
            Consultation.id == consultation_id,
            Consultation.user_id == current_user.id,
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Consultation not found")

    followup_answers = [answer.model_dump() for answer in payload.answers]

    item.follow_up_answers_json = json.dumps(followup_answers)
    item.status = "running_ai_agents"
    item.doctor_decision = None
    item.rejection_reason = None

    db.commit()
    db.refresh(item)

    patient_data = build_patient_data(item)

    agent1 = await agent1_initial_review(patient_data, followup_answers)
    item.agent1_review_json = json.dumps(agent1)
    item.status = "agent1_completed"

    db.commit()
    db.refresh(item)

    agent2 = await agent2_deep_analysis(patient_data, agent1)
    item.agent2_review_json = json.dumps(agent2)
    item.status = "agent2_completed"

    db.commit()
    db.refresh(item)

    agent3 = await agent3_prescription_generator(patient_data, agent1, agent2)
    item.agent3_prescription_json = json.dumps(agent3)

    prescription_text = prescription_json_to_text(agent3)
    item.prescription_text = prescription_text

    draft_pdf = create_pdf(
        consultation_id=item.id,
        patient_name=item.name,
        prescription_text=prescription_text,
        status="AI_Draft",
    )

    draft_docx = create_docx(
        consultation_id=item.id,
        patient_name=item.name,
        prescription_text=prescription_text,
        status="AI_Draft",
    )

    item.pending_pdf_path = draft_pdf
    item.pending_docx_path = draft_docx

    item.final_pdf_path = None
    item.final_docx_path = None

    item.status = "doctor_review_pending"
    item.doctor_decision = "pending"
    item.rejection_reason = None
    item.email_sent = "no"
    item.email_error = None

    db.commit()
    db.refresh(item)

    return consultation_to_response(item)


@app.get("/api/consultations/{consultation_id}", response_model=ConsultationResponse)
def get_consultation(
    consultation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = (
        db.query(Consultation)
        .filter(
            Consultation.id == consultation_id,
            Consultation.user_id == current_user.id,
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Consultation not found")

    return consultation_to_response(item)


@app.get("/api/consultations/{consultation_id}/download/{file_type}")
def patient_download_final_file(
    consultation_id: int,
    file_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = (
        db.query(Consultation)
        .filter(
            Consultation.id == consultation_id,
            Consultation.user_id == current_user.id,
        )
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Consultation not found")

    if item.status != "doctor_approved":
        raise HTTPException(
            status_code=403,
            detail="Doctor approval required before download",
        )

    if file_type == "pdf":
        path = item.final_pdf_path
        media_type = "application/pdf"
    elif file_type == "docx":
        path = item.final_docx_path
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status_code=400, detail="file_type must be pdf or docx")

    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path,
        media_type=media_type,
        filename=os.path.basename(path),
    )


@app.get("/api/doctor/consultations", response_model=List[ConsultationResponse])
def doctor_get_consultations(
    x_doctor_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_doctor_key(x_doctor_key)

    items = db.query(Consultation).order_by(Consultation.id.desc()).all()

    return [consultation_to_response(item) for item in items]


@app.get("/api/doctor/consultations/{consultation_id}", response_model=ConsultationResponse)
def doctor_get_single_consultation(
    consultation_id: int,
    x_doctor_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_doctor_key(x_doctor_key)

    item = db.query(Consultation).filter(Consultation.id == consultation_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Consultation not found")

    return consultation_to_response(item)


@app.get("/api/doctor/consultations/{consultation_id}/download-draft/{file_type}")
def doctor_download_draft_file(
    consultation_id: int,
    file_type: str,
    x_doctor_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_doctor_key(x_doctor_key)

    item = db.query(Consultation).filter(Consultation.id == consultation_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Consultation not found")

    if file_type == "pdf":
        path = item.pending_pdf_path
        media_type = "application/pdf"
    elif file_type == "docx":
        path = item.pending_docx_path
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status_code=400, detail="file_type must be pdf or docx")

    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Draft file not found")

    return FileResponse(
        path,
        media_type=media_type,
        filename=os.path.basename(path),
    )


@app.get("/api/doctor/consultations/{consultation_id}/download-final/{file_type}")
def doctor_download_final_file(
    consultation_id: int,
    file_type: str,
    x_doctor_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_doctor_key(x_doctor_key)

    item = db.query(Consultation).filter(Consultation.id == consultation_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Consultation not found")

    if file_type == "pdf":
        path = item.final_pdf_path
        media_type = "application/pdf"
    elif file_type == "docx":
        path = item.final_docx_path
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status_code=400, detail="file_type must be pdf or docx")

    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Final file not found")

    return FileResponse(
        path,
        media_type=media_type,
        filename=os.path.basename(path),
    )


@app.post("/api/doctor/consultations/{consultation_id}/approve", response_model=ConsultationResponse)
def doctor_approve_consultation(
    consultation_id: int,
    payload: DoctorApproveRequest,
    x_doctor_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_doctor_key(x_doctor_key)

    item = db.query(Consultation).filter(Consultation.id == consultation_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Consultation not found")

    final_text = payload.final_prescription_text or item.prescription_text

    if not final_text:
        raise HTTPException(status_code=400, detail="Prescription content not generated yet")

    item.doctor_name = payload.doctor_name
    item.doctor_registration = payload.doctor_registration
    item.doctor_notes = payload.doctor_notes
    item.prescription_text = final_text

    final_pdf = create_pdf(
        consultation_id=item.id,
        patient_name=item.name,
        prescription_text=final_text,
        status="Doctor_Approved",
        doctor_name=payload.doctor_name,
        doctor_registration=payload.doctor_registration,
        doctor_notes=payload.doctor_notes,
    )

    final_docx = create_docx(
        consultation_id=item.id,
        patient_name=item.name,
        prescription_text=final_text,
        status="Doctor_Approved",
        doctor_name=payload.doctor_name,
        doctor_registration=payload.doctor_registration,
        doctor_notes=payload.doctor_notes,
    )

    item.final_pdf_path = final_pdf
    item.final_docx_path = final_docx

    item.status = "doctor_approved"
    item.doctor_decision = "approved_ai_or_edited_draft"
    item.rejection_reason = None

    email_success, email_error = send_prescription_email(
        to_email=item.email,
        patient_name=item.name,
        pdf_path=final_pdf,
        consultation_id=item.id,
    )

    item.email_sent = "yes" if email_success else "no"
    item.email_error = email_error

    db.commit()
    db.refresh(item)

    return consultation_to_response(item)


@app.post("/api/doctor/consultations/{consultation_id}/reject", response_model=ConsultationResponse)
def doctor_reject_and_approve_manual_prescription(
    consultation_id: int,
    payload: DoctorRejectRequest,
    x_doctor_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    require_doctor_key(x_doctor_key)

    item = db.query(Consultation).filter(Consultation.id == consultation_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Consultation not found")

    manual_prescription_text = payload.new_prescription_text.strip()

    if not manual_prescription_text:
        raise HTTPException(
            status_code=400,
            detail="New manual prescription text is required when rejecting AI draft",
        )

    item.doctor_name = payload.doctor_name
    item.doctor_registration = payload.doctor_registration
    item.doctor_notes = payload.doctor_notes or payload.rejection_reason

    item.rejection_reason = payload.rejection_reason
    item.prescription_text = manual_prescription_text

    final_pdf = create_pdf(
        consultation_id=item.id,
        patient_name=item.name,
        prescription_text=manual_prescription_text,
        status="Doctor_Approved",
        doctor_name=payload.doctor_name,
        doctor_registration=payload.doctor_registration,
        doctor_notes=payload.doctor_notes or payload.rejection_reason,
    )

    final_docx = create_docx(
        consultation_id=item.id,
        patient_name=item.name,
        prescription_text=manual_prescription_text,
        status="Doctor_Approved",
        doctor_name=payload.doctor_name,
        doctor_registration=payload.doctor_registration,
        doctor_notes=payload.doctor_notes or payload.rejection_reason,
    )

    item.final_pdf_path = final_pdf
    item.final_docx_path = final_docx

    item.status = "doctor_approved"
    item.doctor_decision = "ai_draft_rejected_manual_prescription_approved"

    email_success, email_error = send_prescription_email(
        to_email=item.email,
        patient_name=item.name,
        pdf_path=final_pdf,
        consultation_id=item.id,
    )

    item.email_sent = "yes" if email_success else "no"
    item.email_error = email_error

    db.commit()
    db.refresh(item)

    return consultation_to_response(item)