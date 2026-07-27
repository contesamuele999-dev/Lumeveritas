import { createContext, useContext, useEffect, useState } from "react";

const LangContext = createContext(null);

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(() => localStorage.getItem("lv_lang") || "it");
  const [theme, setThemeState] = useState(() => localStorage.getItem("lv_theme") || "light");

  useEffect(() => {
    localStorage.setItem("lv_lang", lang);
    document.documentElement.lang = lang;
  }, [lang]);

  useEffect(() => {
    localStorage.setItem("lv_theme", theme);
    const root = document.documentElement;
    if (theme === "dark") root.classList.add("dark");
    else root.classList.remove("dark");
  }, [theme]);

  return (
    <LangContext.Provider value={{ lang, setLang: setLangState, theme, setTheme: setThemeState }}>
      {children}
    </LangContext.Provider>
  );
}

export const useLang = () => useContext(LangContext);
