// frontend/src/components/InstaAgent.jsx
import React, { useState, useEffect, useCallback } from "react";
import { T, I, GlobalStyles, Spinner, useToast, FeatureCtx, LangCtx, makeLangValue, useLang } from "./common/UIComponents";

import { api } from "./common/api";
import { Sidebar } from "./layout/Sidebar";
import { Header } from "./layout/Header";
import { DashboardView } from "./views/DashboardView";
import { CreatePostView } from "./views/CreatePostView";
import { PostsView } from "./views/MyPostsView";
import { AnalyticsView } from "./views/AnalyticsView";
import { BillingView } from "./views/BillingView";
import { AdminView } from "./views/AdminView";
import { SettingsView } from "./views/SettingsView";
import { TelegramView } from "./views/TelegramBotView";
import { AggregatorView } from "./views/AggregatorView";
import { AdminAggregatorView } from "./views/AdminAggregatorView";

import { OnboardingView } from "./views/OnboardingView";
import { LanguageProvider } from "./common/LanguageContext";
import ErrorBoundary from "./common/ErrorBoundary";

export function InstaAgent() {
  return (
    <ErrorBoundary>
      <InstaAgentContent />
    </ErrorBoundary>
  );
}

function InstaAgentContent() {
  const [view,    setView]    = useState("dashboard");
  const [user,    setUser]    = useState(null);
  const [usage,   setUsage]   = useState(null);
  const [features,setFeatures]= useState({});
  const [token,   setToken]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [authForm,setAuthForm]= useState({ email: "", password: "", full_name: "", isLogin: true });
  
  const { show, Toast } = useToast();

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
            show(err.message || "Session expired. Please sign in again.", "error");
            setToken(null);
            setUser(null);
            localStorage.removeItem("ia_token");
            return false;
        }
    } finally {
        setLoading(false);
    }
    return true;
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

  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
        if (!authForm.isLogin && !authForm.full_name.trim()) {
            show("Please enter your name", "error");
            return;
        }
        const path = authForm.isLogin ? "/api/v1/auth/login" : "/api/v1/auth/register";
        const body = authForm.isLogin 
            ? { email: authForm.email, password: authForm.password } 
            : { email: authForm.email, password: authForm.password, full_name: authForm.full_name };
        
        const res = await api.post(path, body);
        const tk = res.token || res.access_token;
        setToken(tk);
        localStorage.setItem("ia_token", tk);
        const success = await fetchBase(tk);
        if (success) {
            show(authForm.isLogin ? "Welcome back!" : "Account created!");
        }
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

  return (
    <LanguageProvider user={user} token={token} onUserUpdate={setUser}>
      <InstaAgentProviderShell 
        view={view} setView={setView} 
        user={user} setUser={setUser} 
        usage={usage} features={features} 
        token={token} loading={loading} 
        authForm={authForm} setAuthForm={setAuthForm}
        handleAuth={handleAuth} logout={logout}
        fetchBase={fetchBase}
        Toast={Toast}
        show={show}
      />
    </LanguageProvider>
  );
}

function InstaAgentProviderShell({ view, setView, user, setUser, usage, features, token, loading, authForm, setAuthForm, handleAuth, logout, fetchBase, Toast, show }) {
  const { t } = useLang();
  const needsOnboarding = user && !user.onboarding_done;

  return (
    <FeatureCtx.Provider value={{ features: features.features || {}, trialPosts: features.free_trial_posts || 5, botUsername: features.telegram_bot_username || "InstaAgent_bot" }}>
      <GlobalStyles />
      {Toast}
      
      {!token ? (
        <div style={{ height: "100vh", background: T.bg, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
          <div className="fade-up" style={{ width: "100%", maxWidth: 400, background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 32, boxShadow: "0 20px 60px rgba(0,0,0,.5)" }}>
             <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 32, justifyContent: "center" }}>
                <div style={{ width: 44, height: 44, background: `linear-gradient(135deg, ${T.primary}, ${T.accent})`, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center" }}>{I.ig}</div>
                <h1 style={{ fontFamily: T.fontHead, fontSize: 24, fontWeight: 800, color: T.text }}>{t("auth.title")}</h1>
             </div>

             <h2 style={{ fontSize: 18, fontWeight: 700, color: T.text, marginBottom: 8, textAlign: "center" }}>{authForm.isLogin ? t("auth.login_title") : t("auth.register_title")}</h2>
             <p style={{ fontSize: 13, color: T.textMuted, marginBottom: 24, textAlign: "center" }}>{t("auth.subtitle")}</p>

             <form onSubmit={handleAuth} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {!authForm.isLogin && (
                  <div>
                     <label style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, display: "block", marginBottom: 6, textTransform: "uppercase" }}>{t("auth.full_name")}</label>
                     <input type="text" required value={authForm.full_name} onChange={e => setAuthForm({...authForm, full_name: e.target.value})} placeholder="Your Name" style={{ width: "100%", padding: 12, borderRadius: 10, border: `1px solid ${T.border}`, background: T.surfaceAlt, color: T.text, fontSize: 14 }} />
                  </div>
                )}
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, display: "block", marginBottom: 6, textTransform: "uppercase" }}>{t("auth.email")}</label>
                  <input type="email" required value={authForm.email} onChange={e => setAuthForm({...authForm, email: e.target.value})} placeholder="seller@example.com" style={{ width: "100%", padding: 12, borderRadius: 10, border: `1px solid ${T.border}`, background: T.surfaceAlt, color: T.text, fontSize: 14 }} />
                </div>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, display: "block", marginBottom: 6, textTransform: "uppercase" }}>{t("auth.password")}</label>
                  <input type="password" required value={authForm.password} onChange={e => setAuthForm({...authForm, password: e.target.value})} placeholder="••••••••" style={{ width: "100%", padding: 12, borderRadius: 10, border: `1px solid ${T.border}`, background: T.surfaceAlt, color: T.text, fontSize: 14 }} />
                </div>
                <button
                    type="submit"
                    disabled={loading}
                    style={{ width: "100%", padding: 12, background: T.primary, color: "#fff", border: "none", borderRadius: 10, fontWeight: 700, fontSize: 14, cursor: "pointer", display: "flex", justifyContent: "center", alignItems: "center", gap: 8, transition: "all .2s" }}
                  >
                    {loading ? <Spinner size={18} color="#fff" /> : (authForm.isLogin ? t("auth.sign_in") : t("auth.register"))}
                  </button>

                  <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "16px 0" }}>
                    <div style={{ flex: 1, height: 1, background: T.border }} />
                    <span style={{ fontSize: 12, color: T.textMuted }}>{t("auth.or")}</span>
                    <div style={{ flex: 1, height: 1, background: T.border }} />
                  </div>

                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        const res = await api.get("/api/v1/auth/google");
                        if (res.auth_url) window.location.href = res.auth_url;
                      } catch (e) { show(e.message, "error"); }
                    }}
                    style={{ width: "100%", padding: 12, background: "#fff", color: "#000", border: `1px solid ${T.border}`, borderRadius: 10, fontWeight: 600, fontSize: 14, cursor: "pointer", display: "flex", justifyContent: "center", alignItems: "center", gap: 10, transition: "all .2s" }}
                  >
                    <img src="https://www.gstatic.com/images/branding/product/1x/gsa_512dp.png" alt="Google" style={{ width: 18, height: 18 }} />
                    {t("auth.google")}
                  </button>
             </form>
             
             <div style={{ marginTop: 20, textAlign: "center" }}>
                <button onClick={() => setAuthForm({...authForm, isLogin: !authForm.isLogin})} style={{ background: "transparent", border: "none", color: T.primary, fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
                  {authForm.isLogin ? t("auth.no_account") : t("auth.have_account")}
                </button>
             </div>
          </div>
        </div>
      ) : needsOnboarding ? (
        <OnboardingView 
          user={user} 
          token={token} 
          onUserUpdate={setUser}
          onComplete={() => fetchBase(token)} 
        />
      ) : (
        <div style={{ display: "flex", minHeight: "100vh" }}>
            <Sidebar active={view} setActive={setView} user={user} usage={usage} onLogout={logout} loading={loading} />
            <main style={{ flex: 1, position: "relative", display: "flex", flexDirection: "column" }}>
                 <Header activeView={view} />
                 <div style={{ flex: 1, position: "relative" }}>
                    {loading && <div style={{ position: "fixed", top: 80, right: 32, zIndex: 50 }}><Spinner size={20} /></div>}
                    
                    <div className="slide-in" key={view} style={{ height: "100%" }}>
                        {view === "dashboard" && <DashboardView setActive={setView} user={user} usage={usage} token={token} />}
                        {view === "create"    && <CreatePostView user={user} token={token} onPostCreated={() => { fetchBase(token); setView("posts"); }} />}
                        {view === "posts"     && <PostsView token={token} />}
                        {view === "analytics" && <AnalyticsView token={token} setActive={setView} />}
                        {view === "billing"   && <BillingView user={user} usage={usage} token={token} />}
                        {view === "admin"     && <AdminView token={token} user={user} />}
                        {view === "admin_aggregator" && <AdminAggregatorView token={token} />}
                        {view === "settings"  && <SettingsView user={user} token={token} onUserUpdate={(u) => { setUser(u); fetchBase(token); }} />}
                        {view === "telegram"  && <TelegramView user={user} />}
                        {view === "aggregator"&& <AggregatorView token={token} user={user} />}
                    </div>
                 </div>
            </main>
        </div>
      )}
    </FeatureCtx.Provider>
  );
}


export default InstaAgent;
