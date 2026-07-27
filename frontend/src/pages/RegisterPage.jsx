import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useLang } from "@/context/LangContext";
import { t } from "@/lib/i18n";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export default function RegisterPage() {
  const { register } = useAuth();
  const { lang } = useLang();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await register(email, password, name);
      toast.success("OK");
      nav("/");
    } catch (err) {
      toast.error(err?.response?.data?.detail || t(lang, "error_generic"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-md">
      <div className="font-mono-caps text-accent mb-3">{t(lang, "register")}</div>
      <h1 className="font-serif-display text-4xl md:text-5xl leading-none tracking-tight mb-6">{t(lang, "register_cta")}</h1>
      <form onSubmit={onSubmit} className="space-y-4" data-testid="register-form">
        <div>
          <label className="font-mono-caps text-muted-foreground">{t(lang, "name")}</label>
          <input
            data-testid="register-name-input"
            value={name} onChange={(e) => setName(e.target.value)}
            className="w-full h-14 mt-2 px-4 border border-border bg-background focus:border-foreground outline-none text-lg"
          />
        </div>
        <div>
          <label className="font-mono-caps text-muted-foreground">{t(lang, "email")}</label>
          <input
            data-testid="register-email-input"
            type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
            className="w-full h-14 mt-2 px-4 border border-border bg-background focus:border-foreground outline-none text-lg"
          />
        </div>
        <div>
          <label className="font-mono-caps text-muted-foreground">{t(lang, "password")}</label>
          <input
            data-testid="register-password-input"
            type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)}
            className="w-full h-14 mt-2 px-4 border border-border bg-background focus:border-foreground outline-none text-lg"
          />
        </div>
        <button
          type="submit" disabled={busy}
          data-testid="register-submit-btn"
          className="w-full h-14 bg-foreground text-background font-mono-caps hover:bg-accent transition-colors flex items-center justify-center gap-2"
        >
          {busy && <Loader2 className="w-4 h-4 animate-spin" />} {t(lang, "submit")}
        </button>
      </form>
      <div className="mt-6 text-sm">
        {t(lang, "have_account")} <Link to="/login" data-testid="go-login-link" className="link-underline text-accent">{t(lang, "login")}</Link>
      </div>
    </div>
  );
}
