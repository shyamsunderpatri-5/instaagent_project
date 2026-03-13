import React from "react";
import { T, I } from "./UIComponents";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ 
          height: "100vh", 
          background: T.bg, 
          display: "flex", 
          alignItems: "center", 
          justifyContent: "center", 
          padding: 20 
        }}>
          <div className="fade-up" style={{ 
            maxWidth: 500, 
            width: "100%", 
            background: T.surface, 
            border: `1px solid ${T.border}`, 
            borderRadius: 20, 
            padding: 40, 
            textAlign: "center",
            boxShadow: "0 20px 60px rgba(0,0,0,.5)"
          }}>
            <div style={{ 
              width: 64, 
              height: 64, 
              background: T.redDim, 
              borderRadius: "50%", 
              display: "flex", 
              alignItems: "center", 
              justifyContent: "center", 
              margin: "0 auto 24px",
              color: T.red
            }}>
              {I.alert}
            </div>
            
            <h1 style={{ fontFamily: T.fontHead, fontSize: 24, fontWeight: 800, color: T.text, marginBottom: 12 }}>
              Something went wrong
            </h1>
            <p style={{ fontSize: 14, color: T.textMuted, marginBottom: 32, lineHeight: 1.6 }}>
              {this.state.error?.message || "An unexpected error occurred."}
            </p>

            <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
              <button 
                onClick={() => window.location.reload()} 
                style={{ 
                  padding: "12px 24px", 
                  background: T.primary, 
                  color: "#fff", 
                  border: "none", 
                  borderRadius: 12, 
                  fontWeight: 600, 
                  fontSize: 14, 
                  cursor: "pointer" 
                }}
              >
                Reload Page
              </button>
              <button 
                onClick={() => window.location.href = "/"} 
                style={{ 
                  padding: "12px 24px", 
                  background: "transparent", 
                  color: T.text, 
                  border: `1px solid ${T.border}`, 
                  borderRadius: 12, 
                  fontWeight: 600, 
                  fontSize: 14, 
                  cursor: "pointer" 
                }}
              >
                Go to Dashboard
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
