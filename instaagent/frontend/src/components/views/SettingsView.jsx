// frontend/src/components/views/SettingsView.jsx
import { useState, useEffect } from "react";
import { T, I, Spinner, useToast, useLang } from "../common/UIComponents";
import { api } from "../common/api";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिंदी (Hindi)" },
  { code: "te", label: "తెలుగు (Telugu)" },
  { code: "ta", label: "தமிழ் (Tamil)" },
  { code: "kn", label: "ಕನ್ನಡ (Kannada)" },
  { code: "mr", label: "मराठी (Marathi)" },
];

export const SettingsView = ({ user, token, onUserUpdate }) => {
  const [form, setForm] = useState({
    full_name: user?.full_name || "",
    phone:     user?.phone || "",
    city:      user?.city || "",
    language:  user?.language || "hi",
    preferred_post_time: user?.preferred_post_time || "19:00",
    whatsapp_phone: user?.whatsapp_phone || "",
  });
  const [saving, setSaving] = useState(false);
  const [igStatus, setIgStatus] = useState(null);
  const [igLoading, setIgLoading] = useState(false);
  const { show, Toast } = useToast();
  const { t, setLang } = useLang();

  // Load Instagram connection status
  useEffect(() => {
    api.get("/api/v1/instagram/status", token)
      .then(data => setIgStatus(data))
      .catch(() => setIgStatus({ connected: false }));
  }, [token]);

  // Handle ?instagram=connected query param after OAuth redirect
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("instagram") === "connected") {
        show("✅ Instagram connected successfully!");
        window.history.replaceState({}, "", window.location.pathname);
        // Refresh IG status
        api.get("/api/v1/instagram/status", token).then(d => setIgStatus(d));
      }
      if (params.get("instagram") === "error") {
        show("Instagram connection failed: " + (params.get("message") || "Please try again."), "error");
        window.history.replaceState({}, "", window.location.pathname);
      }
    }
  }, []);

  const patch = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await api.patch("/api/v1/auth/profile", form, token);
      show("Settings saved!");
      // Update global language immediately
      if (form.language !== user?.language) {
        setLang(form.language);
        localStorage.setItem("ia_lang", form.language);
      }
      if (onUserUpdate) onUserUpdate(updated.user || updated);
    } catch (e) {
      show(e.message || "Save failed", "error");
    } finally {
      setSaving(false);
    }
  };

  const connectInstagram = async () => {
    setIgLoading(true);
    try {
      const data = await api.get("/api/v1/instagram/connect", token);
      if (data.auth_url) {
        window.location.href = data.auth_url;
      } else {
        show("Could not get Instagram auth URL", "error");
        setIgLoading(false);
      }
    } catch (e) {
      show(e.message || "Instagram connection failed", "error");
      setIgLoading(false);
    }
  };

  const disconnectInstagram = async () => {
    try {
      await api.post("/api/v1/instagram/disconnect", {}, token);
      setIgStatus({ connected: false });
      show("Instagram disconnected");
      if (onUserUpdate) onUserUpdate({ ...user, instagram_username: null });
    } catch (e) {
      show(e.message || "Disconnect failed", "error");
    }
  };

  const inputStyle = { width: "100%", background: T.surfaceAlt, border: `1px solid ${T.borderLight}`, borderRadius: 10, padding: "11px 14px", color: T.text, fontSize: 14, fontFamily: T.fontBody };
  const labelStyle = { fontSize: 12, fontWeight: 600, color: T.textMuted, display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" };
  const fieldWrap  = { marginBottom: 18 };

  // Setup wizard — shown to new users who haven't completed all 3 steps
  const igConnected = !!(igStatus?.connected);
  const waLinked    = !!(form.whatsapp_phone);
  const timeSet     = !!(form.preferred_post_time && form.preferred_post_time !== "19:00");
  const setupSteps  = [
    { id: 1, done: igConnected,  icon: "📸", title: "Connect Instagram",    desc: "One click — lets InstaAgent post on your behalf" },
    { id: 2, done: waLinked,     icon: "💬", title: "Link WhatsApp Number", desc: "Enter your WhatsApp number below" },
    { id: 3, done: timeSet,      icon: "⏰", title: "Set Auto-Post Time",   desc: "Choose what time your posts go live" },
  ];
  const stepsCompleted = setupSteps.filter(s => s.done).length;
  const allDone = stepsCompleted === 3;

  return (
    <div style={{ padding: "28px 32px", maxWidth: 640 }}>
      {Toast}
      <div className="fade-up" style={{ marginBottom: 28 }}>
        <h1 style={{ fontFamily: T.fontHead, fontSize: 24, fontWeight: 800, color: T.text, marginBottom: 6 }}>{t("settings.title")}</h1>
        <p style={{ color: T.textMuted, fontSize: 14 }}>{t("settings.subtitle")}</p>
      </div>

      {/* ── Quick Setup Guide (for new users) ──────────────────────────────── */}
      {!allDone && (
        <div className="fade-up" style={{ background: `linear-gradient(135deg, ${T.primary}12, ${T.accent || T.primary}08)`, border: `1px solid ${T.primary}30`, borderRadius: 18, padding: 22, marginBottom: 24 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 800, color: T.text }}>{t("settings.guide_title")}</div>
              <div style={{ fontSize: 12, color: T.textMuted, marginTop: 2 }}>{t("settings.guide_steps").replace("{val}", stepsCompleted)}</div>
            </div>
            {/* Progress bar */}
            <div style={{ display: "flex", gap: 6 }}>
              {setupSteps.map(s => (
                <div key={s.id} style={{ width: 28, height: 6, borderRadius: 3, background: s.done ? T.primary : `${T.primary}25`, transition: "background 0.3s" }} />
              ))}
            </div>
          </div>
          {setupSteps.map(s => (
            <div key={s.id} style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: "10px 14px", marginBottom: 6, borderRadius: 12, background: s.done ? `${T.green}10` : T.surfaceAlt, border: `1px solid ${s.done ? T.green + "30" : T.border}` }}>
              <div style={{ fontSize: 20, flexShrink: 0, marginTop: 1 }}>{s.done ? "✅" : s.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: s.done ? T.green : T.text }}>{s.title}</div>
                <div style={{ fontSize: 12, color: T.textMuted, marginTop: 2 }}>{s.desc}</div>
              </div>
              {s.done && <div style={{ fontSize: 12, color: T.green, fontWeight: 700, flexShrink: 0 }}>Done ✓</div>}
            </div>
          ))}
          <div style={{ fontSize: 11, color: T.textMuted, marginTop: 10, lineHeight: 1.5 }}>
            {t("settings.how_it_works")}
          </div>
        </div>
      )}

      {/* Profile Section */}
      <div className="fade-up" style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 24, marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 18 }}>{t("settings.profile_info")}</div>
        <div style={fieldWrap}>
          <label style={labelStyle}>{t("settings.full_name")}</label>
          <input value={form.full_name} onChange={e => patch("full_name", e.target.value)} style={inputStyle} placeholder={t("settings.full_name")} />
        </div>
        <div style={fieldWrap}>
          <label style={labelStyle}>{t("settings.phone")}</label>
          <input value={form.phone} onChange={e => patch("phone", e.target.value)} style={inputStyle} placeholder="+91 XXXXX XXXXX" />
        </div>
        <div style={fieldWrap}>
          <label style={labelStyle}>{t("settings.city")}</label>
          <input value={form.city} onChange={e => patch("city", e.target.value)} style={inputStyle} placeholder="Mumbai, Delhi, Hyderabad..." />
        </div>
        <div style={fieldWrap}>
          <label style={labelStyle}>{t("settings.post_time")}</label>
          <input type="time" value={form.preferred_post_time} onChange={e => patch("preferred_post_time", e.target.value)} style={inputStyle} />
          <div style={{ fontSize: 11, color: T.textMuted, marginTop: 4 }}>{t("settings.post_time_desc")}</div>
        </div>
      </div>

      {/* Language Section — changes entire app immediately */}
      <div className="fade-up" style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 24, marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 6 }}>{t("settings.lang_title")}</div>
        <div style={{ fontSize: 12, color: T.textMuted, marginBottom: 16 }}>
          {t("settings.lang_desc")}
        </div>
        <div style={fieldWrap}>
          <label style={labelStyle}>{t("settings.select_lang")}</label>
          <select
            value={form.language}
            onChange={e => {
              patch("language", e.target.value);
              // Instant preview — will also save on handleSave
              setLang(e.target.value);
              localStorage.setItem("ia_lang", e.target.value);
            }}
            style={inputStyle}
          >
            {LANGUAGES.map(l => (
              <option key={l.code} value={l.code}>{l.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Instagram Integration */}
      <div className="fade-up" style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 24, marginBottom: 24 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: T.text, marginBottom: 16 }}>
          {I.ig} {t("settings.ig_integration")}
        </div>
        {igStatus === null ? (
          <div style={{ display: "flex", justifyContent: "center", padding: 16 }}><Spinner /></div>
        ) : igStatus.connected ? (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", background: `${T.green}15`, border: `1px solid ${T.green}40`, borderRadius: 10, marginBottom: 14 }}>
              <span style={{ color: T.green, fontSize: 20 }}>✅</span>
              <div>
                <div style={{ fontWeight: 700, color: T.green, fontSize: 14 }}>{t("settings.ig_connected")}</div>
                <div style={{ fontSize: 12, color: T.textMuted }}>@{igStatus.instagram_username || user?.instagram_username || "account"}</div>
              </div>
            </div>
            <button
              onClick={disconnectInstagram}
              style={{ padding: "10px 18px", background: "transparent", border: `1px solid ${T.red}`, color: T.red, borderRadius: 10, cursor: "pointer", fontSize: 13, fontWeight: 600 }}
            >
              {t("settings.ig_disconnect")}
            </button>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: 12, color: T.textMuted, marginBottom: 14 }}>
              {t("settings.ig_desc")}
            </div>
            <button
              onClick={connectInstagram}
              disabled={igLoading}
              style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 20px", background: `linear-gradient(135deg, #833AB4, #FD1D1D, #FCB045)`, color: "#fff", border: "none", borderRadius: 10, cursor: igLoading ? "wait" : "pointer", fontWeight: 700, fontSize: 14, opacity: igLoading ? 0.7 : 1 }}
            >
              {igLoading ? <><Spinner size={14} color="#fff" /> {t("common.processing")}</> : <>{I.ig} {t("settings.ig_connect_btn")}</>}
            </button>
          </div>
        )}
      </div>

      {/* WhatsApp Business Linking */}
      <div className="fade-up" style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 24, marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <span style={{ fontSize: 22 }}>💬</span>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: T.text }}>{t("settings.wa_bot")}</div>
            <div style={{ fontSize: 11, color: T.textMuted }}>{t("settings.wa_desc")}</div>
          </div>
          {form.whatsapp_phone ? (
            <span style={{ marginLeft: "auto", background: `${T.green}20`, color: T.green, border: `1px solid ${T.green}40`, borderRadius: 20, padding: "3px 10px", fontSize: 11, fontWeight: 700 }}>
              {t("settings.wa_linked")}
            </span>
          ) : (
            <span style={{ marginLeft: "auto", background: `${T.warning || "#F59E0B"}20`, color: T.warning || "#F59E0B", border: `1px solid ${T.warning || "#F59E0B"}40`, borderRadius: 20, padding: "3px 10px", fontSize: 11, fontWeight: 700 }}>
              {t("settings.wa_not_linked")}
            </span>
          )}
        </div>

        <div style={fieldWrap}>
          <label style={labelStyle}>{t("settings.wa_number")}</label>
          <div style={{ display: "flex", gap: 8 }}>
            <span style={{ padding: "11px 12px", background: T.surfaceAlt, border: `1px solid ${T.borderLight}`, borderRadius: 10, color: T.textMuted, fontSize: 14 }}>+91</span>
            <input
              value={form.whatsapp_phone.replace(/^91/, "")}
              onChange={e => {
                const digits = e.target.value.replace(/\D/g, "").slice(0, 10);
                patch("whatsapp_phone", digits ? "91" + digits : "");
              }}
              placeholder="9876543210"
              maxLength={10}
              style={{ ...inputStyle, flex: 1 }}
            />
          </div>
          <div style={{ fontSize: 11, color: T.textMuted, marginTop: 4 }}>
            {t("settings.wa_number_desc")}
          </div>
        </div>

        {form.whatsapp_phone && (
          <div style={{ background: `${T.primary}10`, border: `1px solid ${T.primary}30`, borderRadius: 10, padding: "12px 14px", fontSize: 12, color: T.textMuted, lineHeight: 1.6 }}>
            {t("settings.wa_how_to")}
          </div>
        )}
      </div>

      {/* Save button */}
      <button onClick={handleSave} disabled={saving} style={{ width: "100%", padding: 14, background: T.primary, color: "#fff", border: "none", borderRadius: 12, fontWeight: 700, fontSize: 15, cursor: saving ? "wait" : "pointer", opacity: saving ? 0.7 : 1, transition: "all .2s" }}>
        {saving ? t("common.processing") : t("common.save")}
      </button>
    </div>
  );
};

