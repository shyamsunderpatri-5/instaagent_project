// frontend/src/components/views/AggregatorView.jsx
import { useState, useEffect } from "react";
import { T, I, Badge, Spinner, useToast, useLang } from "../common/UIComponents";
import { api } from "../common/api";

export const AggregatorView = ({ token, user }) => {
  const [accounts, setAccounts] = useState([]);
  const [posts, setPosts] = useState([]);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
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
      show("Account added! Data will sync shortly.");
      setShowAdd(false);
      setNewAcc({ username: "", type: "competitor" });
      fetchData();
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
      show("AI Insights generated!");
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
          {/* Tracked Accounts */}
          <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 24 }}>
            <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 20 }}>{t("aggregator.tracked_accounts")}</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {accounts.map(acc => (
                <div key={acc.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: 12, background: T.surfaceAlt, borderRadius: 14, border: `1px solid ${T.border}` }}>
                   <div style={{ width: 36, height: 36, borderRadius: "50%", background: acc.account_type === "owned" ? T.primaryDim : T.accentDim, display: "flex", alignItems: "center", justifyContent: "center", color: acc.account_type === "owned" ? T.primary : T.accent }}>{I.ig}</div>
                   <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 700 }}>@{acc.instagram_username}</div>
                      <div style={{ fontSize: 11, color: T.textMuted }}>{t(`aggregator.type_${acc.account_type}`)}</div>
                   </div>
                   <Badge 
                     status={acc.last_synced_at ? "active" : "trialing"} 
                     text={acc.last_synced_at ? t("aggregator.synced") : t("aggregator.syncing")}
                   />
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

          {/* AI Insights Display */}
          {insights && (
            <div className="fade-up" style={{ background: `linear-gradient(135deg, ${T.surfaceAlt}, ${T.bg})`, border: `2px solid ${T.primary}40`, borderRadius: 20, padding: 24 }}>
               <h3 style={{ color: T.primary, fontSize: 15, fontWeight: 800, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>{I.zap} {t("aggregator.ai_strategy")}</h3>
               
               <div style={{ marginBottom: 20 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, marginBottom: 8 }}>{t("aggregator.post_ideas")}</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {insights.post_ideas?.map((idea, i) => (
                      <div key={i} style={{ fontSize: 13, background: `${T.primary}10`, padding: "8px 12px", borderRadius: 8, borderLeft: `3px solid ${T.primary}` }}>{idea}</div>
                    ))}
                  </div>
               </div>

               <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, marginBottom: 8 }}>{t("aggregator.market_trends")}</div>
                  <ul style={{ paddingLeft: 16 }}>
                    {insights.trend_summaries?.map((trend, i) => (
                      <li key={i} style={{ fontSize: 13, color: T.text, marginBottom: 4 }}>{trend}</li>
                    ))}
                  </ul>
               </div>
            </div>
          )}
        </div>

        {/* Feed */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 24 }}>
          <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 20 }}>{t("aggregator.feed_title")}</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16 }}>
            {posts.map(post => (
              <div key={post.id} style={{ background: T.surfaceAlt, borderRadius: 16, overflow: "hidden", border: `1px solid ${T.border}` }}>
                {post.media_url ? (
                  <img src={post.media_url} alt="" style={{ width: "100%", height: 180, objectFit: "cover" }} />
                ) : (
                  <div style={{ width: "100%", height: 180, background: T.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>📷</div>
                )}
                <div style={{ padding: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, color: T.primary }}>{post.aggregator_accounts?.instagram_username}</span>
                    <span style={{ fontSize: 11, color: T.textMuted }}>{new Date(post.posted_at).toLocaleDateString()}</span>
                  </div>
                  <div style={{ fontSize: 12, height: 36, overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", color: T.textMuted }}>{post.caption}</div>
                  <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, display: "flex", alignItems: "center", gap: 4 }}>{I.heart} {post.likes}</span>
                    <span style={{ fontSize: 11, fontWeight: 700, display: "flex", alignItems: "center", gap: 4 }}>{I.chat} {post.comments}</span>
                  </div>
                </div>
              </div>
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
