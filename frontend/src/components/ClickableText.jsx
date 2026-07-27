import { useState, useRef } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { api } from "@/lib/api";
import { useLang } from "@/context/LangContext";
import { Loader2, Sparkles } from "lucide-react";

// Split text into word/non-word tokens so we can wrap only real words
const TOKENIZER = /([\p{L}\p{N}][\p{L}\p{N}'’\-]{2,})/gu;

export default function ClickableText({ text, className = "", contextText = null }) {
  if (!text) return null;
  const parts = [];
  let last = 0;
  let m;
  const re = new RegExp(TOKENIZER.source, TOKENIZER.flags);
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push({ t: "s", v: text.slice(last, m.index) });
    parts.push({ t: "w", v: m[0] });
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push({ t: "s", v: text.slice(last) });

  return (
    <span className={className}>
      {parts.map((p, i) =>
        p.t === "s" ? (
          <span key={i}>{p.v}</span>
        ) : (
          <WordPopover key={i} word={p.v} contextText={contextText || text} />
        )
      )}
    </span>
  );
}

function WordPopover({ word, contextText }) {
  const { lang } = useLang();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [expl, setExpl] = useState(null);
  const [err, setErr] = useState(null);
  const fetched = useRef(false);

  const onOpen = async (v) => {
    setOpen(v);
    if (v && !fetched.current) {
      fetched.current = true;
      setLoading(true); setErr(null);
      try {
        const { data } = await api.post("/explain", { word, context: contextText, language: lang });
        setExpl(data.explanation);
      } catch (e) {
        setErr(e?.response?.data?.detail || "Errore");
        fetched.current = false;
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <Popover open={open} onOpenChange={onOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          data-testid={`word-btn-${word.toLowerCase()}`}
          className="hover:bg-accent/15 hover:text-accent rounded-sm px-[1px] cursor-help transition-colors"
        >
          {word}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80 border border-foreground bg-popover" side="top" data-testid="word-popover">
        <div className="font-mono-caps text-accent text-[10px] mb-2 flex items-center gap-2">
          <Sparkles className="w-3 h-3" />
          {lang === "it" ? "SPIEGAZIONE" : "EXPLANATION"}
        </div>
        <div className="font-serif-display text-lg leading-tight mb-2">{word}</div>
        {loading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            {lang === "it" ? "Sto cercando…" : "Looking up…"}
          </div>
        )}
        {err && <div className="text-sm text-accent">{err}</div>}
        {expl && <div className="text-sm leading-relaxed text-foreground/90">{expl}</div>}
      </PopoverContent>
    </Popover>
  );
}
