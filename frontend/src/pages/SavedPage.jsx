import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useLang } from "@/context/LangContext";
import { t } from "@/lib/i18n";
import NewsItem from "@/components/NewsItem";
import { Loader2 } from "lucide-react";
import { Link } from "react-router-dom";

export default function SavedPage() {
  const { user, loading: authLoading } = useAuth();
  const { lang } = useLang();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    if (!user) { setLoading(false); return; }
    setLoading(true);
    api.get("/saved").then(({ data }) => setItems(data)).finally(() => setLoading(false));
  };

  useEffect(() => { if (!authLoading) load(); }, [user, authLoading]); // eslint-disable-line react-hooks/exhaustive-deps

  if (authLoading) return <div className="py-24 flex items-center gap-3 text-muted-foreground"><Loader2 className="w-5 h-5 animate-spin" /> {t(lang, "loading")}</div>;

  if (!user) {
    return (
      <div className="max-w-lg">
        <div className="font-mono-caps text-accent mb-3">{t(lang, "saved")}</div>
        <h1 className="font-serif-display text-4xl md:text-5xl mb-4">{t(lang, "login_first")}</h1>
        <Link to="/login" data-testid="saved-login-link" className="font-mono-caps link-underline text-accent">{t(lang, "login")}</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="font-mono-caps text-accent mb-2">{t(lang, "saved")}</div>
        <h1 className="font-serif-display text-4xl md:text-5xl">{t(lang, "saved")}</h1>
      </div>
      {loading ? (
        <div className="py-16 flex items-center gap-3 text-muted-foreground"><Loader2 className="w-5 h-5 animate-spin" /> {t(lang, "loading")}</div>
      ) : items.length === 0 ? (
        <div className="py-16 text-muted-foreground font-mono-caps">{t(lang, "empty_saved")}</div>
      ) : (
        <div className="col-rule">
          {items.map((it) => (
            <NewsItem key={it.id} item={it} initiallySaved onSaveToggle={load} />
          ))}
        </div>
      )}
    </div>
  );
}
