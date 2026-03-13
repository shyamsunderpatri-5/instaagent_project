"use client";
import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Spinner, useToast } from "../../../components/common/UIComponents";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { show } = useToast();

  useEffect(() => {
    const code = searchParams.get("code");
    if (code) {
      // Exchange code for token on the server
      fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/auth/google/callback?code=${code}`)
        .then(res => res.json())
        .then(data => {
          if (data.token || data.access_token) {
            localStorage.setItem("ia_token", data.token || data.access_token);
            window.location.href = "/";
          } else {
            show(data.detail || "Authentication failed", "error");
            router.push("/");
          }
        })
        .catch(err => {
          show("Failed to complete Google login", "error");
          router.push("/");
        });
    }
  }, [searchParams, router, show]);

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "#0D0F14", color: "#fff" }}>
      <Spinner size={40} />
      <p style={{ marginTop: 20, fontSize: 16, fontWeight: 500 }}>Authenticating you...</p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <CallbackHandler />
    </Suspense>
  );
}
