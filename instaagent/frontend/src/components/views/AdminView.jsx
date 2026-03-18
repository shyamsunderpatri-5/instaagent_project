// frontend/src/components/views/AdminView.jsx
import { useState, useEffect } from "react";
import { T, I, StatCard, Badge, Spinner, useToast, useLang } from "../common/UIComponents";
import { api } from "../common/api";

export const AdminView = ({ token }) => {
  const [stats, setStats] = useState(null);
  const [aggStats, setAggStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [confirmModal, setConfirmModal] = useState(null);
  const { show, Toast } = useToast();
  const { t } = useLang();

  // Initial data fetch for dashboard stats and aggregator stats
  useEffect(() => {
    setLoading(true);
    Promise.all([
        api.get("/api/v1/admin/dashboard", token),
        api.get("/api/v1/aggregator/admin/stats", token).catch(() => null),
    ]).then(([s, as]) => {
        setStats(s.stats);
        setAggStats(as);
    }).finally(() => {
      // stats loading handled
    });
  }, [token]);

  // Separate effect for fetching users, allowing it to be re-triggered
  useEffect(() => {
    setLoading(true);
    api.get("/api/v1/admin/users", token)
      .then(res => setUsers(res.users || []))
      .catch(e => show(e.message, "error"))
      .finally(() => setLoading(false));
  }, [token]);

  const handleAction = async (userId, type) => {
    setConfirmModal({
        type, 
        userId, 
        msg: type === "ban" ? t("admin.ban_msg") : t("admin.reset_msg")
    });
  };

  const executeAction = async () => {
    if (!confirmModal) return;
    const { userId, type } = confirmModal;
    setConfirmModal(null);
    setLoading(true);

    try {
      const endpoint = type === "ban" ? `/api/v1/admin/users/${userId}/ban` : `/api/v1/admin/users/${userId}/reset-quota`;
      await api.post(endpoint, {}, token);
      show(`Action successful`, "success");

      // Refresh list
      const res = await api.get("/api/v1/admin/users", token);
      setUsers(res.users || []);
    } catch (e) {
      show(e.message, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1000 }}>
       {Toast}
       <div className="fade-up" style={{ marginBottom: 24 }}>
          <h1 style={{ fontFamily: T.fontHead, fontSize: 24, fontWeight: 800, color: T.text, marginBottom: 6 }}>{t("admin.title")}</h1>
          <p style={{ color: T.textMuted, fontSize: 14 }}>{t("admin.subtitle")}</p>
       </div>

       <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14, marginBottom: 24 }}>
          <StatCard label={t("admin.total_sellers")} value={stats?.total_users} icon={I.dash} color={T.primary} loading={loading} />
          <StatCard label={t("admin.total_posts")} value={stats?.total_posts} icon={I.posts} color={T.accent} loading={loading} />
          <StatCard label={t("admin.active_subs")} value={stats?.active_subscriptions} icon={I.billing} color={T.green} loading={loading} />
          <StatCard label={t("admin.shared_accounts")} value={aggStats?.total_tracked_accounts} icon={I.aggregator} color={T.primary} loading={loading} />
          <StatCard label={t("admin.market_data")} value={aggStats?.total_aggregated_posts} icon={I.posts} color={T.gold} loading={loading} />
       </div>

       <div className="fade-up" style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 24 }}>
          <div style={{ fontFamily: T.fontHead, fontWeight: 700, fontSize: 16, color: T.text, marginBottom: 20 }}>{t("admin.sellers_table")}</div>
          <div style={{ overflowX: "auto" }}>
             <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                   <tr style={{ borderBottom: `1px solid ${T.border}`, color: T.textMuted, textAlign: "left" }}>
                      <th style={{ padding: "12px 8px" }}>{t("admin.col_name")}</th>
                      <th style={{ padding: "12px 8px" }}>{t("admin.col_plan")}</th>
                      <th style={{ padding: "12px 8px" }}>{t("admin.col_joined")}</th>
                      <th style={{ padding: "12px 16px" }}>{t("admin.col_status")}</th>
                      <th style={{ textAlign: "right", padding: "12px 16px" }}>{t("admin.col_actions")}</th>
                   </tr>
                </thead>
                <tbody>
                   {users.map(u => (
                      <tr key={u.id} style={{ borderBottom: `1px solid ${T.border}` }}>
                         <td style={{ padding: 16 }}>
                            <div style={{ fontWeight: 700, color: T.text }}>{u.full_name}</div>
                            <div style={{ fontSize: 12, color: T.textMuted }}>{u.email}</div>
                         </td>
                         <td style={{ padding: 16 }}>
                            <Badge status={u.plan} />
                         </td>
                         <td style={{ padding: 16 }}>
                            <div style={{ color: T.textDim }}>{new Date(u.created_at).toLocaleDateString()}</div>
                         </td>
                         <td style={{ padding: 16 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: u.is_active ? T.green : T.red }}>
                               <div style={{ width: 6, height: 6, borderRadius: "50%", background: u.is_active ? T.green : T.red }} />
                               {u.is_active ? t("admin.status_active") : t("admin.status_banned")}
                            </div>
                         </td>
                         <td style={{ padding: 16, textAlign: "right" }}>
                            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
                               <button 
                                 onClick={() => handleAction(u.id, "reset-quota")}
                                 title="Reset Quota"
                                 style={{ padding: "6px 10px", borderRadius: 8, border: `1px solid ${T.border}`, background: T.surfaceAlt, color: T.text, cursor: "pointer", fontSize: 12 }}
                               >
                                 {I.usage}
                               </button>
                               <button 
                                 onClick={() => handleAction(u.id, "ban")}
                                 title={u.is_active ? "Ban User" : "Activate User"}
                                 style={{ padding: "6px 10px", borderRadius: 8, border: `1px solid ${u.is_active ? T.red : T.green}`, background: u.is_active ? `${T.red}15` : `${T.green}15`, color: u.is_active ? T.red : T.green, cursor: "pointer", fontSize: 12 }}
                               >
                                  {u.is_active ? I.close : I.check}
                               </button>
                            </div>
                         </td>
                      </tr>
                   ))}
                </tbody>
             </table>
          </div>
       </div>
 
       {confirmModal && (
          <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.6)", backdropFilter: "blur(4px)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
             <div className="fade-up" style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 32, maxWidth: 400, width: "100%", boxShadow: "0 20px 60px rgba(0,0,0,.4)", textAlign: "center" }}>
                <div style={{ width: 48, height: 48, background: T.primaryDim, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 20px", color: T.primary }}>{I.alert}</div>
                <h3 style={{ fontSize: 18, fontWeight: 800, color: T.text, marginBottom: 8 }}>{t("admin.confirm_title")}</h3>
                <p style={{ fontSize: 14, color: T.textMuted, marginBottom: 24, lineHeight: 1.5 }}>{confirmModal.msg}</p>
                <div style={{ display: "flex", gap: 12 }}>
                   <button onClick={() => setConfirmModal(null)} style={{ flex: 1, padding: 12, borderRadius: 12, border: `1px solid ${T.border}`, background: "transparent", color: T.text, fontWeight: 600, cursor: "pointer" }}>{t("onboarding.back")}</button>
                   <button onClick={executeAction} style={{ flex: 1, padding: 12, borderRadius: 12, background: T.primary, color: "white", border: "none", fontWeight: 600, cursor: "pointer" }}>{t("common.save")}</button>
                </div>
             </div>
          </div>
       )}
    </div>
  );
};
