import React, { useState, useEffect } from "react";
import { T, I, GlobalStyles, Spinner, useToast } from "../common/UIComponents";
import { api } from "../common/api";

export function OnboardingWizard({ user, token, onComplete, onUserUpdate }) {
  const [step, setStep] = useState(1);
  const [waPhone, setWaPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const { show, Toast } = useToast();

  // Step 2 logic: Check Instagram status
  useEffect(() => {
    if (step === 2 && user?.instagram_username) {
      setStep(3);
    }
  }, [user, step]);

  const handleConnectInstagram = async () => {
    setLoading(true);
    try {
      const res = await api.get("/api/v1/instagram/connect", token);
      if (res.auth_url) {
        window.location.href = res.auth_url;
      }
    } catch (err) {
      show(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveWhatsApp = async () => {
    if (!waPhone || waPhone.length < 10) {
      show("Please enter a valid WhatsApp number", "error");
      return;
    }
    setLoading(true);
    try {
      // Use PATCH to update the user profile
      const updatedUser = await api.patch("/api/v1/auth/me", { whatsapp_phone: waPhone }, token);
      onUserUpdate(updatedUser);
      show("WhatsApp connected!");
      onComplete();
    } catch (err) {
      show(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  const StepIndicator = () => (
    <div style={{ display: "flex", gap: 8, marginBottom: 40, justifyContent: "center" }}>
      {[1, 2, 3].map(s => (
        <div key={s} style={{ width: 40, height: 4, borderRadius: 2, background: s <= step ? T.primary : T.border, transition: "background .3s" }} />
      ))}
    </div>
  );

  return (
    <div style={{ minHeight: "100vh", background: T.bg, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      {Toast}
      <div className="fade-up" style={{ width: "100%", maxWidth: 500, background: T.surface, border: `1px solid ${T.border}`, borderRadius: 24, padding: 48, boxShadow: "0 30px 90px rgba(0,0,0,.6)" }}>
        
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ width: 56, height: 56, background: `linear-gradient(135deg, ${T.primary}, ${T.accent})`, borderRadius: 16, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>{I.ig}</div>
          <h1 style={{ fontFamily: T.fontHead, fontSize: 28, fontWeight: 800, color: T.text }}>Welcome to InstaAgent</h1>
          <p style={{ color: T.textMuted, fontSize: 14, marginTop: 8 }}>Let's get your store automated in 3 simple steps.</p>
        </div>

        <StepIndicator />

        {step === 1 && (
          <div className="slide-in">
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 12 }}>Step 1: Your Account</h2>
            <p style={{ color: T.textMuted, lineHeight: 1.6, marginBottom: 32 }}>
              Great! Your account is ready. Your AI assistant is standing by to help you grow your Instagram business.
            </p>
            <button onClick={() => setStep(2)} style={{ width: "100%", padding: 16, background: T.primary, color: "#fff", border: "none", borderRadius: 14, fontWeight: 700, cursor: "pointer", fontSize: 16 }}>
              Continue to Instagram
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="slide-in">
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 12 }}>Step 2: Connect Instagram</h2>
            <p style={{ color: T.textMuted, lineHeight: 1.6, marginBottom: 32 }}>
              InstaAgent needs permission to post on your behalf. We only use official Meta APIs to keep your account safe.
            </p>
            <button onClick={handleConnectInstagram} disabled={loading} style={{ width: "100%", padding: 16, background: "#E1306C", color: "#fff", border: "none", borderRadius: 14, fontWeight: 700, cursor: "pointer", fontSize: 16, display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
              {loading ? <Spinner size={20} color="#fff" /> : <>{I.ig} Connect Business Account</>}
            </button>
            <div style={{ marginTop: 20, textAlign: "center" }}>
               <p style={{ fontSize: 12, color: T.textMuted }}>Make sure your IG is a Professional/Business account.</p>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="slide-in">
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 12 }}>Step 3: WhatsApp Hook</h2>
            <p style={{ color: T.textMuted, lineHeight: 1.6, marginBottom: 24 }}>
              Enter your WhatsApp number. You can then send product photos to our bot, and the AI will automatically create and post them!
            </p>
                        <div style={{ marginBottom: 20 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: T.textMuted, display: "block", marginBottom: 8, textTransform: "uppercase" }}>Phone Number (with Country Code)</label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input 
                    value={waPhone} 
                    onChange={e => setWaPhone(e.target.value)} 
                    placeholder="+91 98765 43210" 
                    style={{ flex: 1, padding: "14px 16px", borderRadius: 12, border: `1px solid ${T.border}`, background: T.surfaceAlt, color: T.text, fontSize: 16, fontWeight: 600 }} 
                  />
                </div>
                <p style={{ fontSize: 12, color: T.textMuted, marginTop: 10 }}>Once linked, just send a photo to your agent to post it instantly!</p>
              </div>

              <button 
                onClick={handleSaveWhatsApp} 
                disabled={loading || !waPhone}
                style={{ width: "100%", padding: 16, background: T.primary, color: "#fff", border: "none", borderRadius: 12, fontWeight: 700, cursor: "pointer", fontSize: 16, display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}
              >
                {loading ? <Spinner size={20} color="#fff" /> : <>{I.ig} Finish Setup</>}
              </button>
          </div>
        )}

      </div>
    </div>
  );
}
