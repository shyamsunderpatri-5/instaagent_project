// frontend/src/components/views/TelegramBotView.jsx
import { T, I, useFeatures } from "../common/UIComponents";

export const TelegramView = ({ user }) => {
  const { botUsername } = useFeatures();
  return (
    <div style={{ padding: "28px 32px", maxWidth: 700, textAlign: "center" }}>
       <div className="fade-up" style={{ marginBottom: 40, marginTop: 40 }}>
          <div style={{ width: 80, height: 80, background: T.blue + "20", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px", color: T.blue }}>{I.telegram}</div>
          <h1 style={{ fontFamily: T.fontHead, fontSize: 28, fontWeight: 800, color: T.text, marginBottom: 12 }}>InstaAgent Telegram Bot</h1>
          <p style={{ color: T.textMuted, fontSize: 16, lineHeight: 1.6, maxWidth: 500, margin: "0 auto 30px" }}>
            The bridge between your suppliers and your shop. <br/>
            <strong>Pro Tip:</strong> Forward any photo directly from WhatsApp to the bot.
          </p>
          <div style={{ display: "flex", justifyContent: "center", gap: 16, marginBottom: 32 }}>
            <div style={{ background: T.surfaceAlt, padding: "12px 20px", borderRadius: 12, border: `1px solid ${T.border}`, fontSize: 13 }}>
                <div style={{ fontWeight: 800, color: T.blue, marginBottom: 4 }}>Step 1</div>
                Forward from WhatsApp
            </div>
            <div style={{ background: T.surfaceAlt, padding: "12px 20px", borderRadius: 12, border: `1px solid ${T.border}`, fontSize: 13 }}>
                <div style={{ fontWeight: 800, color: T.blue, marginBottom: 4 }}>Step 2</div>
                Bot Handles Cleanup
            </div>
            <div style={{ background: T.surfaceAlt, padding: "12px 20px", borderRadius: 12, border: `1px solid ${T.border}`, fontSize: 13 }}>
                <div style={{ fontWeight: 800, color: T.blue, marginBottom: 4 }}>Step 3</div>
                Live on Instagram!
            </div>
          </div>
          <a href={`https://t.me/${botUsername}`} target="_blank" rel="noreferrer" style={{ background: T.blue, color: "#fff", textDecoration: "none", padding: "14px 28px", borderRadius: 12, fontWeight: 700, fontSize: 15, display: "inline-flex", alignItems: "center", gap: 10 }}>{I.telegram} Open Telegram Bot</a>
       </div>
    </div>
  );
};
