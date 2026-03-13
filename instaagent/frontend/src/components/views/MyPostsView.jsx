// frontend/src/components/views/MyPostsView.jsx
// FIXED: Clicking a post opens a full detail modal (full caption + all hashtags + action buttons)
// NEW: PostDetailModal component shows everything including SEO hashtags

import { useState, useEffect, useCallback } from "react";
import { T, I, Badge, useToast, Spinner } from "../common/UIComponents";
import { api } from "../common/api";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Full Detail Modal ─────────────────────────────────────────────────────────
const PostDetailModal = ({ post, token, onClose, onRefresh }) => {
  const [publishing, setPublishing] = useState(false);
  const [deleting,   setDeleting]   = useState(false);
  const [msg,        setMsg]        = useState("");

  const handlePublish = async () => {
    setPublishing(true); setMsg("");
    try {
      const res = await fetch(`${API}/api/v1/posts/${post.id}/publish-now`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || t("posts.publish_failed"));
      setMsg(`${t("posts.publish_success")} ${data.permalink || ""}`);
      onRefresh();
    } catch (e) { setMsg(`❌ ${e.message}`); }
    finally { setPublishing(false); }
  };

  const handleDelete = async () => {
    if (!window.confirm(t("posts.delete_confirm"))) return;
    setDeleting(true);
    try {
      await fetch(`${API}/api/v1/posts/${post.id}`, {
        method: "DELETE", headers: { Authorization: `Bearer ${token}` }
      });
      onRefresh(); onClose();
    } catch (e) { setMsg(`❌ ${e.message}`); }
    finally { setDeleting(false); }
  };

  const hashtags = post.hashtags || [];
  const captionEn = post.caption_english || "";
  const captionHi = post.caption_hindi || "";

  return (
    <div
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.72)", backdropFilter: "blur(6px)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}
    >
      <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 24, maxWidth: 740, width: "100%", maxHeight: "90vh", overflow: "auto", padding: 32, position: "relative" }}>
        {/* Close */}
        <button onClick={onClose} style={{ position: "absolute", top: 18, right: 18, background: T.surfaceAlt, border: "none", borderRadius: "50%", width: 34, height: 34, fontSize: 16, cursor: "pointer", color: T.text }}>✕</button>

        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
          <div style={{ fontFamily: T.fontHead, fontSize: 20, fontWeight: 800, color: T.text, flex: 1 }}>
            {post.product_name}
          </div>
          <Badge status={post.status} />
        </div>

        {/* Photo row */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 22 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.08em" }}>{t("posts.original")}</div>
            <div style={{ borderRadius: 12, overflow: "hidden", height: 200, background: T.surfaceAlt }}>
              {post.original_photo_url
                ? <img src={post.original_photo_url} alt={t("posts.original")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                : <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", fontSize: 32 }}>📷</div>}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: T.primary, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.08em" }}>{t("posts.post_photo")}</div>
            <div style={{ borderRadius: 12, overflow: "hidden", height: 200, background: T.surfaceAlt, border: `2px solid ${T.primary}40` }}>
              {(post.edited_photo_url || post.original_photo_url)
                ? <img src={post.edited_photo_url || post.original_photo_url} alt={t("posts.post_photo")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                : <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", fontSize: 32 }}>📷</div>}
            </div>
          </div>
        </div>

        {/* Caption — FULL, not truncated */}
        {(captionHi || captionEn) && (
          <div style={{ background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 14, padding: 18, marginBottom: 18 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: T.textMuted, marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}>
              {t("posts.ai_caption_label")}
            </div>
            {captionHi && (
              <div style={{ fontSize: 14, color: T.text, lineHeight: 1.8, fontFamily: T.fontDevan, marginBottom: captionEn ? 12 : 0, whiteSpace: "pre-wrap" }}>
                {captionHi}
              </div>
            )}
            {captionEn && captionHi && <div style={{ borderTop: `1px solid ${T.border}`, marginBottom: 12 }} />}
            {captionEn && (
              <div style={{ fontSize: 13, color: T.textMuted, lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
                {captionEn}
              </div>
            )}
          </div>
        )}

        {/* Hashtags — ALL of them as chips */}
        {hashtags.length > 0 && (
          <div style={{ marginBottom: 18 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: T.textMuted, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>
              {t("posts.hashtag_label")} ({hashtags.length})
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {hashtags.map((h, i) => (
                <span
                  key={i}
                  onClick={() => navigator.clipboard?.writeText(h)}
                  title="Click to copy"
                  style={{ background: `${T.primary}18`, color: T.primary, fontSize: 12, padding: "4px 10px", borderRadius: 20, fontWeight: 600, cursor: "copy", transition: "all 0.15s" }}
                >
                  {h}
                </span>
              ))}
            </div>
            <div style={{ fontSize: 11, color: T.textDim, marginTop: 6 }}>{t("posts.hashtag_copy_hint")}</div>
          </div>
        )}

        {/* Meta info */}
        <div style={{ display: "flex", gap: 20, marginBottom: 20, flexWrap: "wrap" }}>
          {post.created_at && (
            <div style={{ fontSize: 12, color: T.textMuted }}>
              {t("posts.created_at")}: {new Date(post.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
            </div>
          )}
          {post.scheduled_at && post.status === "scheduled" && (
            <div style={{ fontSize: 12, color: T.primary, fontWeight: 600 }}>
              {t("posts.scheduled_at")}: {new Date(new Date(post.scheduled_at).getTime() + 19800000).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })} IST
            </div>
          )}
          {post.posted_at && (
            <div style={{ fontSize: 12, color: T.green, fontWeight: 600 }}>
              {t("posts.posted_at")}: {new Date(new Date(post.posted_at).getTime() + 19800000).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })} IST
            </div>
          )}
        </div>

        {post.status === "posted" && (
          <div style={{ display: "flex", gap: 20, padding: "12px 0", borderTop: `1px solid ${T.border}`, marginBottom: 16 }}>
            <span style={{ fontSize: 13, color: T.textMuted, display: "flex", alignItems: "center", gap: 6 }}>{I.heart} {post.likes_count || 0} likes</span>
            <span style={{ fontSize: 13, color: T.textMuted, display: "flex", alignItems: "center", gap: 6 }}>{I.eye} {post.reach || 0} reach</span>
            <span style={{ fontSize: 13, color: T.textMuted, display: "flex", alignItems: "center", gap: 6 }}>{I.chat} {post.comments_count || 0} comments</span>
            {post.instagram_permalink && (
              <a href={post.instagram_permalink} target="_blank" rel="noreferrer" style={{ marginLeft: "auto", fontSize: 12, color: T.primary, fontWeight: 600 }}>View on Instagram →</a>
            )}
          </div>
        )}

        {msg && (
          <div style={{ padding: "10px 14px", borderRadius: 10, background: msg.startsWith("✅") ? `${T.green}18` : `${T.red}18`, color: msg.startsWith("✅") ? T.green : T.red, fontSize: 13, marginBottom: 14 }}>
            {msg}
          </div>
        )}

        {/* Action buttons */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          {post.status === "ready" && (
            <button
              onClick={handlePublish}
              disabled={publishing}
              style={{ padding: "11px 22px", background: T.primary, color: "#fff", border: "none", borderRadius: 10, fontWeight: 700, fontSize: 14, cursor: publishing ? "wait" : "pointer", display: "flex", alignItems: "center", gap: 8 }}
            >
              {publishing ? <><Spinner size={14} color="#fff" /> {t("common.processing")}</> : `🚀 ${t("create.publish_btn")}`}
            </button>
          )}
          {post.status === "posted" && post.instagram_permalink && (
            <a href={post.instagram_permalink} target="_blank" rel="noreferrer"
              style={{ padding: "11px 22px", background: `linear-gradient(135deg, #833AB4, #FD1D1D, #FCB045)`, color: "#fff", borderRadius: 10, fontWeight: 700, fontSize: 14, textDecoration: "none" }}>
              {I.ig} {t("posts.view_on_ig")}
            </a>
          )}
          <button
            onClick={handleDelete}
            disabled={deleting}
            style={{ padding: "11px 20px", background: "transparent", color: T.red, border: `1px solid ${T.red}50`, borderRadius: 10, fontWeight: 600, fontSize: 13, cursor: deleting ? "wait" : "pointer" }}
          >
            {deleting ? t("posts.deleting") : t("posts.delete_btn")}
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Main PostsView ────────────────────────────────────────────────────────────
export const PostsView = ({ token }) => {
  const [posts,    setPosts]    = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [filter,   setFilter]   = useState("all");
  const [selected, setSelected] = useState(null);
  const { show, Toast }         = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await api.get("/api/v1/posts?page_size=50", token);
      setPosts(d.posts || []);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const FILTERS = ["all","posted","scheduled","ready","processing","failed"];
  const filtered = filter === "all" ? posts : posts.filter(p => p.status === filter);

  return (
    <div style={{ padding: "28px 32px", maxWidth: 920 }}>
      {Toast}
      {selected && (
        <PostDetailModal
          post={selected}
          token={token}
          onClose={() => setSelected(null)}
          onRefresh={load}
        />
      )}

      <div className="fade-up" style={{ marginBottom: 22 }}>
        <h1 style={{ fontFamily: T.fontHead, fontSize: 24, fontWeight: 800, color: T.text, marginBottom: 6 }}>{t("posts.title")}</h1>
        <p style={{ color: T.textMuted, fontSize: 14 }}>{t("posts.subtitle")}</p>
      </div>

      <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)} style={{ padding: "7px 14px", borderRadius: 20, border: `1px solid ${filter === f ? T.primary : T.border}`, background: filter === f ? `${T.primary}18` : "transparent", color: filter === f ? T.primary : T.textMuted, fontSize: 12, fontWeight: filter === f ? 700 : 400, cursor: "pointer", textTransform: "capitalize" }}>
            {f}
          </button>
        ))}
        <button onClick={load} style={{ marginLeft: "auto", padding: "7px 12px", border: `1px solid ${T.border}`, borderRadius: 10, background: "transparent", color: T.textMuted, fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
          {I.refresh} {t("aggregator.refresh")}
        </button>
      </div>

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {[1,2,3].map(i => <div key={i} className="shimmer" style={{ height: 84, borderRadius: 14 }} />)}
        </div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: "center", padding: 60 }}>
          <div style={{ fontSize: 44, marginBottom: 14 }}>📭</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: T.text, marginBottom: 6 }}>{t("posts.no_posts")}</div>
          <div style={{ fontSize: 14, color: T.textMuted }}>{t("posts.create_first")}</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {filtered.map((post, i) => {
            const captionPreview = post.caption_hindi?.slice(0, 160) || post.caption_english?.slice(0, 160) || "Processing…";
            const hashtagCount   = (post.hashtags || []).length;
            return (
              <div
                key={post.id}
                className="fade-up"
                onClick={() => setSelected(post)}
                style={{ animationDelay: `${i * 30}ms`, background: T.surface, border: `1px solid ${T.border}`, borderRadius: 14, padding: "16px 18px", display: "flex", alignItems: "center", gap: 14, cursor: "pointer", transition: "all 0.15s" }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = T.primary; e.currentTarget.style.transform = "translateY(-1px)"; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.transform = "none"; }}
              >
                {/* Thumbnail */}
                {(post.edited_photo_url || post.original_photo_url)
                  ? <img src={post.edited_photo_url || post.original_photo_url} alt="" style={{ width: 60, height: 60, objectFit: "cover", borderRadius: 10, flexShrink: 0 }} />
                  : <div style={{ width: 60, height: 60, background: `${T.primary}18`, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, flexShrink: 0 }}>📷</div>}

                {/* Text */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: T.text, marginBottom: 4 }}>{post.product_name}</div>
                  <div style={{ fontSize: 12, color: T.textMuted, marginBottom: 4 }}>
                    {captionPreview}{captionPreview.length >= 160 ? "… " : " "}
                    <span style={{ color: T.primary, fontWeight: 600, fontSize: 11 }}>{t("posts.read_more")} ↗</span>
                  </div>
                  {hashtagCount > 0 && (
                    <div style={{ fontSize: 11, color: T.primary, fontWeight: 600 }}>#{hashtagCount} hashtags</div>
                  )}
                  {post.status === "posted" && (
                    <div style={{ display: "flex", gap: 12, marginTop: 4 }}>
                      <span style={{ fontSize: 11, color: T.textMuted }}>{I.heart} {post.likes_count || 0}</span>
                      <span style={{ fontSize: 11, color: T.textMuted }}>{I.eye} {post.reach || 0}</span>
                      <span style={{ fontSize: 11, color: T.textMuted }}>{I.chat} {post.comments_count || 0}</span>
                    </div>
                  )}
                  {post.status === "scheduled" && post.scheduled_at && (
                    <div style={{ fontSize: 11, color: T.primary, fontWeight: 600, marginTop: 3 }}>
                      ⏰ {new Date(new Date(post.scheduled_at).getTime() + 19800000).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })} IST
                    </div>
                  )}
                </div>

                {/* Badge + arrow */}
                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8, flexShrink: 0 }}>
                  <Badge status={post.status} />
                  <span style={{ fontSize: 16, color: T.textDim }}>›</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
