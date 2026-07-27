import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useLang } from "@/context/LangContext";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import AskBar from "@/components/AskBar";
import { Loader2, Sparkles, AlertTriangle, ListChecks } from "lucide-react";

export default function AskPage() {
  const { lang } = useLang();
  const [sp] = useSearchParams();
  const q = sp.get("q") || "";
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!q) { setAnswer(null); return; }
    let cancel = false;
    (async () => {
      setLoading(true); setError(null); setAnswer(null);
      try {
        const { data } = await api.post("/ask", { question: q, language: lang });
        if (!cancel) setAnswer(data);
      } catch (e) {
        if (!cancel) setError(t(lang, "error_generic"));
      } finally {
        if (!cancel) setLoading(false);
      }
    })();
    return () => { cancel = true; };
  }, [q, lang]);

  return (
    <div className="max-w-4xl space-y-10">
      <div>
        <div className="font-mono-caps text-accent mb-3">{t(lang, "ask")}</div>
        <h1 className="font-serif-display text-4xl md:text-6xl leading-none tracking-tight mb-4">
          {t(lang, "ask_title")}
        </h1>
        <p className="text-lg md:text-xl text-foreground/80 max-w-3xl">
          {t(lang, "ask_desc")}
        </p>
      </div>

      <AskBar big />

      {q && (
        <div className="border-t border-border pt-8">
          <div className="font-mono-caps text-muted-foreground mb-4">Query</div>
          <div className="font-serif-display text-2xl md:text-3xl mb-8">&ldquo;{q}&rdquo;</div>

          {loading && (
            <div className="flex items-center gap-3 text-muted-foreground" data-testid="ask-loading">
              <Loader2 className="w-5 h-5 animate-spin" /> {t(lang, "loading")}
            </div>
          )}

          {error && (
            <div className="text-accent font-mono-caps flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> {error}
            </div>
          )}

          {answer && (
            <div className="space-y-8" data-testid="ask-answer">
              <section>
                <div className="flex items-center gap-2 font-mono-caps text-accent mb-3">
                  <Sparkles className="w-4 h-4" /> {t(lang, "answer")}
                </div>
                <p className="text-lg md:text-xl leading-relaxed text-foreground/95">{answer.answer}</p>
              </section>

              {answer.key_points?.length > 0 && (
                <section>
                  <div className="flex items-center gap-2 font-mono-caps text-muted-foreground mb-3">
                    <ListChecks className="w-4 h-4" /> {t(lang, "key_points")}
                  </div>
                  <ul className="space-y-3 col-rule">
                    {answer.key_points.map((p, i) => (
                      <li key={i} className="pt-3 flex gap-4">
                        <span className="font-mono-caps text-accent shrink-0">{String(i + 1).padStart(2, "0")}</span>
                        <span className="text-base md:text-lg">{p}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {answer.caveats?.length > 0 && (
                <section className="border border-border p-5">
                  <div className="flex items-center gap-2 font-mono-caps text-muted-foreground mb-3">
                    <AlertTriangle className="w-4 h-4" /> {t(lang, "caveats")}
                  </div>
                  <ul className="space-y-1 text-sm md:text-base text-foreground/80">
                    {answer.caveats.map((c, i) => <li key={i}>• {c}</li>)}
                  </ul>
                </section>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
