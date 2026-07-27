import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useLang } from "@/context/LangContext";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import { toast } from "sonner";
import { Link, useNavigate } from "react-router-dom";
import { Loader2, LogOut } from "lucide-react";

export default function ProfilePage() {
  const { user, updatePrefs, logout, loading } = useAuth();
  const { lang, setLang } = useLang();
  const nav = useNavigate();
  const [topics, setTopics] = useState([]);
  const [selected, setSelected] = useState([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/topics").then(({ data }) => setTopics(data));
  }, []);

  useEffect(() => {
    if (user) setSelected(user.preferred_topics || []);
  }, [user]);

  if (loading) return <div className="py-24 flex items-center gap-3 text-muted-foreground"><Loader2 className="w-5 h-5 animate-spin" /> {t(lang, "loading")}</div>;

  if (!user) {
    return (
      <div className="max-w-lg space-y-4">
        <div className="font-mono-caps text-accent">{t(lang, "profile")}</div>
        <h1 className="font-serif-display text-4xl md:text-5xl">{t(lang, "login_cta")}</h1>
        <div className="flex gap-4 pt-2">
          <Link to="/login" data-testid="profile-goto-login" className="h-12 px-5 bg-foreground text-background inline-flex items-center font-mono-caps">{t(lang, "login")}</Link>
          <Link to="/register" data-testid="profile-goto-register" className="h-12 px-5 border border-border inline-flex items-center font-mono-caps">{t(lang, "register")}</Link>
        </div>
      </div>
    );
  }

  const toggle = (key) => {
    setSelected((s) => s.includes(key) ? s.filter(k => k !== key) : [...s, key]);
  };

  const save = async () => {
    setBusy(true);
    try {
      await updatePrefs({ preferred_topics: selected, language: lang });
      toast.success(t(lang, "prefs_saved"));
    } catch (e) {
      toast.error(t(lang, "error_generic"));
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-10 max-w-4xl">
      <div>
        <div className="font-mono-caps text-accent mb-2">{t(lang, "profile")}</div>
        <h1 className="font-serif-display text-4xl md:text-5xl">{user.name || user.email}</h1>
        <div className="text-muted-foreground mt-1">{user.email}</div>
      </div>

      <section>
        <h2 className="font-serif-display text-2xl md:text-3xl mb-4">{t(lang, "lang_label")}</h2>
        <div className="flex gap-2">
          {["it", "en"].map((l) => (
            <button
              key={l}
              data-testid={`profile-lang-${l}`}
              onClick={() => setLang(l)}
              className={`h-12 px-5 border font-mono-caps ${lang === l ? "bg-foreground text-background border-foreground" : "border-border"}`}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>
      </section>

      <section>
        <h2 className="font-serif-display text-2xl md:text-3xl mb-4">{t(lang, "choose_topics")}</h2>
        <div className="flex flex-wrap gap-2">
          {topics.map((topic) => {
            const active = selected.includes(topic.key);
            const label = lang === "it" ? topic.label_it : topic.label_en;
            return (
              <button
                key={topic.key}
                data-testid={`profile-topic-${topic.key}`}
                onClick={() => toggle(topic.key)}
                className={`px-4 h-12 border font-mono-caps ${active ? "bg-foreground text-background border-foreground" : "border-border hover:border-foreground"}`}
              >
                {label}
              </button>
            );
          })}
        </div>
        <button
          data-testid="save-prefs-btn"
          onClick={save} disabled={busy}
          className="mt-6 h-12 px-6 bg-accent text-accent-foreground font-mono-caps flex items-center gap-2"
        >
          {busy && <Loader2 className="w-4 h-4 animate-spin" />} {t(lang, "save_prefs")}
        </button>
      </section>

      <section className="border-t border-border pt-8">
        <button
          data-testid="profile-logout-btn"
          onClick={() => { logout(); nav("/"); }}
          className="h-12 px-5 border border-border font-mono-caps flex items-center gap-2"
        >
          <LogOut className="w-4 h-4" /> {t(lang, "logout")}
        </button>
      </section>
    </div>
  );
}
