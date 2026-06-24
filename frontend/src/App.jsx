import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

function App() {
  const [mainTab, setMainTab] = useState("patient");
  const [token, setToken] = useState(localStorage.getItem("mg_token") || "");
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("mg_user");
    return saved ? JSON.parse(saved) : null;
  });

  function saveAuth(data) {
    localStorage.setItem("mg_token", data.token);
    localStorage.setItem("mg_user", JSON.stringify(data.user));
    setToken(data.token);
    setUser(data.user);
  }

  function logout() {
    localStorage.removeItem("mg_token");
    localStorage.removeItem("mg_user");
    setToken("");
    setUser(null);
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>MediGuard AI</h1>
          <p>AI prescription draft, doctor review, approval, history, and email delivery</p>
        </div>

        {user && mainTab === "patient" && (
          <div className="user-chip">
            <span>{user.name}</span>
            <button onClick={logout}>Logout</button>
          </div>
        )}
      </header>

      <div className="tabs">
        <button
          className={mainTab === "patient" ? "active" : ""}
          onClick={() => setMainTab("patient")}
        >
          Patient
        </button>

        <button
          className={mainTab === "doctor" ? "active" : ""}
          onClick={() => setMainTab("doctor")}
        >
          Doctor
        </button>
      </div>

      {mainTab === "patient" ? (
        token && user ? (
          <PatientDashboard token={token} user={user} />
        ) : (
          <AuthPanel onAuth={saveAuth} />
        )
      ) : (
        <DoctorPanel />
      )}
    </div>
  );
}

function AuthPanel({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function updateField(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function submitAuth(e) {
    e.preventDefault();
    setError("");

    if (mode === "register" && !form.name.trim()) {
      setError("Name is required");
      return;
    }

    if (!form.email.trim()) {
      setError("Email is required");
      return;
    }

    if (!form.password.trim()) {
      setError("Password is required");
      return;
    }

    setLoading(true);

    try {
      const endpoint =
        mode === "register"
          ? `${API_BASE}/api/auth/register`
          : `${API_BASE}/api/auth/login`;

      const payload =
        mode === "register"
          ? form
          : {
              email: form.email,
              password: form.password,
            };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Authentication failed");
      }

      onAuth(data);
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <h2>{mode === "login" ? "Patient Login" : "Create Patient Account"}</h2>
        <p className="muted">
          Login to submit symptoms, track consultation history, and download approved prescriptions.
        </p>

        <div className="auth-tabs">
          <button
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            Login
          </button>

          <button
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>

        {error && <div className="error">{error}</div>}
        {loading && <div className="loading">Processing...</div>}

        <form onSubmit={submitAuth} className="auth-form">
          {mode === "register" && (
            <Input
              label="Full Name"
              value={form.name}
              onChange={(v) => updateField("name", v)}
            />
          )}

          <Input
            label="Email"
            type="email"
            value={form.email}
            onChange={(v) => updateField("email", v)}
            placeholder="patient@example.com"
          />

          <Input
            label="Password"
            type="password"
            value={form.password}
            onChange={(v) => updateField("password", v)}
            placeholder="Minimum 6 characters"
          />

          <button className="primary full-width" type="submit" disabled={loading}>
            {mode === "login" ? "Login" : "Create Account"}
          </button>
        </form>
      </section>
    </main>
  );
}

function PatientDashboard({ token, user }) {
  const [history, setHistory] = useState([]);
  const [selected, setSelected] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [showNewForm, setShowNewForm] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    name: user?.name || "",
    age: "",
    sex: "",
    blood_group: "",
    symptoms: "",
    duration: "",
    temperature: "",
    blood_pressure: "",
    oxygen_level: "",
    existing_disease: "",
    current_medicine: "",
    allergies: "",
    additional_info: "",
  });

  useEffect(() => {
    loadHistory();
  }, []);

  function authHeaders(extra = {}) {
    return {
      Authorization: `Bearer ${token}`,
      ...extra,
    };
  }

  async function loadHistory() {
    setError("");

    try {
      const res = await fetch(`${API_BASE}/api/patient/consultations`, {
        headers: authHeaders(),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to load history");
      }

      setHistory(data);
    } catch (err) {
      setError(err.message || "Failed to load history");
    }
  }

  async function selectHistoryItem(id) {
    setError("");
    setShowNewForm(false);

    try {
      const res = await fetch(`${API_BASE}/api/patient/consultations/${id}`, {
        headers: authHeaders(),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to load consultation");
      }

      setSelected(data);

      const questions = data.follow_up_questions || [];
      setAnswers(
        questions.map((q) => ({
          question: q.question,
          answer: "Skipped",
        }))
      );
    } catch (err) {
      setError(err.message || "Failed to load consultation");
    }
  }

  function updateField(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  function validatePatientForm() {
    if (!form.name.trim()) return "Name is required";
    if (!form.age) return "Age is required";
    if (!form.sex.trim()) return "Sex is required";
    if (!form.blood_group.trim()) return "Blood group is required";
    if (!form.symptoms.trim()) return "Symptoms are required";
    if (!form.duration.trim()) return "Symptom duration is required";
    return "";
  }

  async function startConsultation(e) {
    e.preventDefault();

    const validationError = validatePatientForm();

    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const payload = {
        ...form,
        age: Number(form.age),
      };

      const res = await fetch(`${API_BASE}/api/consultations`, {
        method: "POST",
        headers: authHeaders({
          "Content-Type": "application/json",
        }),
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to start consultation");
      }

      setSelected(data);
      setShowNewForm(false);

      const questions = data.follow_up_questions || [];
      setAnswers(
        questions.map((q) => ({
          question: q.question,
          answer: "Skipped",
        }))
      );

      await loadHistory();
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function updateAnswer(index, value) {
    setAnswers((prev) => {
      const copy = [...prev];
      copy[index] = {
        ...copy[index],
        answer: value || "Skipped",
      };
      return copy;
    });
  }

  async function submitFollowups() {
    if (!selected) return;

    setLoading(true);
    setError("");

    try {
      const res = await fetch(
        `${API_BASE}/api/consultations/${selected.id}/submit-followups`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({ answers }),
        }
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to submit follow-up answers");
      }

      setSelected(data);
      await loadHistory();
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function downloadPatientFile(fileType) {
    if (!selected) return;

    try {
      const res = await fetch(
        `${API_BASE}/api/consultations/${selected.id}/download/${fileType}`,
        {
          headers: authHeaders(),
        }
      );

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Could not download ${fileType}`);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = `prescription_${selected.id}.${fileType}`;

      document.body.appendChild(a);
      a.click();
      a.remove();

      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message || `Could not download ${fileType}`);
    }
  }

  return (
    <main className="patient-shell">
      <aside className="history-sidebar">
        <div className="history-head">
          <h2>Prescription History</h2>
          <button
            onClick={() => {
              setShowNewForm(true);
              setSelected(null);
            }}
          >
            + New
          </button>
        </div>

        {history.length === 0 ? (
          <p className="muted">No consultation yet.</p>
        ) : (
          <div className="history-list">
            {history.map((item) => (
              <button
                key={item.id}
                className={`history-item ${selected?.id === item.id ? "selected" : ""}`}
                onClick={() => selectHistoryItem(item.id)}
              >
                <div className="history-row">
                  <strong>RX-{String(item.id).padStart(4, "0")}</strong>
                  <StatusBadge status={item.status} />
                </div>

                <span>{item.symptoms}</span>

                {item.can_patient_download && (
                  <small>PDF/DOCX ready</small>
                )}
              </button>
            ))}
          </div>
        )}
      </aside>

      <section className="patient-main">
        {error && <div className="error">{error}</div>}
        {loading && <div className="loading">Processing...</div>}

        {showNewForm ? (
          <section className="card">
            <h2>New Consultation</h2>
            <p className="muted">
              Submit symptoms. AI will create a draft and doctor will review it.
            </p>

            <form onSubmit={startConsultation} className="form-grid">
              <Input
                label="Patient Name *"
                value={form.name}
                onChange={(v) => updateField("name", v)}
              />

              <Input
                label="Account Email"
                value={user.email}
                onChange={() => {}}
                disabled
              />

              <Input
                label="Age *"
                type="number"
                value={form.age}
                onChange={(v) => updateField("age", v)}
              />

              <Select
                label="Sex *"
                value={form.sex}
                onChange={(v) => updateField("sex", v)}
                options={["", "Male", "Female", "Other"]}
              />

              <Select
                label="Blood Group *"
                value={form.blood_group}
                onChange={(v) => updateField("blood_group", v)}
                options={["", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"]}
              />

              <Input
                label="Symptom Duration *"
                value={form.duration}
                onChange={(v) => updateField("duration", v)}
                placeholder="Example: 1 day"
              />

              <Textarea
                label="Main Symptoms / Difficulties *"
                value={form.symptoms}
                onChange={(v) => updateField("symptoms", v)}
                placeholder="Example: stomach pain, vomiting, diarrhea"
              />

              <Input
                label="Temperature"
                value={form.temperature}
                onChange={(v) => updateField("temperature", v)}
              />

              <Input
                label="Blood Pressure"
                value={form.blood_pressure}
                onChange={(v) => updateField("blood_pressure", v)}
              />

              <Input
                label="Oxygen Level"
                value={form.oxygen_level}
                onChange={(v) => updateField("oxygen_level", v)}
              />

              <Textarea
                label="Existing Disease"
                value={form.existing_disease}
                onChange={(v) => updateField("existing_disease", v)}
              />

              <Textarea
                label="Current Medicine"
                value={form.current_medicine}
                onChange={(v) => updateField("current_medicine", v)}
              />

              <Textarea
                label="Allergies"
                value={form.allergies}
                onChange={(v) => updateField("allergies", v)}
              />

              <Textarea
                label="Additional Info"
                value={form.additional_info}
                onChange={(v) => updateField("additional_info", v)}
              />

              <button className="primary full-width" type="submit" disabled={loading}>
                Start AI Review
              </button>
            </form>
          </section>
        ) : selected ? (
          <ConsultationView
            consultation={selected}
            answers={answers}
            updateAnswer={updateAnswer}
            submitFollowups={submitFollowups}
            downloadPatientFile={downloadPatientFile}
            loading={loading}
          />
        ) : (
          <section className="card">
            <h2>Select a consultation</h2>
            <p className="muted">Choose from left history or create a new one.</p>
          </section>
        )}
      </section>
    </main>
  );
}

function ConsultationView({
  consultation,
  answers,
  updateAnswer,
  submitFollowups,
  downloadPatientFile,
  loading,
}) {
  const status = normalizeStatus(consultation.status);
  const isFollowupStage = status === "follow_up_questions_generated";
  const isApproved = status === "doctor_approved";

  return (
    <section className="card">
      <div className="consultation-top">
        <div>
          <h2>Consultation RX-{String(consultation.id).padStart(4, "0")}</h2>
          <p className="muted">
            Track your consultation status and download your approved prescription.
          </p>
        </div>

        <div className="consultation-top-right">
          <StatusBadge status={consultation.status} />

          <span
            className={`emergency-chip ${
              consultation.emergency_detected === "yes" ? "danger" : "safe"
            }`}
          >
            Emergency: {consultation.emergency_detected === "yes" ? "Yes" : "No"}
          </span>
        </div>
      </div>

      <PatientPublicStatusCard consultation={consultation} />

      <OverviewGrid consultation={consultation} />

      {isFollowupStage && (
        <div className="pretty-section">
          <h3>Additional Questions</h3>
          <p className="muted">
            Please answer these questions if you know the answer. You can also skip.
          </p>

          <div className="question-list">
            {(consultation.follow_up_questions || []).map((q, index) => (
              <div className="question-card patient-question-card" key={index}>
                <div className="question-card-top">
                  <h4>{q.question}</h4>
                  <span className={`priority-pill ${q.priority || "medium"}`}>
                    {q.priority || "medium"}
                  </span>
                </div>

                <div className="answer-area">
                  <select
                    value={answers[index]?.answer || "Skipped"}
                    onChange={(e) => updateAnswer(index, e.target.value)}
                  >
                    <option value="Skipped">I don't know / Skip</option>
                    <option value="Yes">Yes</option>
                    <option value="No">No</option>
                  </select>

                  <input
                    placeholder="Or type your answer"
                    onChange={(e) => updateAnswer(index, e.target.value)}
                  />
                </div>
              </div>
            ))}
          </div>

          <button className="primary" onClick={submitFollowups} disabled={loading}>
            Submit Answers
          </button>
        </div>
      )}

      {!isFollowupStage && !isApproved && (
        <div className="patient-waiting-card">
          <div className="waiting-icon">✓</div>

          <div>
            <h3>Thank you for sharing your health concern with us.</h3>

            <p>
              Our AI system is now analyzing your information and preparing a
              structured prescription draft. A registered doctor will review and
              verify the prescription before it becomes final.
            </p>

            <p>
              Once the doctor approves it, the prescription will be sent
              automatically to your registered email address. You will also be able
              to download the PDF and DOCX prescription from this page.
            </p>

            <strong>Estimated verification time: usually 2–10 minutes.</strong>
          </div>
        </div>
      )}

      {isApproved && (
        <div className="success-box patient-approved-box">
          <h3>Your Prescription is Approved</h3>

          <p>
            A registered doctor has approved your prescription. You can now download
            the final prescription file.
          </p>

          <p>
            Email status: <strong>{consultation.email_sent || "no"}</strong>
          </p>

          {consultation.email_error && (
            <p className="muted">Email note: {consultation.email_error}</p>
          )}

          <div className="download-actions">
            <button onClick={() => downloadPatientFile("pdf")}>
              Download PDF Prescription
            </button>

            <button onClick={() => downloadPatientFile("docx")}>
              Download DOCX Prescription
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function PatientPublicStatusCard({ consultation }) {
  const status = normalizeStatus(consultation.status);

  const steps = [
    {
      key: "submitted",
      label: "Information Submitted",
      active: true,
    },
    {
      key: "ai_processing",
      label: "AI Draft Preparation",
      active:
        status === "running_ai_agents" ||
        status === "agent1_completed" ||
        status === "agent2_completed" ||
        status === "doctor_review_pending" ||
        status === "doctor_approved",
    },
    {
      key: "doctor_review",
      label: "Doctor Review",
      active: status === "doctor_review_pending" || status === "doctor_approved",
    },
    {
      key: "approved",
      label: "Prescription Ready",
      active: status === "doctor_approved",
    },
  ];

  return (
    <div className="patient-status-card">
      <div>
        <h3>
          {status === "doctor_approved"
            ? "Prescription Ready"
            : "Processing Your Consultation"}
        </h3>

        <p>
          We have received your submitted information. Your consultation is being
          processed securely, and the final prescription will be available after
          doctor approval.
        </p>
      </div>

      <div className="patient-progress">
        {steps.map((step) => (
          <div className={`progress-step ${step.active ? "active" : ""}`} key={step.key}>
            <span>{step.active ? "✓" : ""}</span>
            <p>{step.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function DoctorPanel() {
  const [doctorKey, setDoctorKey] = useState("");
  const [consultations, setConsultations] = useState([]);
  const [selected, setSelected] = useState(null);

  const [doctorName, setDoctorName] = useState("");
  const [doctorReg, setDoctorReg] = useState("");
  const [doctorNotes, setDoctorNotes] = useState("");

  const [editedText, setEditedText] = useState("");
  const [manualText, setManualText] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");

  const [showEditBox, setShowEditBox] = useState(false);
  const [showRejectBox, setShowRejectBox] = useState(false);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadConsultations() {
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/doctor/consultations`, {
        headers: {
          "X-Doctor-Key": doctorKey,
        },
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to load consultations");
      }

      setConsultations(data);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function selectConsultation(id) {
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/doctor/consultations/${id}`, {
        headers: {
          "X-Doctor-Key": doctorKey,
        },
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to load consultation");
      }

      setSelected(data);

      const draftText = data.prescription_text || "";

      setEditedText(draftText);
      setManualText(draftText);

      setDoctorName(data.doctor_name || "");
      setDoctorReg(data.doctor_registration || "");
      setDoctorNotes(data.doctor_notes || "");
      setRejectionReason(data.rejection_reason || "");

      setShowEditBox(false);
      setShowRejectBox(false);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function validateDoctorInfo() {
    if (!doctorName.trim()) {
      setError("Doctor name is required");
      return false;
    }

    if (!doctorReg.trim()) {
      setError("Doctor registration number is required");
      return false;
    }

    return true;
  }

  async function approveWithText(finalPrescriptionText, successMessage) {
    if (!selected) return;

    if (!validateDoctorInfo()) return;

    if (!finalPrescriptionText.trim()) {
      setError("Prescription text is required");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const res = await fetch(
        `${API_BASE}/api/doctor/consultations/${selected.id}/approve`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Doctor-Key": doctorKey,
          },
          body: JSON.stringify({
            doctor_name: doctorName,
            doctor_registration: doctorReg,
            doctor_notes: doctorNotes,
            final_prescription_text: finalPrescriptionText,
          }),
        }
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to approve prescription");
      }

      setSelected(data);
      await loadConsultations();

      alert(successMessage);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function approveAiDraft() {
    const draftText = selected?.prescription_text || editedText;

    await approveWithText(
      draftText,
      "AI draft approved. Final PDF/DOCX generated and email process completed."
    );
  }

  async function approveEditedPrescription() {
    await approveWithText(
      editedText,
      "Edited prescription approved. Final PDF/DOCX generated and email process completed."
    );
  }

  async function rejectAndApproveManualPrescription() {
    if (!selected) return;

    if (!validateDoctorInfo()) return;

    if (!rejectionReason.trim()) {
      setError("Rejection reason is required");
      return;
    }

    if (!manualText.trim()) {
      setError("Manual prescription text is required");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const res = await fetch(
        `${API_BASE}/api/doctor/consultations/${selected.id}/reject`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Doctor-Key": doctorKey,
          },
          body: JSON.stringify({
            doctor_name: doctorName,
            doctor_registration: doctorReg,
            doctor_notes: doctorNotes,
            rejection_reason: rejectionReason,
            new_prescription_text: manualText,
          }),
        }
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(
          data.detail || "Failed to reject AI draft and approve manual prescription"
        );
      }

      setSelected(data);
      await loadConsultations();

      alert(
        "AI draft rejected. Manual prescription approved. Final PDF/DOCX generated and email process completed."
      );
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function downloadDoctorFile(fileType, mode = "draft") {
    if (!selected) return;

    try {
      const endpoint =
        mode === "final"
          ? `${API_BASE}/api/doctor/consultations/${selected.id}/download-final/${fileType}`
          : `${API_BASE}/api/doctor/consultations/${selected.id}/download-draft/${fileType}`;

      const res = await fetch(endpoint, {
        headers: {
          "X-Doctor-Key": doctorKey,
        },
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Could not download ${mode} ${fileType}`);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = `${mode}_prescription_${selected.id}.${fileType}`;

      document.body.appendChild(a);
      a.click();
      a.remove();

      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message || `Could not download ${mode} ${fileType}`);
    }
  }

  return (
    <main className="container">
      <section className="card">
        <div className="section-head">
          <div>
            <h2>Doctor Dashboard</h2>
            <p className="muted">Use doctor secret key to access consultations.</p>
          </div>
        </div>

        {error && <div className="error">{error}</div>}
        {loading && <div className="loading">Processing...</div>}

        <div className="row">
          <input
            placeholder="Doctor secret key"
            value={doctorKey}
            onChange={(e) => setDoctorKey(e.target.value)}
          />

          <button onClick={loadConsultations}>Load Consultations</button>
        </div>
      </section>

      <div className="doctor-layout">
        <section className="card">
          <h2>Consultation List</h2>

          {consultations.length === 0 && (
            <p className="muted">No consultation loaded yet.</p>
          )}

          <div className="doctor-list">
            {consultations.map((item) => (
              <button
                key={item.id}
                className={`consultation-item ${
                  selected?.id === item.id ? "selected" : ""
                }`}
                onClick={() => selectConsultation(item.id)}
              >
                <div className="doctor-list-top">
                  <strong>
                    RX-{String(item.id).padStart(4, "0")} - {item.name}
                  </strong>
                  <StatusBadge status={item.status} />
                </div>

                <span>{item.symptoms}</span>
                <small>{item.email}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="card">
          <h2>Review Panel</h2>

          {!selected && <p className="muted">Select a consultation from the left side.</p>}

          {selected && (
            <div>
              <OverviewGrid consultation={selected} />

              <div className="status-info-box">
                <p>
                  Current status: <strong>{prettyStatus(selected.status)}</strong>
                </p>

                <p>
                  Doctor decision:{" "}
                  <strong>{prettyDecision(selected.doctor_decision)}</strong>
                </p>

                <p>
                  Email sent: <strong>{selected.email_sent || "no"}</strong>
                </p>

                {selected.email_error && (
                  <p className="muted">Email note: {selected.email_error}</p>
                )}
              </div>

              {selected.agent3_prescription ? (
                <PrescriptionCard data={selected.agent3_prescription} />
              ) : selected.prescription_text ? (
                <SimplePrescriptionText text={selected.prescription_text} />
              ) : null}

              {(selected.status === "doctor_review_pending" ||
                selected.status === "doctor_approved") && (
                <div className="download-box pending-box">
                  <h3>AI Draft Files</h3>

                  <div className="download-actions">
                    <button type="button" onClick={() => downloadDoctorFile("pdf", "draft")}>
                      Download Draft PDF
                    </button>

                    <button type="button" onClick={() => downloadDoctorFile("docx", "draft")}>
                      Download Draft DOCX
                    </button>
                  </div>
                </div>
              )}

              {selected.status === "doctor_approved" && (
                <div className="download-box">
                  <h3>Final Approved Files</h3>

                  <div className="download-actions">
                    <button type="button" onClick={() => downloadDoctorFile("pdf", "final")}>
                      Download Final PDF
                    </button>

                    <button type="button" onClick={() => downloadDoctorFile("docx", "final")}>
                      Download Final DOCX
                    </button>
                  </div>
                </div>
              )}

              <div className="pretty-section">
                <h3>Doctor Information</h3>

                <div className="form-grid doctor-form-grid">
                  <Input
                    label="Doctor Name"
                    value={doctorName}
                    onChange={setDoctorName}
                  />

                  <Input
                    label="BMDC / Registration No"
                    value={doctorReg}
                    onChange={setDoctorReg}
                  />

                  <Textarea
                    label="Doctor Notes"
                    value={doctorNotes}
                    onChange={setDoctorNotes}
                  />
                </div>
              </div>

              <div className="pretty-section">
                <h3>Doctor Decision</h3>

                <div className="smart-action-grid">
                  <button
                    className="action-card approve-card"
                    onClick={approveAiDraft}
                    disabled={loading}
                  >
                    <span className="action-title">Approve AI Draft</span>
                    <span className="action-desc">
                      AI draft is correct. Generate final PDF/DOCX and email patient.
                    </span>
                  </button>

                  <button
                    className="action-card edit-card"
                    onClick={() => {
                      setShowEditBox((prev) => !prev);
                      setShowRejectBox(false);
                    }}
                    disabled={loading}
                  >
                    <span className="action-title">Edit & Approve</span>
                    <span className="action-desc">
                      Make small changes, then approve the edited prescription.
                    </span>
                  </button>

                  <button
                    className="action-card reject-card"
                    onClick={() => {
                      setShowRejectBox((prev) => !prev);
                      setShowEditBox(false);
                    }}
                    disabled={loading}
                  >
                    <span className="action-title">Reject AI Draft</span>
                    <span className="action-desc">
                      Replace AI draft with a manual prescription and approve it.
                    </span>
                  </button>
                </div>
              </div>

              {showEditBox && (
                <div className="decision-panel edit-panel">
                  <h3>Edit Prescription & Approve</h3>

                  <textarea
                    className="smart-textarea"
                    value={editedText}
                    onChange={(e) => setEditedText(e.target.value)}
                  />

                  <button
                    className="primary decision-submit"
                    onClick={approveEditedPrescription}
                    disabled={loading}
                  >
                    Approve Edited Prescription
                  </button>
                </div>
              )}

              {showRejectBox && (
                <div className="decision-panel reject-panel">
                  <h3>Reject AI Draft & Create Manual Prescription</h3>

                  <Textarea
                    label="Rejection Reason"
                    value={rejectionReason}
                    onChange={setRejectionReason}
                    placeholder="Example: AI draft missed important symptoms."
                  />

                  <label className="field">
                    <span>Manual Prescription Text</span>
                    <textarea
                      className="smart-textarea manual-prescription-area"
                      value={manualText}
                      onChange={(e) => setManualText(e.target.value)}
                    />
                  </label>

                  <button
                    className="danger-button decision-submit"
                    onClick={rejectAndApproveManualPrescription}
                    disabled={loading}
                  >
                    Approve Manual Prescription
                  </button>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function OverviewGrid({ consultation }) {
  return (
    <div className="overview-grid">
      <InfoCard label="Patient Name" value={consultation.name} />
      <InfoCard label="Email" value={consultation.email} />
      <InfoCard label="Age" value={consultation.age} />
      <InfoCard label="Sex" value={consultation.sex} />
      <InfoCard label="Blood Group" value={consultation.blood_group} />
      <InfoCard label="Symptoms" value={consultation.symptoms} />
      <InfoCard label="Duration" value={consultation.duration} />
    </div>
  );
}

function PrescriptionCard({ data }) {
  const patient = data?.patient_information || {};
  const complaints = Array.isArray(data?.chief_complaints) ? data.chief_complaints : [];
  const diagnosis = Array.isArray(data?.possible_diagnosis) ? data.possible_diagnosis : [];
  const meds = Array.isArray(data?.medicine_section) ? data.medicine_section : [];
  const advice = Array.isArray(data?.healthcare_advice) ? data.healthcare_advice : [];
  const tests = Array.isArray(data?.investigation_advice) ? data.investigation_advice : [];

  return (
    <div className="pretty-section prescription-card">
      <h3>{data?.document_title || "AI Prescription Draft"}</h3>

      {data?.top_warning && <div className="danger-banner">{data.top_warning}</div>}

      <div className="overview-grid">
        <InfoCard label="Name" value={patient.name || "-"} />
        <InfoCard label="Age" value={patient.age || "-"} />
        <InfoCard label="Sex" value={patient.sex || "-"} />
        <InfoCard label="Blood Group" value={patient.blood_group || "-"} />
      </div>

      <SubList title="Chief Complaints" items={complaints} />
      <SubList title="Provisional Diagnosis" items={diagnosis} />

      <div className="sub-block">
        <h4>Rx / Medicine</h4>

        <div className="stack-list">
          {meds.length === 0 ? (
            <p className="muted">No medicine available.</p>
          ) : (
            meds.map((med, index) => (
              <div className="medicine-card" key={index}>
                <h5>
                  {index + 1}. {med.medicine_name || "Medicine"}
                </h5>

                <div className="medicine-grid">
                  <span>
                    <strong>Dose:</strong> {med.dose || "-"}
                  </span>
                  <span>
                    <strong>Frequency:</strong> {med.frequency || "-"}
                  </span>
                  <span>
                    <strong>Duration:</strong> {med.duration || "-"}
                  </span>
                </div>

                <p>
                  <strong>Note:</strong> {med.note || "-"}
                </p>
              </div>
            ))
          )}
        </div>
      </div>

      <SubList title="Advice" items={advice} />
      <SubList title="Investigations" items={tests} />

      <div className="sub-block">
        <h4>Follow-up</h4>
        <p>{data?.follow_up_advice || "-"}</p>
      </div>
    </div>
  );
}

function SubList({ title, items }) {
  return (
    <div className="sub-block">
      <h4>{title}</h4>

      <ul className="clean-list">
        {items.length === 0 ? (
          <li>Not available</li>
        ) : (
          items.map((item, index) => <li key={index}>{item}</li>)
        )}
      </ul>
    </div>
  );
}

function SimplePrescriptionText({ text }) {
  return (
    <div className="pretty-section">
      <h3>Prescription Text</h3>
      <pre className="text-preview">{text}</pre>
    </div>
  );
}

function InfoCard({ label, value }) {
  return (
    <div className="info-card">
      <span className="info-label">{label}</span>
      <span className="info-value">{value || "-"}</span>
    </div>
  );
}

function Input({ label, value, onChange, type = "text", placeholder = "", disabled = false }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

function Textarea({ label, value, onChange, placeholder = "" }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((item) => (
          <option key={item} value={item}>
            {item || "Select"}
          </option>
        ))}
      </select>
    </label>
  );
}

function normalizeStatus(status) {
  if (!status) return "pending";
  return String(status).toLowerCase().replace(/\s+/g, "_");
}

function prettyStatus(status) {
  const map = {
    intake_submitted: "Intake Submitted",
    follow_up_questions_generated: "Follow-up Questions Generated",
    running_ai_agents: "Running AI Agents",
    agent1_completed: "Agent 1 Completed",
    agent2_completed: "Agent 2 Completed",
    doctor_review_pending: "Doctor Review Pending",
    doctor_approved: "Doctor Approved",
    ai_draft: "AI Draft",
  };

  return map[normalizeStatus(status)] || status;
}

function prettyDecision(decision) {
  const map = {
    pending: "Pending Doctor Review",
    approved_ai_or_edited_draft: "AI Draft Approved / Edited Draft Approved",
    ai_draft_rejected_manual_prescription_approved:
      "AI Draft Rejected, Manual Prescription Approved",
  };

  return map[decision] || decision || "not decided";
}

function StatusBadge({ status }) {
  const normalized = normalizeStatus(status);

  return <span className={`badge ${normalized}`}>{prettyStatus(status)}</span>;
}

export default App;