import { useLang } from "@/context/LangContext";
import { t } from "@/lib/i18n";
import { Sparkles, Users, ShieldCheck, History } from "lucide-react";

// Approfondisci / Dibattito / Storia / Verifica: aprono DeepDiveSheet sulla scheda giusta.
export default function DeepDiveButtons({ id, onOpen }) {
  const { lang } = useLang();
  const outline = "h-10 md:h-12 px-3 md:px-5 border border-foreground bg-background transition-colors font-mono-caps flex items-center gap-2";
  return (
    <>
      <button
        data-testid={`approfondisci-btn-${id}`}
        onClick={() => onOpen("deep")}
        className="h-10 md:h-12 px-3 md:px-5 bg-accent text-accent-foreground hover:opacity-90 transition-opacity font-mono-caps flex items-center gap-2"
      >
        <Sparkles className="w-4 h-4" /> {t(lang, "approfondisci")}
      </button>
      <button data-testid={`debate-btn-${id}`} onClick={() => onOpen("debate")} className={`${outline} hover:bg-foreground hover:text-background`}>
        <Users className="w-4 h-4" /> {t(lang, "debate_btn")}
      </button>
      <button data-testid={`history-btn-${id}`} onClick={() => onOpen("history")} className={`${outline} hover:bg-foreground hover:text-background`}>
        <History className="w-4 h-4" /> {t(lang, "tab_history")}
      </button>
      <button data-testid={`verify-btn-${id}`} onClick={() => onOpen("verify")} className={`${outline} hover:bg-emerald-600 hover:text-white hover:border-emerald-600`}>
        <ShieldCheck className="w-4 h-4" /> {t(lang, "verify_btn")}
      </button>
    </>
  );
}
