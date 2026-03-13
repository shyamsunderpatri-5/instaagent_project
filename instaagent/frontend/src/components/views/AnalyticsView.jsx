// frontend/src/components/views/AnalyticsView.jsx
import { useState, useEffect } from "react";
import { T, I, StatCard, Badge } from "../common/UIComponents";
import { api } from "../common/api";

export const AnalyticsView = ({ token, setActive }) => {
  const [stats, setStats] = useState(null);
  const [snaps, setSnaps] = useState([]);
  const [topPosts, setTopPosts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const fetchData = async () => {
        try {
            const [st, sn, tp] = await Promise.all([
                api.get("/api/v1/analytics/dashboard", token).catch(() => null),
                api.get("/api/v1/analytics/snapshots?limit=30", token).catch(() => ({ snapshots: [] })),
                api.get("/api/v1/analytics/posts?page_size=5&sort=reach", token).catch(() => ({ posts: [] })),
            ]);
            setStats(st?.data || null);
            setSnaps(sn?.snapshots || []);
            setTopPosts(tp?.posts || []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }
    fetchData();
  }, [token]);

  // SVG Line Chart for 30-day reach
  const chartData = snaps.length > 0 ? [...snaps].reverse() : [];
  const maxReach = Math.max(...chartData.map(d => d.reach_30d || 0), 100);
  const points = chartData.map((d, i) => {
    const x = (i / Math.max(chartData.length - 1, 1)) * 100;
    const y = 100 - ((d.reach_30d || 0) / maxReach) * 100;
    return `${x},${y}`;
  }).join(" ");

  const hasNoData = !loading && stats === null && snaps.length === 0;

  const handleConnect = async () => {
    try {
      const res = await api.get("/api/v1/instagram/status", token);
      if (!res.connected) {
        const conn = await api.get("/api/v1/instagram/connect", token);
        if (conn.auth_url) window.location.href = conn.auth_url;
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1000 }}>
      <div className="fade-up" style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: T.fontHead, fontSize: 24, fontWeight: 800, color: T.text, marginBottom: 6 }}>Analytics</h1>
        <p style={{ color: T.textMuted, fontSize: 14 }}>Real-time performance tracking for your account</p>
      </div>

      {loading && (
        <div style={{ display: "flex", justifyContent: "center", padding: "100px 0" }}>
          <Spinner size={32} color={T.primary} />
        </div>
      )}

      {!loading && hasNoData && (
        <div className="fade-up" style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "60vh", textAlign: "center", padding: "0 20px" }}>
          <div style={{ width: 64, height: 64, background: T.primaryDim, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 20, color: T.primary }}>
            {I.analytics || "📊"}
          </div>
          <h2 style={{ fontSize: 22, fontWeight: 800, color: T.text, marginBottom: 12 }}>No Analytics Yet</h2>
          <p style={{ color: T.textMuted, fontSize: 14, maxWidth: 380, lineHeight: 1.6, marginBottom: 28 }}>
            Connect your Instagram account and publish your first post to start seeing real engagement data here.
          </p>
          <div style={{ display: "flex", gap: 12 }}>
            <button 
              onClick={handleConnect}
              style={{ background: T.primary, color: "#fff", border: "none", padding: "12px 24px", borderRadius: 10, fontWeight: 700, cursor: "pointer", fontSize: 14 }}
            >
              Connect Instagram →
            </button>
            <button 
              onClick={() => setActive?.("create")}
              style={{ background: "transparent", color: T.primary, border: `2px solid ${T.primary}`, padding: "12px 24px", borderRadius: 10, fontWeight: 700, cursor: "pointer", fontSize: 14 }}
            >
              Create First Post →
            </button>
          </div>
        </div>
      )}

      {!loading && !hasNoData && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 24 }}>
            <StatCard label="Followers"   value={stats?.total_followers ?? "—"} sub="Total followers" icon={I.dash} color={T.primary} loading={loading} />
            <StatCard label="Avg Likes"   value={stats?.avg_likes ?? "—"}     sub="Per post"        icon={I.heart} color={T.accent}  loading={loading} delay={50} />
            <StatCard label="Engagement"  value={stats ? `${stats.avg_engagement_rate}%` : "—"} sub="Avg rate" icon={I.trend}  color={T.gold}    loading={loading} delay={100} />
            <StatCard label="Reach"       value={stats?.total_reach ?? "—"}   sub="Total reach"     icon={I.eye}   color={T.green}   loading={loading} delay={150} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "2fr 1.2fr", gap: 18, marginBottom: 24 }}>
            <div className="fade-up" style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 24 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
                <div>
                  <div style={{ fontFamily: T.fontHead, fontWeight: 700, fontSize: 16, color: T.text }}>30-Day Reach Growth</div>
                  <div style={{ fontSize: 11, color: T.textMuted }}>Performance over the last month</div>
                </div>
                <Badge status="active" />
              </div>
              
              <div style={{ height: 180, width: "100%", position: "relative", marginTop: 10 }}>
                {chartData.length > 1 ? (
                  <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ width: "100%", height: "100%", overflow: "visible" }}>
                    <defs>
                      <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={T.primary} stopOpacity="0.3" />
                        <stop offset="100%" stopColor={T.primary} stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <path d={`M 0,100 L ${points} L 100,100 Z`} fill="url(#chartGrad)" />
                    <polyline points={points} fill="none" stroke={T.primary} strokeWidth="2" strokeLinejoin="round" />
                  </svg>
                ) : (
                  <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: T.textDim, fontSize: 13 }}>
                    Need at least 2 days of data to show chart
                  </div>
                )}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10 }}>
                   <span style={{ fontSize: 10, color: T.textDim }}>30 days ago</span>
                   <span style={{ fontSize: 10, color: T.textDim }}>Today</span>
              </div>
            </div>

            <div className="fade-up" style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 24 }}>
               <div style={{ fontFamily: T.fontHead, fontWeight: 700, fontSize: 16, color: T.text, marginBottom: 20 }}>Account Insights</div>
               <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  {[
                    { label: "Profile Views", value: stats?.profile_views || 0, icon: I.eye, color: T.blue },
                    { label: "Website Clicks", value: stats?.website_clicks || 0, icon: I.link, color: T.green },
                    { label: "Impressions", value: stats?.total_impressions || 0, icon: I.trend, color: T.accent },
                    { label: "Saves", value: stats?.total_saves || 0, icon: I.posts, color: T.gold },
                  ].map(item => (
                    <div key={item.label} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                       <div style={{ width: 32, height: 32, background: `${item.color}15`, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", color: item.color }}>{item.icon}</div>
                       <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 11, color: T.textMuted, textTransform: "uppercase", letterSpacing: ".05em" }}>{item.label}</div>
                          <div style={{ fontSize: 15, fontWeight: 700, color: T.text }}>{item.value.toLocaleString()}</div>
                       </div>
                    </div>
                  ))}
               </div>
            </div>
          </div>

          <div className="fade-up" style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <div style={{ fontFamily: T.fontHead, fontWeight: 700, fontSize: 16, color: T.text }}>Top Performing Posts</div>
            </div>
            {topPosts.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 0" }}>
                <div style={{ fontSize: 24, marginBottom: 10 }}>📸</div>
                <div style={{ fontSize: 14, color: T.textMuted }}>No posts found for this period</div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {topPosts.map((post, i) => (
                  <div key={post.id} style={{ display: "flex", alignItems: "center", gap: 14, paddingBottom: 12, borderBottom: i < topPosts.length - 1 ? `1px solid ${T.border}` : "none" }}>
                     <img src={post.edited_photo_url} style={{ width: 44, height: 44, borderRadius: 8, objectFit: "cover" }} />
                     <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{post.product_name}</div>
                        <div style={{ fontSize: 11, color: T.textMuted }}>{new Date(post.created_at).toLocaleDateString()}</div>
                     </div>
                     <div style={{ display: "flex", gap: 12 }}>
                        <div style={{ textAlign: "center" }}><div style={{ fontSize: 12, fontWeight: 700, color: T.text }}>{post.reach}</div><div style={{ fontSize: 9, color: T.textMuted }}>Reach</div></div>
                        <div style={{ textAlign: "center" }}><div style={{ fontSize: 12, fontWeight: 700, color: T.green }}>{post.engagement_rate}%</div><div style={{ fontSize: 9, color: T.textMuted }}>Eng.</div></div>
                     </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
