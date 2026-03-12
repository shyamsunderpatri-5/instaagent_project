// frontend/src/components/common/UIComponents.jsx
import { useState, useCallback, createContext, useContext } from "react";


// ─── DESIGN TOKENS ───────────────────────────────────────────────────────────
export const T = {
  // Midnight Slate Palette
  bg:          "#0B0E14", // Deep dark background
  surface:     "#12161F", // Main panels
  surfaceAlt:  "#1A202C", // Secondary surfaces/inputs
  border:      "#2D3748", // Subtle borders
  borderLight: "#4A5568", // Visible separators
  
  // Brand & Accents
  primary:     "#6366F1", // Indigo
  primaryDim:  "rgba(99,102,241,0.12)",
  primaryGlow: "rgba(99,102,241,0.25)",
  accent:      "#F43F5E", // Rose/Soft Red
  accentDim:   "rgba(244,63,94,0.12)",
  
  // States
  gold:        "#F59E0B", // Amber/Gold
  goldDim:     "rgba(245,158,11,0.10)",
  green:       "#10B981", // Emerald
  greenDim:    "rgba(16,185,129,0.10)",
  red:         "#EF4444", 
  redDim:      "rgba(239,68,68,0.10)",
  blue:        "#3B82F6",
  
  // Text
  text:        "#F8FAFC", // High contrast text
  textMuted:   "#94A3B8", // Secondary text
  textDim:     "#475569", // Disabled/Meta text
  
  // Typography
  fontHead:    "'Plus Jakarta Sans', system-ui, sans-serif",
  fontBody:    "'Inter', system-ui, sans-serif",
  fontDevan:   "'Noto Sans Devanagari', system-ui, sans-serif",
  fontMono:    "'JetBrains Mono', monospace",
};

// ─── GLOBAL STYLES ────────────────────────────────────────────────────────────
export const GlobalStyles = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600&family=Noto+Sans+Devanagari:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    body{background:${T.bg};color:${T.text};font-family:${T.fontBody};-webkit-font-smoothing:antialiased;overflow-x:hidden}
    ::-webkit-scrollbar{width:4px;height:4px}
    ::-webkit-scrollbar-track{background:transparent}
    ::-webkit-scrollbar-thumb{background:${T.border};border-radius:2px}
    @keyframes fadeUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
    @keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:.45}}
    @keyframes shimmer{0%{background-position:-600px 0}100%{background-position:600px 0}}
    @keyframes slideIn{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:translateX(0)}}
    .fade-up{animation:fadeUp .45s ease both}
    .slide-in{animation:slideIn .3s ease both}
    .shimmer{background:linear-gradient(90deg,${T.surface} 25%,${T.surfaceAlt} 50%,${T.surface} 75%);background-size:600px 100%;animation:shimmer 1.5s infinite}
    input,select,textarea{font-family:${T.fontBody}}
    button{font-family:${T.fontBody}}
  `}</style>
);

// ─── MINI ICONS ──────────────────────────────────────────────────────────────
export const I = {
  dash:     <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>,
  create:   <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>,
  posts:    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>,
  analytics:<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>,
  billing:  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>,
  settings: <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>,
  telegram: <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M11.944 0A12 12 0 1 0 12 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>,
  ig:       <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/></svg>,
  logout:   <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>,
  check:    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>,
  alert:    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
  link:     <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>,
  refresh:  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>,
  copy:     <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>,
  star:     <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>,
  upload:   <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>,
  trend:    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>,
  zap:      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>,
  heart:    <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>,
  eye:      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>,
  chat:     <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>,
  clock:    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  globe:    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>,
  aggregator:<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="2" y="2" width="20" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="8"/><path d="M7 12h10"/></svg>,
};

// ─── UTILITY COMPONENTS ───────────────────────────────────────────────────────
export const Spinner = ({ size = 16, color = T.primary }) => (
  <div style={{ width: size, height: size, border: `2px solid ${color}33`, borderTopColor: color, borderRadius: "50%", animation: "spin .75s linear infinite", flexShrink: 0 }} />
);

export const Badge = ({ status }) => {
  const map = {
    posted:     { c: T.green, l: "Posted" },
    scheduled:  { c: T.gold,  l: "Scheduled" },
    ready:      { c: T.primary, l: "Ready" },
    processing: { c: T.blue,  l: "Processing" },
    failed:     { c: T.red,   l: "Failed" },
    free:       { c: T.textMuted, l: "Free" },
    starter:    { c: T.green, l: "Starter" },
    growth:     { c: T.primary, l: "Growth" },
    agency:     { c: T.accent, l: "Agency" },
    active:     { c: T.green, l: "Active" },
    cancelled:  { c: T.red,   l: "Cancelled" },
    trialing:   { c: T.gold,  l: "Trial" },
  }[status] || { c: T.textMuted, l: status || "—" };
  return <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: ".06em", textTransform: "uppercase", color: map.c, background: `${map.c}18`, padding: "3px 9px", borderRadius: 20 }}>{map.l}</span>;
};

export const StatCard = ({ label, value, sub, icon, color = T.primary, delay = 0, loading }) => (
  <div className="fade-up" style={{ animationDelay: `${delay}ms`, background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: "20px 22px", position: "relative", overflow: "hidden" }}>
    <div style={{ position: "absolute", top: 0, right: 0, width: 70, height: 70, background: `radial-gradient(circle at 100% 0%, ${color}20, transparent 70%)`, borderRadius: "0 16px 0 100%" }} />
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
      <span style={{ fontSize: 11, color: T.textMuted, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".07em" }}>{label}</span>
      <span style={{ color, opacity: .75 }}>{icon}</span>
    </div>
    {loading
      ? <div className="shimmer" style={{ height: 28, borderRadius: 6, width: "60%" }} />
      : <div style={{ fontSize: 26, fontWeight: 800, fontFamily: T.fontHead, color: T.text, lineHeight: 1 }}>{value ?? "—"}</div>
    }
    {sub && <div style={{ fontSize: 11, color: T.textMuted, marginTop: 6 }}>{sub}</div>}
  </div>
);

export const Toggle = ({ value, onChange }) => (
  <div onClick={() => onChange(!value)} style={{ width: 42, height: 22, background: value ? T.primary : T.border, borderRadius: 11, cursor: "pointer", position: "relative", transition: "background .2s", flexShrink: 0 }}>
    <div style={{ width: 16, height: 16, background: "white", borderRadius: "50%", position: "absolute", top: 3, left: value ? 23 : 3, transition: "left .2s", boxShadow: "0 1px 4px rgba(0,0,0,.3)" }} />
  </div>
);

export function useToast() {
  const [toast, setToast] = useState(null);
  const show = useCallback((msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3200);
  }, []);
  const Toast = toast ? (
    <div style={{ position: "fixed", bottom: 28, right: 28, zIndex: 1000, background: toast.type === "error" ? T.red : T.green, color: "#fff", padding: "12px 20px", borderRadius: 12, fontSize: 14, fontWeight: 600, boxShadow: "0 8px 32px rgba(0,0,0,.4)", display: "flex", alignItems: "center", gap: 8, animation: "fadeUp .3s ease" }}>
      {toast.type === "error" ? I.alert : I.check} {toast.msg}
    </div>
  ) : null;
  return { show, Toast };
}

// ─── LANGUAGE CONTEXT ──────────────────────────────────────────────────────
const TRANSLATIONS = {
  en: {
    dashboard: "Dashboard", create: "Create Post", posts: "My Posts",
    analytics: "Analytics", billing: "Billing", telegram: "Telegram Bot",
    admin: "Admin Panel", settings: "Settings", logout: "Sign Out",
    menu: "Menu", monthly_usage: "Monthly Usage", aggregator: "Aggregator",
    "aggregator.title": "Market Intelligence",
    "aggregator.subtitle": "Aggregator",
    "aggregator.add_account": "Add Account",
    "aggregator.tracked_accounts": "Tracked Accounts",
    "aggregator.generate_insights": "Generate AI Insights",
    "aggregator.ai_strategy": "Claude Strategy",
    "aggregator.post_ideas": "Post Ideas",
    "aggregator.market_trends": "Market Trends",
    "aggregator.feed_title": "Competitive Feed",
    "aggregator.type_owned": "Owned",
    "aggregator.type_competitor": "Competitor",
    "aggregator.type_owned_full": "Owned Account",
    "aggregator.type_competitor_full": "Competitor Account",
    "aggregator.account_type": "Account Type",
    "aggregator.synced": "Synced",
    "aggregator.syncing": "Pending",
    "aggregator.no_accounts": "No accounts yet. Add one to get started.",
    "aggregator.fetching_data": "Fetching competitor data...",
    "aggregator.sync_pending_banner": "Syncing posts in background — takes ~30 seconds",
    "aggregator.account_added_msg": "Account added! Data will sync shortly.",
    "aggregator.insights_generated_msg": "AI Insights generated!",
    "aggregator.add_modal_title": "Add Instagram Account",
    "aggregator.add_modal_desc": "Enter the username of a competitor or your own account to track.",
    "aggregator.ig_username": "Instagram Username",
    "aggregator.track_btn": "Start Tracking",
    "common.cancel": "Cancel",
  },
  hi: {
    dashboard: "डैशबोर्ड", create: "पोस्ट बनाएं", posts: "मेरे पोस्ट",
    analytics: "विश्लेषण", billing: "बिलिंग", telegram: "टेलीग्राम बॉट",
    admin: "एडमिन पैनल", settings: "सेटिंग्स", logout: "लॉग आउट",
    menu: "मेन्यू", monthly_usage: "मासिक उपयोग", aggregator: "एग्रीगेटर",
    "aggregator.title": "मार्केट इंटेलिजेंस",
    "aggregator.subtitle": "एग्रीगेटर",
    "aggregator.add_account": "खाता जोड़ें",
    "aggregator.tracked_accounts": "ट्रैक किए गए खाते",
    "aggregator.generate_insights": "AI Insights जनरेट करें",
    "aggregator.ai_strategy": "Claude रणनीति",
    "aggregator.post_ideas": "पोस्ट विचार",
    "aggregator.market_trends": "मार्केट ट्रेंड्स",
    "aggregator.feed_title": "कॉम्पिटिटिव फीड",
    "aggregator.type_owned": "निजी",
    "aggregator.type_competitor": "प्रतिद्वंद्वी",
    "aggregator.type_owned_full": "निजी खाता",
    "aggregator.type_competitor_full": "प्रतिद्वंद्वी खाता",
    "aggregator.account_type": "खाते का प्रकार",
    "aggregator.synced": "सिंक हुआ",
    "aggregator.syncing": "लंबित",
    "aggregator.no_accounts": "अभी तक कोई खाता नहीं है। शुरू करने के लिए एक जोड़ें।",
    "aggregator.fetching_data": "प्रतिद्वंद्वी डेटा प्राप्त किया जा रहा है...",
    "aggregator.sync_pending_banner": "बैकग्राउंड में पोस्ट सिंक हो रहे हैं — इसमें ~30 सेकंड लगते हैं",
    "aggregator.account_added_msg": "खाता जोड़ दिया गया है! डेटा जल्द ही सिंक हो जाएगा।",
    "aggregator.insights_generated_msg": "AI Insights जनरेट हो गए हैं!",
    "aggregator.add_modal_title": "इंस्टाग्राम खाता जोड़ें",
    "aggregator.add_modal_desc": "ट्रैक करने के लिए प्रतिद्वंद्वी या अपने खाते का यूजरनेम दर्ज करें।",
    "aggregator.ig_username": "इंस्टाग्राम यूजरनेम",
    "aggregator.track_btn": "ट्रैकिंग शुरू करें",
    "common.cancel": "रद्द करें",
  },
  te: {
    dashboard: "డ్యాష్‌బోర్డ్", create: "పోస్ట్ చేయండి", posts: "నా పోస్ట్లు",
    analytics: "విశ్లేషణ", billing: "చెల్లింపు", telegram: "టెలిగ్రామ్ బాట్",
    admin: "అడ్మిన్ ప్యానల్", settings: "సెట్టింగ్స్", logout: "లాగ్ అవుట్",
    menu: "మెనూయు", monthly_usage: "నెలవారీ వినియోగం", aggregator: "అగ్రిగేటర్",
    "aggregator.title": "మార్కెట్ ఇంటెలిజెన్స్",
    "aggregator.subtitle": "అగ్రిగేటర్",
    "aggregator.add_account": "ఖాతాను జోడించండి",
    "aggregator.tracked_accounts": "ట్రాక్ చేయబడిన ఖాతాలు",
    "aggregator.generate_insights": "AI Insights సృష్టించండి",
    "aggregator.ai_strategy": "Claude వ్యూహం",
    "aggregator.post_ideas": "పోస్ట్ ఆలోచనలు",
    "aggregator.market_trends": "మార్కెట్ ట్రెండ్స్",
    "aggregator.feed_title": "కాంపిటిటివ్ ఫీడ్",
    "aggregator.type_owned": "స్వంత",
    "aggregator.type_competitor": "పోటీదారు",
    "aggregator.type_owned_full": "స్వంత ఖాతా",
    "aggregator.type_competitor_full": "పోటీదారి ఖాతా",
    "aggregator.account_type": "ఖాతా రకం",
    "aggregator.synced": "సింక్ అయింది",
    "aggregator.syncing": "పెండింగ్",
    "aggregator.no_accounts": "ఇంకా ఖాతాలు లేవు. ప్రారంభించడానికి ఒకటి జోడించండి.",
    "aggregator.fetching_data": "పోటీదారుల డేటా సేకరించబడుతోంది...",
    "aggregator.sync_pending_banner": "పోస్ట్లు బ్యాక్‌గ్రౌండ్‌లో సింక్ అవుతున్నాయి — దీనికి ~30 సెకన్లు పడుతుంది",
    "aggregator.account_added_msg": "ఖాతా జోడించబడింది! డేటా త్వరలోనే సింక్ అవుతుంది.",
    "aggregator.insights_generated_msg": "AI Insights సృష్టించబడ్డాయి!",
    "aggregator.add_modal_title": "ఇన్‌స్టాగ్రామ్ ఖాతాను జోడించండి",
    "aggregator.add_modal_desc": "ట్రాక్ చేయడానికి పోటీదారు లేదా మీ స్వంత ఖాతా యూజర్‌నేమ్ నమోదు చేయండి.",
    "aggregator.ig_username": "ఇన్‌స్టాగ్రామ్ యూజర్‌నేమ్",
    "aggregator.track_btn": "ట్రాకింగ్ ప్రారంభించండి",
    "common.cancel": "రద్దు చేయండి",
  },
  ta: {
    dashboard: "டாஷ்போர்ட்", create: "போஸ்ட் உருவாக்கு", posts: "என் போஸ்டுகள்",
    analytics: "பகுப்பாய்வு", billing: "பில்லிங்", telegram: "டெலிகிராம் போட்",
    admin: "அட்மின் பலகை", settings: "அமைப்புகள்", logout: "வெளியேறு",
    menu: "மெனு", monthly_usage: "மாத பயன்பாடு", aggregator: "அகிரிகேட்டர்",
    "aggregator.title": "சந்தை நுண்ணறிவு",
    "aggregator.subtitle": "அகிரிகேட்டர்",
    "aggregator.add_account": "கணக்கைச் சேர்",
    "aggregator.tracked_accounts": "கண்காணிக்கப்படும் கணக்குகள்",
    "aggregator.generate_insights": "AI Insights உருவாக்கு",
    "aggregator.ai_strategy": "Claude வயூகம்",
    "aggregator.post_ideas": "போஸ்ட் சிந்தனைகள்",
    "aggregator.market_trends": "சந்தை யுக்திகள்",
    "aggregator.feed_title": "போட்டி பீட்",
    "aggregator.type_owned": "சொந்த",
    "aggregator.type_competitor": "போட்டியாளர்",
    "aggregator.type_owned_full": "சொந்த கணக்கு",
    "aggregator.type_competitor_full": "போட்டியாளர் கணக்கு",
    "aggregator.account_type": "கணக்கு வகை",
    "aggregator.synced": "சிங்க் செய்யப்பட்டது",
    "aggregator.syncing": "நிலுவை",
    "aggregator.no_accounts": "இன்னும் கணக்குகள் இல்லை. உருவாக்க ஒன்றைச் சேர்க்கவும்.",
    "aggregator.fetching_data": "போட்டியாளர் தரவு பெறப்படுகிறது...",
    "aggregator.sync_pending_banner": "போஸ்டுகள் பின்னணியில் சிங்க் செய்யப்படுகின்றன — இதற்கு ~30 வினாடிகள் ஆகும்",
    "aggregator.account_added_msg": "கணக்கு சேர்க்கப்பட்டது! தகவல்கள் விரைவில் சிங்க் செய்யப்படும்",
    "aggregator.insights_generated_msg": "AI Insights உருவாக்கப்பட்டது!",
    "aggregator.add_modal_title": "இன்ஸ்டாகிராம் கணக்கைச் சேர்",
    "aggregator.add_modal_desc": "கண்காணிக்க போட்டியாளர் அல்லது உங்கள் சொந்த கணக்கின் பயனர் பெயரை உள்ளிடவும்.",
    "aggregator.ig_username": "இன்ஸ்டாகிராம் பயனர் பெயர்",
    "aggregator.track_btn": "கண்காணிக்கத் தொடங்கு",
    "common.cancel": "ரத்து",
  },
  kn: {
    dashboard: "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", create: "ಪೋಸ್ಟ್ ಮಾಡಿ", posts: "ನನ್ನ ಪೋಸ್ಟ್‌ಗಳು",
    analytics: "ವಿಶ್ಲೇಷಣೆ", billing: "ಬಿಲಿಂಗ್", telegram: "ಟೆಲಿಗ್ರಾಮ್ ಬೋಟ್",
    admin: "ಅಡ್ಮಿನ್ ಪ್ಯಾನಲ್", settings: "ಸೆಟ್ಟಿಂಗ್ಸ್", logout: "ಲಾಗ್ ಔಟ್",
    menu: "ಮೆನು", monthly_usage: "ಮಾಸಿಕ ಬಳಕೆ", aggregator: "ಅಗ್ರಿವೇಟರ್",
    "aggregator.title": "ಮಾರುಕಟ್ಟೆ ಬುದ್ಧಿವಂತಿಕೆ",
    "aggregator.subtitle": "ಅಗ್ರಿವೇಟರ್",
    "aggregator.add_account": "ಖಾತೆಯನ್ನು ಸೇರಿಸಿ",
    "aggregator.tracked_accounts": "ಟ್ರ್ಯಾಕ್ ಮಾಡಲಾದ ಖಾತೆಗಳು",
    "aggregator.generate_insights": "AI Insights ಮಾಡಿ",
    "aggregator.ai_strategy": "Claude ಯುಕ್ತಿ",
    "aggregator.post_ideas": "ಪೋಸ್ಟ್ ಐಡಿಯಾಗಳು",
    "aggregator.market_trends": "ಮಾರುಕಟ್ಟೆ ಪ್ರವೃತ್ತಿಗಳು",
    "aggregator.feed_title": "ಸ್ಪರ್ಧಾತ್ಮಕ ಫೀಡ್",
    "aggregator.type_owned": "ಸ್ವಂತ",
    "aggregator.type_competitor": "ಸ್ಪರ್ಧಿ",
    "aggregator.type_owned_full": "ಸ್ವಂತ ಖಾತೆ",
    "aggregator.type_competitor_full": "ಸ್ಪರ್ಧಿಯ ಖಾತೆ",
    "aggregator.account_type": "ಖಾತೆ ವಿಧ",
    "aggregator.synced": "ಸಿಂಕ್ ಆಗಿದೆ",
    "aggregator.syncing": "ಬಾಕಿ",
    "aggregator.no_accounts": "ಇನ್ನೂ ಯಾವುದೇ ಖಾತೆಗಳಿಲ್ಲ. ಪ್ರಾರಂಭಿಸಲು ಒಂದನ್ನು ಸೇರಿಸಿ.",
    "aggregator.fetching_data": "ಸ್ಪರ್ಧಿಯ ಡೇಟಾ ಪಡೆಯಲಾಗುತ್ತಿದೆ...",
    "aggregator.sync_pending_banner": "ಪೋಸ್ಟ್‌ಗಳು ಹಿನ್ನೆಲೆಯಲ್ಲಿ ಸಿಂಕ್ ಆಗುತ್ತಿವೆ - ಇದಕ್ಕೆ ~30 ಸೆಕೆಂಡ್‌ಗಳು ಬೇಕು",
    "aggregator.account_added_msg": "ಖಾತೆಯನ್ನು ಸೇರಿಸಲಾಗಿದೆ! ಡೇಟಾ ವೇಗದಲ್ಲಿ ಸಿಂಕ್ ಆಗುತ್ತಿದೆ.",
    "aggregator.insights_generated_msg": "AI Insights ಮಾಡಲಾಗಿದೆ!",
    "aggregator.add_modal_title": "ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್ ಖಾತೆಯನ್ನು ಸೇರಿಸಿ",
    "aggregator.add_modal_desc": "ಟ್ರ್ಯಾಕ್ ಮಾಡಲು ಸ್ಪರ್ಧಿ ಅಥವಾ ನಿಮ್ಮ ಸ್ವಂತ ಖಾತೆಯ ಬಳಕೆದಾರ ಹೆಸರನ್ನು ನಮೂದಿಸಿ.",
    "aggregator.ig_username": "ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್ ಬಳಕೆದಾರ ಹೆಸರು",
    "aggregator.track_btn": "ಟ್ರ್ಯಾಕಿಂಗ್ ಪ್ರಾರಂಭಿಸಿ",
    "common.cancel": "ರದ್ದು ಮಾಡಿ",
  },
  mr: {
    dashboard: "डॅशबोर्ड", create: "पोस्ट तयार करा", posts: "माझे पोस्ट",
    analytics: "विश्लेषण", billing: "बिलिंग", telegram: "टेलिग्राम बॉट",
    admin: "अडमिन पॅनल", settings: "सेटिग्स", logout: "लॉग आऊट",
    menu: "मेनू", monthly_usage: "मासिक वापर", aggregator: "ॲग्रिगेटर",
    "aggregator.title": "मार्केट इंटेलिजेंस",
    "aggregator.subtitle": "ॲग्रिगेटर",
    "aggregator.add_account": "खाते जोडा",
    "aggregator.tracked_accounts": "ट्रॅक केलेले खाते",
    "aggregator.generate_insights": "AI Insights तयार करा",
    "aggregator.ai_strategy": "Claude व्यूह",
    "aggregator.post_ideas": "पोस्ट आयडिया",
    "aggregator.market_trends": "मार्केट ट्रेंड्स",
    "aggregator.feed_title": "स्पर्धात्मक फीड",
    "aggregator.type_owned": "स्वतःचे",
    "aggregator.type_competitor": "स्पर्धक",
    "aggregator.type_owned_full": "स्वतःचे खाते",
    "aggregator.type_competitor_full": "स्पर्धकाचे खाते",
    "aggregator.account_type": "खात्याचा प्रकार",
    "aggregator.synced": "सिंक झाले",
    "aggregator.syncing": "पेंडिंग",
    "aggregator.no_accounts": "कोणतेही खाते नाहीत. सुरु करण्यासाठी एक जोडा.",
    "aggregator.fetching_data": "स्पर्धकाचा डेटा मिळवत आहे...",
    "aggregator.sync_pending_banner": "बॅकग्राउंडमध्ये पोस्ट सिंक होत आहेत — याला ~30 सेकंद लागतील",
    "aggregator.account_added_msg": "खाते जोडले गेले आहे! डेटा लवकरच सिंक होईल.",
    "aggregator.insights_generated_msg": "AI Insights तयार झाले आहेत!",
    "aggregator.add_modal_title": "इंस्टाग्राम खाते जोडा",
    "aggregator.add_modal_desc": "ट्रॅक करण्यासाठी स्पर्धक किंवा स्वतःच्या खात्याचे युजरनेम टाका.",
    "aggregator.ig_username": "इंस्टाग्राम युजरनेम",
    "aggregator.track_btn": "ट्रॅकिंग सुरू करा",
    "common.cancel": "रद्द करा",
  },
};

export const LangCtx = createContext({ lang: "en", t: (k) => k, setLang: () => {} });
export const useLang = () => useContext(LangCtx);

export function makeLangValue(lang, setLang) {
  const t = (key) => TRANSLATIONS[lang]?.[key] || TRANSLATIONS["en"][key] || key;
  return { lang, t, setLang };
}

// ─── FEATURE FLAG CONTEXT ────────────────────────────────────────────────────
export const FeatureCtx = createContext({ features: {}, trialPosts: 5, botUsername: "InstaAgent_bot" });
export const useFeatures = () => useContext(FeatureCtx);
