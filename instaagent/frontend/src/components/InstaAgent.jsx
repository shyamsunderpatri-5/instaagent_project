// frontend/src/components/InstaAgent.jsx
import React, { useState, useEffect, useCallback } from "react";
import { T, I, GlobalStyles, Spinner, useToast, FeatureCtx, LangCtx, makeLangValue } from "./common/UIComponents";

import { api } from "./common/api";
import { Sidebar } from "./layout/Sidebar";
import { DashboardView } from "./views/DashboardView";
import { CreatePostView } from "./views/CreatePostView";
import { PostsView } from "./views/MyPostsView";
import { AnalyticsView } from "./views/AnalyticsView";
import { BillingView } from "./views/BillingView";
import { AdminView } from "./views/AdminView";
import { SettingsView } from "./views/SettingsView";
import { TelegramView } from "./views/TelegramBotView";

import { OnboardingWizard } from "./views/OnboardingWizard";

export function InstaAgent() {
  const [view,    setView]    = useState("dashboard");
  const [user,    setUser]    = useState(null);
  const [usage,   setUsage]   = useState(null);
  const [features,setFeatures]= useState({});
  const [token,   setToken]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [authForm,setAuthForm]= useState({ email: "", password: "", isLogin: true });
  // Language state — initialized from localStorage or user profile
  const [lang, setLangState] = useState(() => (
    typeof window !== "undefined" ? (localStorage.getItem("ia_lang") || "hi") : "hi"
  ));
  const setLang = (l) => { setLangState(l); if (typeof window !== "undefined") localStorage.setItem("ia_lang", l); };
  const langValue = makeLangValue(lang, setLang);
  const { show, Toast } = useToast();

  const needsOnboarding = user && (!user.instagram_username || !user.whatsapp_phone);


  const fetchBase = useCallback(async (tk) => {
    try {
        const timeout = new Promise((_, reject) =>
            setTimeout(() => reject(new Error("timeout")), 15000)
        );
        const [u, us, f] = await Promise.race([
            Promise.all([
                api.get("/api/v1/auth/me", tk),
                api.get("/api/v1/usage", tk),
                api.get("/api/v1/features", tk),
            ]),
            timeout,
        ]);
        setUser(u);
        setUsage(us);
        setFeatures(f);
    } catch (err) {
        const msg = err.message || "";
        if (msg === "timeout") {
            show("Connection timed out. Check your backend.", "error");
        } else {
            show("Session expired. Please sign in again.", "error");
            setToken(null);
            setUser(null);
            localStorage.removeItem("ia_token");
        }
    } finally {
        setLoading(false);
    }
  }, [show]);

  useEffect(() => {
    const saved = localStorage.getItem("ia_token");
    if (saved) {
        setToken(saved);
        fetchBase(saved);
    } else {
        setLoading(false);
    }
  }, [fetchBase]);

  // Sync language from user profile when loaded
  useEffect(() => {
    if (user?.language && user.language !== lang) {
      setLang(user.language);
    }
  }, [user?.language]);



  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
        const path = authForm.isLogin ? "/api/v1/auth/login" : "/api/v1/auth/register";
        const body = authForm.isLogin 
            ? { email: authForm.email, password: authForm.password } 
            : { email: authForm.email, password: authForm.password, full_name: "New Seller" };
        
        const res = await api.post(path, body);
        const tk = res.token || res.access_token;
        setToken(tk);
        localStorage.setItem("ia_token", tk);
        await fetchBase(tk);
        show(authForm.isLogin ? "Welcome back!" : "Account created!");
    } catch (err) {
        show(err.message, "error");
    } finally {
        setLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("ia_token");
    show("Logged out successfully");
  };

  if (loading) {
    return (
        <div style={{ height: "100vh", background: T.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Spinner size={32} />
        </div>
    );
  }

  // Auth Screen
  if (!token) {
    return (
      <div style={{ height: "100vh", background: T.bg, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
        {Toast}
        <GlobalStyles />
        <div className="fade-up" style={{ width: "100%", maxWidth: 400, background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 32, boxShadow: "0 20px 60px rgba(0,0,0,.5)" }}>
           <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 32, justifyContent: "center" }}>
              <div style={{ width: 44, height: 44, background: `linear-gradient(135deg, ${T.primary}, ${T.accent})`, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center" }}>{I.ig}</div>
              <h1 style={{ fontFamily: T.fontHead, fontSize: 24, fontWeight: 800, color: T.text }}>InstaAgent</h1>
           </div>

           <h2 style={{ fontSize: 18, fontWeight: 700, color: T.text, marginBottom: 8, textAlign: "center" }}>{authForm.isLogin ? "Seller Login" : "Join InstaAgent"}</h2>
           <p style={{ fontSize: 13, color: T.textMuted, marginBottom: 24, textAlign: "center" }}>Enterprise-grade Instagram Automation</p>

           <form onSubmit={handleAuth}>
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, display: "block", marginBottom: 6, textTransform: "uppercase" }}>Email Address</label>
                <input type="email" required value={authForm.email} onChange={e => setAuthForm({...authForm, email: e.target.value})} placeholder="seller@example.com" style={{ width: "100%", padding: 12, borderRadius: 10, border: `1px solid ${T.border}`, background: T.surfaceAlt, color: T.text, fontSize: 14 }} />
              </div>
              <div style={{ marginBottom: 24 }}>
                <label style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, display: "block", marginBottom: 6, textTransform: "uppercase" }}>Password</label>
                <input type="password" required value={authForm.password} onChange={e => setAuthForm({...authForm, password: e.target.value})} placeholder="••••••••" style={{ width: "100%", padding: 12, borderRadius: 10, border: `1px solid ${T.border}`, background: T.surfaceAlt, color: T.text, fontSize: 14 }} />
              </div>
              <button disabled={loading} style={{ width: "100%", padding: 14, background: T.primary, color: "#fff", border: "none", borderRadius: 12, fontWeight: 700, cursor: "pointer", fontSize: 15, display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                 {loading ? <Spinner size={18} color="#fff" /> : authForm.isLogin ? "Sign In" : "Create Account"}
              </button>
           </form>
           
           <div style={{ marginTop: 20, textAlign: "center" }}>
              <button onClick={() => setAuthForm({...authForm, isLogin: !authForm.isLogin})} style={{ background: "transparent", border: "none", color: T.primary, fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
                {authForm.isLogin ? "Don't have an account? Sign Up" : "Already have an account? Sign In"}
              </button>
           </div>
        </div>
      </div>
    );
  }

  // Onboarding Wizard
  if (needsOnboarding) {
    return (
      <OnboardingWizard 
        user={user} 
        token={token} 
        onUserUpdate={setUser}
        onComplete={() => fetchBase(token)} 
      />
    );
  }

  // Dashboard Context Provider and Layout
  return (
    <LangCtx.Provider value={langValue}>
    <FeatureCtx.Provider value={{ features: features.features || {}, trialPosts: features.free_trial_posts || 5, botUsername: features.telegram_bot_username || "InstaAgent_bot" }}>
        <GlobalStyles />
        <div style={{ display: "flex", minHeight: "100vh" }}>
            <Sidebar active={view} setActive={setView} user={user} usage={usage} onLogout={logout} loading={loading} />
            <main style={{ flex: 1, position: "relative" }}>
                 {loading && <div style={{ position: "fixed", top: 20, right: 32, zIndex: 50 }}><Spinner size={20} /></div>}
                 
                 <div className="slide-in" key={view}>
                    {view === "dashboard" && <DashboardView setActive={setView} user={user} usage={usage} token={token} />}
                    {view === "create"    && <CreatePostView user={user} token={token} onPostCreated={() => { fetchBase(token); setView("posts"); }} />}
                    {view === "posts"     && <PostsView token={token} />}
                    {view === "analytics" && <AnalyticsView token={token} />}
                    {view === "billing"   && <BillingView user={user} usage={usage} token={token} />}
                    {view === "admin"     && <AdminView token={token} user={user} />}
                    {view === "settings"  && <SettingsView user={user} token={token} onUserUpdate={(u) => { setUser(u); fetchBase(token); }} />}
                    {view === "telegram"  && <TelegramView user={user} />}
                 </div>
            </main>
        </div>
        {Toast}
    </FeatureCtx.Provider>
    </LangCtx.Provider>
  );
}


export default InstaAgent;
