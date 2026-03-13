import React from "react";
import { T, useLang } from "../common/UIComponents";
import { LanguageSwitcher } from "../common/LanguageSwitcher";

const VIEW_TITLES = {
  dashboard: "dashboard",
  create:    "create",
  posts:     "posts",
  analytics: "analytics",
  billing:   "billing",
  aggregator:"aggregator",
  settings:  "settings",
  admin:     "admin",
  telegram:  "telegram",
  admin_aggregator: "admin_aggregator"
};

export const Header = ({ activeView }) => {
  const { t } = useLang();
  
  return (
    <header style={{ 
      height: 72, 
      display: "flex", 
      alignItems: "center", 
      justifyContent: "space-between", 
      padding: "0 40px", 
      background: "#0F1117", 
      borderBottom: `1px solid ${T.border}`,
      position: "sticky",
      top: 0,
      zIndex: 90
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: T.text, margin: 0 }}>
          {t(VIEW_TITLES[activeView] || "dashboard")}
        </h2>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <LanguageSwitcher />
        
        {/* Profile Circle placeholder */}
        <div style={{ width: 36, height: 36, borderRadius: "50%", background: T.surfaceAlt, border: `1px solid ${T.border}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: T.textDim }}>
          USR
        </div>
      </div>
    </header>
  );
};
