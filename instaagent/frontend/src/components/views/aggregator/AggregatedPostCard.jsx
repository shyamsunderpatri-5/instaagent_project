// frontend/src/components/views/aggregator/AggregatedPostCard.jsx
import React, { useState } from "react";
import { T, I, Spinner } from "../../common/UIComponents";
import { api } from "../../common/api";

export const AggregatedPostCard = ({ post, token, onSaveSuccess, isAdmin, t }) => {
  const [saving, setSaving] = useState(false);
  const [hidden, setHidden] = useState(post.hidden || false);

  const handleSave = async () => {
    // ... same as before
  };

  const handleHide = async () => {
    try {
      await api.patch(`/api/v1/aggregator/admin/posts/${post.id}`, { hidden: !hidden }, token);
      setHidden(!hidden);
    } catch (err) {
      console.error("Moderation failed", err);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Delete this post permanently?")) return;
    try {
      await api.delete(`/api/v1/aggregator/admin/posts/${post.id}`, token);
      setHidden(true); // Treat as hidden in UI after delete
    } catch (err) {
      console.error("Delete failed", err);
    }
  };

  if (hidden && !isAdmin) return null;

  return (
    <div style={{ background: T.surfaceAlt, borderRadius: 16, overflow: "hidden", border: `1px solid ${T.border}`, display: "flex", flexDirection: "column", opacity: hidden ? 0.5 : 1 }}>
      {post.media_url ? (
        <img src={post.media_url} alt="" style={{ width: "100%", height: 180, objectFit: "cover" }} />
      ) : (
        <div style={{ width: "100%", height: 180, background: T.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>📷</div>
      )}
      <div style={{ padding: 12, flex: 1, display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: T.primary }}>@{post.aggregator_accounts?.instagram_username}</span>
          <span style={{ fontSize: 11, color: T.textMuted }}>{new Date(post.posted_at).toLocaleDateString()}</span>
        </div>
        <div style={{ fontSize: 12, height: 36, overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", color: T.text, marginBottom: 12 }}>{post.caption}</div>
        
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "auto" }}>
          <div style={{ display: "flex", gap: 8 }}>
             <span style={{ fontSize: 11, fontWeight: 700, display: "flex", alignItems: "center", gap: 4 }}>{I.heart} {post.likes}</span>
             <span style={{ fontSize: 11, fontWeight: 700, display: "flex", alignItems: "center", gap: 4 }}>{I.chat} {post.comments}</span>
          </div>
          
          <div style={{ display: "flex", gap: 4 }}>
            {isAdmin && (
              <>
                <button 
                  onClick={handleHide}
                  style={{ background: T.surfaceAlt, color: T.textMuted, border: `1px solid ${T.border}`, borderRadius: 8, padding: "4px 8px", fontSize: 11, cursor: "pointer" }}
                >
                  {hidden ? "Show" : "Hide"}
                </button>
                <button 
                  onClick={handleDelete}
                  style={{ background: `${T.red}10`, color: T.red, border: `1px solid ${T.red}40`, borderRadius: 8, padding: "4px 8px", fontSize: 11, cursor: "pointer" }}
                >
                  Delete
                </button>
              </>
            )}
            <button 
              disabled={saving}
              onClick={handleSave}
              style={{ 
                background: saving ? T.surfaceAlt : `${T.primary}20`, 
                color: T.primary, 
                border: `1px solid ${T.primary}40`, 
                borderRadius: 8, 
                padding: "4px 8px", 
                fontSize: 11, 
                fontWeight: 700, 
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 4
              }}
            >
              {saving ? <Spinner size={10} color={T.primary} /> : I.create} {t("aggregator.save_to_my_posts")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
