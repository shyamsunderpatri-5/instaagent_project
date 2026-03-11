// frontend/src/pages/index.js
// ─────────────────────────────────────────────────────────────────────────────
// InstaAgent — Auth Entry Point
// Handles routing between: login | register | forgot-password | app
//
// All API calls hit real backend endpoints. No mock data anywhere.
// Passwords are never logged or stored in state beyond the form lifetime.
// Tokens are stored in localStorage with the key "ia_token".
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useEffect, useRef, useCallback } from "react";
import dynamic from "next/dynamic";

const InstaAgent = dynamic(() => import("../components/InstaAgent"), { ssr: false });

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─────────────────────────────────────────────────────────────────────────────
// API LAYER — All network calls isolated here
// ─────────────────────────────────────────────────────────────────────────────

async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await res.json();
  if (!res.ok) {
    // FastAPI validation errors come back as { detail: [{msg: "..."}] }
    const msg = Array.isArray(json.detail)
      ? json.detail.map((e) => e.msg).join(", ")
      : json.detail || "Something went wrong. Please try again.";
    throw new Error(msg);
  }
  return json;
}

const Auth = {
  login: (email, password) =>
    apiPost("/api/v1/auth/login", { email, password }),

  register: (payload) =>
    apiPost("/api/v1/auth/register", payload),

  forgotPassword: (email) =>
    apiPost("/api/v1/auth/forgot-password", { email }),

  verifyOtp: (email, otp) =>
    apiPost("/api/v1/auth/verify-otp", { email, otp }),

  resetPassword: (reset_token, new_password) =>
    apiPost("/api/v1/auth/reset-password", { reset_token, new_password }),
};

// ─────────────────────────────────────────────────────────────────────────────
// DESIGN SYSTEM
// ─────────────────────────────────────────────────────────────────────────────

const DS = {
  // Midnight Slate Theme
  pageBg:       "#0B0E14",
  panelBg:      "#12161F",
  surfaceBg:    "#1A202C",
  inputBg:      "#0F172A",
  inputHoverBg: "#1E293B",

  // Borders
  borderDefault: "rgba(255,255,255,0.06)",
  borderHover:   "rgba(255,255,255,0.10)",
  borderFocus:   "#6366F1",

  // Brand
  indigo:        "#6366F1",
  indigoLight:   "#818CF8",
  indigoGlow:    "rgba(99,102,241,0.15)",
  indigoDeep:    "#4F46E5",
  gold:          "#F59E0B",
  goldBg:        "rgba(245,158,11,0.08)",
  goldBorder:    "rgba(245,158,11,0.20)",

  // Status
  success:       "#10B981",
  successBg:     "rgba(16,185,129,0.08)",
  successBorder: "rgba(16,185,129,0.15)",
  error:         "#EF4444",
  errorBg:       "rgba(239,68,68,0.08)",
  errorBorder:   "rgba(239,68,68,0.15)",
  warning:       "#F59E0B",

  // Text
  textPrimary:   "#F8FAFC",
  textSecondary: "#94A3B8",
  textMuted:     "#64748B",
  textDisabled:  "#334155",

  // Typography
  fontSans:  "'Inter', system-ui, -apple-system, sans-serif",
  fontDisplay: "'Plus Jakarta Sans', system-ui, sans-serif",
  fontMono:  "'JetBrains Mono', monospace",
};

// ─────────────────────────────────────────────────────────────────────────────
// SHARED UI PRIMITIVES
// ─────────────────────────────────────────────────────────────────────────────

function FormInput({ label, id, type = "text", value, onChange, placeholder, autoComplete, icon, error, hint, disabled }) {
  const [focused, setFocused] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const isPassword = type === "password";
  const resolvedType = isPassword ? (showPass ? "text" : "password") : type;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label
        htmlFor={id}
        style={{
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          color: error ? DS.error : focused ? DS.indigo : DS.textSecondary,
          transition: "color 0.2s",
          userSelect: "none",
        }}
      >
        {label}
      </label>

      <div style={{ position: "relative" }}>
        {/* Left icon */}
        {icon && (
          <span
            aria-hidden="true"
            style={{
              position: "absolute",
              left: 14,
              top: "50%",
              transform: "translateY(-50%)",
              color: error ? DS.error : focused ? DS.indigo : DS.textMuted,
              transition: "color 0.2s",
              display: "flex",
              alignItems: "center",
              pointerEvents: "none",
            }}
          >
            {icon}
          </span>
        )}

        <input
          id={id}
          type={resolvedType}
          value={value}
          onChange={onChange}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          disabled={disabled}
          spellCheck={false}
          style={{
            width: "100%",
            background: focused ? DS.inputHoverBg : DS.inputBg,
            border: `1.5px solid ${error ? DS.errorBorder : focused ? DS.borderFocus : DS.borderDefault}`,
            borderRadius: 10,
            padding: `13px ${isPassword ? "44px" : "16px"} 13px ${icon ? "44px" : "16px"}`,
            color: DS.textPrimary,
            fontSize: 14,
            fontFamily: DS.fontSans,
            outline: "none",
            transition: "background 0.2s, border-color 0.2s, box-shadow 0.2s",
            boxShadow: focused && !error
              ? `0 0 0 3px ${DS.indigoGlow}`
              : focused && error
              ? `0 0 0 3px rgba(240,82,82,0.15)`
              : "none",
            boxSizing: "border-box",
            opacity: disabled ? 0.5 : 1,
            cursor: disabled ? "not-allowed" : "text",
          }}
        />

        {/* Show/hide password */}
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPass((s) => !s)}
            tabIndex={-1}
            aria-label={showPass ? "Hide password" : "Show password"}
            style={{
              position: "absolute",
              right: 14,
              top: "50%",
              transform: "translateY(-50%)",
              background: "none",
              border: "none",
              cursor: "pointer",
              color: DS.textMuted,
              display: "flex",
              alignItems: "center",
              padding: 2,
              transition: "color 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = DS.textSecondary)}
            onMouseLeave={(e) => (e.currentTarget.style.color = DS.textMuted)}
          >
            {showPass ? (
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                <line x1="1" y1="1" x2="23" y2="23" />
              </svg>
            ) : (
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            )}
          </button>
        )}
      </div>

      {error && (
        <p role="alert" style={{ margin: 0, fontSize: 12, color: DS.error, display: "flex", alignItems: "center", gap: 5 }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </p>
      )}
      {hint && !error && (
        <p style={{ margin: 0, fontSize: 12, color: DS.textMuted }}>{hint}</p>
      )}
    </div>
  );
}

function FormSelect({ label, id, value, onChange, options, icon }) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label htmlFor={id} style={{ fontSize: 12, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", color: focused ? DS.indigo : DS.textSecondary, transition: "color 0.2s", userSelect: "none" }}>
        {label}
      </label>
      <div style={{ position: "relative" }}>
        {icon && (
          <span aria-hidden="true" style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)", color: focused ? DS.indigo : DS.textMuted, pointerEvents: "none", display: "flex", alignItems: "center", transition: "color 0.2s" }}>
            {icon}
          </span>
        )}
        <select
          id={id}
          value={value}
          onChange={onChange}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={{ width: "100%", background: DS.inputBg, border: `1.5px solid ${focused ? DS.borderFocus : DS.borderDefault}`, borderRadius: 10, padding: `13px 40px 13px ${icon ? "44px" : "16px"}`, color: DS.textPrimary, fontSize: 14, fontFamily: DS.fontSans, outline: "none", appearance: "none", WebkitAppearance: "none", cursor: "pointer", transition: "border-color 0.2s", boxSizing: "border-box", boxShadow: focused ? `0 0 0 3px ${DS.indigoGlow}` : "none" }}
        >
          {options.map((o) => (
            <option key={o.value} value={o.value} style={{ background: DS.surfaceBg }}>{o.label}</option>
          ))}
        </select>
        <span aria-hidden="true" style={{ position: "absolute", right: 14, top: "50%", transform: "translateY(-50%)", pointerEvents: "none", color: DS.textMuted }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="6 9 12 15 18 9" /></svg>
        </span>
      </div>
    </div>
  );
}

function PrimaryButton({ type = "button", onClick, disabled, loading, children, fullWidth = true }) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      style={{
        width: fullWidth ? "100%" : "auto",
        background: disabled || loading
          ? "rgba(79,114,248,0.25)"
          : `linear-gradient(135deg, ${DS.indigoDeep} 0%, ${DS.indigoLight} 100%)`,
        border: "none",
        borderRadius: 10,
        padding: "14px 24px",
        color: disabled || loading ? DS.textMuted : "#ffffff",
        fontSize: 15,
        fontWeight: 700,
        fontFamily: DS.fontSans,
        cursor: disabled || loading ? "not-allowed" : "pointer",
        transition: "all 0.2s",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        boxShadow: disabled || loading ? "none" : `0 4px 20px rgba(79,114,248,0.35)`,
        letterSpacing: "0.01em",
      }}
      onMouseEnter={(e) => {
        if (!disabled && !loading) {
          e.currentTarget.style.boxShadow = `0 6px 28px rgba(79,114,248,0.50)`;
          e.currentTarget.style.transform = "translateY(-1px)";
        }
      }}
      onMouseLeave={(e) => {
        if (!disabled && !loading) {
          e.currentTarget.style.boxShadow = `0 4px 20px rgba(79,114,248,0.35)`;
          e.currentTarget.style.transform = "translateY(0)";
        }
      }}
    >
      {loading && (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ animation: "ia-spin 0.75s linear infinite", flexShrink: 0 }}>
          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
        </svg>
      )}
      {children}
    </button>
  );
}

function GhostButton({ type = "button", onClick, children, fullWidth = true }) {
  const [hov, setHov] = useState(false);
  return (
    <button
      type={type}
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        width: fullWidth ? "100%" : "auto",
        background: hov ? "rgba(255,255,255,0.04)" : "transparent",
        border: `1.5px solid ${hov ? DS.borderHover : DS.borderDefault}`,
        borderRadius: 10,
        padding: "13px 24px",
        color: hov ? DS.textPrimary : DS.textSecondary,
        fontSize: 14,
        fontWeight: 600,
        fontFamily: DS.fontSans,
        cursor: "pointer",
        transition: "all 0.18s",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        letterSpacing: "0.01em",
      }}
    >
      {children}
    </button>
  );
}

function AlertBox({ type, children }) {
  const cfg = {
    error:   { bg: DS.errorBg,   border: DS.errorBorder,   color: DS.error,   icon: "⊘" },
    success: { bg: DS.successBg, border: DS.successBorder, color: DS.success, icon: "✓" },
    info:    { bg: DS.indigoGlow, border: "rgba(79,114,248,0.25)", color: DS.indigo, icon: "ℹ" },
  }[type] || {};

  return (
    <div role="alert" style={{ background: cfg.bg, border: `1px solid ${cfg.border}`, borderRadius: 10, padding: "12px 16px", display: "flex", alignItems: "flex-start", gap: 10 }}>
      <span style={{ color: cfg.color, fontSize: 15, lineHeight: 1, flexShrink: 0, marginTop: 1 }}>{cfg.icon}</span>
      <p style={{ margin: 0, color: cfg.color, fontSize: 13, lineHeight: 1.55 }}>{children}</p>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SHARED LEFT BRAND PANEL
// ─────────────────────────────────────────────────────────────────────────────

const FEATURES = [
  { icon: "✦", text: "AI captions in Hindi, Telugu, Tamil, Kannada & more" },
  { icon: "✦", text: "Background removal + photo enhancement in seconds" },
  { icon: "✦", text: "Telegram notifications when your post is ready" },
  { icon: "✦", text: "Schedule posts at the best time for your audience" },
];

function BrandPanel({ headline, subtext }) {
  return (
    <div
      style={{
        flex: "0 0 480px",
        background: DS.panelBg,
        borderRight: `1px solid ${DS.borderDefault}`,
        padding: "48px 52px",
        display: "flex",
        flexDirection: "column",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Decorative mesh */}
      <div aria-hidden="true" style={{ position: "absolute", inset: 0, pointerEvents: "none", overflow: "hidden" }}>
        <div style={{ position: "absolute", top: "-20%", left: "-15%", width: 500, height: 500, borderRadius: "50%", background: "radial-gradient(circle, rgba(79,114,248,0.09) 0%, transparent 65%)" }} />
        <div style={{ position: "absolute", bottom: "5%", right: "-20%", width: 400, height: 400, borderRadius: "50%", background: "radial-gradient(circle, rgba(212,168,83,0.07) 0%, transparent 65%)" }} />
        <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.04 }} xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="ia-grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" strokeWidth="0.8" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#ia-grid)" />
        </svg>
      </div>

      {/* Logo */}
      <div style={{ position: "relative", zIndex: 1, marginBottom: "auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 11, marginBottom: 52 }}>
          <div style={{ width: 40, height: 40, borderRadius: 11, background: `linear-gradient(135deg, ${DS.indigoDeep}, ${DS.indigoLight})`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, boxShadow: `0 4px 18px ${DS.indigoGlow}` }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8" strokeLinecap="round">
              <rect x="2" y="2" width="20" height="20" rx="5" />
              <circle cx="12" cy="12" r="4" />
              <circle cx="17.5" cy="6.5" r="1.2" fill="white" stroke="none" />
            </svg>
          </div>
          <span style={{ fontSize: 19, fontWeight: 800, color: DS.textPrimary, fontFamily: DS.fontDisplay, letterSpacing: "-0.3px" }}>
            InstaAgent
          </span>
        </div>

        {/* Headline */}
        <h2 style={{ fontFamily: DS.fontDisplay, fontSize: 34, fontWeight: 800, color: DS.textPrimary, lineHeight: 1.18, margin: "0 0 14px", letterSpacing: "-0.6px" }}>
          {headline}
        </h2>
        <p style={{ fontSize: 15, color: DS.textSecondary, lineHeight: 1.65, margin: "0 0 40px" }}>
          {subtext}
        </p>

        {/* Feature list */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {FEATURES.map((f) => (
            <div key={f.text} style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
              <div style={{ width: 22, height: 22, borderRadius: 6, background: DS.indigoGlow, border: `1px solid rgba(79,114,248,0.25)`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 }}>
                <span style={{ fontSize: 9, color: DS.indigoLight }}>✓</span>
              </div>
              <span style={{ fontSize: 14, color: DS.textSecondary, lineHeight: 1.5 }}>{f.text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Trust bar */}
      <div style={{ position: "relative", zIndex: 1, marginTop: 48, paddingTop: 24, borderTop: `1px solid ${DS.borderDefault}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ display: "flex" }}>
            {["#3B82F6", "#8B5CF6", "#EC4899", "#F97316"].map((c, i) => (
              <div key={i} style={{ width: 30, height: 30, borderRadius: "50%", background: c, border: `2px solid ${DS.panelBg}`, marginLeft: i ? -10 : 0 }} />
            ))}
          </div>
          <div>
            <p style={{ margin: 0, fontSize: 13, fontWeight: 700, color: DS.textPrimary }}>Trusted by 500+ Indian businesses</p>
            <p style={{ margin: 0, fontSize: 12, color: DS.textMuted }}>Jewellery · Food · Clothing · Handmade</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// PASSWORD STRENGTH METER
// ─────────────────────────────────────────────────────────────────────────────

function getPasswordStrength(pw) {
  if (!pw) return { score: 0, label: "", bars: [false, false, false, false] };
  const checks = [
    pw.length >= 8,
    /[A-Z]/.test(pw),
    /[0-9]/.test(pw),
    /[^A-Za-z0-9]/.test(pw),
  ];
  const score = checks.filter(Boolean).length;
  const labels = ["", "Weak", "Fair", "Good", "Strong"];
  const colors = ["", DS.error, DS.warning, "#84CC16", DS.success];
  return { score, label: labels[score], color: colors[score], bars: checks };
}

function PasswordMeter({ password }) {
  const { score, label, color, bars } = getPasswordStrength(password);
  if (!password) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: -2 }}>
      <div style={{ display: "flex", gap: 4 }}>
        {bars.map((filled, i) => (
          <div key={i} style={{ flex: 1, height: 3, borderRadius: 2, background: filled ? color : DS.borderDefault, transition: "background 0.3s" }} />
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 11, color, fontWeight: 600 }}>Password strength: {label}</span>
        {score < 3 && <span style={{ fontSize: 11, color: DS.textMuted }}>Add uppercase, numbers, symbols</span>}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// LOGIN PAGE
// ─────────────────────────────────────────────────────────────────────────────

function LoginPage({ onSuccess, onGoRegister, onGoForgot }) {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  // Pre-fill remembered email
  useEffect(() => {
    const saved = typeof window !== "undefined" && localStorage.getItem("ia_remembered_email");
    if (saved) { setEmail(saved); setRemember(true); }
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setError("");
    setLoading(true);

    try {
      const data = await Auth.login(email.trim().toLowerCase(), password);
      if (remember) {
        localStorage.setItem("ia_remembered_email", email.trim().toLowerCase());
      } else {
        localStorage.removeItem("ia_remembered_email");
      }
      localStorage.setItem("ia_token", data.token);
      localStorage.setItem("ia_user", JSON.stringify(data.user));
      onSuccess(data.user, data.token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: DS.pageBg, fontFamily: DS.fontSans }}>
      {/* Left brand panel */}
      <BrandPanel
        headline="Turn product photos into viral Instagram posts"
        subtext="Upload a photo, get a professional Hindi or regional language caption with 20 hashtags — ready to post in under 15 seconds."
      />

      {/* Right form panel */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "48px 32px", overflowY: "auto" }}>
        <div style={{ width: "100%", maxWidth: 400 }}>

          {/* Heading */}
          <div style={{ marginBottom: 32 }}>
            <h1 style={{ fontFamily: DS.fontDisplay, fontSize: 28, fontWeight: 800, color: DS.textPrimary, margin: "0 0 8px", letterSpacing: "-0.4px" }}>
              Welcome back
            </h1>
            <p style={{ margin: 0, fontSize: 14, color: DS.textSecondary }}>
              Sign in to your InstaAgent account
            </p>
          </div>

          {error && <div style={{ marginBottom: 20 }}><AlertBox type="error">{error}</AlertBox></div>}

          <form onSubmit={handleSubmit} noValidate style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <FormInput
              label="Email address"
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setError(""); }}
              placeholder="you@example.com"
              autoComplete="email"
              icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" /><polyline points="22,6 12,13 2,6" /></svg>}
            />

            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <FormInput
                label="Password"
                id="login-password"
                type="password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(""); }}
                placeholder="Enter your password"
                autoComplete="current-password"
                icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>}
              />
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button type="button" onClick={onGoForgot} style={{ background: "none", border: "none", cursor: "pointer", color: DS.indigo, fontSize: 13, fontWeight: 600, fontFamily: DS.fontSans, padding: 0 }}>
                  Forgot password?
                </button>
              </div>
            </div>

            {/* Remember me */}
            <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", userSelect: "none" }}>
              <div
                role="checkbox"
                aria-checked={remember}
                tabIndex={0}
                onClick={() => setRemember((r) => !r)}
                onKeyDown={(e) => e.key === " " && setRemember((r) => !r)}
                style={{ width: 18, height: 18, borderRadius: 5, border: `2px solid ${remember ? DS.indigo : DS.borderDefault}`, background: remember ? DS.indigo : "transparent", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, transition: "all 0.15s", cursor: "pointer" }}
              >
                {remember && <svg width="10" height="10" viewBox="0 0 12 12" fill="none"><path d="M2 6L5 9L10 3" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>}
              </div>
              <span style={{ fontSize: 13, color: DS.textSecondary }}>Remember me on this device</span>
            </label>

            <PrimaryButton type="submit" loading={loading} disabled={!email.trim() || !password}>
              {!loading && <>Sign in <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12h14M12 5l7 7-7 7" /></svg></>}
              {loading && "Signing in…"}
            </PrimaryButton>
          </form>

          <div style={{ margin: "28px 0", display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ flex: 1, height: 1, background: DS.borderDefault }} />
            <span style={{ fontSize: 12, color: DS.textMuted, whiteSpace: "nowrap" }}>New to InstaAgent?</span>
            <div style={{ flex: 1, height: 1, background: DS.borderDefault }} />
          </div>

          <GhostButton onClick={onGoRegister}>
            Create a free account →
          </GhostButton>

          <p style={{ marginTop: 24, textAlign: "center", fontSize: 11, color: DS.textMuted, lineHeight: 1.6 }}>
            By signing in, you agree to our{" "}
            <a href="#" style={{ color: DS.textSecondary, textDecoration: "underline" }}>Terms of Service</a>{" "}and{" "}
            <a href="#" style={{ color: DS.textSecondary, textDecoration: "underline" }}>Privacy Policy</a>.
          </p>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// REGISTER PAGE
// ─────────────────────────────────────────────────────────────────────────────

const LANGUAGE_OPTIONS = [
  { value: "hi", label: "🇮🇳  हिंदी — Hindi" },
  { value: "te", label: "🇮🇳  తెలుగు — Telugu" },
  { value: "ta", label: "🇮🇳  தமிழ் — Tamil" },
  { value: "kn", label: "🇮🇳  ಕನ್ನಡ — Kannada" },
  { value: "mr", label: "🇮🇳  मराठी — Marathi" },
  { value: "en", label: "🌐  English" },
];

function validateRegisterForm(form) {
  const errors = {};
  if (!form.full_name.trim() || form.full_name.trim().length < 2)
    errors.full_name = "Name must be at least 2 characters";
  if (!form.email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
    errors.email = "Enter a valid email address";
  if (form.phone && !/^[6-9]\d{9}$/.test(form.phone.replace(/\D/g, "")))
    errors.phone = "Enter a valid 10-digit Indian mobile number";
  if (form.password.length < 8)
    errors.password = "Minimum 8 characters required";
  if (!/[A-Z]/.test(form.password))
    errors.password = "Must include at least one uppercase letter";
  if (!/[0-9]/.test(form.password))
    errors.password = "Must include at least one number";
  if (form.password !== form.confirm_password)
    errors.confirm_password = "Passwords do not match";
  return errors;
}

function RegisterPage({ onSuccess, onGoLogin }) {
  const [form, setForm] = useState({
    full_name: "", email: "", phone: "", city: "",
    language: "hi", password: "", confirm_password: "",
  });
  const [errors, setErrors]     = useState({});
  const [apiError, setApiError] = useState("");
  const [loading, setLoading]   = useState(false);
  const [agreed, setAgreed]     = useState(false);

  function set(field) {
    return (e) => {
      setForm((f) => ({ ...f, [field]: e.target.value }));
      if (errors[field]) setErrors((prev) => { const n = { ...prev }; delete n[field]; return n; });
    };
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const errs = validateRegisterForm(form);
    if (!agreed) errs.agreed = "You must accept the terms to continue";
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }

    setApiError("");
    setLoading(true);

    try {
      const payload = {
        full_name: form.full_name.trim(),
        email:     form.email.trim().toLowerCase(),
        password:  form.password,
        phone:     form.phone.trim() || undefined,
        city:      form.city.trim()  || undefined,
        language:  form.language,
      };
      const data = await Auth.register(payload);
      localStorage.setItem("ia_token", data.token);
      localStorage.setItem("ia_user", JSON.stringify(data.user));
      onSuccess(data.user, data.token);
    } catch (err) {
      setApiError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: DS.pageBg, fontFamily: DS.fontSans }}>
      {/* Left brand panel */}
      <BrandPanel
        headline="Start automating your Instagram in 2 minutes"
        subtext="Create your free account. No credit card required. Post AI-generated captions for your products starting today."
      />

      {/* Right form panel */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-start", padding: "48px 32px", overflowY: "auto" }}>
        <div style={{ width: "100%", maxWidth: 420 }}>

          {/* Heading */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 8, background: DS.goldBg, border: `1px solid ${DS.goldBorder}`, borderRadius: 20, padding: "4px 12px", marginBottom: 14 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: DS.gold, display: "inline-block" }} />
              <span style={{ fontSize: 11, fontWeight: 700, color: DS.gold, letterSpacing: "0.07em", textTransform: "uppercase" }}>Free — No credit card needed</span>
            </div>
            <h1 style={{ fontFamily: DS.fontDisplay, fontSize: 26, fontWeight: 800, color: DS.textPrimary, margin: "0 0 8px", letterSpacing: "-0.4px" }}>
              Create your account
            </h1>
            <p style={{ margin: 0, fontSize: 14, color: DS.textSecondary }}>
              Already have an account?{" "}
              <button type="button" onClick={onGoLogin} style={{ background: "none", border: "none", cursor: "pointer", color: DS.indigo, fontWeight: 600, fontSize: 14, fontFamily: DS.fontSans, padding: 0 }}>Sign in</button>
            </p>
          </div>

          {apiError && <div style={{ marginBottom: 20 }}><AlertBox type="error">{apiError}</AlertBox></div>}

          <form onSubmit={handleSubmit} noValidate style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Full name */}
            <FormInput
              label="Full Name *"
              id="reg-name"
              value={form.full_name}
              onChange={set("full_name")}
              placeholder="Shyam Kumar"
              autoComplete="name"
              error={errors.full_name}
              icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>}
            />

            {/* Email */}
            <FormInput
              label="Business Email *"
              id="reg-email"
              type="email"
              value={form.email}
              onChange={set("email")}
              placeholder="you@yourbusiness.com"
              autoComplete="email"
              error={errors.email}
              icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" /><polyline points="22,6 12,13 2,6" /></svg>}
            />

            {/* Phone + City on same row */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <FormInput
                label="Phone (WhatsApp)"
                id="reg-phone"
                type="tel"
                value={form.phone}
                onChange={set("phone")}
                placeholder="9876543210"
                autoComplete="tel"
                error={errors.phone}
                hint="Optional — for Telegram alerts"
                icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13 19.79 19.79 0 0 1 1.65 4.35 2 2 0 0 1 3.62 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" /></svg>}
              />
              <FormInput
                label="City"
                id="reg-city"
                value={form.city}
                onChange={set("city")}
                placeholder="Hyderabad"
                autoComplete="address-level2"
                icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" /></svg>}
              />
            </div>

            {/* Language */}
            <FormSelect
              label="Caption Language *"
              id="reg-lang"
              value={form.language}
              onChange={set("language")}
              options={LANGUAGE_OPTIONS}
              icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="10" /><line x1="2" y1="12" x2="22" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></svg>}
            />

            {/* Password */}
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <FormInput
                label="Password *"
                id="reg-pass"
                type="password"
                value={form.password}
                onChange={set("password")}
                placeholder="Min. 8 chars, 1 uppercase, 1 number"
                autoComplete="new-password"
                error={errors.password}
                icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>}
              />
              <PasswordMeter password={form.password} />
            </div>

            {/* Confirm password */}
            <FormInput
              label="Confirm Password *"
              id="reg-confirm"
              type="password"
              value={form.confirm_password}
              onChange={set("confirm_password")}
              placeholder="Re-enter your password"
              autoComplete="new-password"
              error={errors.confirm_password}
              icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>}
            />

            {/* Terms */}
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <label style={{ display: "flex", alignItems: "flex-start", gap: 10, cursor: "pointer", userSelect: "none" }}>
                <div
                  role="checkbox"
                  aria-checked={agreed}
                  tabIndex={0}
                  onClick={() => { setAgreed((a) => !a); if (errors.agreed) setErrors((p) => { const n = { ...p }; delete n.agreed; return n; }); }}
                  onKeyDown={(e) => e.key === " " && setAgreed((a) => !a)}
                  style={{ width: 18, height: 18, borderRadius: 5, border: `2px solid ${errors.agreed ? DS.errorBorder : agreed ? DS.indigo : DS.borderDefault}`, background: agreed ? DS.indigo : "transparent", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1, transition: "all 0.15s", cursor: "pointer" }}
                >
                  {agreed && <svg width="10" height="10" viewBox="0 0 12 12" fill="none"><path d="M2 6L5 9L10 3" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg>}
                </div>
                <span style={{ fontSize: 13, color: DS.textSecondary, lineHeight: 1.5 }}>
                  I agree to InstaAgent's{" "}
                  <a href="#" style={{ color: DS.indigo }}>Terms of Service</a>{" "}and{" "}
                  <a href="#" style={{ color: DS.indigo }}>Privacy Policy</a>
                </span>
              </label>
              {errors.agreed && <p style={{ margin: "0 0 0 28px", fontSize: 12, color: DS.error }}>{errors.agreed}</p>}
            </div>

            <PrimaryButton type="submit" loading={loading}>
              {!loading && <>Create Free Account <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12h14M12 5l7 7-7 7" /></svg></>}
              {loading && "Creating your account…"}
            </PrimaryButton>
          </form>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// OTP DIGIT INPUT — 6 individual boxes (like banking apps)
// ─────────────────────────────────────────────────────────────────────────────

function OtpBoxes({ value, onChange, error, disabled }) {
  const refs = useRef([]);
  const digits = (value + "      ").slice(0, 6).split("");

  function focusBox(i) {
    refs.current[i]?.focus();
  }

  function handleChange(i, raw) {
    const digit = raw.replace(/\D/g, "").slice(-1);
    const next = digits.map((d, idx) => (idx === i ? digit : d)).join("").trimEnd();
    onChange(next.slice(0, 6));
    if (digit && i < 5) focusBox(i + 1);
  }

  function handleKeyDown(i, e) {
    if (e.key === "Backspace") {
      if (!digits[i].trim() && i > 0) {
        const next = digits.map((d, idx) => (idx === i - 1 ? "" : d)).join("").trimEnd();
        onChange(next);
        focusBox(i - 1);
      } else {
        const next = digits.map((d, idx) => (idx === i ? "" : d)).join("").trimEnd();
        onChange(next);
      }
      e.preventDefault();
    }
    if (e.key === "ArrowLeft" && i > 0) focusBox(i - 1);
    if (e.key === "ArrowRight" && i < 5) focusBox(i + 1);
  }

  function handlePaste(e) {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    onChange(pasted);
    focusBox(Math.min(pasted.length, 5));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
        {[0, 1, 2, 3, 4, 5].map((i) => {
          const filled = !!digits[i].trim();
          return (
            <input
              key={i}
              ref={(el) => (refs.current[i] = el)}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digits[i].trim()}
              onChange={(e) => handleChange(i, e.target.value)}
              onKeyDown={(e) => handleKeyDown(i, e)}
              onPaste={handlePaste}
              disabled={disabled}
              aria-label={`OTP digit ${i + 1}`}
              style={{
                width: 52,
                height: 58,
                textAlign: "center",
                fontSize: 22,
                fontWeight: 800,
                fontFamily: DS.fontMono,
                background: error ? DS.errorBg : filled ? DS.inputHoverBg : DS.inputBg,
                border: `2px solid ${error ? DS.errorBorder : filled ? DS.borderFocus : DS.borderDefault}`,
                borderRadius: 10,
                color: DS.textPrimary,
                outline: "none",
                cursor: disabled ? "not-allowed" : "text",
                transition: "all 0.15s",
                boxShadow: filled ? `0 0 0 3px ${DS.indigoGlow}` : "none",
              }}
            />
          );
        })}
      </div>
      {error && (
        <p role="alert" style={{ margin: 0, textAlign: "center", fontSize: 12, color: DS.error, display: "flex", alignItems: "center", justifyContent: "center", gap: 5 }}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
          {error}
        </p>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// FORGOT PASSWORD — 3-step flow
// Step 1: email → Step 2: OTP → Step 3: new password
// ─────────────────────────────────────────────────────────────────────────────

const FP_STEPS = [
  { id: 1, label: "Email" },
  { id: 2, label: "Verify OTP" },
  { id: 3, label: "New Password" },
];

function StepIndicator({ current }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 0, marginBottom: 32 }}>
      {FP_STEPS.map((step, idx) => {
        const done    = current > step.id;
        const active  = current === step.id;
        const pending = current < step.id;
        return (
          <div key={step.id} style={{ display: "flex", alignItems: "center", flex: idx < FP_STEPS.length - 1 ? 1 : "none" }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
              <div style={{
                width: 34, height: 34, borderRadius: "50%",
                background: done ? DS.success : active ? DS.indigo : "transparent",
                border: `2px solid ${done ? DS.success : active ? DS.indigo : DS.borderDefault}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                transition: "all 0.3s",
                boxShadow: active ? `0 0 0 4px ${DS.indigoGlow}` : "none",
              }}>
                {done
                  ? <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5"><polyline points="20 6 9 17 4 12" /></svg>
                  : <span style={{ fontSize: 12, fontWeight: 700, color: active ? "white" : DS.textMuted }}>{step.id}</span>
                }
              </div>
              <span style={{ fontSize: 11, fontWeight: 600, color: active || done ? DS.textSecondary : DS.textMuted, letterSpacing: "0.04em", textTransform: "uppercase", whiteSpace: "nowrap" }}>
                {step.label}
              </span>
            </div>
            {idx < FP_STEPS.length - 1 && (
              <div style={{ flex: 1, height: 1.5, marginBottom: 20, marginLeft: 8, marginRight: 8, background: current > step.id ? DS.success : DS.borderDefault, transition: "background 0.3s" }} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// Masks an email for display: sh***@gmail.com
function maskEmail(email) {
  const [user, domain] = email.split("@");
  if (!domain) return email;
  const visible = user.slice(0, Math.min(2, user.length));
  return `${visible}${"*".repeat(Math.max(0, user.length - 2))}@${domain}`;
}

function ForgotPasswordPage({ onGoLogin }) {
  const [step, setStep]               = useState(1);
  const [email, setEmail]             = useState("");
  const [otp, setOtp]                 = useState("");
  const [resetToken, setResetToken]   = useState("");
  const [newPass, setNewPass]         = useState("");
  const [confirmPass, setConfirmPass] = useState("");
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState("");
  const [successMsg, setSuccessMsg]   = useState("");
  const [resendSecs, setResendSecs]   = useState(0);
  const [done, setDone]               = useState(false);
  const timerRef = useRef(null);

  // Countdown for resend button
  const startCountdown = useCallback((secs = 60) => {
    setResendSecs(secs);
    timerRef.current = setInterval(() => {
      setResendSecs((s) => {
        if (s <= 1) { clearInterval(timerRef.current); return 0; }
        return s - 1;
      });
    }, 1000);
  }, []);

  useEffect(() => () => clearInterval(timerRef.current), []);

  // ── Step 1 handler ────────────────────────────────────────────────────────
  async function handleSendOtp(e) {
    e.preventDefault();
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Please enter a valid email address");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await Auth.forgotPassword(email.trim().toLowerCase());
      setStep(2);
      startCountdown(60);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Resend OTP ────────────────────────────────────────────────────────────
  async function handleResend() {
    if (resendSecs > 0) return;
    setError("");
    setOtp("");
    setLoading(true);
    try {
      await Auth.forgotPassword(email.trim().toLowerCase());
      startCountdown(60);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Step 2 handler ────────────────────────────────────────────────────────
  async function handleVerifyOtp(e) {
    e.preventDefault();
    if (otp.length < 6) { setError("Please enter all 6 digits"); return; }
    setError("");
    setLoading(true);
    try {
      const data = await Auth.verifyOtp(email.trim().toLowerCase(), otp);
      setResetToken(data.reset_token);
      setStep(3);
    } catch (err) {
      setError(err.message);
      setOtp("");
    } finally {
      setLoading(false);
    }
  }

  // ── Step 3 handler ────────────────────────────────────────────────────────
  async function handleResetPassword(e) {
    e.preventDefault();
    if (newPass.length < 8)              { setError("Password must be at least 8 characters"); return; }
    if (!/[A-Z]/.test(newPass))          { setError("Password must include at least one uppercase letter"); return; }
    if (!/[0-9]/.test(newPass))          { setError("Password must include at least one number"); return; }
    if (newPass !== confirmPass)         { setError("Passwords do not match"); return; }
    setError("");
    setLoading(true);
    try {
      await Auth.resetPassword(resetToken, newPass);
      setDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: DS.pageBg, fontFamily: DS.fontSans, display: "flex", alignItems: "center", justifyContent: "center", padding: "32px 20px", position: "relative", overflow: "hidden" }}>
      {/* Background decoration */}
      <div aria-hidden="true" style={{ position: "fixed", inset: 0, pointerEvents: "none" }}>
        <div style={{ position: "absolute", top: "15%", left: "50%", transform: "translateX(-50%)", width: 600, height: 400, borderRadius: "50%", background: "radial-gradient(ellipse, rgba(79,114,248,0.07) 0%, transparent 65%)" }} />
        <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.025 }} xmlns="http://www.w3.org/2000/svg">
          <defs><pattern id="ia-grid-fp" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" strokeWidth="0.8" /></pattern></defs>
          <rect width="100%" height="100%" fill="url(#ia-grid-fp)" />
        </svg>
      </div>

      <div style={{ width: "100%", maxWidth: 460, position: "relative", zIndex: 1 }}>
        {/* Card */}
        <div style={{ background: DS.panelBg, border: `1px solid ${DS.borderDefault}`, borderRadius: 20, padding: "40px 40px 36px", boxShadow: "0 24px 64px rgba(0,0,0,0.55)" }}>

          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 32 }}>
            <div style={{ width: 36, height: 36, borderRadius: 9, background: `linear-gradient(135deg, ${DS.indigoDeep}, ${DS.indigoLight})`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, boxShadow: `0 3px 12px ${DS.indigoGlow}` }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8" strokeLinecap="round"><rect x="2" y="2" width="20" height="20" rx="5" /><circle cx="12" cy="12" r="4" /><circle cx="17.5" cy="6.5" r="1.2" fill="white" stroke="none" /></svg>
            </div>
            <span style={{ fontSize: 17, fontWeight: 800, color: DS.textPrimary, fontFamily: DS.fontDisplay, letterSpacing: "-0.3px" }}>InstaAgent</span>
          </div>

          {!done ? (
            <>
              {/* Step header */}
              <div style={{ marginBottom: 28 }}>
                <h1 style={{ fontFamily: DS.fontDisplay, fontSize: 24, fontWeight: 800, color: DS.textPrimary, margin: "0 0 6px", letterSpacing: "-0.3px" }}>
                  {step === 1 && "Reset your password"}
                  {step === 2 && "Enter verification code"}
                  {step === 3 && "Set a new password"}
                </h1>
                <p style={{ margin: 0, fontSize: 13, color: DS.textSecondary, lineHeight: 1.55 }}>
                  {step === 1 && "Enter your account email and we'll send a 6-digit OTP."}
                  {step === 2 && <>We sent a 6-digit code to <strong style={{ color: DS.textPrimary }}>{maskEmail(email)}</strong>. Check your inbox and spam folder.</>}
                  {step === 3 && "Choose a strong password for your account. You'll be signed in after resetting."}
                </p>
              </div>

              {/* Step indicator */}
              <StepIndicator current={step} />

              {error && <div style={{ marginBottom: 20 }}><AlertBox type="error">{error}</AlertBox></div>}

              {/* ── STEP 1: Email ── */}
              {step === 1 && (
                <form onSubmit={handleSendOtp} noValidate style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                  <FormInput
                    label="Email address"
                    id="fp-email"
                    type="email"
                    value={email}
                    onChange={(e) => { setEmail(e.target.value); setError(""); }}
                    placeholder="you@example.com"
                    autoComplete="email"
                    icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" /><polyline points="22,6 12,13 2,6" /></svg>}
                  />
                  <PrimaryButton type="submit" loading={loading} disabled={!email.trim()}>
                    {!loading && "Send Verification Code"}
                    {loading && "Sending OTP…"}
                  </PrimaryButton>
                </form>
              )}

              {/* ── STEP 2: OTP ── */}
              {step === 2 && (
                <form onSubmit={handleVerifyOtp} noValidate style={{ display: "flex", flexDirection: "column", gap: 24 }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <label style={{ fontSize: 12, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase", color: DS.textSecondary, userSelect: "none" }}>
                      6-Digit OTP
                    </label>
                    <OtpBoxes value={otp} onChange={(v) => { setOtp(v); setError(""); }} error={null} disabled={loading} />
                    <p style={{ margin: 0, fontSize: 11, color: DS.textMuted, textAlign: "center" }}>
                      OTP expires in 10 minutes. Do not share it with anyone.
                    </p>
                  </div>

                  <PrimaryButton type="submit" loading={loading} disabled={otp.length < 6}>
                    {!loading && "Verify OTP"}
                    {loading && "Verifying…"}
                  </PrimaryButton>

                  {/* Resend */}
                  <div style={{ textAlign: "center" }}>
                    {resendSecs > 0 ? (
                      <p style={{ margin: 0, fontSize: 13, color: DS.textMuted }}>
                        Resend code in <span style={{ color: DS.indigo, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>{resendSecs}s</span>
                      </p>
                    ) : (
                      <button
                        type="button"
                        onClick={handleResend}
                        disabled={loading}
                        style={{ background: "none", border: "none", cursor: loading ? "wait" : "pointer", color: DS.indigo, fontSize: 13, fontWeight: 600, fontFamily: DS.fontSans, padding: 0, opacity: loading ? 0.5 : 1 }}
                      >
                        Resend verification code
                      </button>
                    )}
                  </div>
                </form>
              )}

              {/* ── STEP 3: New password ── */}
              {step === 3 && (
                <form onSubmit={handleResetPassword} noValidate style={{ display: "flex", flexDirection: "column", gap: 18 }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    <FormInput
                      label="New Password *"
                      id="fp-newpass"
                      type="password"
                      value={newPass}
                      onChange={(e) => { setNewPass(e.target.value); setError(""); }}
                      placeholder="Min. 8 chars, 1 uppercase, 1 number"
                      autoComplete="new-password"
                      icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>}
                    />
                    <PasswordMeter password={newPass} />
                  </div>

                  <FormInput
                    label="Confirm Password *"
                    id="fp-confirm"
                    type="password"
                    value={confirmPass}
                    onChange={(e) => { setConfirmPass(e.target.value); setError(""); }}
                    placeholder="Re-enter new password"
                    autoComplete="new-password"
                    icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></svg>}
                  />

                  <PrimaryButton type="submit" loading={loading} disabled={!newPass || !confirmPass}>
                    {!loading && <>Set New Password <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12h14M12 5l7 7-7 7" /></svg></>}
                    {loading && "Updating password…"}
                  </PrimaryButton>
                </form>
              )}
            </>
          ) : (
            /* ── SUCCESS STATE ── */
            <div style={{ textAlign: "center", padding: "16px 0" }}>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: DS.successBg, border: `1.5px solid ${DS.successBorder}`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px" }}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={DS.success} strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
              </div>
              <h2 style={{ fontFamily: DS.fontDisplay, fontSize: 22, fontWeight: 800, color: DS.textPrimary, margin: "0 0 10px" }}>
                Password reset successfully
              </h2>
              <p style={{ margin: "0 0 28px", fontSize: 14, color: DS.textSecondary, lineHeight: 1.6 }}>
                Your password has been updated. You can now sign in with your new credentials.
              </p>
              <PrimaryButton onClick={onGoLogin}>
                Sign in now <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </PrimaryButton>
            </div>
          )}
        </div>

        {/* Back to login */}
        {!done && (
          <div style={{ textAlign: "center", marginTop: 20 }}>
            <button
              type="button"
              onClick={onGoLogin}
              style={{ background: "none", border: "none", cursor: "pointer", color: DS.textMuted, fontSize: 13, fontFamily: DS.fontSans, display: "inline-flex", alignItems: "center", gap: 6, padding: 0, transition: "color 0.15s" }}
              onMouseEnter={(e) => (e.currentTarget.style.color = DS.textSecondary)}
              onMouseLeave={(e) => (e.currentTarget.style.color = DS.textMuted)}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
              Back to Sign In
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// FULL-PAGE LOADER (shown while checking localStorage token)
// ─────────────────────────────────────────────────────────────────────────────

function AppLoader() {
  return (
    <div style={{ minHeight: "100vh", background: DS.pageBg, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: DS.fontSans }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
        <div style={{ width: 44, height: 44, borderRadius: 12, background: `linear-gradient(135deg, ${DS.indigoDeep}, ${DS.indigoLight})`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: `0 4px 18px ${DS.indigoGlow}` }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8" strokeLinecap="round" style={{ animation: "ia-spin 0.9s linear infinite" }}>
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
        </div>
        <p style={{ margin: 0, color: DS.textMuted, fontSize: 13 }}>Loading InstaAgent…</p>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ROOT PAGE — router for the entire auth flow
// ─────────────────────────────────────────────────────────────────────────────

export default function Home() {
  // "login" | "register" | "forgot-password" | "app"
  const [page, setPage]   = useState("loading");
  const [user, setUser]   = useState(null);
  const [token, setToken] = useState(null);

  useEffect(() => {
    const savedToken = localStorage.getItem("ia_token");
    const savedUser  = localStorage.getItem("ia_user");
    if (savedToken && savedUser) {
      try {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
        setPage("app");
      } catch {
        localStorage.removeItem("ia_token");
        localStorage.removeItem("ia_user");
        setPage("login");
      }
    } else {
      setPage("login");
    }
  }, []);

  function handleAuthSuccess(userData, userToken) {
    setUser(userData);
    setToken(userToken);
    setPage("app");
  }

  function handleLogout() {
    localStorage.removeItem("ia_token");
    localStorage.removeItem("ia_user");
    setUser(null);
    setToken(null);
    setPage("login");
  }

  if (page === "loading") return <AppLoader />;

  if (page === "app") {
    return <InstaAgent user={user} token={token} onLogout={handleLogout} />;
  }

  if (page === "register") {
    return (
      <RegisterPage
        onSuccess={handleAuthSuccess}
        onGoLogin={() => setPage("login")}
      />
    );
  }

  if (page === "forgot-password") {
    return (
      <ForgotPasswordPage
        onGoLogin={() => setPage("login")}
      />
    );
  }

  // Default: login
  return (
    <LoginPage
      onSuccess={handleAuthSuccess}
      onGoRegister={() => setPage("register")}
      onGoForgot={() => setPage("forgot-password")}
    />
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// GLOBAL STYLES
// Injected as a style tag via Next.js _app or directly here
// ─────────────────────────────────────────────────────────────────────────────

if (typeof window !== "undefined") {
  const styleId = "ia-global-styles";
  if (!document.getElementById(styleId)) {
    const style = document.createElement("style");
    style.id = styleId;
    style.textContent = `
      @import url('https://fonts.googleapis.com/css2?family=Sora:wght@700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@700&display=swap');

      *, *::before, *::after { box-sizing: border-box; }
      body { margin: 0; padding: 0; }

      @keyframes ia-spin {
        from { transform: rotate(0deg); }
        to   { transform: rotate(360deg); }
      }

      input::placeholder { color: #2E3D55; }
      select option       { background: #0F1A2E; color: #F1F5FC; }

      input:-webkit-autofill,
      input:-webkit-autofill:hover,
      input:-webkit-autofill:focus {
        -webkit-box-shadow: 0 0 0 100px #0C1525 inset !important;
        -webkit-text-fill-color: #F1F5FC !important;
        caret-color: #F1F5FC;
      }

      a { color: inherit; }
      button { font-family: inherit; }

      ::-webkit-scrollbar       { width: 6px; }
      ::-webkit-scrollbar-track { background: transparent; }
      ::-webkit-scrollbar-thumb { background: #1E2D45; border-radius: 3px; }
    `;
    document.head.appendChild(style);
  }
}