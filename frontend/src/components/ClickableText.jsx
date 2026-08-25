import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ArrowLeft, Loader2, Sparkles, X } from "lucide-react";
import { api } from "@/lib/api";
import { useLang } from "@/context/LangContext";

/* Un solo pannello di spiegazione per tutta l'app.
   Prima ogni parola del testo era un <button> con dentro un Popover di Radix: una
   pagina di notizie arrivava a ~450 Popover montati contemporaneamente, con il relativo
   costo di render, e uno screen reader annunciava 450 pulsanti da attraversare con Tab.
   Qui le parole restano semplici <span> e il pannello è montato una volta sola;
   il click viene raccolto in delega dal contenitore. */

// Parole "vere": almeno 3 caratteri, lettere/numeri, apostrofi e trattini interni.
const TOKENIZER = /([\p{L}\p{N}][\p{L}\p{N}'’\-]{2,})/gu;

// quante volte si può scendere: parola → spiegazione → parola della spiegazione → …
export const MAX_DEPTH = 3;

// le spiegazioni non cambiano: una volta chieste restano in memoria per la sessione
const memCache = new Map();

const ExplainContext = createContext(null);

export function ExplainProvider({ children }) {
  const { lang } = useLang();
  const [stack, setStack] = useState([]); // [{word, context, explanation, loading, error}]
  const [rect, setRect] = useState(null);
  const anchorRef = useRef(null);
  const panelRef = useRef(null);
  const open = stack.length > 0;

  const close = useCallback(() => {
    setStack([]);
    anchorRef.current = null;
    setRect(null);
  }, []);

  const back = useCallback(() => setStack((s) => (s.length <= 1 ? [] : s.slice(0, -1))), []);

  const fetchExplanation = useCallback(
    async (word, context, index) => {
      const key = `${lang}:${word.toLowerCase()}`;
      const put = (patch) =>
        setStack((s) => (s.length - 1 === index ? s.map((e, i) => (i === index ? { ...e, ...patch } : e)) : s));
      if (memCache.has(key)) {
        put({ explanation: memCache.get(key), loading: false });
        return;
      }
      try {
        const { data } = await api.post("/explain", { word, context, language: lang });
        memCache.set(key, data.explanation);
        put({ explanation: data.explanation, loading: false });
      } catch (e) {
        put({
          error: e?.response?.data?.detail || (lang === "it" ? "Spiegazione non disponibile" : "Explanation unavailable"),
          loading: false,
        });
      }
    },
    [lang],
  );

  /** Apre (o approfondisce di un livello) la spiegazione di una parola. */
  const explain = useCallback(
    (word, context, el) => {
      const clean = (word || "").trim();
      if (!clean) return;
      if (el && !anchorRef.current) {
        anchorRef.current = el;
        setRect(el.getBoundingClientRect());
      }
      setStack((s) => {
        if (s.length > MAX_DEPTH) return s;
        // ricliccare la parola già in cima non deve duplicare il livello
        if (s.length && s[s.length - 1].word.toLowerCase() === clean.toLowerCase()) return s;
        fetchExplanation(clean, context, s.length);
        return [...s, { word: clean, context, explanation: null, loading: true, error: null }];
      });
    },
    [fetchExplanation],
  );

  // il pannello resta agganciato alla parola mentre la pagina scorre o cambia dimensione
  useEffect(() => {
    if (!open) return;
    const sync = () => anchorRef.current && setRect(anchorRef.current.getBoundingClientRect());
    const onKey = (e) => e.key === "Escape" && close();
    const onDown = (e) => {
      if (panelRef.current?.contains(e.target)) return;
      if (e.target?.closest?.("[data-lv-word]")) return;
      close();
    };
    window.addEventListener("scroll", sync, true);
    window.addEventListener("resize", sync);
    window.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown, true);
    return () => {
      window.removeEventListener("scroll", sync, true);
      window.removeEventListener("resize", sync);
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown, true);
    };
  }, [open, close]);

  const value = useMemo(() => ({ explain }), [explain]);

  return (
    <ExplainContext.Provider value={value}>
      {children}
      {open && (
        <ExplainPanel panelRef={panelRef} stack={stack} rect={rect} onBack={back} onClose={close} lang={lang} />
      )}
    </ExplainContext.Provider>
  );
}

function ExplainPanel({ panelRef, stack, rect, onBack, onClose, lang }) {
  const current = stack[stack.length - 1];
  const isMobile = typeof window !== "undefined" && window.innerWidth < 640;

  /* pointerEvents esplicito: quando il pannello di approfondimento (Radix Dialog) è
     aperto, Radix mette `pointer-events: none` su <body> e il riquadro, che vive in un
     portale sul body, diventerebbe non cliccabile. */
  let style;
  if (isMobile || !rect) {
    // su touch un pannello ancorato finisce sotto il dito: meglio una scheda dal basso
    style = { position: "fixed", left: 0, right: 0, bottom: 0, pointerEvents: "auto" };
  } else {
    const W = 340;
    const M = 12;
    const left = Math.min(Math.max(M, rect.left + rect.width / 2 - W / 2), window.innerWidth - W - M);
    const below = window.innerHeight - rect.bottom > 260;
    style = below
      ? { position: "fixed", top: rect.bottom + 8, left, width: W, pointerEvents: "auto" }
      : { position: "fixed", bottom: window.innerHeight - rect.top + 8, left, width: W, pointerEvents: "auto" };
  }

  return createPortal(
    <div
      ref={panelRef}
      role="dialog"
      aria-label={lang === "it" ? "Spiegazione" : "Explanation"}
      data-testid="word-popover"
      style={style}
      className={`z-[60] bg-popover text-popover-foreground border border-foreground shadow-xl p-4 max-h-[70vh] overflow-y-auto ${
        isMobile ? "pb-[calc(1rem+env(safe-area-inset-bottom))]" : ""
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="font-mono-caps text-accent text-[10px] flex items-center gap-2 min-w-0">
          {stack.length > 1 ? (
            <button
              type="button"
              onClick={onBack}
              data-testid="explain-back"
              aria-label={lang === "it" ? "Indietro" : "Back"}
              className="flex items-center gap-1 hover:text-foreground transition-colors min-w-0"
            >
              <ArrowLeft className="w-3 h-3 shrink-0" />
              <span className="truncate">{stack[stack.length - 2].word}</span>
            </button>
          ) : (
            <>
              <Sparkles className="w-3 h-3" />
              {lang === "it" ? "SPIEGAZIONE" : "EXPLANATION"}
            </>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          data-testid="explain-close"
          aria-label={lang === "it" ? "Chiudi" : "Close"}
          className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="font-serif-display text-lg leading-tight mb-2 break-words">{current.word}</div>

      {current.loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          {lang === "it" ? "Sto cercando…" : "Looking up…"}
        </div>
      )}
      {current.error && <div className="text-sm text-accent">{current.error}</div>}
      {current.explanation && (
        <div className="text-sm leading-relaxed text-foreground/90">
          {/* anche le parole della spiegazione sono cliccabili, fino a MAX_DEPTH */}
          <ClickableText text={current.explanation} contextText={current.explanation} depth={stack.length} />
        </div>
      )}
      {stack.length > MAX_DEPTH && (
        <div className="mt-3 font-mono-caps text-[10px] text-muted-foreground">
          {lang === "it" ? "Fine dell'approfondimento" : "End of the drill-down"}
        </div>
      )}
    </div>,
    document.body,
  );
}

export const useExplain = () => useContext(ExplainContext);

/** Spezza il testo in parole cliccabili. Il risultato è memoizzato per testo. */
const tokenCache = new Map();
function tokenize(text) {
  const hit = tokenCache.get(text);
  if (hit) return hit;
  const parts = [];
  const re = new RegExp(TOKENIZER.source, TOKENIZER.flags);
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push({ w: false, v: text.slice(last, m.index) });
    parts.push({ w: true, v: m[0] });
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push({ w: false, v: text.slice(last) });
  if (tokenCache.size > 500) tokenCache.clear();
  tokenCache.set(text, parts);
  return parts;
}

export default function ClickableText({ text, className = "", contextText = null, depth = 0 }) {
  const explain = useExplain()?.explain;

  const onClick = useCallback(
    (e) => {
      const el = e.target.closest?.("[data-lv-word]");
      if (!el || !explain) return;
      // una selezione in corso significa che l'utente sta copiando, non chiedendo
      if (window.getSelection?.().toString().trim().length > 1) return;
      explain(el.dataset.lvWord, contextText || text, el);
    },
    [explain, contextText, text],
  );

  const onKeyDown = useCallback(
    (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      const el = e.target.closest?.("[data-lv-word]");
      if (!el || !explain) return;
      e.preventDefault();
      explain(el.dataset.lvWord, contextText || text, el);
    },
    [explain, contextText, text],
  );

  if (!text) return null;
  if (depth > MAX_DEPTH || !explain) return <span className={className}>{text}</span>;

  return (
    <span className={className} onClick={onClick} onKeyDown={onKeyDown}>
      {tokenize(text).map((p, i) =>
        p.w ? (
          <span
            key={i}
            data-lv-word={p.v}
            tabIndex={-1}
            className="cursor-help rounded-sm px-[1px] transition-colors hover:bg-accent/15 hover:text-accent"
          >
            {p.v}
          </span>
        ) : (
          p.v
        ),
      )}
    </span>
  );
}
