import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { api } from "@/lib/api";
import { useLang } from "@/context/LangContext";
import { t } from "@/lib/i18n";
import ClickableText from "@/components/ClickableText";
import SourceLinks from "@/components/SourceLinks";
import AudioButton from "@/components/AudioButton";
import ShareButton from "@/components/ShareButton";
import { Loader2, ArrowLeft, Landmark, BarChart3, BookOpen, ScrollText, Eye } from "lucide-react";

const API_BASE = process.env.REACT_APP_BACKEND_URL;

export default function PublicBriefingPage() {
  const { id } = useParams();
  const { lang } = useLang();
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    let deepTimer = null;

    // Il backend su piano free può dormire: il primo tentativo va in timeout, non è un 404.
    const fetchItem = async (attempt = 0) => {
      try {
        const { data } = await api.get(`/public/${id}`, { timeout: 60000 });
        if (!alive) return;
        setItem(data);
        setError(null);
        setLoading(false);
        // l'approfondimento viene generato in background: si ricontrolla una volta
        if (!data.real_reasons) {
          deepTimer = setTimeout(async () => {
            try {
              const { data: fresh } = await api.get(`/public/${id}`, { timeout: 60000 });
              if (alive && fresh.real_reasons) setItem(fresh);
            } catch { /* opzionale: si tiene la versione base */ }
          }, 12000);
        }
      } catch (e) {
        if (!alive) return;
        if (e?.response?.status === 404) {
          setError(lang === "it" ? "Notizia non trovata o non più disponibile." : "Story not found or no longer available.");
          setLoading(false);
          return;
        }
        if (attempt < 2) {
          setTimeout(() => fetchItem(attempt + 1), 3000);
          return;
        }
        setError(t(lang, "error_generic"));
        setLoading(false);
      }
    };

    setLoading(true);
    setError(null);
    fetchItem();
    return () => { alive = false; if (deepTimer) clearTimeout(deepTimer); };
  }, [id, lang]);

  if (loading) return <div className="py-24 flex items-center gap-3 text-muted-foreground"><Loader2 className="w-5 h-5 animate-spin" /> {t(lang, "loading")}</div>;
  if (error || !item) return (
    <div className="py-24 text-center space-y-4">
      <div className="font-mono-caps text-muted-foreground">{error || (lang === "it" ? "Notizia non trovata" : "Story not found")}</div>
      <Link to="/" className="font-mono-caps text-accent link-underline inline-block">
        {lang === "it" ? "Vai a Lume Veritas →" : "Go to Lume Veritas →"}
      </Link>
    </div>
  );

  const shareUrl = `${window.location.origin}/s/${item.id}`;
  const ogImage = `${API_BASE}/api/og/${item.id}.png`;
  const desc = (item.summary || "").slice(0, 200);
  const viewsLabel = lang === "it"
    ? `Letta da ${item.views || 1} ${(item.views || 1) === 1 ? "persona" : "persone"}`
    : `Read by ${item.views || 1} ${(item.views || 1) === 1 ? "person" : "people"}`;

  return (
    <>
      <Helmet>
        <title>{`${item.headline} — Lume Veritas`}</title>
        <meta name="description" content={desc} />
        <link rel="canonical" href={shareUrl} />
        <meta property="og:type" content="article" />
        <meta property="og:url" content={shareUrl} />
        <meta property="og:site_name" content="Lume Veritas" />
        <meta property="og:title" content={item.headline} />
        <meta property="og:description" content={desc} />
        <meta property="og:image" content={ogImage} />
        <meta property="og:image:width" content="1200" />
        <meta property="og:image:height" content="630" />
        <meta property="article:section" content={item.topic} />
        <meta property="article:published_time" content={item.generated_at} />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={item.headline} />
        <meta name="twitter:description" content={desc} />
        <meta name="twitter:image" content={ogImage} />
      </Helmet>

      <article className="max-w-3xl space-y-6 md:space-y-10">
        <Link to="/" data-testid="public-back-link" className="font-mono-caps text-muted-foreground hover:text-accent flex items-center gap-2 w-fit">
          <ArrowLeft className="w-4 h-4" /> Lume Veritas
        </Link>

        <header className="space-y-4 border-b border-border pb-8">
          <div className="font-mono-caps text-accent flex items-center gap-3 flex-wrap">
            <span>{item.topic}</span>
            <span className="w-1 h-1 bg-accent rounded-full" />
            <span className="tabular">{new Date(item.generated_at).toLocaleDateString(lang === "it" ? "it-IT" : "en-US")}</span>
            <span className="w-1 h-1 bg-accent rounded-full" />
            <span className="flex items-center gap-1.5 tabular" data-testid="public-views-counter">
              <Eye className="w-3.5 h-3.5" /> {viewsLabel}
            </span>
          </div>
          <h1 className="font-serif-display text-3xl md:text-6xl leading-[1.02] tracking-tight">
            <ClickableText text={item.headline} contextText={item.summary} />
          </h1>
          <div className="text-lg md:text-xl text-foreground/85 leading-relaxed">
            <ClickableText text={item.summary} />
          </div>
          <div className="flex flex-wrap gap-3 pt-4">
            <AudioButton item={item} testid={`public-audio-${item.id}`} />
            <ShareButton briefingId={item.id} testid={`public-share-${item.id}`} />
          </div>
        </header>

        {item.key_facts?.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3 font-mono-caps text-accent">
              <ScrollText className="w-4 h-4" /> {t(lang, "key_facts")}
            </div>
            <ul className="space-y-3">
              {item.key_facts.map((f, i) => (
                <li key={i} className="flex gap-3 text-base md:text-lg">
                  <span className="font-mono-caps text-muted-foreground shrink-0 mt-1">{String(i + 1).padStart(2, "0")}</span>
                  <span><ClickableText text={f} /></span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {item.real_reasons && (
          <section>
            <div className="flex items-center gap-2 mb-3 font-mono-caps text-accent">
              <Landmark className="w-4 h-4" /> {t(lang, "real_reasons")}
            </div>
            <div className="text-base md:text-lg leading-relaxed"><ClickableText text={item.real_reasons} /></div>
          </section>
        )}

        {item.data_points?.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3 font-mono-caps text-accent">
              <BarChart3 className="w-4 h-4" /> {t(lang, "data_points")}
            </div>
            <ul className="col-rule">
              {item.data_points.map((d, i) => (
                <li key={i} className="pt-2 text-base md:text-lg"><ClickableText text={d} /></li>
              ))}
            </ul>
          </section>
        )}

        {item.context && (
          <section>
            <div className="flex items-center gap-2 mb-3 font-mono-caps text-accent">
              <BookOpen className="w-4 h-4" /> {t(lang, "context")}
            </div>
            <div className="text-base md:text-lg leading-relaxed"><ClickableText text={item.context} /></div>
          </section>
        )}

        <SourceLinks sources={item.sources} />

        <footer className="border-t border-border pt-8">
          <Link to="/" className="font-mono-caps text-accent link-underline">
            {lang === "it" ? "Scopri di più su Lume Veritas →" : "Discover more on Lume Veritas →"}
          </Link>
        </footer>
      </article>
    </>
  );
}
