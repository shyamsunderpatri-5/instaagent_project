// frontend/src/components/views/CreatePostView.jsx
// FIXED: isEnhanced default = false (was true — caused bad background removal)
// NEW: Step 3 shows full caption + hashtags + Post Now / Schedule Later options

import { useState, useRef, useEffect } from "react";
import { T, I, Spinner, Toggle, useFeatures, useLang } from "../common/UIComponents";
import { api } from "../common/api";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ACCEPTED = "image/*";

export const CreatePostView = ({ user, token, onPostCreated }) => {
  const [step,        setStep]        = useState(1);
  const [photos,      setPhotos]      = useState([]);
  const [product,     setProduct]     = useState("");
  const [category,    setCategory]    = useState("jewellery");
  const [info,        setInfo]        = useState("");
  const [procStep,    setProcStep]    = useState(0);
  const [error,       setError]       = useState("");
  // isEnhanced defaults to FALSE — background removal was causing bad results
  const [isEnhanced,  setIsEnhanced]  = useState(false);
  const [postData,    setPostData]    = useState(null);
  const [scheduling,  setScheduling]  = useState(false);
  const [publishing,  setPublishing]  = useState(false);
  const [scheduleMode,setScheduleMode]= useState(null); // null | "settings" | "custom"
  const [customDt,    setCustomDt]    = useState("");
  const [actionDone,  setActionDone]  = useState(null); // { type, message }
  const fileRef = useRef();
  const { features } = useFeatures();
  const { t } = useLang();

  // Poll for edited photo URL after upload
  useEffect(() => {
    let interval;
    let startTime = Date.now();
    const TIMEOUT_MS = 120000; // 120s timeout

    if (step === 3 && postData?.post_id && !postData.edited_photo_url) {
      interval = setInterval(async () => {
        // Timeout check
        if (Date.now() - startTime > TIMEOUT_MS) {
          setError("Processing is taking longer than expected. Please check 'My Posts' later.");
          clearInterval(interval);
          return;
        }

        try {
          const res = await fetch(`${API}/api/v1/posts/${postData.post_id}`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          if (res.ok) {
            const data = await res.json();
            if (data.edited_photo_url || data.status === "ready" || data.status === "failed") {
              setPostData(prev => ({ ...prev, ...data }));
              clearInterval(interval);
              if (data.status === "failed") setError(data.error_message || "Processing failed");
            }
          }
        } catch (e) { 
          console.error("Polling error:", e);
        }
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [step, postData, token]);

  const handleFiles = (files) => {
    const imgs = Array.from(files).filter(f => {
      const type = f.type.toLowerCase();
      const name = f.name.toLowerCase();
      return type.startsWith("image/") || name.endsWith(".heic") || name.endsWith(".heif");
    });

    if (imgs.length === 0) {
      setError("Please select valid image files (JPG, PNG, WebP, HEIC).");
      return;
    }
    
    // HEIC/HEIF Rejection (C1.4): Backend lacks system libraries for native processing
    if (imgs[0].name.toLowerCase().endsWith(".heic") || imgs[0].name.toLowerCase().endsWith(".heif")) {
      setError("HEIC/HEIF not supported yet. Please use a JPG/PNG or convert your photo first.");
      setPhotos([]);
      return;
    }
    setError("");

    setPhotos(imgs);
  };

  const runProcess = async () => {
    if (photos.length === 0 || !product) { setError("Please select a photo and enter a product name."); return; }
    setStep(2); setError(""); setProcStep(0);
    try {
      const fd = new FormData();
      fd.append("photo", photos[0]);
      fd.append("product_name", product);
      fd.append("product_type", category);
      fd.append("additional_info", info);
      fd.append("is_enhanced", isEnhanced);
      fd.append("is_carousel_duo", false);
      const res = await fetch(`${API}/api/v1/posts/create`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd
      });
      if (!res.ok) throw new Error("Processing failed. Please try again.");
      const data = await res.json();
      setPostData(data.post || data);
      setProcStep(2);
      setTimeout(() => setStep(3), 1500);
    } catch (e) { setError(e.message); setStep(1); }
  };

  const doPublishNow = async () => {
    if (!postData?.post_id) return;
    setPublishing(true);
    try {
      const res = await fetch(`${API}/api/v1/posts/${postData.post_id}/publish-now`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Publish failed");
      setActionDone({ type: "posted", message: `✅ Posted! ${data.permalink || ""}` });
    } catch (e) {
      setError(e.message);
    } finally {
      setPublishing(false);
    }
  };

  const doScheduleFromSettings = async () => {
    if (!postData?.post_id) return;
    setScheduling(true);
    try {
      const res = await fetch(`${API}/api/v1/posts/${postData.post_id}/schedule-from-settings`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Schedule failed");
      setActionDone({ type: "scheduled", message: `⏰ Scheduled for ${data.scheduled_at_ist}` });
    } catch (e) {
      setError(e.message);
    } finally {
      setScheduling(false);
    }
  };

  const doScheduleCustom = async () => {
    if (!postData?.post_id || !customDt) return;
    setScheduling(true);
    try {
      // customDt is "YYYY-MM-DDTHH:mm"
      // Force it to be interpreted as IST (+05:30) regardless of browser timezone
      const istString = customDt + "+05:30";
      const utcIso = new Date(istString).toISOString();
      const res = await fetch(
        `${API}/api/v1/posts/${postData.post_id}/schedule?scheduled_at=${encodeURIComponent(utcIso)}`,
        { method: "POST", headers: { Authorization: `Bearer ${token}` } }
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Schedule failed");
      setActionDone({ type: "scheduled", message: `⏰ Scheduled for ${data.scheduled_at_ist}` });
    } catch (e) {
      setError(e.message);
    } finally {
      setScheduling(false);
    }
  };

  const handleSuccess = () => {
    if (onPostCreated) onPostCreated();
    reset();
  };

  const reset = () => {
    setStep(1); setPhotos([]); setProduct(""); setInfo(""); setError("");
    setPostData(null); setScheduleMode(null); setCustomDt(""); setActionDone(null);
    setIsEnhanced(false);
  };

  const inputStyle = { width: "100%", background: T.surfaceAlt, border: `1px solid ${T.borderLight}`, borderRadius: 10, padding: "11px 14px", color: T.text, fontSize: 14, boxSizing: "border-box" };
  const hashtags  = postData?.hashtags || [];
  const captionEn = postData?.caption_english || "";
  const captionHi = postData?.caption_hindi  || "";
  const postReady = postData?.status === "ready" || !!(postData?.edited_photo_url);

  const CATEGORIES = [
  { value: "jewellery",   label: "💍 Jewellery" },
  { value: "clothing",    label: "👗 Clothing & Fashion" },
  { value: "food",        label: "🍛 Food & Restaurant" },
  { value: "electronics", label: "📱 Electronics" },
  { value: "handmade",    label: "🎨 Handmade & Craft" },
  { value: "furniture",   label: "🏠 Furniture & Home Decor" },
  { value: "cosmetics",   label: "💄 Beauty & Skincare" },
  { value: "grocery",     label: "🛒 Grocery & Kirana" },
  { value: "fitness",     label: "💪 Fitness & Wellness" },
  { value: "education",   label: "📚 Education & Courses" },
  { value: "real_estate", label: "🏗️ Real Estate" },
  { value: "travel",      label: "✈️ Travel & Tours" },
  { value: "automobile",  label: "🚗 Automobile" },
  { value: "other",       label: "🏪 Other Business" },
];

  return (
    <div style={{ padding: "28px 32px", maxWidth: 720 }}>
      <div style={{ marginBottom: 26 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: T.text, marginBottom: 4 }}>
          {t("create.title")}
        </h1>
        <p style={{ color: T.textMuted, fontSize: 14 }}>{t("create.photo_desc")}</p>
      </div>

      {/* ── STEP 1: Photo + Product Info ──────────────────────────────────── */}
      {step === 1 && (
        <div className="fade-up">
          {/* Drop zone */}
          <div
            onClick={() => fileRef.current.click()}
            onDragOver={e => e.preventDefault()}
            onDrop={e => { e.preventDefault(); handleFiles(e.dataTransfer.files); }}
            style={{ border: `2px dashed ${photos.length > 0 ? T.primary : T.border}`, borderRadius: 16, padding: 36, textAlign: "center", cursor: "pointer", marginBottom: 18, background: photos.length > 0 ? `${T.primary}10` : "transparent", transition: "all .2s" }}
          >
            <input ref={fileRef} type="file" accept={ACCEPTED} style={{ display: "none" }} onChange={e => handleFiles(e.target.files)} />
            {photos.length > 0 ? (
              <div>
                <div style={{ fontSize: 28, marginBottom: 8 }}>📷</div>
                <div style={{ fontWeight: 700, color: T.primary }}>{photos[0].name}</div>
                <div style={{ fontSize: 11, color: T.textMuted, marginTop: 4 }}>{t("common.upload")}</div>
                {/* Preview */}
                <img
                  src={URL.createObjectURL(photos[0])}
                  alt="preview"
                  style={{ marginTop: 12, maxHeight: 160, maxWidth: "100%", objectFit: "contain", borderRadius: 10 }}
                />
              </div>
            ) : (
              <div>
                <div style={{ fontSize: 36, marginBottom: 12 }}>{I.upload}</div>
                <div style={{ fontWeight: 600, color: T.text }}>{t("common.first_photo")}</div>
                <div style={{ fontSize: 12, color: T.textMuted, marginTop: 6 }}>JPG, PNG, HEIC, WebP — any format</div>
                <div style={{ fontSize: 11, color: T.textDim, marginTop: 4 }}>{t("aggregator.ai_footer")}</div>
              </div>
            )}
          </div>

          {error && (
            <div style={{ background: `${T.red}18`, border: `1px solid ${T.red}50`, borderRadius: 10, padding: "10px 14px", color: T.red, fontSize: 13, marginBottom: 14, display: "flex", alignItems: "center", gap: 8 }}>
              {I.alert} {error}
            </div>
          )}

          <input value={product} onChange={e => setProduct(e.target.value)} placeholder={t("create.product_name")} style={{ ...inputStyle, marginBottom: 12 }} />

          <select value={category} onChange={e => setCategory(e.target.value)} style={{ ...inputStyle, marginBottom: 12 }}>
            {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>

          <textarea value={info} onChange={e => setInfo(e.target.value)} placeholder={t("create.price")} rows={2} style={{ ...inputStyle, marginBottom: 14, resize: "vertical" }} />

          {/* AI Photo Editing — DEFAULT OFF (user wants original unless they explicitly opt-in) */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18, background: T.surfaceAlt, padding: "12px 16px", borderRadius: 12, border: `1px solid ${T.border}` }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: T.text }}>AI Sharpening & Color Enhancement</div>
              <div style={{ fontSize: 11, color: T.textMuted, marginTop: 2 }}>Fix blurry pics & lift colors. Keep OFF for original photo.</div>
            </div>
            <Toggle value={isEnhanced} onChange={setIsEnhanced} />
          </div>

          <button
            onClick={runProcess}
            disabled={photos.length === 0 || !product}
            style={{ width: "100%", padding: 14, background: (photos.length === 0 || !product) ? T.border : T.primary, color: "#fff", border: "none", borderRadius: 12, fontWeight: 700, fontSize: 15, cursor: (photos.length === 0 || !product) ? "not-allowed" : "pointer", transition: "all .2s", opacity: (photos.length === 0 || !product) ? 0.5 : 1 }}
          >
            ✨ Generate AI Caption &amp; Hashtags
          </button>
        </div>
      )}

      {/* ── STEP 2: Processing ────────────────────────────────────────────── */}
      {step === 2 && (
        <div style={{ textAlign: "center", padding: 40 }}>
          <Spinner size={36} color={T.primary} />
          <div style={{ fontSize: 18, fontWeight: 700, marginTop: 20, color: T.text }}>
            {procStep === 0 && `📤 ${t("common.upload")}`}
            {procStep === 1 && `🔍 ${t("common.processing")}`}
            {procStep >= 2 && `✍️ ${t("common.generate")}`}
          </div>
          <div style={{ fontSize: 13, color: T.textMuted, marginTop: 8 }}>
            AI is working its magic (~12s)
          </div>
        </div>
      )}

      {/* ── STEP 3: Review + Publish/Schedule ─────────────────────────────── */}
      {step === 3 && (
        <div className="fade-up">
          {/* Action Done Banner */}
          {actionDone && (
            <div style={{ background: actionDone.type === "posted" ? `${T.green}18` : `${T.primary}18`, border: `1px solid ${actionDone.type === "posted" ? T.green : T.primary}40`, borderRadius: 14, padding: "16px 20px", marginBottom: 20, textAlign: "center" }}>
              <div style={{ fontSize: 20, marginBottom: 6 }}>{actionDone.type === "posted" ? "🎉" : "⏰"}</div>
              <div style={{ fontWeight: 700, color: actionDone.type === "posted" ? T.green : T.primary, fontSize: 15 }}>{actionDone.message}</div>
              <button onClick={handleSuccess} style={{ marginTop: 12, padding: "10px 22px", background: T.primary, color: "#fff", border: "none", borderRadius: 10, fontWeight: 700, cursor: "pointer" }}>{t("create.title")}</button>
            </div>
          )}

          {!actionDone && (
            <>
              {/* Photo Comparison */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 22 }}>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: T.textMuted, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.08em" }}>Original Photo</div>
                  <div style={{ borderRadius: 12, overflow: "hidden", border: `1px solid ${T.border}`, height: 180, background: T.surfaceAlt, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    {postData?.original_photo_url
                      ? <img src={postData.original_photo_url} alt="Original" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                      : <div style={{ color: T.textMuted, fontSize: 12 }}>Loading...</div>}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: T.primary, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                    {isEnhanced ? "AI Enhanced" : "Ready to Post"}
                  </div>
                  <div style={{ borderRadius: 12, overflow: "hidden", border: `2px solid ${postReady ? T.primary : T.border}`, height: 180, background: T.surfaceAlt, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    {postData?.edited_photo_url
                      ? <img src={postData.edited_photo_url} alt="Enhanced" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                      : (
                        <div style={{ textAlign: "center", padding: 10 }}>
                          <Spinner size={18} color={T.primary} />
                          <div style={{ color: T.primary, fontSize: 11, marginTop: 8, fontWeight: 600 }}>AI PROCESSING...</div>
                        </div>
                      )}
                  </div>
                </div>
              </div>

              {/* Caption Preview */}
              {(captionEn || captionHi) && (
                <div style={{ background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 14, padding: 18, marginBottom: 18 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: T.textMuted, marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}>{t("create.generate_btn")}</div>
                  {captionHi && (
                    <div style={{ fontSize: 14, color: T.text, lineHeight: 1.7, marginBottom: 10, fontFamily: T.fontDevan }}>
                      {captionHi}
                    </div>
                  )}
                  {captionEn && (
                    <div style={{ fontSize: 13, color: T.textMuted, lineHeight: 1.6, marginBottom: 12, borderTop: `1px solid ${T.border}`, paddingTop: 10 }}>
                      {captionEn}
                    </div>
                  )}
                  {hashtags.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {hashtags.map((h, i) => (
                        <span key={i} style={{ background: `${T.primary}18`, color: T.primary, fontSize: 11, padding: "3px 9px", borderRadius: 20, fontWeight: 600 }}>
                          {h}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {error && (
                <div style={{ background: `${T.red}18`, border: `1px solid ${T.red}40`, borderRadius: 10, padding: "10px 14px", color: T.red, fontSize: 13, marginBottom: 14 }}>
                  {I.alert} {error}
                </div>
              )}

              {/* ── Publish / Schedule Buttons ────────────────────────────────── */}
              <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 20 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: T.text, marginBottom: 16 }}>
                  📤 {t("create.publish_btn")}
                </div>

                {/* Post Now */}
                <button
                  onClick={doPublishNow}
                  disabled={publishing || scheduling || !postReady}
                  style={{ width: "100%", padding: "15px 20px", background: postReady ? `linear-gradient(135deg, ${T.primary}, ${T.accent || T.primary})` : T.border, color: "#fff", border: "none", borderRadius: 14, fontWeight: 800, fontSize: 16, cursor: (publishing || scheduling || !postReady) ? "wait" : "pointer", marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 10, opacity: !postReady ? 0.5 : 1, boxShadow: postReady ? `0 4px 15px ${T.primary}40` : "none" }}
                >
                  {publishing ? <><Spinner size={18} color="#fff" /> {t("common.processing")}</> : `🚀 ${t("create.publish_btn")}`}
                </button>

                {/* Schedule at settings time */}
                <button
                  onClick={doScheduleFromSettings}
                  disabled={publishing || scheduling || !postReady}
                  style={{ width: "100%", padding: "13px 20px", background: "transparent", color: T.primary, border: `2px solid ${T.primary}`, borderRadius: 14, fontWeight: 700, fontSize: 14, cursor: (publishing || scheduling || !postReady) ? "wait" : "pointer", marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 8, opacity: !postReady ? 0.5 : 1 }}
                >
                  {scheduling && scheduleMode === "settings"
                    ? <><Spinner size={16} color={T.primary} /> Scheduling...</>
                    : `⏰ Schedule at My Settings Time (${user?.preferred_post_time || "19:00"} IST)`}
                </button>

                {/* Custom time */}
                <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 12, marginTop: 2 }}>
                  <div style={{ fontSize: 12, color: T.textMuted, marginBottom: 8 }}>📅 Or pick a custom time (IST):</div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <input
                      type="datetime-local"
                      value={customDt}
                      onChange={e => setCustomDt(e.target.value)}
                      style={{ flex: 1, background: T.surfaceAlt, border: `1px solid ${T.borderLight}`, borderRadius: 10, padding: "10px 12px", color: T.text, fontSize: 13 }}
                    />
                    <button
                      onClick={() => { setScheduleMode("custom"); doScheduleCustom(); }}
                      disabled={!customDt || publishing || scheduling || !postReady}
                      style={{ padding: "10px 18px", background: T.surfaceAlt, color: T.text, border: `1px solid ${T.border}`, borderRadius: 10, fontWeight: 600, fontSize: 13, cursor: (!customDt || !postReady) ? "not-allowed" : "pointer" }}
                    >
                      {scheduling && scheduleMode === "custom" ? <Spinner size={14} /> : "Set"}
                    </button>
                  </div>
                </div>

                {/* Discard */}
                <button onClick={reset} style={{ width: "100%", marginTop: 14, padding: "10px 0", background: "transparent", color: T.textMuted, border: "none", fontSize: 13, cursor: "pointer", textDecoration: "underline" }}>
                  {t("common.cancel")}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};
