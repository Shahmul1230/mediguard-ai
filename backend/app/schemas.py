from typing import Any, List, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserOut(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class PatientIntakeRequest(BaseModel):
    name: str = Field(..., min_length=1)

    age: int = Field(..., gt=0)
    sex: str = Field(..., min_length=1)
    blood_group: str = Field(..., min_length=1)

    symptoms: str = Field(..., min_length=1)
    duration: str = Field(..., min_length=1)

    temperature: Optional[str] = None
    blood_pressure: Optional[str] = None
    oxygen_level: Optional[str] = None
    existing_disease: Optional[str] = None
    current_medicine: Optional[str] = None
    allergies: Optional[str] = None
    additional_info: Optional[str] = None


class FollowUpAnswer(BaseModel):
    question: str
    answer: str


class FollowUpSubmitRequest(BaseModel):
    answers: List[FollowUpAnswer] = []


class DoctorApproveRequest(BaseModel):
    doctor_name: str = Field(..., min_length=1)
    doctor_registration: str = Field(..., min_length=1)
    doctor_notes: Optional[str] = None
    final_prescription_text: Optional[str] = None


class DoctorRejectRequest(BaseModel):
    doctor_name: str = Field(..., min_length=1)
    doctor_registration: str = Field(..., min_length=1)
    doctor_notes: Optional[str] = None

    rejection_reason: str = Field(..., min_length=1)
    new_prescription_text: str = Field(..., min_length=1)


class ConsultationResponse(BaseModel):
    id: int
    user_id: int

    name: str
    email: str
    age: int
    sex: str
    blood_group: str

    symptoms: str
    duration: str

    status: str
    emergency_detected: str

    follow_up_questions: Optional[Any] = None
    follow_up_answers: Optional[Any] = None

    agent1_review: Optional[Any] = None
    agent2_review: Optional[Any] = None
    agent3_prescription: Optional[Any] = None

    prescription_text: Optional[str] = None

    doctor_name: Optional[str] = None
    doctor_registration: Optional[str] = None
    doctor_notes: Optional[str] = None

    doctor_decision: Optional[str] = None
    rejection_reason: Optional[str] = None

    email_sent: Optional[str] = None
    email_error: Optional[str] = None

    can_patient_download: bool = False

    class Config:
        from_attributes = True