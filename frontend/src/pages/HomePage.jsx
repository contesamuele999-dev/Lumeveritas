import { useEffect, useMemo, useRef, useState } from "react";
import AskBar from "@/components/AskBar";
import TopicPills from "@/components/TopicPills";
import NewsItem from "@/components/NewsItem";
import { api } from "@/lib/api";
import { useLang } from "@/context/LangContext";
import { useAuth } from "@/context/AuthContext";
import { t } from "@/lib/i18n";
import { Loader2, RefreshCcw, MousePointerClick, Radio } from "lucide-react";
import { toast } from "sonner";
import RssFeed from "@/components/RssFeed";

export default function HomePage() {
  const { lang } = useLang();
  const { user } = useAuth();
  const [topics, setTopics] = useState([]);
  const [selected, setSelected] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    api.get("/topics").then(({ data }) => setTopics(data));
  }, []);

  const allTopics = useMemo(() => {
    const custom = (user?.custom_topics || []).map(t => ({ ...t, custom: true }));
    return [...topics, ...custom];
  }, [topics, user]);

  const visibleTopics = useMemo(() => {
    if (!user || !user.preferred_topics?.length) return allTopics;
    const keys = new Set(user.preferred_topics);
    const preferred = allTopics.filter(x => keys.has(x.key));
    const rest = allTopics.filter(x => !keys.has(x.key));
    return [...preferred, ...rest];
  }, [allTopics, user]);

  useEffect(() => {
    if (!topics.length) return;
    if (!selected) setSelected(visibleTopics[0] || topics[0]);
  }, [topics, visibleTopics, selected]);

  const reqId = useRef(0);

  const loadBriefing = async (topic, refresh = false) => {
    if (!topic) return;
    const myReq = ++reqId.current;
    if (refresh) setRefreshing(true);
    else { setLoading(true); setItems([]); }  // niente notizie del topic precedente durante l'attesa
    try {
      const label = lang === "it" ? topic.label_it : topic.label_en;
      const body = { topic: label, language: lang, refresh };
      if (topic.custom && topic.kind && topic.kind !== "topic") {
        body.kind = topic.kind;
        if (topic.source) body.source = topic.source;
      }
      const { data } = await api.post("/news/briefing", body);
      if (myReq !== reqId.current) return;  // click rapido su un altro argomento: risposta obsoleta
      setItems(data.items);
    } catch (e) {
      if (myReq !== reqId.current) return;
      toast.error(e?.response?.data?.detail || e?.message || (lang === "it" ? "Errore nel caricamento" : "Loading error"));
      setItems([]);
    } finally {
      if (myReq === reqId.current) { setLoading(false); setRefreshing(false); }
    }
  };

  useEffect(() => {
    if (selected) loadBriefing(selected, false);
  }, [selected, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  const featured = items[0];
  const rest = items.slice(1);

  return (
    <div className="space-y-6 md:space-y-10">
      {/* HERO */}
      <section className="pt-1 pb-3 md:pt-2 md:pb-4 border-b border-border">
        <div className="grid md:grid-cols-12 gap-4 md:gap-8 items-end">
          <div className="md:col-span-8">
            <div className="font-mono-caps text-accent mb-2 md:mb-4">{t(lang, "welcome")} — Lume Veritas</div>
            <h1 className="font-serif-display text-3xl md:text-7xl leading-[1] md:leading-[0.95] tracking-tight">
              {lang === "it"
                ? <>Le notizie <em className="italic text-accent">vere</em>, ciò che gli altri <em className="italic">trascurano</em>.</>
                : <>The <em className="italic text-accent">real</em> news, the stories others <em className="italic">overlook</em>.</>}
            </h1>
          </div>
          <div className="md:col-span-4">
            <p className="hidden md:block text-lg md:text-xl text-foreground/80 leading-relaxed">
              {lang === "it"
                ? "Mercati, sondaggi, leggi, scoperte, guerre. Con i veri motivi dietro. Approfondisci qualsiasi notizia con un click."
                : "Markets, polls, laws, discoveries, wars. With the real reasons behind. Deep-dive any story with one click."}
            </p>
          </div>
        </div>
        <div className="mt-4 md:mt-8 max-w-3xl space-y-2">
          <AskBar big />
          <div className="font-mono-caps text-muted-foreground text-[11px] flex items-center gap-2">
            <MousePointerClick className="w-3.5 h-3.5" /> {t(lang, "click_word_hint")}
          </div>
        </div>
      </section>

      {/* TOPICS */}
      <section>
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="font-serif-display text-2xl md:text-3xl">{user ? t(lang, "my_topics") : t(lang, "all_topics")}</h2>
          {selected && (
            <button
              data-testid="refresh-briefing-btn"
              onClick={() => loadBriefing(selected, true)}
              className="font-mono-caps flex items-center gap-2 hover:text-accent transition-colors"
            >
              <RefreshCcw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} /> {t(lang, "refresh")}
            </button>
          )}
        </div>
        <TopicPills topics={visibleTopics} selected={selected?.key} onSelect={setSelected} />
      </section>

      {/* NEWS FEED */}
      <section>
        {loading ? (
          <div className="py-8 space-y-6" data-testid="briefing-loading">
            <div className="flex items-center gap-3 text-muted-foreground font-mono-caps text-[11px]">
              <Loader2 className="w-4 h-4 animate-spin" />
              {t(lang, "loading")} — {lang === "it" ? selected?.label_it : selected?.label_en}
            </div>
            {[0, 1, 2].map((i) => (
              <div key={i} className="animate-pulse space-y-3 border-b border-border pb-6">
                <div className="h-3 w-24 bg-muted" />
                <div className="h-7 md:h-9 w-4/5 bg-muted" />
                <div className="h-4 w-full bg-muted" />
                <div className="h-4 w-2/3 bg-muted" />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="py-24 text-center text-muted-foreground font-mono-caps">— no items —</div>
        ) : (
          <>
            {featured && (
              <div className="border-b border-border pb-6">
                <NewsItem item={featured} featured />
              </div>
            )}
            <div className="grid md:grid-cols-2 gap-x-10 mt-2 col-rule md:col-rule-0" >
              {rest.map((it) => (
                <div key={it.id} className="border-b border-border md:border-b md:pr-2 first:pt-2">
                  <NewsItem item={it} />
                </div>
              ))}
            </div>
          </>
        )}
      </section>

      {selected && (
        <section className="border-t border-border pt-10" data-testid="rss-section">
          <div className="flex items-center gap-3 mb-4">
            <Radio className="w-5 h-5 text-accent" />
            <h2 className="font-serif-display text-2xl md:text-3xl">
              {lang === "it" ? "Fonti indipendenti in tempo reale" : "Independent sources — live"}
            </h2>
          </div>
          <div className="font-mono-caps text-muted-foreground text-[11px] mb-4">
            {lang === "it"
              ? "Estratto RSS da testate alternative internazionali sull'argomento selezionato."
              : "RSS from alternative international outlets for the selected topic."}
          </div>
          <RssFeed topic={selected} />
        </section>
      )}
    </div>
  );
}
