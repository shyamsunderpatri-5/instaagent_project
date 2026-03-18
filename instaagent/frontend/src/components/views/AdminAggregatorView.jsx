// frontend/src/components/views/AdminAggregatorView.jsx
import { useState, useEffect } from "react";
import { T, I, StatCard, Spinner, useToast, useLang } from "../common/UIComponents";
import { api } from "../common/api";
import { AggregatedPostCard } from "./aggregator/AggregatedPostCard";

export const AdminAggregatorView = ({ token }) => {
  const [stats, setStats] = useState(null);
  const [trends, setTrends] = useState([]);
  const [posts, setPosts] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const { show } = useToast();
  const { t } = useLang();

  const fetchData = async () => {
    setLoading(true);
    try {
      const [s, t, p, a] = await Promise.all([
        api.get("/api/v1/aggregator/admin/stats", token),
        api.get("/api/v1/aggregator/admin/trends", token),
        api.get("/api/v1/aggregator/posts?limit=50", token),
        api.get("/api/v1/aggregator/accounts", token) // Using admin token to get all if RLS allows, or need admin endpoint
      ]);
      setStats(s);
      setTrends(t.trends || []);
      setPosts(p || []);
      setAccounts(a || []);
    } catch (err) {
      show(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [token]);

  const handleRefresh = async (accountId) => {
    try {
      await api.post(`/api/v1/aggregator/refresh/${accountId}`, {}, token);
      show(t("admin_agg.refresh_success"), "success");
    } catch (err) {
      show(t("admin_agg.refresh_error"), "error");
    }
  };

  if (loading) return <div style={{ display: "flex", justifyContent: "center", padding: 100 }}><Spinner size={32} /></div>;

  return (
    <div className="fade-up" style={{ padding: 32, maxWidth: 1200, margin: "0 auto" }}>
       <h1 style={{ fontFamily: T.fontHead, fontSize: 24, fontWeight: 800, color: T.text, marginBottom: 24 }}>{t("admin_agg.title")}</h1>

       <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 32 }}>
          <StatCard label="Total Tracked" value={stats?.total_tracked_accounts} icon={I.dash} color={T.primary} />
          <StatCard label="Total Posts" value={stats?.total_aggregated_posts} icon={I.posts} color={T.accent} />
          <StatCard label="Active Users" value={stats?.active_users} icon={I.billing} color={T.green} />
          <StatCard label="Premium Plan" value="₹999" icon={I.zap} color={T.gold} />
       </div>

       <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <section style={{ background: T.surface, padding: 24, borderRadius: 24, border: `1px solid ${T.border}` }}>
          <h2 style={{ fontSize: 18, marginBottom: 16 }}>{t("admin_agg.users_title")}</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {stats?.user_details?.map(u => (
              <div key={u.id} style={{ padding: 12, background: T.surfaceAlt, borderRadius: 12, display: "flex", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontWeight: 700 }}>{u.full_name}</div>
                  <div style={{ fontSize: 12, color: T.textMuted }}>{u.email}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 12, fontWeight: 700 }}>{u.account_count} Accounts</div>
                  <div style={{ fontSize: 11, color: T.textMuted }}>{u.post_count} Posts</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section style={{ background: T.surface, padding: 24, borderRadius: 24, border: `1px solid ${T.border}` }}>
          <h2 style={{ fontSize: 18, marginBottom: 16 }}>{t("admin_agg.accounts_title")}</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {accounts.map(acc => (
              <div key={acc.id} style={{ padding: 12, background: T.surfaceAlt, borderRadius: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 700 }}>@{acc.instagram_username}</div>
                  <div style={{ fontSize: 11, color: T.textMuted }}>Type: {acc.account_type}</div>
                </div>
                <button 
                  onClick={() => handleRefresh(acc.id)}
                  style={{ background: `${T.primary}20`, color: T.primary, border: `1px solid ${T.primary}40`, borderRadius: 8, padding: "4px 12px", fontSize: 11, fontWeight: 700, cursor: "pointer" }}
                >
                  {t("admin_agg.manual_refresh")}
                </button>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section style={{ marginTop: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 16 }}>{t("admin_agg.hashtags_title")}</h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
          {trends.map(t => (
            <div key={t.tag} style={{ background: T.surface, border: `1px solid ${T.border}`, padding: "8px 16px", borderRadius: 100 }}>
              <span style={{ color: T.primary, fontWeight: 700 }}>#{t.tag}</span>
              <span style={{ marginLeft: 8, fontSize: 12, color: T.textMuted }}>{t.count}</span>
            </div>
          ))}
        </div>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2 style={{ fontSize: 18, marginBottom: 16 }}>{t("admin_agg.moderation_title")}</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 24 }}>
           {posts.map(p => <AggregatedPostCard key={p.id} post={p} token={token} isAdmin={true} t={t} />)}
        </div>
      </section>
    </div>
  );
};
