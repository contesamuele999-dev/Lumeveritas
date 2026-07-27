import { useState } from "react";
import { useLang } from "@/context/LangContext";
import { t } from "@/lib/i18n";
import { Bookmark, BookmarkCheck, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import DeepDiveSheet from "@/components/DeepDiveSheet";

export default function NewsItem({ item, featured = false, onSaveToggle, initiallySaved = false }) {
  const { lang } = useLang();
  const { user } = useAuth();
  const [openDeep, setOpenDeep] = useState(false);
  const [saved, setSaved] = useState(initiallySaved);
  const [busy, setBusy] = useState(false);

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
      className={`reveal ${featured ? "py-6" : "py-6"}`}
    >
      <div className="font-mono-caps text-muted-foreground mb-3 flex items-center gap-3">
        <span>{item.topic}</span>
        <span className="w-1 h-1 bg-muted-foreground rounded-full" />
        <span className="tabular">{new Date(item.generated_at).toLocaleDateString(lang === "it" ? "it-IT" : "en-US")}</span>
      </div>
      <h3 className={`font-serif-display leading-[1.05] tracking-tight mb-4 ${featured ? "text-4xl md:text-6xl" : "text-2xl md:text-3xl"}`}>
        {item.headline}
      </h3>
      <p className={`text-foreground/85 ${featured ? "text-lg md:text-xl max-w-3xl" : "text-base md:text-lg max-w-2xl"} leading-relaxed`}>
        {item.summary}
      </p>

      {item.key_facts?.length > 0 && (
        <ul className="mt-5 space-y-2 max-w-2xl">
          {item.key_facts.slice(0, featured ? 5 : 3).map((f, i) => (
            <li key={i} className="flex gap-3 text-sm md:text-base">
              <span className="font-mono-caps text-accent shrink-0 mt-1">{String(i + 1).padStart(2, "0")}</span>
              <span className="text-foreground/80">{f}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          data-testid={`approfondisci-btn-${item.id}`}
          onClick={() => setOpenDeep(true)}
          className="h-12 px-5 bg-accent text-accent-foreground hover:opacity-90 transition-opacity font-mono-caps flex items-center gap-2"
        >
          <Sparkles className="w-4 h-4" /> {t(lang, "approfondisci")}
        </button>
        <button
          data-testid={`save-btn-${item.id}`}
          onClick={toggleSave}
          disabled={busy}
          className="h-12 px-5 border border-border hover:border-foreground transition-colors font-mono-caps flex items-center gap-2"
        >
          {saved ? <BookmarkCheck className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
          {saved ? t(lang, "unsave") : t(lang, "save")}
        </button>
      </div>

      <DeepDiveSheet item={item} open={openDeep} onOpenChange={setOpenDeep} />
    </article>
  );
}
