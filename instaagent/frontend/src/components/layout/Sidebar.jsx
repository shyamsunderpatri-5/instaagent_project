// frontend/src/components/layout/Sidebar.jsx
import { T, I, Badge, useFeatures, useLang } from "../common/UIComponents";

const NAV_IDS = [
  { id: "dashboard", labelKey: "dashboard", icon: I.dash },
  { id: "create",    labelKey: "create",    icon: I.create,   badge: "NEW" },
  { id: "posts",     labelKey: "posts",     icon: I.posts },
  { id: "analytics", labelKey: "analytics", icon: I.analytics, featureKey: "enable_analytics" },
  { id: "billing",   labelKey: "billing",   icon: I.billing,   featureKey: "enable_billing" },
  { id: "telegram",  labelKey: "telegram",  icon: I.telegram, featureKey: "enable_telegram_bot" },
  { id: "aggregator",labelKey: "aggregator",icon: I.aggregator, featureKey: "enable_aggregator" },
  { id: "admin",     labelKey: "admin",     icon: I.globe,     adminOnly: true },
  { id: "admin_aggregator", labelKey: "admin_aggregator", icon: I.trend, adminOnly: true },
  { id: "settings",  labelKey: "settings",  icon: I.settings },
];


export const Sidebar = ({ active, setActive, user, usage, onLogout, loading }) => {
  const { features } = useFeatures();
  const { t } = useLang();
  const name     = user?.full_name || "Seller";
  const initials = name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
  const plan     = user?.plan || "free";
  const used     = usage?.posts_used || 0;
  const limit    = usage?.posts_limit || 5;
  const pct      = Math.min(100, Math.round((used / limit) * 100));

  const visibleNav = NAV_IDS.filter(n => {
    if (n.adminOnly && !user?.is_admin) return false;
    return !n.featureKey || features[n.featureKey] !== false;
  });


  return (
    <aside style={{ width: 240, minWidth: 240, background: T.surface, borderRight: `1px solid ${T.border}`, display: "flex", flexDirection: "column", height: "100vh", position: "sticky", top: 0, zIndex: 10 }}>
      {/* Brand Header */}
      <div style={{ padding: "28px 20px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 40, height: 40, background: `linear-gradient(135deg, ${T.primary}, ${T.primary}dd)`, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: `0 8px 16px ${T.primary}20` }}>{I.ig}</div>
          <div>
            <div style={{ fontFamily: T.fontHead, fontWeight: 800, fontSize: 17, color: T.text, letterSpacing: "-0.02em" }}>InstaAgent</div>
            <div style={{ fontSize: 10, color: T.textDim, letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 700 }}>Enterprise AI</div>
          </div>
        </div>
      </div>

      {/* User Session Info */}
      <div style={{ padding: "0 16px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px", background: T.surfaceAlt, borderRadius: 14, border: `1px solid ${T.border}` }}>
          <div style={{ width: 32, height: 32, background: T.primary, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700, color: "#fff", flexShrink: 0 }}>{initials}</div>
          <div style={{ flex: 1, overflow: "hidden" }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: T.text, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{name}</div>
            <div style={{ fontSize: 11, color: T.textMuted }}>{user?.city || "Active Now"}</div>
          </div>
          <Badge status={plan} />
        </div>
      </div>

      {/* Sidebar Navigation */}
      <nav style={{ flex: 1, padding: "0 12px", display: "flex", flexDirection: "column", gap: 4 }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: T.textDim, padding: "0 12px 8px", textTransform: "uppercase", letterSpacing: "0.1em" }}>{t("menu")}</div>
        {visibleNav.map(item => {
          const on = active === item.id;
          return (
            <button key={item.id} onClick={() => setActive(item.id)} style={{ display: "flex", alignItems: "center", gap: 12, padding: "11px 12px", borderRadius: 10, border: "none", cursor: "pointer", background: on ? T.primaryDim : "transparent", color: on ? T.primary : T.textMuted, fontFamily: T.fontBody, fontSize: 14, fontWeight: on ? 600 : 500, transition: "all .2s ease", textAlign: "left", width: "100%" }}>
              <span style={{ flexShrink: 0, opacity: on ? 1 : 0.7 }}>{item.icon}</span>
              <span style={{ flex: 1 }}>{t(item.labelKey)}</span>
              {item.badge && <span style={{ background: T.primary, color: "#fff", fontSize: 10, fontWeight: 800, padding: "1px 6px", borderRadius: 6, letterSpacing: "0.02em" }}>{item.badge}</span>}
              {on && <div style={{ width: 4, height: 4, borderRadius: "50%", background: T.primary }} />}
            </button>
          );
        })}
      </nav>


      {/* Usage & Logout */}
      <div style={{ padding: "20px 16px", background: `linear-gradient(to top, ${T.bg}, transparent)` }}>
        <div style={{ background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 14, padding: "16px", marginBottom: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 10 }}>
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>{t("monthly_usage")}</div>
              <div style={{ fontSize: 14, fontWeight: 800, color: T.text }}>{used} / {limit} <span style={{ fontSize: 11, fontWeight: 400, color: T.textDim }}>posts</span></div>
            </div>
            <div style={{ fontSize: 12, fontWeight: 700, color: T.primary }}>{pct}%</div>
          </div>

          <div style={{ height: 6, background: T.bg, borderRadius: 3, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${pct}%`, background: T.primary, borderRadius: 3, transition: "width 1s cubic-bezier(0.4, 0, 0.2, 1)" }} />
          </div>
        </div>
        
        <button onClick={onLogout} style={{ width: "100%", display: "flex", alignItems: "center", gap: 10, padding: "12px", borderRadius: 12, border: `1px solid ${T.border}`, background: "transparent", color: T.textMuted, fontSize: 13, fontWeight: 600, cursor: "pointer", transition: "all .2s" }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = T.red; e.currentTarget.style.color = T.red; e.currentTarget.style.background = T.redDim; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.color = T.textMuted; e.currentTarget.style.background = "transparent"; }}>
          {I.logout} {t("logout")}
        </button>

      </div>
    </aside>
  );
};
