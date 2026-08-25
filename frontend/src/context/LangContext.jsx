import { createContext, useContext, useEffect, useMemo, useState } from "react";

const LangContext = createContext(null);

/* Prima visita: si parte da come è impostato il dispositivo invece di imporre
   italiano e tema chiaro. La scelta esplicita dell'utente resta salvata e vince
   sempre. Gli stessi due valori vengono letti dallo script in public/index.html
   prima del primo disegno, per non far lampeggiare il bianco a chi usa il tema scuro. */
const initialLang = () => {
  const saved = localStorage.getItem("lv_lang");
  if (saved === "it" || saved === "en") return saved;
  return (navigator.language || "it").toLowerCase().startsWith("it") ? "it" : "en";
};

const initialTheme = () => {
  const saved = localStorage.getItem("lv_theme");
  if (saved === "dark" || saved === "light") return saved;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
};

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(initialLang);
  const [theme, setThemeState] = useState(initialTheme);

  useEffect(() => {
    localStorage.setItem("lv_lang", lang);
    document.documentElement.lang = lang;
  }, [lang]);

  useEffect(() => {
    localStorage.setItem("lv_theme", theme);
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    // la barra di sistema su mobile deve seguire il tema, altrimenti resta chiara sul nero
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#12141a" : "#f9f9f6");
  }, [theme]);

  const value = useMemo(
    () => ({ lang, setLang: setLangState, theme, setTheme: setThemeState }),
    [lang, theme],
  );

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export const useLang = () => useContext(LangContext);
