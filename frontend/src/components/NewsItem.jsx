import { useEffect, useState } from "react";
import { useLang } from "@/context/LangContext";
import { t } from "@/lib/i18n";
import { Bookmark, BookmarkCheck, Sparkles, Users, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import DeepDiveSheet from "@/components/DeepDiveSheet";
import ClickableText from "@/components/ClickableText";
import SourceLinks from "@/components/SourceLinks";
import AudioButton from "@/components/AudioButton";
import ShareButton from "@/components/ShareButton";
import { VerifyBadge } from "@/components/VerifyPanel";

export default function NewsItem({ item, featured = false, onSaveToggle, initiallySaved = false }) {
  const { lang } = useLang();
  const { user } = useAuth();
  const [openDeep, setOpenDeep] = useState(false);
  const [initialTab, setInitialTab] = useState("deep");
  const [saved, setSaved] = useState(initiallySaved);
  const [busy, setBusy] = useState(false);
  const [verifyScore, setVerifyScore] = useState(null);

  useEffect(() => {
    let cancel = false;
    api.get(`/news/${item.id}/verify`).then(({ data }) => {
      if (!cancel) setVerifyScore(data.overall_score);
    }).catch(() => {});
    return () => { cancel = true; };
  }, [item.id]);

  const toggleSave = async () => {
    if (!user) { toast.error(t(lang, "login_first")); return; }
    setBusy(true);
    try {
      if (saved) {
        await api.delete(`/saved/${item.id}`);
        setSaved(false);
        toast.success(t(lang, "unsaved_ok"));
      } else {
        await api.post(`/saved/add`, { briefing_id: item.id });
        setSaved(true);
        toast.success(t(lang, "saved_ok"));
      }
      onSaveToggle && onSaveToggle();
    } catch (e) {
      toast.error(t(lang, "error_generic"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <article
      data-testid={`news-item-${item.id}`}
      className="reveal py-4 md:py-6"
    >
      <div className="font-mono-caps text-muted-foreground mb-2 md:mb-3 flex items-center gap-2 md:gap-3">
        <span>{item.topic}</span>
        <span className="w-1 h-1 bg-muted-foreground rounded-full" />
        <span className="tabular">{new Date(item.generated_at).toLocaleDateString(lang === "it" ? "it-IT" : "en-US")}</span>
      </div>
      <h3 className={`font-serif-display leading-[1.05] tracking-tight mb-2 md:mb-4 ${featured ? "text-2xl md:text-6xl" : "text-xl md:text-3xl"}`}>
        <ClickableText text={item.headline} contextText={item.summary} />
      </h3>
      <div className={`text-foreground/85 ${featured ? "text-base md:text-xl max-w-3xl" : "text-sm md:text-lg max-w-2xl"} leading-relaxed`}>
        <ClickableText text={item.summary} />
      </div>

      {item.key_facts?.length > 0 && (
        <ul className="mt-3 md:mt-5 space-y-1.5 md:space-y-2 max-w-2xl">
          {item.key_facts.slice(0, featured ? 5 : 3).map((f, i) => (
            <li key={i} className="flex gap-2 md:gap-3 text-sm md:text-base">
              <span className="font-mono-caps text-accent shrink-0 mt-1">{String(i + 1).padStart(2, "0")}</span>
              <span className="text-foreground/80"><ClickableText text={f} contextText={item.summary} /></span>
            </li>
          ))}
        </ul>
      )}

      <SourceLinks sources={item.sources} compact />

      <div className="mt-4 md:mt-6 flex flex-wrap items-center gap-2 md:gap-3">
        <button
          data-testid={`approfondisci-btn-${item.id}`}
          onClick={() => { setInitialTab("deep"); setOpenDeep(true); }}
          className="h-10 md:h-12 px-3 md:px-5 bg-accent text-accent-foreground hover:opacity-90 transition-opacity font-mono-caps flex items-center gap-2"
        >
          <Sparkles className="w-4 h-4" /> {t(lang, "approfondisci")}
        </button>
        <button
          data-testid={`debate-btn-${item.id}`}
          onClick={() => { setInitialTab("debate"); setOpenDeep(true); }}
          className="h-10 md:h-12 px-3 md:px-5 border border-foreground bg-background hover:bg-foreground hover:text-background transition-colors font-mono-caps flex items-center gap-2"
        >
          <Users className="w-4 h-4" /> {t(lang, "debate_btn")}
        </button>
        <button
          data-testid={`verify-btn-${item.id}`}
          onClick={() => { setInitialTab("verify"); setOpenDeep(true); }}
          className="h-10 md:h-12 px-3 md:px-5 border border-foreground bg-background hover:bg-emerald-600 hover:text-white hover:border-emerald-600 transition-colors font-mono-caps flex items-center gap-2"
        >
          <ShieldCheck className="w-4 h-4" /> {t(lang, "verify_btn")}
        </button>
        <button
          data-testid={`save-btn-${item.id}`}
          onClick={toggleSave}
          disabled={busy}
          className="h-10 md:h-12 px-3 md:px-5 border border-border hover:border-foreground transition-colors font-mono-caps flex items-center gap-2"
        >
          {saved ? <BookmarkCheck className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
          {saved ? t(lang, "unsave") : t(lang, "save")}
        </button>
        <AudioButton item={item} testid={`audio-btn-${item.id}`} />
        <ShareButton briefingId={item.id} testid={`share-btn-${item.id}`} />
      </div>

      <DeepDiveSheet item={item} open={openDeep} onOpenChange={setOpenDeep} initialTab={initialTab} />
    </article>
  );
}
