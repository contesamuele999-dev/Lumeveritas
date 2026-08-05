import { useEffect, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { api } from "@/lib/api";
import { useLang } from "@/context/LangContext";
import { t } from "@/lib/i18n";
import { Loader2, BookOpen, BarChart3, Landmark, ScrollText, MessageCircleQuestion, Users, Send, ArrowRight, ShieldCheck, History, Milestone, HelpCircle } from "lucide-react";
import ClickableText from "@/components/ClickableText";
import AudioButton from "@/components/AudioButton";
import ShareButton from "@/components/ShareButton";
import VerifyPanel from "@/components/VerifyPanel";
import SourceLinks from "@/components/SourceLinks";
import useBackClose from "@/hooks/useBackClose";

export default function DeepDiveSheet({ item, open, onOpenChange, initialTab = "deep" }) {
  const { lang } = useLang();
  const [tab, setTab] = useState(initialTab);
  const [data, setData] = useState(item);
  const [loadingDeep, setLoadingDeep] = useState(false);
  const [debate, setDebate] = useState(null);
  const [loadingDebate, setLoadingDebate] = useState(false);
  const [history, setHistory] = useState(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState(false);
  const [qas, setQas] = useState([]);
  const [qaInput, setQaInput] = useState("");
  const [asking, setAsking] = useState(false);

  useEffect(() => { if (open) setTab(initialTab); }, [open, initialTab]);

  // il tasto Indietro chiude il pannello e torna alla lista, non fuori dal sito
  useBackClose(open, () => onOpenChange(false));

  // Load deep dive
  useEffect(() => {
    let cancel = false;
    const load = async () => {
      if (!open || !item) return;
      setData(item);
      if (tab === "deep") {
        if (item.real_reasons) return;
        setLoadingDeep(true);
        try {
          const { data: d } = await api.post(`/news/deep-dive/${item.id}`);
          if (!cancel) setData(d);
        } catch (e) {} finally {
          if (!cancel) setLoadingDeep(false);
        }
      }
    };
    load();
    return () => { cancel = true; };
  }, [open, item, tab]);

  // Load debate on demand
  useEffect(() => {
    let cancel = false;
    const load = async () => {
      if (!open || !item || tab !== "debate") return;
      if (debate) return;
      setLoadingDebate(true);
      try {
        const { data: d } = await api.post(`/news/${item.id}/debate`);
        if (!cancel) setDebate(d);
      } catch (e) {} finally {
        if (!cancel) setLoadingDebate(false);
      }
    };
    load();
    return () => { cancel = true; };
  }, [open, item, tab, debate]);

  // Load storico (timeline) on demand
  const loadHistory = async ({ force = false } = {}) => {
    if (!item) return;
    setLoadingHistory(true);
    setHistoryError(false);
    try {
      const { data: d } = await api.post(`/news/${item.id}/timeline${force ? "?refresh=true" : ""}`);
      setHistory(d);
    } catch (e) {
      setHistoryError(true);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (!open || !item || tab !== "history") return;
    if (history || loadingHistory || historyError) return;
    loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, item, tab, history, loadingHistory, historyError]);

  // cambiando notizia lo storico precedente non ha più senso
  useEffect(() => { setHistory(null); setHistoryError(false); setDebate(null); }, [item?.id]);

  // Load Q&A history
  useEffect(() => {
    let cancel = false;
    const load = async () => {
      if (!open || !item || tab !== "qa") return;
      try {
        const { data: d } = await api.get(`/news/${item.id}/qa`);
        if (!cancel) setQas(d);
      } catch (e) {}
    };
    load();
    return () => { cancel = true; };
  }, [open, item, tab]);

  const submitQa = async (e) => {
    e?.preventDefault();
    const q = qaInput.trim();
    if (!q || asking) return;
    setAsking(true);
    try {
      const { data: d } = await api.post(`/news/${item.id}/qa`, { question: q });
      setQas((prev) => [d, ...prev]);
      setQaInput("");
    } catch (err) {} finally { setAsking(false); }
  };

  const tabs = [
    { key: "deep", label: t(lang, "tab_deep"), icon: BookOpen },
    { key: "qa", label: t(lang, "tab_qa"), icon: MessageCircleQuestion },
    { key: "debate", label: t(lang, "tab_debate"), icon: Users },
    { key: "history", label: t(lang, "tab_history"), icon: History },
    { key: "verify", label: t(lang, "tab_verify"), icon: ShieldCheck },
  ];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto p-0" data-testid="deep-dive-sheet">
        <div className="p-4 md:p-8 border-b border-border">
          <div className="font-mono-caps text-accent mb-3">{data?.topic}</div>
          <SheetHeader className="text-left space-y-2">
            <SheetTitle className="font-serif-display text-2xl md:text-4xl leading-tight tracking-tight">
              <ClickableText text={data?.headline} contextText={data?.summary} />
            </SheetTitle>
            <SheetDescription className="sr-only">
              {data?.headline}
            </SheetDescription>
          </SheetHeader>
          <div className="mt-4 text-base md:text-lg text-foreground/85 leading-relaxed">
            <ClickableText text={data?.summary} />
          </div>
          <SourceLinks sources={data?.sources} />
          {data?.id && (
            <div className="mt-5 flex flex-wrap gap-3">
              <AudioButton item={data} testid={`deep-audio-${data.id}`} />
              <ShareButton briefingId={data.id} testid={`deep-share-${data.id}`} />
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="sticky top-0 z-10 bg-background border-b border-border flex overflow-x-auto no-scrollbar">
          {tabs.map((tb) => (
            <button
              key={tb.key}
              data-testid={`deep-tab-${tb.key}`}
              onClick={() => setTab(tb.key)}
              className={`flex-1 shrink-0 min-w-[5.5rem] px-2 md:px-4 h-12 md:h-14 font-mono-caps flex items-center justify-center gap-1.5 md:gap-2 transition-colors border-r border-border last:border-r-0 ${
                tab === tb.key ? "bg-foreground text-background" : "hover:bg-secondary"
              }`}
            >
              <tb.icon className="w-4 h-4 shrink-0" />
              <span className="truncate">{tb.label}</span>
            </button>
          ))}
        </div>

        <div className="p-4 md:p-8">
          {tab === "deep" && (
            <>
              {loadingDeep && (
                <div className="flex items-center gap-3 text-muted-foreground py-6" data-testid="deep-dive-loading">
                  <Loader2 className="w-5 h-5 animate-spin" /> {t(lang, "loading")}
                </div>
              )}
              {!loadingDeep && data && (
                <div className="space-y-8" data-testid="deep-dive-content">
                  {data.real_reasons && (
                    <section>
                      <div className="flex items-center gap-2 mb-3 font-mono-caps text-accent">
                        <Landmark className="w-4 h-4" /> {t(lang, "real_reasons")}
                      </div>
                      <div className="text-base md:text-lg leading-relaxed text-foreground/90"><ClickableText text={data.real_reasons} /></div>
                    </section>
                  )}
                  {data.data_points?.length > 0 && (
                    <section>
                      <div className="flex items-center gap-2 mb-3 font-mono-caps text-accent">
                        <BarChart3 className="w-4 h-4" /> {t(lang, "data_points")}
                      </div>
                      <ul className="space-y-2 col-rule">
                        {data.data_points.map((d, i) => (
                          <li key={i} className="pt-2 text-base md:text-lg text-foreground/90"><ClickableText text={d} /></li>
                        ))}
                      </ul>
                    </section>
                  )}
                  {data.context && (
                    <section>
                      <div className="flex items-center gap-2 mb-3 font-mono-caps text-accent">
                        <BookOpen className="w-4 h-4" /> {t(lang, "context")}
                      </div>
                      <div className="text-base md:text-lg leading-relaxed text-foreground/90"><ClickableText text={data.context} /></div>
                    </section>
                  )}
                  {data.key_facts?.length > 0 && (
                    <section>
                      <div className="flex items-center gap-2 mb-3 font-mono-caps text-accent">
                        <ScrollText className="w-4 h-4" /> {t(lang, "key_facts")}
                      </div>
                      <ul className="space-y-2">
                        {data.key_facts.map((f, i) => (
                          <li key={i} className="flex gap-3 text-base md:text-lg">
                            <span className="font-mono-caps text-muted-foreground shrink-0 mt-1">{String(i + 1).padStart(2, "0")}</span>
                            <span><ClickableText text={f} /></span>
                          </li>
                        ))}
                      </ul>
                    </section>
                  )}
                </div>
              )}
            </>
          )}

          {tab === "qa" && (
            <div className="space-y-6" data-testid="deep-qa">
              <form onSubmit={submitQa} className="flex items-stretch border border-foreground h-14">
                <input
                  data-testid="deep-qa-input"
                  value={qaInput}
                  onChange={(e) => setQaInput(e.target.value)}
                  placeholder={t(lang, "ask_about_article")}
                  className="flex-1 bg-transparent outline-none px-4 text-base"
                />
                <button
                  type="submit"
                  data-testid="deep-qa-submit"
                  disabled={asking || !qaInput.trim()}
                  className="px-5 font-mono-caps bg-foreground text-background hover:bg-accent transition-colors flex items-center gap-2 disabled:opacity-60"
                >
                  {asking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  {t(lang, "ask_about_send")}
                </button>
              </form>
              {qas.length === 0 ? (
                <div className="text-muted-foreground font-mono-caps text-sm">{t(lang, "no_qas_yet")}</div>
              ) : (
                <div className="col-rule">
                  {qas.map((qa) => (
                    <div key={qa.id} className="py-5" data-testid={`qa-item-${qa.id}`}>
                      <div className="flex gap-3 items-start mb-3">
                        <ArrowRight className="w-4 h-4 text-accent shrink-0 mt-1.5" />
                        <div className="font-serif-display text-lg leading-snug"><ClickableText text={qa.question} /></div>
                      </div>
                      <div className="pl-7 space-y-2">
                        <div className="text-base leading-relaxed"><ClickableText text={qa.answer} /></div>
                        {qa.key_points?.length > 0 && (
                          <ul className="mt-2 space-y-1">
                            {qa.key_points.map((p, i) => (
                              <li key={i} className="flex gap-2 text-sm text-foreground/80">
                                <span className="font-mono-caps text-accent text-[10px] mt-1">•</span>
                                <span><ClickableText text={p} contextText={qa.answer} /></span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === "debate" && (
            <div data-testid="deep-debate">
              {loadingDebate && (
                <div className="flex items-center gap-3 text-muted-foreground py-6">
                  <Loader2 className="w-5 h-5 animate-spin" /> {t(lang, "loading")}
                </div>
              )}
              {!loadingDebate && debate && (
                <div className="space-y-8">
                  <div className="font-mono-caps text-accent flex items-center gap-2">
                    <Users className="w-4 h-4" /> {t(lang, "debate_title")}
                  </div>
                  <div className="grid gap-6">
                    {debate.sides.map((s, i) => (
                      <div key={i} className="border-l-2 border-foreground pl-5" data-testid={`debate-side-${i}`}>
                        <div className="font-mono-caps text-[11px] text-muted-foreground mb-1">
                          {lang === "it" ? `PARTE ${String(i + 1).padStart(2, "0")}` : `SIDE ${String(i + 1).padStart(2, "0")}`}
                        </div>
                        <div className="font-serif-display text-2xl leading-tight mb-2">{s.persona}</div>
                        <div className="text-base italic text-foreground/85 mb-3">"<ClickableText text={s.stance} />"</div>
                        <ul className="space-y-2">
                          {s.arguments.map((a, j) => (
                            <li key={j} className="flex gap-3 text-sm md:text-base">
                              <span className="font-mono-caps text-accent shrink-0 mt-1">{String(j + 1).padStart(2, "0")}</span>
                              <span><ClickableText text={a} /></span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                  {debate.synthesis && (
                    <section className="border-t border-border pt-6">
                      <div className="font-mono-caps text-accent mb-2">{t(lang, "debate_synthesis")}</div>
                      <div className="text-base md:text-lg leading-relaxed"><ClickableText text={debate.synthesis} /></div>
                    </section>
                  )}
                </div>
              )}
            </div>
          )}
          {tab === "history" && (
            <div data-testid="deep-history">
              {loadingHistory && (
                <div className="flex items-center gap-3 text-muted-foreground py-6">
                  <Loader2 className="w-5 h-5 animate-spin" /> {t(lang, "loading")}
                </div>
              )}

              {!loadingHistory && historyError && (
                <div className="py-6 space-y-4">
                  <div className="text-muted-foreground">{t(lang, "history_empty")}</div>
                  <button
                    data-testid="history-retry"
                    onClick={() => loadHistory({ force: true })}
                    className="h-11 px-5 border border-foreground hover:bg-foreground hover:text-background transition-colors font-mono-caps"
                  >
                    {t(lang, "retry")}
                  </button>
                </div>
              )}

              {!loadingHistory && !historyError && history && (
                <div className="space-y-8">
                  <div className="font-mono-caps text-accent flex items-center gap-2">
                    <History className="w-4 h-4" /> {t(lang, "history_title")}
                  </div>

                  {history.summary && (
                    <section>
                      <div className="font-mono-caps text-muted-foreground mb-2">{t(lang, "history_summary")}</div>
                      <div className="text-base md:text-lg leading-relaxed text-foreground/90">
                        <ClickableText text={history.summary} />
                      </div>
                      <div className="mt-4">
                        <AudioButton text={history.summary} testid={`history-audio-${item?.id}`} />
                      </div>
                    </section>
                  )}

                  {history.events?.length > 0 && (
                    <section>
                      <div className="font-mono-caps text-accent mb-4 flex items-center gap-2">
                        <ScrollText className="w-4 h-4" /> {t(lang, "history_events")}
                      </div>
                      {/* linea verticale = asse del tempo, dal più antico al presente */}
                      <ol className="relative border-l border-border ml-2">
                        {history.events.map((ev, i) => (
                          <li key={i} className="relative pl-6 pb-7 last:pb-0" data-testid={`history-event-${i}`}>
                            <span className="absolute -left-[5px] top-1.5 w-[9px] h-[9px] bg-accent rounded-full" />
                            <div className="font-mono-caps text-accent text-[11px] mb-1">{ev.date}</div>
                            <div className="font-serif-display text-xl md:text-2xl leading-snug mb-1">
                              <ClickableText text={ev.title} contextText={ev.description} />
                            </div>
                            {ev.description && (
                              <div className="text-sm md:text-base text-foreground/85 leading-relaxed">
                                <ClickableText text={ev.description} />
                              </div>
                            )}
                            {ev.significance && (
                              <div className="mt-2 text-sm text-muted-foreground border-l-2 border-border pl-3">
                                <ClickableText text={ev.significance} contextText={ev.description} />
                              </div>
                            )}
                          </li>
                        ))}
                      </ol>
                    </section>
                  )}

                  {history.turning_points?.length > 0 && (
                    <section className="border-t border-border pt-6">
                      <div className="font-mono-caps text-accent mb-3 flex items-center gap-2">
                        <Milestone className="w-4 h-4" /> {t(lang, "history_turning")}
                      </div>
                      <ul className="space-y-2">
                        {history.turning_points.map((p, i) => (
                          <li key={i} className="flex gap-3 text-base">
                            <span className="font-mono-caps text-muted-foreground shrink-0 mt-1">{String(i + 1).padStart(2, "0")}</span>
                            <span><ClickableText text={p} /></span>
                          </li>
                        ))}
                      </ul>
                    </section>
                  )}

                  {history.open_questions?.length > 0 && (
                    <section className="border-t border-border pt-6">
                      <div className="font-mono-caps text-accent mb-3 flex items-center gap-2">
                        <HelpCircle className="w-4 h-4" /> {t(lang, "history_open")}
                      </div>
                      <ul className="space-y-2">
                        {history.open_questions.map((q, i) => (
                          <li key={i} className="flex gap-2 text-sm md:text-base text-foreground/85">
                            <span className="text-accent shrink-0">•</span>
                            <span><ClickableText text={q} /></span>
                          </li>
                        ))}
                      </ul>
                    </section>
                  )}
                </div>
              )}
            </div>
          )}

          {tab === "verify" && (
            <div data-testid="deep-verify">
              <VerifyPanel briefingId={item.id} />
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
