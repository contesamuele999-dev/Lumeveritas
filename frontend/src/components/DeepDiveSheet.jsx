import { useEffect, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import ClickableText from "@/components/ClickableText";
import { api } from "@/lib/api";
import { useLang } from "@/context/LangContext";
import { t } from "@/lib/i18n";
import { Loader2, BookOpen, BarChart3, Landmark, ScrollText } from "lucide-react";

export default function DeepDiveSheet({ item, open, onOpenChange }) {
  const { lang } = useLang();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(item);

  useEffect(() => {
    let cancel = false;
    const load = async () => {
      if (!open || !item) return;
      if (item.real_reasons) { setData(item); return; }
      setLoading(true);
      try {
        const { data: d } = await api.post(`/news/deep-dive/${item.id}`);
        if (!cancel) setData(d);
      } catch (e) {
        // silent
      } finally {
        if (!cancel) setLoading(false);
      }
    };
    load();
    return () => { cancel = true; };
  }, [open, item]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-2xl overflow-y-auto p-0" data-testid="deep-dive-sheet">
        <div className="p-6 md:p-8 border-b border-border">
          <div className="font-mono-caps text-accent mb-3">{t(lang, "approfondisci")}</div>
          <SheetHeader className="text-left space-y-2">
            <SheetTitle className="font-serif-display text-3xl md:text-4xl leading-tight tracking-tight">
              {data?.headline}
            </SheetTitle>
            <SheetDescription className="sr-only">
              {t(lang, "approfondisci")}: {data?.headline}
            </SheetDescription>
          </SheetHeader>
          <div className="mt-4 text-base md:text-lg text-foreground/85 leading-relaxed">
            <ClickableText text={data?.summary} />
          </div>
        </div>

        {loading && (
          <div className="p-10 flex items-center gap-3 text-muted-foreground" data-testid="deep-dive-loading">
            <Loader2 className="w-5 h-5 animate-spin" /> {t(lang, "loading")}
          </div>
        )}

        {!loading && data && (
          <div className="p-6 md:p-8 space-y-8" data-testid="deep-dive-content">
            {data.real_reasons && (
              <section>
                <div className="flex items-center gap-2 mb-3 font-mono-caps text-accent">
                  <Landmark className="w-4 h-4" /> {t(lang, "real_reasons")}
                </div>
                <div className="text-base md:text-lg leading-relaxed text-foreground/90">
                  <ClickableText text={data.real_reasons} />
                </div>
              </section>
            )}

            {data.data_points?.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-3 font-mono-caps text-accent">
                  <BarChart3 className="w-4 h-4" /> {t(lang, "data_points")}
                </div>
                <ul className="space-y-2 col-rule">
                  {data.data_points.map((d, i) => (
                    <li key={i} className="pt-2 text-base md:text-lg text-foreground/90">
                      <ClickableText text={d} />
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {data.context && (
              <section>
                <div className="flex items-center gap-2 mb-3 font-mono-caps text-accent">
                  <BookOpen className="w-4 h-4" /> {t(lang, "context")}
                </div>
                <div className="text-base md:text-lg leading-relaxed text-foreground/90">
                  <ClickableText text={data.context} />
                </div>
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
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {data.sources_hint?.length > 0 && (
              <section>
                <div className="font-mono-caps text-muted-foreground mb-2">{t(lang, "sources")}</div>
                <ul className="text-sm text-muted-foreground space-y-1">
                  {data.sources_hint.map((s, i) => <li key={i}>• {s}</li>)}
                </ul>
              </section>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
