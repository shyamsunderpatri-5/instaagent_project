// frontend/src/components/views/aggregator/AnalyticsDashboard.jsx
import { useEffect, useRef } from "react";
import { T, I, Badge } from "../../common/UIComponents";

export const AnalyticsDashboard = ({ formatStats, freqData, compStats, tagStats, t }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
      {/* Metrics Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 20 }}>
          <StatCard 
            title={t("aggregator.avg_weekly_posts")} 
            value={freqData?.avg_per_week_owned || 0} 
            subtitle={t("aggregator.competitor_avg", { val: freqData?.avg_per_week_competitor || 0 })}
            icon={I.posts}
          />
          <StatCard 
            title={t("aggregator.top_format")} 
            value={formatStats.sort((a,b) => b.avg_engagement - a.avg_engagement)[0]?.media_type || "—"} 
            subtitle={t("aggregator.highest_er")}
            icon={I.zap}
          />
          <StatCard 
            title={t("aggregator.network_er")} 
            value={`${compStats?.owned?.avg_engagement || 0}%`} 
            subtitle={t("aggregator.owned_account")}
            icon={I.analytics}
          />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: 32 }}>
        {/* Frequency Chart */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>{t("aggregator.posting_frequency")}</h3>
          <FrequencyChart data={freqData?.heatmap || []} t={t} />
        </div>

        {/* Top Hashtags */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>{t("aggregator.trending_hashtags")}</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {tagStats.slice(0, 10).map((tag, idx) => (
              <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: idx < 9 ? `1px solid ${T.border}50` : "none" }}>
                <span style={{ fontSize: 13, color: T.text, fontWeight: 600 }}>#{tag.tag}</span>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 11, color: T.primary, fontWeight: 800 }}>{tag.avg_engagement}% ER</div>
                  <div style={{ fontSize: 10, color: T.textDim }}>{tag.count} posts</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.5fr", gap: 32 }}>
        {/* Content Format Distribution */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>{t("aggregator.engagement_by_format")}</h3>
          <FormatChart data={formatStats} />
        </div>

        {/* Competitor Table */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>{t("aggregator.competitor_comparison")}</h3>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
               <tr style={{ textAlign: "left", fontSize: 11, color: T.textDim, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                 <th style={{ padding: "0 0 12px 0" }}>{t("aggregator.account")}</th>
                 <th style={{ padding: "0 0 12px 0" }}>{t("aggregator.followers")}</th>
                 <th style={{ padding: "0 0 12px 0" }}>{t("aggregator.avg_er")}</th>
                 <th style={{ padding: "0 0 12px 0" }}>{t("aggregator.weekly_posts")}</th>
               </tr>
            </thead>
            <tbody>
              {[compStats?.owned, ...(compStats?.competitors || [])].filter(Boolean).map((acc, idx) => (
                <tr key={idx} style={{ borderTop: `1px solid ${T.border}40`, fontSize: 13 }}>
                  <td style={{ padding: "12px 0", fontWeight: 700, color: idx === 0 ? T.primary : T.text }}>
                    @{acc.username} {idx === 0 && <span style={{ fontSize: 9 }}>({t("aggregator.you")})</span>}
                  </td>
                  <td style={{ padding: "12px 0" }}>{acc.followers.toLocaleString()}</td>
                  <td style={{ padding: "12px 0", fontWeight: 800 }}>{acc.avg_engagement}%</td>
                  <td style={{ padding: "12px 0" }}>{acc.posts_per_week}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ title, value, subtitle, icon }) => (
  <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 20, padding: 24, display: "flex", gap: 16, alignItems: "center" }}>
    <div style={{ background: `${T.primary}10`, width: 48, height: 48, borderRadius: 14, display: "flex", alignItems: "center", justifyContent: "center", color: T.primary }}>
      {icon}
    </div>
    <div>
      <div style={{ fontSize: 12, color: T.textDim, fontWeight: 600, marginBottom: 4 }}>{title}</div>
      <div style={{ fontSize: 24, fontWeight: 800, color: T.text, lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 11, color: T.textMuted, marginTop: 4 }}>{subtitle}</div>
    </div>
  </div>
);

const FormatChart = ({ data }) => {
  const canvasRef = useRef(null);
  useEffect(() => {
    if (typeof Chart === "undefined" || !data.length) return;
    const ctx = canvasRef.current.getContext("2d");
    const chart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.map(d => d.media_type),
        datasets: [{
          label: "Avg Engagement %",
          data: data.map(d => d.avg_engagement),
          backgroundColor: T.primary + "80",
          borderColor: T.primary,
          borderWidth: 1,
          borderRadius: 8
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { grid: { display: false } }, y: { grid: { display: false } } }
      }
    });
    return () => chart.destroy();
  }, [data]);
  return <canvas ref={canvasRef} height="120"></canvas>;
};

const FrequencyChart = ({ data, t }) => {
  const canvasRef = useRef(null);
  useEffect(() => {
    if (typeof Chart === "undefined" || !data.length) return;
    const ctx = canvasRef.current.getContext("2d");
    const chart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.map(d => d.day),
        datasets: [
          {
            label: t("aggregator.owned"),
            data: data.map(d => d.owned_count),
            backgroundColor: T.primary,
            borderRadius: 6
          },
          {
            label: t("aggregator.competitor_avg"),
            data: data.map(d => d.competitor_avg_count),
            backgroundColor: T.surfaceAlt,
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 6, font: { weight: "700" } } } },
        scales: { x: { grid: { display: false } }, y: { grid: { color: T.border + "40" } } }
      }
    });
    return () => chart.destroy();
  }, [data]);
  return <canvas ref={canvasRef} height="120"></canvas>;
};
