// frontend/src/components/views/AggregatorView.jsx
import { useState, useEffect } from "react";
import { T, I, Badge, Spinner, useToast, useLang, Toggle } from "../common/UIComponents";
import { api } from "../common/api";

import { AggregatorAccountCard } from "./aggregator/AggregatorAccountCard";
import { AggregatedPostCard } from "./aggregator/AggregatedPostCard";
import { AIInsightsPanel } from "./aggregator/AIInsightsPanel";
import { AnalyticsDashboard } from "./aggregator/AnalyticsDashboard";

export const AggregatorView = ({ token, user }) => {
  const [accounts, setAccounts] = useState([]);
  const [posts, setPosts] = useState([]);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncPending, setSyncPending] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [newAcc, setNewAcc] = useState({ username: "", type: "competitor" });
  
  // New State for Analytics
  const [activeTab, setActiveTab] = useState("feed"); // feed, analytics, accounts
  const [sortPosts, setSortPosts] = useState("recent");
  const [formatStats, setFormatStats] = useState([]);
  const [freqData, setFreqData] = useState(null);
  const [compStats, setCompStats] = useState(null);
  const [tagStats, setTagStats] = useState([]);
  
  const { show } = useToast();
  const { t } = useLang();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [accs, pts] = await Promise.all([
        api.get("/api/v1/aggregator/accounts", token),
        api.get(`/api/v1/aggregator/posts?limit=30&sort=${sortPosts}`, token)
      ]);
      setAccounts(accs || []);
      setPosts(pts || []);
      
      // Load analytics if needed
      if (activeTab === "analytics") {
        const [fmts, freq, comp, tags] = await Promise.all([
          api.get("/api/v1/aggregator/analytics/content-formats", token),
          api.get("/api/v1/aggregator/analytics/frequency", token),
          api.get("/api/v1/aggregator/analytics/comparison", token),
          api.get("/api/v1/aggregator/analytics/hashtags", token)
        ]);
        setFormatStats(fmts.formats || []);
        setFreqData(freq);
        setCompStats(comp);
        setTagStats(tags.hashtags || []);
      }
    } catch (err) {
      show(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [token, sortPosts, activeTab]);

  // Load Chart.js (C2.3: Security check and deduplication)
  useEffect(() => {
    if (activeTab === "analytics" && !window.Chart) {
      if (document.getElementById("chartjs-script")) return;
      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/npm/chart.js";
      script.async = true;
      script.id = "chartjs-script";
      document.body.appendChild(script);
      return () => {
        const s = document.getElementById("chartjs-script");
        if (s) document.body.removeChild(s);
      }
    }
  }, [activeTab]);

  const handleAddAccount = async (e) => {
    e.preventDefault();
    setSyncing(true);
    try {
      await api.post("/api/v1/aggregator/accounts", {
        instagram_username: newAcc.username,
        account_type: newAcc.type
      }, token);
      show(t("aggregator.account_added_msg"));
      setShowAdd(false);
      setNewAcc({ username: "", type: "competitor" });
      setSyncPending(true);
      setTimeout(() => setSyncPending(false), 30000); // hide after 30s
      fetchData();
    } catch (err) {
      show(err.message, "error");
    } finally {
      setSyncing(false);
    }
  };

  const handleRefresh = async (accId) => {
    setSyncing(true);
    try {
      await api.post(`/api/v1/aggregator/refresh/${accId}`, {}, token);
      show(t("aggregator.refresh_triggered"));
      setSyncPending(true);
      setTimeout(() => setSyncPending(false), 20000);
    } catch (err) {
      show(err.message, "error");
    } finally {
      setSyncing(false);
    }
  };

  const generateInsights = async () => {
    if (accounts.length === 0) return;
    setSyncing(true);
    try {
      const res = await api.post("/api/v1/aggregator/ai-analyze", {
        account_ids: accounts.map(a => a.id)
      }, token);
      setInsights(res);
      show(t("aggregator.insights_generated_msg"));
    } catch (err) {
      show(err.message, "error");
    } finally {
      setSyncing(false);
    }
  };

  // Debounced Alert Update helper to avoid API firehose during slider movement
  const [debouncedTimers, setDebouncedTimers] = useState({});
  const handleUpdateAlerts = (accId, enabled, threshold) => {
    // 1. Pessimistic UI Update (Immediate)
    setAccounts(accounts.map(a => a.id === accId ? { ...a, alert_enabled: enabled, alert_threshold_er: threshold } : a));

    // 2. Debounce API Call (500ms)
    if (debouncedTimers[accId]) clearTimeout(debouncedTimers[accId]);
    
    const timer = setTimeout(async () => {
      try {
        await api.patch(`/api/v1/aggregator/accounts/${accId}/alerts`, {
          alert_enabled: enabled,
          alert_threshold_er: parseFloat(threshold)
        }, token);
        show(t("aggregator.alerts_updated_msg"));
      } catch (err) {
        show(err.message, "error");
        fetchData(); // Reset on error
      }
    }, 500);

    setDebouncedTimers(prev => ({ ...prev, [accId]: timer }));
  };

  const saveToPosts = async (postId) => {
    try {
      await api.post(`/api/v1/aggregator/posts/${postId}/save`, {}, token);
      show(t("aggregator.save_success"));
    } catch (err) {
      show(err.message, "error");
    }
  };
  const isAggregatorPlan = user?.plan === "aggregator" || user?.is_admin;

  if (!loading && !isAggregatorPlan) {
    return (
      <div className="fade-up" style={{ padding: 40, maxWidth: 600, margin: "100px auto", textAlign: "center" }}>
        <div style={{ display: "inline-flex", padding: 24, borderRadius: "50%", background: `${T.primary}15`, color: T.primary, marginBottom: 24 }}>
          {I.zap}
        </div>
        <h1 style={{ fontFamily: T.fontHead, fontSize: 32, fontWeight: 800, marginBottom: 16 }}>Enterprise Aggregator</h1>
        <p style={{ fontSize: 16, color: T.textMuted, lineHeight: 1.6, marginBottom: 32 }}>
          Track competitors, generate AI content strategies, and analyze market trends. This feature is exclusive to the <strong>Enterprise Aggregator Plan</strong>.
        </p>
        <button onClick={() => window.location.href = '/dashboard'} style={{ background: T.primary, color: "#fff", border: "none", borderRadius: 12, padding: "14px 32px", fontSize: 15, fontWeight: 700, cursor: "pointer" }}>
          Go to Dashboard
        </button>
      </div>
    );
  }

  if (loading) return <div style={{ display: "flex", justifyContent: "center", padding: 100 }}><Spinner size={32} /></div>;

  return (
    <div className="fade-up" style={{ padding: 40, maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 12, color: T.primary, fontWeight: 800, letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 8 }}>{t("aggregator.subtitle")}</div>
          <h1 style={{ fontFamily: T.fontHead, fontSize: 32, fontWeight: 800, color: T.text, letterSpacing: "-0.02em" }}>{t("aggregator.title")}</h1>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <button onClick={() => setShowAdd(true)} style={{ background: T.surface, color: T.text, border: `1px solid ${T.border}`, borderRadius: 12, padding: "10px 20px", fontWeight: 700, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
            {I.create} {t("aggregator.add_account")}
          </button>
          <button disabled={syncing} onClick={generateInsights} style={{ background: T.primary, color: "#fff", border: "none", borderRadius: 12, padding: "10px 20px", fontWeight: 700, fontSize: 13, cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
            {syncing ? <Spinner color="#fff" /> : I.zap} {t("aggregator.generate_insights")}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 32, borderBottom: `1px solid ${T.border}`, marginBottom: 32 }}>
        {[
          { id: "feed", label: t("aggregator.feed_tab"), icon: I.posts },
          { id: "analytics", label: t("aggregator.analytics_tab"), icon: I.analytics },
          { id: "accounts", label: t("aggregator.accounts_tab"), icon: I.settings },
        ].map(tab => (
          <div 
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{ 
              padding: "12px 4px", 
              fontSize: 14, 
              fontWeight: 700, 
              color: activeTab === tab.id ? T.primary : T.textMuted,
              cursor: "pointer",
              borderBottom: `2px solid ${activeTab === tab.id ? T.primary : 'transparent'}`,
              display: "flex",
              alignItems: "center",
              gap: 8,
              transition: "all .2s"
            }}
          >
            {tab.icon} {tab.label}
          </div>
        ))}
      </div>

      {syncPending && (
        <div className="fade-up" style={{ background: `${T.primary}15`, border: `1px solid ${T.primary}40`, borderRadius: 12, padding: "12px 16px", fontSize: 13, color: T.primary, display: "flex", alignItems: "center", gap: 10, marginBottom: 24 }}>
          <Spinner size={14} color={T.primary} />
          {t("aggregator.sync_pending_banner")}
        </div>
      )}
      {/* Tab Content */}
      {activeTab === "feed" && (
        <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 32 }}>
          <div>
            <AIInsightsPanel insights={insights} t={t} />
          </div>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <h2 style={{ fontSize: 18, fontWeight: 800 }}>{t("aggregator.feed_title")}</h2>
              <div style={{ display: "flex", background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 4 }}>
                {["recent", "top"].map(s => (
                  <button 
                    key={s}
                    onClick={() => setSortPosts(s)}
                    style={{ 
                      padding: "6px 12px", 
                      borderRadius: 6, 
                      border: "none", 
                      background: sortPosts === s ? T.surfaceAlt : "transparent",
                      color: sortPosts === s ? T.text : T.textDim,
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer"
                    }}
                  >
                    {t(`aggregator.sort_${s}`)}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 24 }}>
              {posts.map(post => (
                <AggregatedPostCard 
                  key={post.id} 
                  post={post} 
                  token={token} 
                  t={t} 
                  onSaveSuccess={() => show(t("aggregator.save_success"), "success")} 
                />
              ))}
              {posts.length === 0 && <div style={{ textAlign: "center", padding: 60, color: T.textDim }}>{t("aggregator.fetching_data")}</div>}
            </div>
          </div>
        </div>
      )}

      {activeTab === "analytics" && (
        <div className="fade-up" style={{ display: "flex", flexDirection: "column", gap: 40 }}>
           <AnalyticsDashboard 
             formatStats={formatStats} 
             freqData={freqData} 
             compStats={compStats} 
             tagStats={tagStats}
             t={t}
           />
        </div>
      )}

      {activeTab === "accounts" && (
        <div className="fade-up">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 24 }}>
            {accounts.map(acc => (
              <div key={acc.id} style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 24, position: "relative" }}>
                 <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
                    <AggregatorAccountCard acc={acc} t={t} />
                    <button onClick={() => handleRefresh(acc.id)} style={{ background: T.surfaceAlt, border: "none", color: T.textDim, cursor: "pointer", padding: 8, borderRadius: 8 }}>{I.refresh}</button>
                 </div>
                 
                 {acc.account_type === "competitor" && (
                   <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 20, marginTop: 16 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                        <span style={{ fontSize: 13, fontWeight: 700 }}>{t("aggregator.enable_alerts")}</span>
                        <Toggle value={acc.alert_enabled} onChange={(val) => handleUpdateAlerts(acc.id, val, acc.alert_threshold_er || 3.0)} />
                      </div>
                      <div style={{ display: acc.alert_enabled ? "block" : "none" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: T.textDim, marginBottom: 8 }}>
                          <span>{t("aggregator.alert_threshold")}</span>
                          <span style={{ color: T.primary, fontWeight: 800 }}>{acc.alert_threshold_er}% ER</span>
                        </div>
                        <input 
                          type="range" min="0.5" max="10" step="0.5" 
                          value={acc.alert_threshold_er || 3.0}
                          onChange={(e) => handleUpdateAlerts(acc.id, acc.alert_enabled, e.target.value)}
                          style={{ width: "100%", accentColor: T.primary, cursor: "pointer" }}
                        />
                      </div>
                   </div>
                 )}

                 <button 
                  onClick={async () => {
                    if (confirm(t("aggregator.confirm_delete"))) {
                      await api.del(`/api/v1/aggregator/accounts/${acc.id}`, token);
                      fetchData();
                    }
                  }}
                  style={{ width: "100%", marginTop: 24, padding: "8px", background: "transparent", border: `1px solid ${T.red}30`, borderRadius: 10, color: T.red, fontSize: 12, fontWeight: 600, cursor: "pointer" }}
                 >
                   {t("aggregator.remove_account")}
                 </button>
              </div>
            ))}
          </div>
          {accounts.length === 0 && <div style={{ textAlign: "center", color: T.textDim, padding: 60 }}>{t("aggregator.no_accounts")}</div>}
        </div>
      )}

      {/* Add Modal */}
      {showAdd && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.8)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, backdropFilter: "blur(4px)" }}>
           <div key="add-account-form" className="fade-up" style={{ background: T.surface, padding: 32, borderRadius: 24, width: "100%", maxWidth: 400, border: `1px solid ${T.border}` }}>
              <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 8 }}>{t("aggregator.add_modal_title")}</h2>
              <p style={{ fontSize: 13, color: T.textMuted, marginBottom: 24 }}>{t("aggregator.add_modal_desc")}</p>
              
              <form onSubmit={handleAddAccount}>
                <div style={{ marginBottom: 16 }}>
                  <label style={{ fontSize: 11, fontWeight: 700, color: T.textDim, textTransform: "uppercase", display: "block", marginBottom: 6 }}>{t("aggregator.ig_username")}</label>
                  <input required value={newAcc.username} onChange={e => setNewAcc({...newAcc, username: e.target.value.replace("@", "")})} placeholder="username" style={{ width: "100%", padding: 12, background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 10, color: T.text }} />
                </div>
                <div style={{ marginBottom: 24 }}>
                  <label style={{ fontSize: 11, fontWeight: 700, color: T.textDim, textTransform: "uppercase", display: "block", marginBottom: 6 }}>{t("aggregator.account_type")}</label>
                  <select value={newAcc.type} onChange={e => setNewAcc({...newAcc, type: e.target.value})} style={{ width: "100%", padding: 12, background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 10, color: T.text }}>
                    <option value="competitor">{t("aggregator.type_competitor_full")}</option>
                    <option value="owned">{t("aggregator.type_owned_full")}</option>
                  </select>
                </div>
                <div style={{ display: "flex", gap: 12 }}>
                  <button type="button" onClick={() => setShowAdd(false)} style={{ flex: 1, padding: 12, background: "transparent", border: `1px solid ${T.border}`, borderRadius: 12, color: T.text, fontWeight: 600 }}>{t("common.cancel")}</button>
                  <button disabled={syncing} type="submit" style={{ flex: 1, padding: 12, background: T.primary, border: "none", borderRadius: 12, color: "#fff", fontWeight: 700 }}>
                    {syncing ? <Spinner color="#fff" /> : t("aggregator.track_btn")}
                  </button>
                </div>
              </form>
           </div>
        </div>
      )}
    </div>
  );
};
