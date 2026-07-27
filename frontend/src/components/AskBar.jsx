import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLang } from "@/context/LangContext";
import { t } from "@/lib/i18n";
import { Search, ArrowRight } from "lucide-react";

export default function AskBar({ big = false }) {
  const { lang } = useLang();
  const [q, setQ] = useState("");
  const nav = useNavigate();

  const submit = (e) => {
    e.preventDefault();
    if (!q.trim()) return;
    nav(`/ask?q=${encodeURIComponent(q.trim())}`);
  };

  return (
    <form onSubmit={submit} data-testid="ask-bar-form" className="w-full">
      <div className={`flex items-stretch border border-foreground bg-background ${big ? "h-16" : "h-14"}`}>
        <div className="flex items-center justify-center px-4 border-r border-foreground">
          <Search className="w-5 h-5" />
        </div>
        <input
          data-testid="ask-bar-input"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t(lang, "ask_placeholder")}
          className={`flex-1 bg-transparent outline-none px-4 ${big ? "text-lg md:text-xl" : "text-base md:text-lg"}`}
        />
        <button
          type="submit"
          data-testid="ask-bar-submit"
          className="px-5 md:px-7 font-mono-caps bg-foreground text-background hover:bg-accent transition-colors flex items-center gap-2"
        >
          {t(lang, "send")} <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </form>
  );
}
