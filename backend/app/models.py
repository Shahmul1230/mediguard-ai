from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    auth_token = Column(String, unique=True, index=True, nullable=True)

    consultations = relationship("Consultation", back_populates="user")


class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="consultations")

    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    sex = Column(String, nullable=False)
    blood_group = Column(String, nullable=False)

    symptoms = Column(Text, nullable=False)
    duration = Column(String, nullable=False)

    temperature = Column(String, nullable=True)
    blood_pressure = Column(String, nullable=True)
    oxygen_level = Column(String, nullable=True)
    existing_disease = Column(Text, nullable=True)
    current_medicine = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    additional_info = Column(Text, nullable=True)

    emergency_detected = Column(String, default="no")
    status = Column(String, default="intake_submitted")

    follow_up_questions_json = Column(Text, nullable=True)
    follow_up_answers_json = Column(Text, nullable=True)

    agent1_review_json = Column(Text, nullable=True)
    agent2_review_json = Column(Text, nullable=True)
    agent3_prescription_json = Column(Text, nullable=True)

    prescription_text = Column(Text, nullable=True)

    pending_pdf_path = Column(String, nullable=True)
    pending_docx_path = Column(String, nullable=True)

    final_pdf_path = Column(String, nullable=True)
    final_docx_path = Column(String, nullable=True)

    doctor_name = Column(String, nullable=True)
    doctor_registration = Column(String, nullable=True)
    doctor_notes = Column(Text, nullable=True)

    doctor_decision = Column(String, default=None)
    rejection_reason = Column(Text, nullable=True)

    email_sent = Column(String, default="no")
    email_error = Column(Text, nullable=True)