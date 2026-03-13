// frontend/src/components/views/aggregator/AIInsightsPanel.jsx
import React from "react";
import { T, I } from "../../common/UIComponents";

export const AIInsightsPanel = ({ insights, t }) => {
  if (!insights) return null;

  return (
    <div className="fade-up" style={{ 
      background: `linear-gradient(135deg, ${T.surfaceAlt}, ${T.bg})`, 
      border: `2px solid ${T.primary}40`, 
      borderRadius: 20, 
      padding: 24,
      marginBottom: 24
    }}>
       <h3 style={{ color: T.primary, fontSize: 15, fontWeight: 800, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
         {I.zap} {t("aggregator.ai_strategy")}
       </h3>
       
       <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          <div>
             <div style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, marginBottom: 8, textTransform: "uppercase" }}>
               {t("aggregator.post_ideas")}
             </div>
             <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
               {insights.post_ideas?.map((idea, i) => (
                 <div key={i} style={{ 
                   fontSize: 13, 
                   background: `${T.primary}10`, 
                   padding: "8px 12px", 
                   borderRadius: 8, 
                   borderLeft: `3px solid ${T.primary}` 
                 }}>{idea}</div>
               ))}
             </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
             <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, marginBottom: 8, textTransform: "uppercase" }}>
                  {t("aggregator.market_trends")}
                </div>
                <ul style={{ paddingLeft: 16, margin: 0 }}>
                  {insights.trend_summaries?.map((trend, i) => (
                    <li key={i} style={{ fontSize: 13, color: T.text, marginBottom: 4 }}>{trend}</li>
                  ))}
                </ul>
             </div>

             <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, marginBottom: 8, textTransform: "uppercase" }}>
                  {t("aggregator.best_posting_times")}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {insights.best_posting_times?.map((time, i) => (
                    <span key={i} style={{ fontSize: 11, background: T.surface, border: `1px solid ${T.border}`, padding: "4px 8px", borderRadius: 6 }}>{time}</span>
                  ))}
                </div>
             </div>
          </div>
       </div>

       {insights.caption_suggestions && (
          <div style={{ marginTop: 24, paddingTop: 20, borderTop: `1px dashed ${T.border}` }}>
             <div style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, marginBottom: 12, textTransform: "uppercase" }}>
               {t("aggregator.caption_suggestions")}
             </div>
             <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
                {insights.caption_suggestions.map((hook, i) => (
                   <div key={i} style={{ fontSize: 12, fontStyle: "italic", color: T.textDim, background: T.surfaceAlt, padding: 12, borderRadius: 12 }}>
                      "{hook}"
                   </div>
                ))}
             </div>
          </div>
       )}
    </div>
  );
};
