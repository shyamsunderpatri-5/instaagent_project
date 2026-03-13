// frontend/src/components/views/DashboardView.jsx
import { useState, useEffect } from "react";
import { T, I, StatCard, useFeatures, useLang } from "../common/UIComponents";
import { api } from "../common/api";

const Badge = ({ status }) => {
  const { t } = useLang();
  const STATUS_COLOR = {
    processing: { bg: "#f59e0b22", text: "#f59e0b", label: t("common.processing") },
    ready:      { bg: "#3b82f622", text: "#3b82f6", label: t("common.ready") },
    scheduled:  { bg: "#8b5cf622", text: "#8b5cf6", label: t("common.scheduled") },
    posted:     { bg: "#10b98122", text: "#10b981", label: t("common.posted") },
    failed:     { bg: "#ef444422", text: "#ef4444", label: t("common.failed") },
    discarded:  { bg: "#6b728022", text: "#6b7280", label: "🗑️ Discarded" },
  };
  const s = STATUS_COLOR[status] || { bg: "#6b728022", text: "#6b7280", label: status };
  return (
    <span style={{ background: s.bg, color: s.text, fontSize: 11, fontWeight: 700, padding: "4px 10px", borderRadius: 20, backdropFilter: "blur(4px)" }}>
      {s.label}
    </span>
  );
};

export const DashboardView = ({ setActive, user, usage, token }) => {
  const [stats,    setStats]   = useState(null);
  const [snaps,    setSnaps]   = useState([]);
  const [lastPost, setLastPost]= useState(null);
  const [loading,  setLoading] = useState(true);
  const { features, trialPosts } = useFeatures();
  const { t } = useLang();

  useEffect(() => {
    setLoading(true);
    const fetchData = async () => {
        try {
            const [st, sn, po] = await Promise.all([
                features.enable_analytics ? api.get("/api/v1/analytics/dashboard", token).catch(() => null) : Promise.resolve(null),
                features.enable_analytics ? api.get("/api/v1/analytics/snapshots?limit=7", token).catch(() => ({ snapshots: [] })) : Promise.resolve({ snapshots: [] }),
                api.get("/api/v1/posts?page=1&page_size=1", token).catch(() => ({ posts: [] })),
            ]);
            setStats(st?.data || null);
            setSnaps(sn?.snapshots || []);
            setLastPost((po?.posts || [])[0] || null);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };
    fetchData();
  }, [token, features.enable_analytics]);

  const hour = new Date().getHours();
  const greetingKey = hour < 12 ? "dashboard.greeting_morning" : hour < 17 ? "dashboard.greeting_afternoon" : "dashboard.greeting_evening";
  const name = user?.full_name?.split(" ")[0] || "there";
  const plan = user?.plan || "free";
  const postsLeft = (usage?.posts_limit || trialPosts) - (usage?.posts_used || 0);
  const trialLow  = plan === "free" && postsLeft <= 2;

  const chartData = snaps.length
    ? [...snaps].reverse()
    : Array.from({ length: 7 }, (_, i) => ({ reach_30d: 0, snapshotted_at: new Date(Date.now() - (6 - i) * 86400000).toISOString() }));
  const maxR = Math.max(...chartData.map(d => d.reach_30d || 0), 1);

  return (
    <div style={{ padding: "40px", maxWidth: 1200, margin: "0 auto" }}>
      {trialLow && (
        <div className="fade-up" style={{ marginBottom: 32, background: `linear-gradient(135deg,${T.gold}15,${T.gold}05)`, border: `1px solid ${T.gold}30`, borderRadius: 16, padding: "16px 24px", display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ color: T.gold, flexShrink: 0 }}>{I.alert}</span>
          <div style={{ flex: 1 }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: T.gold }}>Limited Trial: {postsLeft} post{postsLeft !== 1 ? "s" : ""} remaining</span>
            <div style={{ fontSize: 13, color: T.textMuted, marginTop: 2 }}>Upgrade to a professional plan for unlimited AI processing and Instagram automation.</div>
          </div>
          <button onClick={() => setActive("billing")} style={{ background: T.gold, color: "#000", border: "none", borderRadius: 10, padding: "10px 20px", fontWeight: 700, fontSize: 13, cursor: "pointer", transition: "opacity .2s" }}>{t("billing.upgrade")}</button>
        </div>
      )}

      <div className="fade-up" style={{ marginBottom: 40 }}>
        <div style={{ fontSize: 12, color: T.primary, fontWeight: 800, letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 12 }}>{t("dashboard.analytics_overview")}</div>
        <h1 style={{ fontFamily: T.fontHead, fontSize: 32, fontWeight: 800, color: T.text, marginBottom: 8, letterSpacing: "-0.02em" }}>{t(greetingKey)}, {name}!</h1>
        <p style={{ color: T.textMuted, fontSize: 15, fontWeight: 500 }}>
          {user?.instagram_username ? (
            <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: T.green }} />
              {t("dashboard.connected_to").replace("{user}", user.instagram_username)}
              {stats?.avg_engagement_rate && <span style={{ color: T.textDim }}>·</span>}
              {stats?.avg_engagement_rate && <span style={{ color: T.textDim }}>{stats.avg_engagement_rate}% engagement rate</span>}
            </span>
          ) : `⚠️ ${t("dashboard.connect_ig_msg")}`}
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 20, marginBottom: 32 }}>
        <StatCard label={t("dashboard.monthly_posts")} value={usage?.posts_used ?? 0} sub={`Quota: ${usage?.posts_limit || trialPosts} posts`} icon={I.posts} color={T.primary} delay={0} loading={loading} />
        <StatCard label={t("dashboard.reach")} value={stats ? (stats.total_reach > 999 ? `${(stats.total_reach/1000).toFixed(1)}K` : stats.total_reach) : "—"} sub="Total audience reach" icon={I.trend} color={T.accent} delay={100} loading={loading} />
        <StatCard label={t("dashboard.engagement")} value={stats ? `${stats.avg_engagement_rate ?? 0}%` : "—"} sub="Avg engagement" icon={I.heart} color={T.gold} delay={200} loading={loading} />
        <StatCard label={t("dashboard.account_status")} value={user?.instagram_username ? t("dashboard.live") : t("dashboard.inactive")} sub={user?.instagram_username ? t("dashboard.connected") : t("dashboard.not_linked")} icon={I.ig} color={T.green} delay={300} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr", gap: 24 }}>
        {/* Reach Chart */}
        <div className="fade-up" style={{ animationDelay: "350ms", background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 28 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
            <div>
              <div style={{ fontFamily: T.fontHead, fontWeight: 700, fontSize: 17, color: T.text }}>{t("dashboard.engagement_growth")}</div>
              <div style={{ fontSize: 12, color: T.textMuted }}>{t("dashboard.reach_trends")}</div>
            </div>
            {I.trend}
          </div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 10, height: 120, padding: "10px 0" }}>
            {chartData.map((d, i) => {
              const h = Math.max(6, Math.round(((d.reach_30d || 0) / maxR) * 100));
              const day = new Date(d.snapshotted_at).toLocaleDateString("en-IN", { weekday: "short" });
              const isLast = i === chartData.length - 1;
              return (
                <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
                  <div style={{ width: "100%", background: isLast ? T.primary : `${T.primary}25`, borderRadius: "6px 6px 2px 2px", height: h, transition: "height 1s ease" }} />
                  <span style={{ fontSize: 10, fontWeight: 700, color: isLast ? T.text : T.textDim, textTransform: "uppercase" }}>{day}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Latest Post Card */}
        <div className="fade-up" style={{ animationDelay: "400ms", background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 28 }}>
          <div style={{ fontFamily: T.fontHead, fontWeight: 700, fontSize: 17, color: T.text, marginBottom: 20 }}>{t("dashboard.recent_activity")}</div>
          {lastPost ? (
            <div>
              <div style={{ position: "relative", borderRadius: 14, overflow: "hidden", marginBottom: 16 }}>
                {lastPost.edited_photo_url ? (
                  <img src={lastPost.edited_photo_url} alt="Post" style={{ width: "100%", height: 140, objectFit: "cover" }} />
                ) : (
                  <div style={{ width: "100%", height: 140, background: T.surfaceAlt, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 32 }}>📷</div>
                )}
                <div style={{ position: "absolute", top: 12, right: 12 }}>
                   <Badge status={lastPost.status} />
                </div>
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: T.text, marginBottom: 6 }}>{lastPost.product_name}</div>
              <div style={{ fontSize: 12, color: T.textMuted, lineHeight: 1.5, height: 36, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                 {lastPost.caption_english || "Processing product details..."}
              </div>
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "20px 0" }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>✨</div>
              <div style={{ fontSize: 14, color: T.textMuted }}>{t("common.no_posts")}</div>
              <button onClick={() => setActive("create")} style={{ marginTop: 16, background: T.primary, color: "#fff", border: "none", borderRadius: 10, padding: "10px 18px", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>{t("create")}</button>
            </div>
          )}
        </div>

        {/* AI Performance Card */}
        <div className="fade-up" style={{ animationDelay: "450ms", background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 28 }}>
          <div style={{ fontFamily: T.fontHead, fontWeight: 700, fontSize: 17, color: T.text, marginBottom: 20 }}>{t("dashboard.ai_performance")}</div>
          {stats?.authenticity_score ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
               <div style={{ background: T.surfaceAlt, padding: 14, borderRadius: 16, border: `1px solid ${T.border}` }}>
                  <div style={{ fontSize: 11, fontWeight: 800, color: T.primary, marginBottom: 8, letterSpacing: "0.05em" }}>{t("dashboard.enhanced_edit")}</div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                     <span style={{ fontSize: 18, fontWeight: 800, color: T.text }}>{stats.authenticity_score.enhanced.avg_eng}% <span style={{ fontSize: 11, fontWeight: 400, color: T.textMuted }}>{t("dashboard.eng_short")}</span></span>
                     <span style={{ fontSize: 12, fontWeight: 600, color: T.red }}>{stats.authenticity_score.enhanced.return_rate}% {t("dashboard.returns")}</span>
                  </div>
               </div>
               <div style={{ background: T.surfaceAlt, padding: 14, borderRadius: 16, border: `1px solid ${T.border}` }}>
                  <div style={{ fontSize: 11, fontWeight: 800, color: T.green, marginBottom: 8, letterSpacing: "0.05em" }}>{t("dashboard.authentic_look")}</div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                     <span style={{ fontSize: 18, fontWeight: 800, color: T.text }}>{stats.authenticity_score.original.avg_eng}% <span style={{ fontSize: 11, fontWeight: 400, color: T.textMuted }}>{t("dashboard.eng_short")}</span></span>
                     <span style={{ fontSize: 12, fontWeight: 600, color: T.green }}>{stats.authenticity_score.original.return_rate}% {t("dashboard.returns")}</span>
                  </div>
               </div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 140, textAlign: "center" }}>
               <div style={{ color: T.textDim, fontSize: 24, marginBottom: 12 }}>🚀</div>
               <div style={{ fontSize: 13, color: T.textMuted }}>{t("dashboard.authenticity_msg")}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
