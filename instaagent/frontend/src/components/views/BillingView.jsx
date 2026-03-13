// frontend/src/components/views/BillingView.jsx
import { useState, useEffect } from "react";
import { T, I, Badge, useToast, Spinner } from "../common/UIComponents";
import { api } from "../common/api";

// Fallback plans in case API is unavailable — prices should match backend .env
const FALLBACK_PLANS = [
  {
    id: "free",
    name: "Free",
    price: 0,
    posts_limit: 5,
    features_list: ["5 posts/month", "AI captions", "Background removal", "Telegram bot"],
  },
  {
    id: "starter",
    name: "Starter",
    price: 299,
    posts_limit: 30,
    features_list: ["30 posts/month", "All Free features", "Studio enhancement", "Priority processing"],
  },
  {
    id: "growth",
    name: "Growth",
    price: 599,
    posts_limit: 90,
    features_list: ["90 posts/month", "All Starter features", "Carousel duos", "Scheduled posting"],
  },
  {
    id: "agency",
    name: "Agency",
    price: 1999,
    posts_limit: 300,
    features_list: ["300 posts/month", "All Growth features", "Multiple accounts", "Priority support"],
  },
];

export const BillingView = ({ user, usage, token }) => {
  const [plans, setPlans] = useState([]);
  const [sub, setSub] = useState(null);
  const [loading, setLoading] = useState(true);
  const { show, Toast } = useToast();

  useEffect(() => {
    setLoading(true);
    Promise.all([
        api.get("/api/v1/subscription/plans", token).catch(() => ({ plans: FALLBACK_PLANS })),
        api.get("/api/v1/subscription/current", token).catch(() => null),
    ]).then(([p, s]) => {
        setPlans(p.plans && p.plans.length > 0 ? p.plans : FALLBACK_PLANS);
        setSub(s?.subscription || null);
        setLoading(false);
    });

    // Dynamically load Razorpay SDK
    if (!window.Razorpay) {
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      document.body.appendChild(script);
    }
  }, [token]);

  const handleUpgrade = async (planId) => {
    if (planId === "free") {
      show("You're already on the free plan.");
      return;
    }

    if (!window.Razorpay) {
      show("Payment gateway is still loading. Please wait a second.", "info");
      return;
    }

    try {
        const res = await api.post("/api/v1/subscription/create", { plan_id: planId }, token);
        
        // Response should contain Razorpay order details
        const options = {
          key: res.razorpay_key,
          subscription_id: res.subscription_id,
          name: "InstaAgent",
          description: `Upgrade to ${planId.charAt(0).toUpperCase() + planId.slice(1)} Plan`,
          image: "https://instaagent.app/logo.png",
          prefill: {
            name: res.user?.name || user?.full_name || "",
            email: res.user?.email || user?.email || "",
            contact: res.user?.phone || user?.phone || ""
          },
          theme: { color: "#2D4FD6" },
          handler: async (response) => {
            show("Payment successful! Refreshing your plan...", "success");
            // Refresh user and subscription state
            const currentSub = await api.get("/api/v1/subscription/current", token);
            setSub(currentSub?.subscription || null);
          },
          modal: {
            ondismiss: () => {
              show("Payment cancelled.");
            }
          }
        };

        const rzp = new window.Razorpay(options);
        rzp.open();

    } catch (err) {
        if (err.message?.includes("razorpay") || err.message?.includes("plan_id")) {
          show("Payment gateway not yet configured. Contact support.", "error");
        } else {
          show(err.message || "Upgrade failed", "error");
        }
    }
  };

  // Determine current plan from subscription or user profile
  const currentPlanId = sub?.plan_id || sub?.plan || user?.plan || "free";
  const status = sub?.status || "active";
  const currentPlan = plans.find(p => p.id === currentPlanId) || FALLBACK_PLANS.find(p => p.id === currentPlanId);

  return (
    <div style={{ padding: "28px 32px", maxWidth: 960 }}>
       {Toast}
       <div className="fade-up" style={{ marginBottom: 28 }}>
        <h1 style={{ fontFamily: T.fontHead, fontSize: 24, fontWeight: 800, color: T.text, marginBottom: 6 }}>{t("billing.title")}</h1>
        <p style={{ color: T.textMuted, fontSize: 14 }}>{t("billing.subtitle")}</p>
      </div>

      {/* Current Plan Summary (always shown) */}
      <div className="fade-up" style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 24, marginBottom: 28, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontSize: 12, color: T.textMuted, fontWeight: 600, textTransform: "uppercase", marginBottom: 6 }}>{t("billing.current_plan")}</div>
          <div style={{ fontSize: 18, fontWeight: 800, color: T.text, display: "flex", alignItems: "center", gap: 10 }}>
            <Badge status={currentPlanId} />
            {currentPlan?.name || currentPlanId.charAt(0).toUpperCase() + currentPlanId.slice(1)} {t("billing.plan")}
          </div>
          <div style={{ fontSize: 13, color: T.textMuted, marginTop: 4 }}>
            {t("billing.status")}: <span style={{ color: T.green }}>{status.toUpperCase()}</span>
            {usage && ` · ${t("billing.usage_limit").replace("{used}", usage.posts_used || 0).replace("{limit}", usage.posts_limit || 5)}`}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 28, fontWeight: 800, color: T.text }}>
            ₹{currentPlan?.price ?? 0}
            <span style={{ fontSize: 13, color: T.textMuted, fontWeight: 400 }}>/mo</span>
          </div>
          {sub && (
            <button
              onClick={async () => {
                try {
                  await api.post("/api/v1/subscription/cancel", {}, token);
                  show("Subscription cancelled.");
                } catch (e) { show(e.message, "error"); }
              }}
              style={{ background: "transparent", border: `1px solid ${T.border}`, borderRadius: 8, padding: "6px 14px", color: T.textMuted, fontSize: 12, cursor: "pointer", marginTop: 8 }}
            >
              {t("billing.cancel_btn")}
            </button>
          )}
        </div>
      </div>

      {/* Usage bar */}
      {usage && (
        <div className="fade-up" style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 14, padding: "16px 24px", marginBottom: 28 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: T.text }}>{t("billing.monthly_usage")}</div>
            <div style={{ fontSize: 13, color: T.textMuted }}>{usage.posts_used || 0} of {usage.posts_limit || 5} posts</div>
          </div>
          <div style={{ height: 8, background: T.bg, borderRadius: 4, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${Math.min(100, Math.round(((usage.posts_used || 0) / (usage.posts_limit || 5)) * 100))}%`, background: T.primary, borderRadius: 4, transition: "width 1s ease" }} />
          </div>
        </div>
      )}

      {/* Plan Cards */}
      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: 40 }}><Spinner size={32} /></div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 20 }}>
          {plans.map((p, i) => (
            <div key={p.id} className="fade-up" style={{ animationDelay: `${i * 100}ms`, background: currentPlanId === p.id ? T.primaryDim : T.surface, border: `1px solid ${currentPlanId === p.id ? T.primary : T.border}`, borderRadius: 16, padding: 24, display: "flex", flexDirection: "column", position: "relative" }}>
               {currentPlanId === p.id && <div style={{ position: "absolute", top: -12, left: "50%", transform: "translateX(-50%)", background: T.primary, color: "#fff", fontSize: 10, fontWeight: 800, padding: "4px 12px", borderRadius: 20, whiteSpace: "nowrap" }}>{t("billing.current_plan").toUpperCase()}</div>}
               <div style={{ fontSize: 18, fontWeight: 800, color: T.text, marginBottom: 8 }}>{p.name}</div>
               <div style={{ fontSize: 26, fontWeight: 800, color: T.text, marginBottom: 4 }}>
                 ₹{p.price}<span style={{ fontSize: 14, color: T.textMuted, fontWeight: 400 }}>/mo</span>
               </div>
               <div style={{ fontSize: 12, color: T.textMuted, marginBottom: 16 }}>{p.posts_limit} posts/month</div>
               <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
                  {(p.features_list || []).map((f, fi) => (
                    <div key={fi} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: T.textMuted }}>
                       <span style={{ color: T.primary, flexShrink: 0 }}>{I.check}</span> {f}
                    </div>
                  ))}
               </div>
               <button
                 onClick={() => handleUpgrade(p.id)}
                 disabled={currentPlanId === p.id}
                 style={{ width: "100%", padding: 12, background: currentPlanId === p.id ? T.border : T.primary, color: "#fff", border: "none", borderRadius: 10, fontWeight: 700, cursor: currentPlanId === p.id ? "not-allowed" : "pointer", opacity: currentPlanId === p.id ? 0.5 : 1, transition: "all .2s" }}
               >
                 {currentPlanId === p.id ? t("billing.active") : p.id === "free" ? t("billing.downgrade") : t("billing.upgrade_to").replace("{name}", p.name)}
               </button>
            </div>
          ))}
        </div>
      )}

      {/* Payment note */}
      <div style={{ marginTop: 24, padding: "14px 18px", background: T.surfaceAlt, border: `1px solid ${T.border}`, borderRadius: 12, fontSize: 12, color: T.textMuted }}>
        {I.billing} {t("billing.footer")}
      </div>
    </div>
  );
};
