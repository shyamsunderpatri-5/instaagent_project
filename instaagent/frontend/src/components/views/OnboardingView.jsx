import { useState } from "react";
import { T, I, Badge, Spinner, useToast } from "../common/UIComponents";
import { api } from "../common/api";

export const OnboardingView = ({ user, token, onComplete, onUserUpdate }) => {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    instagram_username: user?.instagram_username || "",
    whatsapp_phone: user?.whatsapp_phone || "",
    posting_time: "09:00",
    language: user?.language || "en"
  });
  const { show, Toast } = useToast();

  const handleNext = async () => {
    if (step < 3) {
      setStep(step + 1);
    } else {
      setLoading(true);
      try {
        const res = await api.post("/api/v1/auth/onboard", formData, token);
        show("Onboarding complete!", "success");
        onUserUpdate(res.user);
        onComplete();
      } catch (err) {
        show(err.message, "error");
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div style={{ height: "100vh", background: T.bg, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      {Toast}
      <div className="fade-up" style={{ width: "100%", maxWidth: 500, background: T.surface, border: `1px solid ${T.border}`, borderRadius: 24, padding: 40, boxShadow: "0 20px 80px rgba(0,0,0,.6)" }}>
        
        {/* Progress Bar */}
        <div style={{ display: "flex", gap: 8, marginBottom: 32 }}>
          {[1, 2, 3].map(s => (
            <div key={s} style={{ flex: 1, height: 4, background: s <= step ? T.primary : T.border, borderRadius: 2 }} />
          ))}
        </div>

        {step === 1 && (
          <div className="slide-in">
            <h1 style={{ fontSize: 24, fontWeight: 800, color: T.text, marginBottom: 12 }}>Connect Instagram</h1>
            <p style={{ color: T.textMuted, fontSize: 14, marginBottom: 24 }}>Enter your business handle to start automating.</p>
            <div style={{ marginBottom: 20 }}>
              <label style={{ fontSize: 12, fontWeight: 700, color: T.textMuted, display: "block", marginBottom: 8, textTransform: "uppercase" }}>Instagram Handle</label>
              <div style={{ position: "relative" }}>
                <span style={{ position: "absolute", left: 12, top: 12, color: T.textMuted }}>@</span>
                <input 
                  value={formData.instagram_username}
                  onChange={e => setFormData({...formData, instagram_username: e.target.value})}
                  placeholder="yourstore.official" 
                  style={{ width: "100%", padding: "12px 12px 12px 32px", borderRadius: 12, border: `1px solid ${T.border}`, background: T.surfaceAlt, color: T.text, fontSize: 15 }} 
                />
              </div>
            </div>
            <p style={{ fontSize: 12, color: T.textMuted, display: "flex", alignItems: "center", gap: 6 }}>
              {I.info} You can change this later in settings.
            </p>
          </div>
        )}

        {step === 2 && (
          <div className="slide-in">
            <h1 style={{ fontSize: 24, fontWeight: 800, color: T.text, marginBottom: 12 }}>Preferred Timing</h1>
            <p style={{ color: T.textMuted, fontSize: 14, marginBottom: 24 }}>When should we suggest your daily posts? (IST)</p>
            <div style={{ marginBottom: 24 }}>
              <label style={{ fontSize: 12, fontWeight: 700, color: T.textMuted, display: "block", marginBottom: 8, textTransform: "uppercase" }}>Suggest Posts At</label>
              <input 
                type="time"
                value={formData.posting_time}
                onChange={e => setFormData({...formData, posting_time: e.target.value})}
                style={{ width: "100%", padding: 12, borderRadius: 12, border: `1px solid ${T.border}`, background: T.surfaceAlt, color: T.text, fontSize: 16 }} 
              />
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="slide-in">
            <h1 style={{ fontSize: 24, fontWeight: 800, color: T.text, marginBottom: 12 }}>Language Preference</h1>
            <p style={{ color: T.textMuted, fontSize: 14, marginBottom: 24 }}>Choose your primary language for AI captions.</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
              {[
                { id: "en", name: "English", flag: "🇬🇧" },
                { id: "hi", name: "Hindi / Hinglish", flag: "🇮🇳" }
              ].map(l => (
                <div 
                  key={l.id} 
                  onClick={() => setFormData({...formData, language: l.id})}
                  style={{ 
                    padding: 20, 
                    borderRadius: 16, 
                    border: `2px solid ${formData.language === l.id ? T.primary : T.border}`, 
                    background: formData.language === l.id ? T.primaryDim : T.surfaceAlt,
                    cursor: "pointer",
                    textAlign: "center",
                    transition: "all .2s"
                  }}
                >
                  <div style={{ fontSize: 24, marginBottom: 8 }}>{l.flag}</div>
                  <div style={{ fontWeight: 700, color: T.text }}>{l.name}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: "flex", gap: 12, marginTop: 40 }}>
          {step > 1 && (
            <button 
              onClick={() => setStep(step - 1)}
              style={{ flex: 1, padding: 14, borderRadius: 12, border: `1px solid ${T.border}`, background: "transparent", color: T.text, fontWeight: 700, cursor: "pointer" }}
            >
              Back
            </button>
          )}
          <button 
            onClick={handleNext}
            disabled={loading || (step === 1 && !formData.instagram_username)}
            style={{ flex: 2, padding: 14, borderRadius: 12, border: "none", background: T.primary, color: "#fff", fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
          >
            {loading ? <Spinner size={20} color="#fff" /> : (step === 3 ? "Finish Setup" : "Continue")} {step < 3 && I.arrowRight}
          </button>
        </div>
      </div>
    </div>
  );
};
