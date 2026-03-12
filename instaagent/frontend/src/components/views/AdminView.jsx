// frontend/src/components/views/AdminView.jsx
import { useState, useEffect } from "react";
import { T, I, StatCard, Badge, Spinner } from "../common/UIComponents";
import { api } from "../common/api";

export const AdminView = ({ token }) => {
  const [stats, setStats] = useState(null);
  const [aggStats, setAggStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
        api.get("/api/v1/admin/dashboard", token),
        api.get("/api/v1/admin/users", token),
        api.get("/api/v1/aggregator/admin/stats", token).catch(() => null),
    ]).then(([s, u, as]) => {
        setStats(s.stats);
        setUsers(u.users);
        setAggStats(as);
        setLoading(false);
    });
  }, [token]);

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1000 }}>
       <div className="fade-up" style={{ marginBottom: 24 }}>
          <h1 style={{ fontFamily: T.fontHead, fontSize: 24, fontWeight: 800, color: T.text, marginBottom: 6 }}>Admin Panel</h1>
          <p style={{ color: T.textMuted, fontSize: 14 }}>Platform-wide statistics and user management</p>
       </div>

       <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14, marginBottom: 24 }}>
          <StatCard label="Total Sellers" value={stats?.total_users} icon={I.dash} color={T.primary} loading={loading} />
          <StatCard label="Total Posts" value={stats?.total_posts} icon={I.posts} color={T.accent} loading={loading} />
          <StatCard label="Active Subs" value={stats?.active_subscriptions} icon={I.billing} color={T.green} loading={loading} />
          <StatCard label="Shared Accounts" value={aggStats?.total_tracked_accounts} icon={I.aggregator} color={T.primary} loading={loading} />
          <StatCard label="Market Data" value={aggStats?.total_aggregated_posts} icon={I.posts} color={T.gold} loading={loading} />
       </div>

       <div className="fade-up" style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 24 }}>
          <div style={{ fontFamily: T.fontHead, fontWeight: 700, fontSize: 16, color: T.text, marginBottom: 20 }}>All Registered Sellers</div>
          <div style={{ overflowX: "auto" }}>
             <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                   <tr style={{ borderBottom: `1px solid ${T.border}`, color: T.textMuted, textAlign: "left" }}>
                      <th style={{ padding: "12px 8px" }}>Name / Email</th>
                      <th style={{ padding: "12px 8px" }}>Status</th>
                      <th style={{ padding: "12px 8px" }}>Joined</th>
                      <th style={{ padding: "12px 8px" }}>IG Linked</th>
                   </tr>
                </thead>
                <tbody>
                   {users.map(u => (
                      <tr key={u.id} style={{ borderBottom: `1px solid ${T.border}`, color: T.text }}>
                         <td style={{ padding: "12px 8px" }}>
                            <div style={{ fontWeight: 600 }}>{u.full_name}</div>
                            <div style={{ fontSize: 11, color: T.textMuted }}>{u.email}</div>
                         </td>
                         <td style={{ padding: "12px 8px" }}><Badge status={u.plan || "free"} /></td>
                         <td style={{ padding: "12px 8px" }}>{new Date(u.created_at).toLocaleDateString()}</td>
                         <td style={{ padding: "12px 8px" }}>{u.instagram_username ? <span style={{ color: T.green }}>@{u.instagram_username}</span> : <span style={{ color: T.textMuted }}>No</span>}</td>
                      </tr>
                   ))}
                </tbody>
             </table>
          </div>
       </div>
    </div>
  );
};
