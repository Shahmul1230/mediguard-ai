# MediGuard AI

MediGuard AI is a full-stack AI-assisted medical consultation and prescription review platform. It allows patients to submit symptoms, receive AI-generated consultation drafts, and lets a registered doctor review, approve, and generate final prescription files. Approved prescriptions can be downloaded as PDF/DOCX and delivered to the patient by email.

> **Important Disclaimer:**
> MediGuard AI is a prototype/demo system for AI-assisted clinical workflow automation. It is not a replacement for a licensed medical professional. All AI-generated prescriptions must be reviewed and approved by a registered doctor before use.

---

## Live Deployment

* **Frontend:** `https://mediguard-ai-mu.vercel.app`

---

## Project Overview

MediGuard AI simulates a real-world digital healthcare workflow:

1. A patient registers or logs in.
2. The patient submits symptoms, duration, medical background, allergies, vitals, and additional information.
3. The AI generates follow-up questions and a structured clinical review.
4. A deeper AI analysis is generated using the full patient context.
5. An AI prescription draft is created for doctor review.
6. A doctor reviews the case, adds doctor information and notes, and approves the prescription.
7. Final PDF and DOCX prescriptions are generated.
8. The approved prescription is emailed to the patient.
9. Patients can view prescription history and download final files.

---

## Key Features

### Patient Side

* Patient registration and login
* New consultation submission
* Symptom, duration, vitals, allergy, existing disease, and current medicine input
* Prescription history
* Final approved prescription download
* Email delivery status tracking

### Doctor Side

* Doctor login using a secure doctor secret key
* Consultation review panel
* AI-generated clinical draft review
* Doctor name, registration number, and notes entry
* Final prescription approval
* PDF and DOCX generation after approval

### AI Workflow

MediGuard AI uses multiple AI-driven stages:

* **Agent 1:** Generates follow-up questions and initial clinical review
* **Agent 2:** Performs deeper clinical analysis
* **Agent 3:** Generates a structured prescription draft for doctor review

The AI considers:

* Age
* Sex
* Blood group
* Symptoms
* Duration
* Temperature
* Blood pressure
* Oxygen level
* Existing disease
* Current medicine
* Allergies
* Additional information
* Follow-up answers
* Bangladesh healthcare context

### Prescription Output

* AI prescription draft
* Doctor-approved final prescription
* PDF prescription file
* DOCX prescription file
* Email attachment delivery

### Email System

* SMTP-based email delivery
* Gmail App Password support
* Prescription PDF sent as email attachment
* Email status displayed in patient panel

---

## Tech Stack

### Frontend

* React
* Vite
* JavaScript
* CSS
* Vercel deployment

### Backend

* FastAPI
* Python
* SQLAlchemy
* SQLite
* Pydantic Settings
* Groq API
* ReportLab for PDF generation
* python-docx for DOCX generation
* SMTP email service
* Uvicorn
* systemd service on VPS
* Nginx reverse proxy

### Deployment

* Frontend deployed on Vercel
* Backend deployed on Hostinger VPS
* Nginx reverse proxy
* Custom subdomain
* SSL with Certbot
* Gmail SMTP for email delivery

---

## Folder Structure

```text
mediguard-ai/
│
├── backend/
│   ├── app/
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
│   ├── generated_reports/
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── public/
│   │   └── favicon.svg
│   │
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── style.css
│   │
│   ├── index.html
│   ├── package.json
│   └── .env
│
├── .gitignore
└── README.md
```

---

## Environment Variables

Secrets are not committed to GitHub. Create a `.env` file locally and on the VPS.

### Backend `.env`

Create this file:

```text
backend/.env
```

Example:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

DOCTOR_SECRET_KEY=your_secure_doctor_secret
APP_NAME=MediGuard AI
DATABASE_URL=sqlite:///./mediguard.db

EMAIL_ENABLED=true
EMAIL_PROVIDER=smtp

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password_without_space
SMTP_FROM_EMAIL=your_email@gmail.com
SMTP_FROM_NAME=MediGuard AI
```

### Frontend `.env`

Create this file:

```text
frontend/.env
```

Example:

```env
VITE_API_BASE=https://mediguard-api.pixelstack.cloud
```

For local development:

```env
VITE_API_BASE=http://127.0.0.1:8000
```

---

## Security Notes

* Never commit `.env` files.
* Never commit API keys, Gmail passwords, SMTP passwords, or doctor secret keys.
* Use Gmail App Password instead of your normal Gmail password.
* Rotate API keys immediately if they are accidentally exposed.
* Use a strong `DOCTOR_SECRET_KEY` in production.
* Keep backend access behind HTTPS.
* Use environment variables for all sensitive configuration.

---

## Local Backend Setup

Go to the backend folder:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment.

On Windows:

```bash
venv\Scripts\activate
```

On Linux/macOS:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env`:

```bash
cp .env.example .env
```

Or manually create `backend/.env` using the example above.

Run the backend:

```bash
uvicorn app.main:app --reload
```

Backend will run at:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

---

## Local Frontend Setup

Go to the frontend folder:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create `.env`:

```env
VITE_API_BASE=http://127.0.0.1:8000
```

Run the frontend:

```bash
npm run dev
```

Frontend will run at:

```text
http://localhost:5173
```

---

## Backend Deployment on Hostinger VPS

The backend is deployed as an isolated FastAPI service on a Hostinger VPS.

### Safe Deployment Strategy

To avoid affecting other running VPS projects:

* Use a separate folder: `/srv/mediguard-ai`
* Use a separate Python virtual environment
* Use a separate internal port: `8011`
* Use a separate systemd service: `mediguard-backend`
* Use a separate Nginx config file
* Do not edit existing project folders
* Do not edit existing Nginx site configs

### VPS Setup Commands

Clone the project:

```bash
mkdir -p /srv/mediguard-ai
cd /srv/mediguard-ai
git clone https://github.com/your-username/mediguard-ai.git .
```

Install backend dependencies:

```bash
cd /srv/mediguard-ai/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m compileall app
mkdir -p generated_reports
```

Create VPS `.env`:

```bash
nano /srv/mediguard-ai/backend/.env
```

Run backend manually for testing:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8011
```

Test backend internally:

```bash
curl http://127.0.0.1:8011/
```

Expected response:

```json
{
  "message": "MediGuard AI backend is running",
  "docs": "/docs"
}
```

---

## systemd Service

Create service file:

```bash
nano /etc/systemd/system/mediguard-backend.service
```

Paste:

```ini
[Unit]
Description=MediGuard AI FastAPI Backend
After=network.target

[Service]
User=root
WorkingDirectory=/srv/mediguard-ai/backend
Environment="PATH=/srv/mediguard-ai/backend/venv/bin"
ExecStart=/srv/mediguard-ai/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8011
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable mediguard-backend
systemctl start mediguard-backend
systemctl status mediguard-backend --no-pager
```

Restart after code updates:

```bash
systemctl restart mediguard-backend
```

View logs:

```bash
journalctl -u mediguard-backend -f
```

---

## Nginx Reverse Proxy

Create a new Nginx config:

```bash
nano /etc/nginx/sites-available/mediguard-api.pixelstack.cloud
```

Example config:

```nginx
server {
    listen 80;
    server_name mediguard-api.pixelstack.cloud;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8011;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
}
```

Enable site:

```bash
ln -s /etc/nginx/sites-available/mediguard-api.pixelstack.cloud /etc/nginx/sites-enabled/mediguard-api.pixelstack.cloud
nginx -t
systemctl reload nginx
```

Add SSL:

```bash
certbot --nginx -d mediguard-api.pixelstack.cloud
nginx -t
systemctl reload nginx
```

Test public backend:

```bash
curl https://mediguard-api.pixelstack.cloud/
```

---

## Frontend Deployment on Vercel

1. Push code to GitHub.
2. Import the repository into Vercel.
3. Add environment variable:

```env
VITE_API_BASE=https://mediguard-api.pixelstack.cloud
```

4. Redeploy the frontend.

---

## Updating Production

After changing backend code:

```bash
cd /srv/mediguard-ai
git pull

cd /srv/mediguard-ai/backend
source venv/bin/activate
python -m compileall app

systemctl restart mediguard-backend
systemctl status mediguard-backend --no-pager
```

After changing frontend code:

```bash
git add .
git commit -m "Update frontend"
git push
```

Vercel will automatically redeploy.

---

## Roadmap

Planned improvements:

* Doctor editable AI prescription before approval
* Better role-based authentication
* PostgreSQL production database
* Cloud file storage for generated reports
* Patient email verification
* Admin dashboard
* Multi-doctor support
* Prescription version history
* Better audit logs
* Improved medical safety guardrails
* UI improvements for mobile devices

---

## License

This project is created for educational, portfolio, and prototype purposes.

---

## Author

Developed by **Shahmul Islam**.

MediGuard AI demonstrates a complete AI-assisted healthcare workflow using FastAPI, React, Groq AI, PDF/DOCX generation, SMTP email delivery, and VPS deployment.
