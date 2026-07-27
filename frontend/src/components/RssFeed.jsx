import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useLang } from "@/context/LangContext";
import { t } from "@/lib/i18n";
import { ExternalLink, Loader2 } from "lucide-react";

export default function RssFeed({ topic }) {
  const { lang } = useLang();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!topic) return;
    setLoading(true); setItems([]);
    const label = lang === "it" ? topic.label_it : topic.label_en;
    api.get(`/rss/feed?topic=${encodeURIComponent(label)}&limit=8`)
      .then(({ data }) => setItems(data.items || []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [topic, lang]);

  if (loading) {
    return (
      <div className="py-8 text-muted-foreground flex items-center gap-2 font-mono-caps">
        <Loader2 className="w-4 h-4 animate-spin" /> {t(lang, "loading")}
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="py-6 text-muted-foreground font-mono-caps text-sm">
        {lang === "it" ? "— nessuna fonte RSS per questo argomento —" : "— no live sources for this topic —"}
      </div>
    );
  }

  return (
    <div className="col-rule" data-testid="rss-feed">
      {items.map((it, i) => (
        <a
          key={i}
          href={it.link}
          target="_blank"
          rel="noopener noreferrer"
          data-testid={`rss-item-${i}`}
          className="block py-4 hover:bg-secondary/40 transition-colors px-1"
        >
          <div className="font-mono-caps text-muted-foreground text-[11px] mb-1 flex items-center gap-2">
            <span>{it.source?.slice(0, 40)}</span>
            {it.published && <><span>•</span><span>{it.published.slice(0, 16)}</span></>}
          </div>
          <div className="font-serif-display text-lg md:text-xl leading-snug mb-1 flex items-start gap-2">
            <span className="link-underline">{it.title}</span>
            <ExternalLink className="w-4 h-4 shrink-0 mt-1 text-muted-foreground" />
          </div>
          {it.summary && <div className="text-sm text-foreground/70 line-clamp-2">{it.summary}</div>}
        </a>
      ))}
    </div>
  );
}
