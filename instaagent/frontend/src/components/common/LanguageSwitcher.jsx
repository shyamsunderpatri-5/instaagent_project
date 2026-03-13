import React, { useState, useRef, useEffect } from "react";
import { T, I, useLang } from "./UIComponents";
import { useLanguage } from "./LanguageContext";

const LANGUAGES = [
  { code: "en", name: "English", native: "English" },
  { code: "hi", name: "Hindi", native: "हिंदी" },
  { code: "te", name: "Telugu", native: "తెలుగు" },
  { code: "ta", name: "Tamil", native: "தமிழ்" },
  { code: "kn", name: "Kannada", native: "ಕನ್ನಡ" },
  { code: "mr", name: "Marathi", native: "ಮರಾಠಿ" },
];

export const LanguageSwitcher = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { currentLang, setLang } = useLanguage();
  const dropdownRef = useRef(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const activeLang = LANGUAGES.find(l => l.code === currentLang) || LANGUAGES[0];

  return (
    <div ref={dropdownRef} style={{ position: "relative" }}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        style={{ 
          background: T.surfaceAlt, 
          border: `1px solid ${T.border}`, 
          borderRadius: 10, 
          padding: "8px 14px", 
          display: "flex", 
          alignItems: "center", 
          gap: 10, 
          color: T.text, 
          cursor: "pointer", 
          fontSize: 13, 
          fontWeight: 600,
          transition: "all .2s ease"
        }}
        onMouseEnter={e => e.currentTarget.style.borderColor = T.primary}
        onMouseLeave={e => e.currentTarget.style.borderColor = T.border}
      >
        <span style={{ fontSize: 16 }}>{I.globe}</span>
        <span>{activeLang.native}</span>
        <svg width="10" height="6" viewBox="0 0 10 6" fill="none" style={{ marginLeft: 4, transform: isOpen ? "rotate(180deg)" : "none", transition: "transform .2s" }}>
          <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      {isOpen && (
        <div 
          className="fade-up"
          style={{ 
            position: "absolute", 
            top: "calc(100% + 8px)", 
            right: 0, 
            background: "#0F1117", 
            border: `1px solid ${T.border}`, 
            borderRadius: 14, 
            padding: "8px", 
            width: 160, 
            boxShadow: "0 10px 30px rgba(0,0,0,.5)", 
            zIndex: 1000 
          }}
        >
          {LANGUAGES.map(lang => {
            const isActive = lang.code === currentLang;
            return (
              <button 
                key={lang.code}
                onClick={() => { setLang(lang.code); setIsOpen(false); }}
                style={{ 
                  width: "100%", 
                  textAlign: "left", 
                  padding: "10px 12px", 
                  borderRadius: 8, 
                  border: "none", 
                  background: isActive ? T.primaryDim : "transparent", 
                  color: isActive ? T.primary : T.textMuted, 
                  fontSize: 13, 
                  fontWeight: isActive ? 700 : 500, 
                  cursor: "pointer", 
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  transition: "all .15s"
                }}
                onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = T.surfaceAlt; e.currentTarget.style.color = T.text; } }}
                onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = T.textMuted; } }}
              >
                {lang.native}
                {isActive && <div style={{ width: 4, height: 4, borderRadius: "50%", background: T.primary }} />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
