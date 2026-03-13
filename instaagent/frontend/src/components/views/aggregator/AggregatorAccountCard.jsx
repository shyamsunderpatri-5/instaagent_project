// frontend/src/components/views/aggregator/AggregatorAccountCard.jsx
import React from "react";
import { T, I, Badge } from "../../common/UIComponents";

export const AggregatorAccountCard = ({ acc, t }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 12, padding: 12, background: T.surfaceAlt, borderRadius: 14, border: `1px solid ${T.border}` }}>
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
);
