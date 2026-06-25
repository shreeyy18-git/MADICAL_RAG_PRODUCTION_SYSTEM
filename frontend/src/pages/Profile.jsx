import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getSession } from "../services/auth";
import { getProfile, updateProfile } from "../services/api";

export default function Profile() {
  const [session, setSession] = useState(null);
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [phone, setPhone] = useState("");
  const [olderDisease, setOlderDisease] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    getSession().then((s) => {
      if (!s) { navigate("/login"); return; }
      setSession(s);
      loadProfile(s.access_token);
    });
  }, []);

  const loadProfile = (token) => {
    getProfile(token).then((p) => {
      setName(p.name || "");
      setAge(p.age != null ? String(p.age) : "");
      setPhone(p.phone || "");
      setOlderDisease(p.older_disease || "");
    }).catch(() => {});
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMsg("");
    try {
      await updateProfile(session.access_token, {
        name, age: age ? parseInt(age) : null, phone, older_disease: olderDisease,
      });
      setMsg("Profile saved");
      loadProfile(session.access_token);
    } catch (err) {
      setMsg(err.message);
    }
    setSaving(false);
  };

  if (!session) return null;

  return (
    <div className="profile-page">
      <div className="profile-card">
        <h2>Profile</h2>
        <p style={{ color: "var(--text-light)", fontSize: "14px", marginBottom: "4px" }}>Manage your personal information</p>
        <p className="profile-email">{session.user.email}</p>
        <form onSubmit={handleSave}>
          <div className="form-group">
            <label>Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
          </div>
          <div className="form-group">
            <label>Age</label>
            <input type="number" value={age} onChange={(e) => setAge(e.target.value)} placeholder="Your age" min={1} max={150} />
          </div>
          <div className="form-group">
            <label>Phone <span className="optional">(optional)</span></label>
            <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone number" />
          </div>
          <div className="form-group">
            <label>Older Diseases <span className="optional">(for better responses)</span></label>
            <textarea value={olderDisease} onChange={(e) => setOlderDisease(e.target.value)} placeholder="List any existing conditions, e.g. diabetes, hypertension..." rows={3} />
          </div>
          {msg && <p className={`form-msg ${msg === "Profile saved" ? "success" : "error"}`}>{msg}</p>}
          <button type="submit" className="btn btn-primary btn-full" disabled={saving}>
            {saving ? "Saving..." : "Save Profile"}
          </button>
        </form>
      </div>
    </div>
  );
}
