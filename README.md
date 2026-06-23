# MediGuard AI

**MediGuard AI** is a full-stack AI-powered medical consultation and prescription workflow system. The platform allows patients to create an account, submit symptoms, answer AI-generated follow-up questions, track consultation history, and download doctor-approved prescriptions. Doctors can review AI-generated prescription drafts, approve them, edit and approve them, or reject the AI draft and create a manual prescription.

The project demonstrates a real-world healthcare automation workflow using **React**, **FastAPI**, **SQLite**, **Groq AI**, **PDF/DOCX generation**, and **email delivery**.

---

## Project Overview

MediGuard AI is designed as a smart medical consultation workflow where AI assists in preparing a structured prescription draft, but the final prescription becomes available to the patient only after doctor approval.

The system includes:

* Patient registration and login
* Patient consultation history
* AI-generated follow-up questions
* Multi-agent AI clinical analysis
* AI-generated prescription draft
* Doctor review dashboard
* Doctor approval, edit, or rejection workflow
* Manual prescription creation by doctor
* Final PDF/DOCX prescription generation
* Email delivery of approved prescription
* Download option for approved prescription

---

## Key Features

### Patient Features

* Register and login with email and password
* Submit symptoms and basic medical information
* Answer or skip AI-generated follow-up questions
* View consultation status
* Access previous consultation history from sidebar
* Download PDF/DOCX only after doctor approval
* Receive doctor-approved prescription by email

### Doctor Features

* Secure doctor dashboard using secret key
* View all patient consultations
* Review AI-generated prescription drafts
* Download draft PDF/DOCX
* Approve AI draft directly
* Edit AI draft and approve
* Reject AI draft and create manual prescription
* Generate final doctor-approved PDF/DOCX
* Trigger email delivery to patient

### AI Workflow

MediGuard AI uses a multi-agent workflow:

1. **Agent 1 — Follow-up Question Generator**

   * Reviews patient symptoms
   * Generates important follow-up questions
   * Detects emergency signals

2. **Agent 1 — Initial Clinical Review**

   * Structures symptoms
   * Provides initial clinical reasoning
   * Identifies urgency level

3. **Agent 2 — Deep Clinical Analysis**

   * Performs deeper symptom analysis
   * Suggests possible causes and investigations
   * Provides clinical reasoning support

4. **Agent 3 — Prescription Draft Generator**

   * Creates structured AI prescription draft
   * Includes complaints, diagnosis, medicine section, advice, investigations, and follow-up
   * Final draft is sent to doctor review before patient access

---

## Doctor Review Workflow

The prescription is not directly available to the patient after AI generation. It follows a doctor review workflow:

```text
Patient submits symptoms
        ↓
AI generates follow-up questions
        ↓
Patient submits answers
        ↓
AI agents analyze case
        ↓
AI prescription draft generated
        ↓
Doctor review pending
        ↓
Doctor chooses one action:
    1. Approve AI Draft
    2. Edit & Approve
    3. Reject AI Draft & Create Manual Prescription
        ↓
Final prescription generated
        ↓
Patient can download PDF/DOCX
        ↓
Prescription sent by email
```

---

## Tech Stack

### Frontend

* React
* Vite
* JavaScript
* CSS

### Backend

* FastAPI
* Python
* SQLAlchemy
* SQLite
* Pydantic
* Groq API

### Document Generation

* ReportLab for PDF generation
* python-docx for DOCX generation

### Email

* SMTP email delivery
* Gmail App Password support

---

## Project Structure

```text
mediguard-ai/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── agents.py
│   │   ├── auth_service.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── email_service.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── report_service.py
│   │   └── schemas.py
│   │
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       └── style.css
│
├── .gitignore
└── README.md
```

---

## Installation and Setup

### Prerequisites

Make sure the following are installed:

* Python 3.10+
* Node.js 18+
* Git
* Groq API key

---

## Backend Setup

Go to the backend folder:

```bash
cd backend
```

Create and activate virtual environment:

```bash
python -m venv venv
```

For Windows PowerShell:

```bash
.\venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env` file inside the `backend` folder:

```bash
copy .env.example .env
```

Then update `.env` with your own values:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
DOCTOR_SECRET_KEY=123456
APP_NAME=MediGuard AI
DATABASE_URL=sqlite:///./mediguard.db

EMAIL_ENABLED=false

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password_without_space
SMTP_FROM_EMAIL=your_email@gmail.com
SMTP_FROM_NAME=MediGuard AI
```

Run the backend server:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend will run at:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Frontend Setup

Go to the frontend folder:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Run frontend:

```bash
npm run dev
```

Frontend will run at:

```text
http://localhost:5173
```

---

## Environment Variables

### Backend `.env`

| Variable            | Description                     |
| ------------------- | ------------------------------- |
| `GROQ_API_KEY`      | Groq API key for AI agents      |
| `GROQ_MODEL`        | Groq model name                 |
| `DOCTOR_SECRET_KEY` | Secret key for doctor dashboard |
| `DATABASE_URL`      | SQLite database URL             |
| `EMAIL_ENABLED`     | Enable or disable email sending |
| `SMTP_HOST`         | SMTP server host                |
| `SMTP_PORT`         | SMTP server port                |
| `SMTP_USERNAME`     | SMTP email address              |
| `SMTP_PASSWORD`     | SMTP app password               |
| `SMTP_FROM_EMAIL`   | Sender email                    |
| `SMTP_FROM_NAME`    | Sender name                     |

---

## Email Setup

For Gmail SMTP, normal Gmail password will not work. You need a Gmail App Password.

Recommended setup:

```env
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password_without_space
SMTP_FROM_EMAIL=your_email@gmail.com
SMTP_FROM_NAME=MediGuard AI
```

After changing `.env`, restart the backend server.

---

## Main API Endpoints

### Authentication

| Method | Endpoint             | Description                   |
| ------ | -------------------- | ----------------------------- |
| `POST` | `/api/auth/register` | Register patient account      |
| `POST` | `/api/auth/login`    | Login patient                 |
| `GET`  | `/api/patient/me`    | Get logged-in patient profile |

### Patient

| Method | Endpoint                                   | Description                      |
| ------ | ------------------------------------------ | -------------------------------- |
| `GET`  | `/api/patient/consultations`               | Get patient consultation history |
| `GET`  | `/api/patient/consultations/{id}`          | Get single consultation          |
| `POST` | `/api/consultations`                       | Create new consultation          |
| `POST` | `/api/consultations/{id}/submit-followups` | Submit follow-up answers         |
| `GET`  | `/api/consultations/{id}/download/pdf`     | Download approved PDF            |
| `GET`  | `/api/consultations/{id}/download/docx`    | Download approved DOCX           |

### Doctor

| Method | Endpoint                                             | Description                                     |
| ------ | ---------------------------------------------------- | ----------------------------------------------- |
| `GET`  | `/api/doctor/consultations`                          | Get all consultations                           |
| `GET`  | `/api/doctor/consultations/{id}`                     | Get consultation details                        |
| `GET`  | `/api/doctor/consultations/{id}/download-draft/pdf`  | Download draft PDF                              |
| `GET`  | `/api/doctor/consultations/{id}/download-draft/docx` | Download draft DOCX                             |
| `GET`  | `/api/doctor/consultations/{id}/download-final/pdf`  | Download final PDF                              |
| `GET`  | `/api/doctor/consultations/{id}/download-final/docx` | Download final DOCX                             |
| `POST` | `/api/doctor/consultations/{id}/approve`             | Approve AI draft or edited draft                |
| `POST` | `/api/doctor/consultations/{id}/reject`              | Reject AI draft and approve manual prescription |

---

## Testing Workflow

### Patient Test

1. Open frontend
2. Register a patient account
3. Login with email and password
4. Create a new consultation
5. Submit symptoms and medical details
6. Answer or skip follow-up questions
7. Submit to AI agents
8. Status becomes `Doctor Review Pending`
9. Patient history sidebar shows the consultation

### Doctor Test

1. Go to Doctor tab
2. Enter doctor secret key:

```text
123456
```

3. Load consultations
4. Select patient case
5. Choose one of the three actions:

   * Approve AI Draft
   * Edit & Approve
   * Reject AI Draft and Create Manual Prescription
6. Final prescription is generated
7. Email process is triggered
8. Patient can download PDF/DOCX from history

---

## Prescription Output

The generated prescription includes:

* Prescription ID
* Date
* Patient information
* Chief complaints
* Provisional diagnosis
* Rx / medicine section
* Advice
* Investigations
* Follow-up
* Doctor name
* Doctor registration number
* Doctor notes
* Doctor signature section

The final PDF and DOCX are only generated after doctor approval.

---

## Security Notes

* `.env` file is ignored from Git and must not be uploaded publicly
* API keys and SMTP passwords should be stored only in environment variables
* Patient password is hashed before storage
* Patient consultation history is protected by authentication token
* Doctor dashboard is protected by doctor secret key
* Generated prescriptions and database files are ignored from Git

---

## Current Limitations

This project is built as an MVP/demo system. Some production-level improvements are recommended before real-world use:

* Replace SQLite with PostgreSQL
* Store PDF/DOCX files in cloud storage
* Add proper doctor account authentication
* Add role-based access control
* Add audit logs
* Add token expiry and refresh tokens
* Add email verification
* Add deployment-ready database migrations
* Add stronger validation and monitoring

---

## Future Improvements

* Doctor registration and login system
* Admin dashboard
* Appointment scheduling
* Prescription search and filtering
* Cloud file storage
* PostgreSQL integration
* Real-time notification system
* Improved analytics dashboard
* Patient profile and medical history
* Multi-doctor support
* Deployment with Docker

---

## Disclaimer

MediGuard AI is a software project and demonstration system. It is not intended to replace professional medical judgment. AI-generated content should always be reviewed and approved by a qualified medical professional before being used as a final prescription.

---

## Author

Developed by **Shahmul**

GitHub: [Shahmul1230](https://github.com/Shahmul1230)

---

## License

This project is currently provided for educational and portfolio purposes.
