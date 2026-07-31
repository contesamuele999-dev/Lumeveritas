import { useLang } from "@/context/LangContext";
import { ExternalLink, Link2 } from "lucide-react";

// Gemini restituisce URL di redirect (vertexaisearch...) uguali per tutte le fonti:
// mostrarli renderebbe ogni link indistinguibile. Si preferisce sempre il dominio reale.
const REDIRECT_HOSTS = ["vertexaisearch.cloud.google.com", "www.google.com", "google.com"];

const host = (url) => {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; }
};

const isRedirect = (url) => {
  try { return REDIRECT_HOSTS.includes(new URL(url).hostname); } catch { return false; }
};

/** Etichetta leggibile: dominio reale > titolo > ultima parte significativa dell'URL. */
export const sourceLabel = (s, compact = false) => {
  const title = (s?.title || "").trim();
  const looksLikeUrl = /^https?:\/\//i.test(title);
  if (s?.domain) return compact ? s.domain : (looksLikeUrl || !title ? s.domain : title);
  if (title && !looksLikeUrl) return title;
  if (!s?.url) return "fonte";
  if (!isRedirect(s.url)) return compact ? host(s.url) : (title && !looksLikeUrl ? title : host(s.url));
  // redirect non risolto: si tiene la parte finale del link, senza token illeggibili
  try {
    const seg = new URL(s.url).pathname.split("/").filter(Boolean).pop() || "";
    const clean = decodeURIComponent(seg).replace(/[-_+]/g, " ").trim();
    if (clean && clean.length <= 40 && /[aeiou]/i.test(clean)) return clean;
  } catch { /* noop */ }
  return "fonte web";
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
            title={s.title || s.domain || s.url}
            className="inline-flex items-center gap-1 max-w-full border border-border hover:border-foreground px-2 py-1 text-[11px] text-foreground/75 hover:text-foreground transition-colors"
          >
            <span className="truncate max-w-[220px]">{sourceLabel(s, compact)}</span>
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
