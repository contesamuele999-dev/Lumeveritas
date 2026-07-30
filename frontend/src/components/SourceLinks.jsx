import { useLang } from "@/context/LangContext";
import { ExternalLink, Link2 } from "lucide-react";

const host = (url) => {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; }
};

export default function SourceLinks({ sources, compact = false }) {
  const { lang } = useLang();
  if (!sources?.length) return null;
  const list = compact ? sources.slice(0, 4) : sources;

  return (
    <div className="mt-4" data-testid="source-links">
      <div className="font-mono-caps text-muted-foreground text-[10px] mb-2 flex items-center gap-1.5">
        <Link2 className="w-3 h-3" /> {lang === "it" ? "Fonti" : "Sources"}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {list.map((s, i) => (
          <a
            key={i}
            href={s.url}
            target="_blank"
            rel="noopener noreferrer"
            title={s.title}
            className="inline-flex items-center gap-1 max-w-full border border-border hover:border-foreground px-2 py-1 text-[11px] text-foreground/75 hover:text-foreground transition-colors"
          >
            <span className="truncate">{compact ? host(s.url) : s.title || host(s.url)}</span>
            <ExternalLink className="w-3 h-3 shrink-0" />
          </a>
        ))}
        {compact && sources.length > list.length && (
          <span className="text-[11px] text-muted-foreground self-center">+{sources.length - list.length}</span>
        )}
      </div>
    </div>
  );
}
