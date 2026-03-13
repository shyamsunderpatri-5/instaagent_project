// frontend/src/components/views/AggregatorView.jsx
import { useState, useEffect } from "react";
import { T, I, Badge, Spinner, useToast, useLang } from "../common/UIComponents";
import { api } from "../common/api";

import { AggregatorAccountCard } from "./aggregator/AggregatorAccountCard";
import { AggregatedPostCard } from "./aggregator/AggregatedPostCard";
import { AIInsightsPanel } from "./aggregator/AIInsightsPanel";

export const AggregatorView = ({ token, user }) => {
  const [accounts, setAccounts] = useState([]);
  const [posts, setPosts] = useState([]);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncPending, setSyncPending] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [newAcc, setNewAcc] = useState({ username: "", type: "competitor" });
  
  const { show } = useToast();
  const { t } = useLang();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [accs, pts] = await Promise.all([
        api.get("/api/v1/aggregator/accounts", token),
        api.get("/api/v1/aggregator/posts?limit=30", token)
      ]);
      setAccounts(accs || []);
      setPosts(pts || []);
    } catch (err) {
      show(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [token]);

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
      const res = await api.post("/api/v1/aggregator/insights", {
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

  if (loading) return <div style={{ display: "flex", justifyContent: "center", padding: 100 }}><Spinner size={32} /></div>;

  return (
    <div className="fade-up" style={{ padding: 40, maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 32 }}>
        <div>
          <div style={{ fontSize: 12, color: T.primary, fontWeight: 800, letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 8 }}>{t("aggregator.subtitle")}</div>
          <h1 style={{ fontFamily: T.fontHead, fontSize: 32, fontWeight: 800, color: T.text, letterSpacing: "-0.02em" }}>{t("aggregator.title")}</h1>
        </div>
        <button onClick={() => setShowAdd(true)} style={{ background: T.primary, color: "#fff", border: "none", borderRadius: 12, padding: "12px 24px", fontWeight: 700, fontSize: 14, cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
          {I.create} {t("aggregator.add_account")}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 24 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {syncPending && (
            <div className="fade-up" style={{ background: `${T.primary}15`, border: `1px solid ${T.primary}40`, borderRadius: 12, padding: "12px 16px", fontSize: 13, color: T.primary, display: "flex", alignItems: "center", gap: 10 }}>
              <Spinner size={14} color={T.primary} />
              {t("aggregator.sync_pending_banner")}
            </div>
          )}
          {/* Tracked Accounts */}
          <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 24 }}>
            <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 20 }}>{t("aggregator.tracked_accounts")}</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {accounts.map(acc => (
                <div key={acc.id} style={{ position: "relative" }}>
                   <AggregatorAccountCard acc={acc} t={t} />
                   <button 
                     onClick={() => handleRefresh(acc.id)}
                     style={{ position: "absolute", right: 8, top: 8, background: "transparent", border: "none", color: T.textDim, cursor: "pointer", padding: 4 }}
                     title={t("aggregator.refresh")}
                   >
                     {I.refresh}
                   </button>
                </div>
              ))}
              {accounts.length === 0 && <div style={{ textAlign: "center", color: T.textDim, padding: 20, fontSize: 13 }}>{t("aggregator.no_accounts")}</div>}
            </div>
            {accounts.length > 0 && (
              <button disabled={syncing} onClick={generateInsights} style={{ width: "100%", marginTop: 20, padding: 12, background: syncing ? T.surfaceAlt : T.accent, color: "#fff", border: "none", borderRadius: 12, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                {syncing ? <Spinner color="#fff" /> : I.zap} {t("aggregator.generate_insights")}
              </button>
            )}
          </div>

          <AIInsightsPanel insights={insights} t={t} />
        </div>

        {/* Feed */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 24 }}>
          <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 20 }}>{t("aggregator.feed_title")}</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16 }}>
            {posts.map(post => (
              <AggregatedPostCard 
                key={post.id} 
                post={post} 
                token={token} 
                t={t} 
                onSaveSuccess={() => show(t("aggregator.save_success"), "success")} 
              />
            ))}
            {posts.length === 0 && <div style={{ gridColumn: "span 2", textAlign: "center", padding: 40, color: T.textDim }}>{t("aggregator.fetching_data")}</div>}
          </div>
        </div>
      </div>

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
