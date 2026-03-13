// frontend/src/components/views/aggregator/AIInsightsPanel.jsx
import React from "react";
import { T, I } from "../../common/UIComponents";

export const AIInsightsPanel = ({ insights, t }) => {
  if (!insights) return null;

  const renderList = (title, items, icon, color = T.primary) => {
    if (!items || items.length === 0) return null;
    return (
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, marginBottom: 12, textTransform: "uppercase", display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ color }}>{icon}</span> {title}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {items.map((item, i) => (
            <div key={i} style={{ 
              fontSize: 13, 
              background: `${color}08`, 
              padding: "10px 14px", 
              borderRadius: 10, 
              borderLeft: `3px solid ${color}`,
              color: T.text
            }}>{item}</div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="fade-up" style={{ 
      background: `linear-gradient(135deg, ${T.surfaceAlt}, ${T.bg})`, 
      border: `2px solid ${T.primary}20`, 
      borderRadius: 24, 
      padding: 24,
      marginBottom: 24
    }}>
      <h3 style={{ color: T.primary, fontSize: 15, fontWeight: 800, marginBottom: 20, display: "flex", alignItems: "center", gap: 8 }}>
        {I.zap} {t("aggregator.ai_strategy")}
      </h3>

      {/* Enhanced Metrics */}
      {(insights.content_sentiment || insights.top_format) && (
        <div style={{ marginBottom: 24, padding: "16px", background: T.surface, borderRadius: 16, border: `1px solid ${T.border}` }}>
          {insights.content_sentiment && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: T.textDim, fontWeight: 700, textTransform: "uppercase", marginBottom: 4 }}>{t("aggregator.content_sentiment")}</div>
              <div style={{ fontSize: 14, fontWeight: 800, color: T.primary }}>{insights.content_sentiment}</div>
            </div>
          )}
          {insights.top_format && (
            <div>
              <div style={{ fontSize: 10, color: T.textDim, fontWeight: 700, textTransform: "uppercase", marginBottom: 4 }}>{t("aggregator.top_format_ai")}</div>
              <div style={{ fontSize: 14, fontWeight: 800, color: T.text }}>{insights.top_format}</div>
            </div>
          )}
        </div>
      )}

      {renderList(t("aggregator.post_ideas"), insights.post_ideas, I.zap)}
      {renderList(t("aggregator.trend_summaries"), insights.trend_summaries, I.analytics)}
      {renderList(t("aggregator.posting_times"), insights.best_posting_times, I.clock)}
      {renderList(t("aggregator.caption_suggestions"), insights.caption_suggestions, I.create)}
      {renderList(t("aggregator.weak_spots"), insights.weak_spots, I.warning, T.red)}

      <div style={{ fontSize: 10, color: T.textDim, textAlign: "center", marginTop: 12, fontStyle: "italic" }}>
        {t("aggregator.ai_footer")}
      </div>
    </div>
  );
};
