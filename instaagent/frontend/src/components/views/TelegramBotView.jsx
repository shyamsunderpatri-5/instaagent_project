// frontend/src/components/views/TelegramBotView.jsx
import { T, I, useFeatures, useLang } from "../common/UIComponents";

export const TelegramView = ({ user }) => {
  const { botUsername } = useFeatures();
  const { t } = useLang();
  return (
    <div style={{ padding: "28px 32px", maxWidth: 700, textAlign: "center" }}>
       <div className="fade-up" style={{ marginBottom: 40, marginTop: 40 }}>
          <div style={{ width: 80, height: 80, background: T.blue + "20", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px", color: T.blue }}>{I.telegram}</div>
          <h1 style={{ fontFamily: T.fontHead, fontSize: 28, fontWeight: 800, color: T.text, marginBottom: 12 }}>{t("telegram.title")}</h1>
          <p style={{ color: T.textMuted, fontSize: 16, lineHeight: 1.6, maxWidth: 500, margin: "0 auto 30px" }}>
            {t("telegram.subtitle")} <br/>
            <strong>{t("telegram.pro_tip")}</strong>
          </p>
          <div style={{ display: "flex", justifyContent: "center", gap: 16, marginBottom: 32 }}>
            <div style={{ background: T.surfaceAlt, padding: "12px 20px", borderRadius: 12, border: `1px solid ${T.border}`, fontSize: 13 }}>
                <div style={{ fontWeight: 800, color: T.blue, marginBottom: 4 }}>{t("telegram.step1")}</div>
                {t("telegram.step1_desc")}
            </div>
            <div style={{ background: T.surfaceAlt, padding: "12px 20px", borderRadius: 12, border: `1px solid ${T.border}`, fontSize: 13 }}>
                <div style={{ fontWeight: 800, color: T.blue, marginBottom: 4 }}>{t("telegram.step2")}</div>
                {t("telegram.step2_desc")}
            </div>
            <div style={{ background: T.surfaceAlt, padding: "12px 20px", borderRadius: 12, border: `1px solid ${T.border}`, fontSize: 13 }}>
                <div style={{ fontWeight: 800, color: T.blue, marginBottom: 4 }}>{t("telegram.step3")}</div>
                {t("telegram.step3_desc")}
            </div>
          </div>
          <a href={`https://t.me/${botUsername}`} target="_blank" rel="noreferrer" style={{ background: T.blue, color: "#fff", textDecoration: "none", padding: "14px 28px", borderRadius: 12, fontWeight: 700, fontSize: 15, display: "inline-flex", alignItems: "center", gap: 10 }}>{I.telegram} {t("telegram.open_bot")}</a>
       </div>
    </div>
  );
};
