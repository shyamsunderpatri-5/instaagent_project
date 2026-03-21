import React, { createContext, useContext, useState, useEffect } from "react";
import { TRANSLATIONS } from "./UIComponents";
import { api } from "./api";

const LanguageContext = createContext();

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
};

export const LanguageProvider = ({ children, user, token, onUserUpdate }) => {
  // Read from localStorage -> User Profile -> Fallback to Hindi "hi"
  const [currentLang, setCurrentLang] = useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("instaagent_lang");
      if (saved) return saved;
    }
    return user?.language || "en";
  });

  // Translation helper
  const t = (key) => {
    const translationSet = TRANSLATIONS[currentLang] || TRANSLATIONS["en"];
    return translationSet[key] || TRANSLATIONS["en"][key] || key;
  };

  const setLang = async (langCode) => {
    setCurrentLang(langCode);
    if (typeof window !== "undefined") {
      localStorage.setItem("instaagent_lang", langCode);
    }

    // Sync with backend if logged in
    if (token) {
      try {
        const res = await api.patch("/api/v1/auth/me", { language: langCode }, token);
        if (onUserUpdate) onUserUpdate(res.user || res);
      } catch (err) {
        console.error("Failed to sync language to profile:", err);
      }
    }
  };

  // Sync state if user object updates externally (e.g., initial load)
  useEffect(() => {
    if (user?.language && user.language !== currentLang && !localStorage.getItem("instaagent_lang")) {
      setCurrentLang(user.language);
    }
  }, [user?.language]);

  return (
    <LanguageContext.Provider value={{ currentLang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
};
