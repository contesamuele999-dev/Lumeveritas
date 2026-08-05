import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useLang } from "@/context/LangContext";
import { useAuth } from "@/context/AuthContext";
import { t } from "@/lib/i18n";
import { Sun, Moon, LogIn, LogOut, User, Bookmark, Home, MessageCircleQuestion, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import InstallPrompt from "@/components/InstallPrompt";

export default function AppShell() {
  const { lang, setLang, theme, setTheme } = useLang();
  const { user, logout } = useAuth();
  const nav = useNavigate();

  const links = [
    { to: "/", label: t(lang, "home"), icon: Home, testid: "nav-home" },
    { to: "/ask", label: t(lang, "ask"), icon: MessageCircleQuestion, testid: "nav-ask" },
    { to: "/saved", label: t(lang, "saved"), icon: Bookmark, testid: "nav-saved" },
    { to: "/profile", label: t(lang, "profile"), icon: User, testid: "nav-profile" },
  ];

  return (
    <div className="App min-h-screen grain relative">
      {/* HEADER */}
      <header data-app-header className="sticky top-0 z-40 bg-background/85 backdrop-blur-md border-b border-border">
        <div className="max-w-[1400px] mx-auto px-4 md:px-10 py-2.5 md:py-4 flex items-center gap-3 md:gap-6">
          <button
            data-testid="brand-home-btn"
            onClick={() => nav("/")}
            className="flex items-center gap-3 group"
          >
            <div className="w-8 h-8 md:w-10 md:h-10 shrink-0 bg-foreground text-background flex items-center justify-center font-serif-display text-xl font-semibold">L</div>
            <div className="hidden sm:block text-left leading-tight">
              <div className="font-serif-display text-xl md:text-2xl font-semibold tracking-tight">Lume Veritas</div>
              <div data-app-tagline className="font-mono-caps text-muted-foreground">{t(lang, "tagline")}</div>
            </div>
          </button>

          <div className="flex-1" />

          <div className="hidden md:flex items-center gap-1">
            <button
              data-testid="lang-toggle-btn"
              onClick={() => setLang(lang === "it" ? "en" : "it")}
              className="flex items-center gap-2 px-3 h-11 border border-border hover:bg-secondary transition-colors font-mono-caps"
              title={t(lang, "lang_label")}
            >
              <Globe className="w-4 h-4" />
              {lang.toUpperCase()}
            </button>
            <button
              data-testid="theme-toggle-btn"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="flex items-center justify-center w-11 h-11 border border-border hover:bg-secondary transition-colors"
              title={t(lang, "theme_label")}
            >
              {theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
          </div>

          {user ? (
            <Button
              data-testid="header-logout-btn"
              variant="ghost"
              onClick={() => { logout(); nav("/"); }}
              className="hidden md:inline-flex h-11"
            >
              <LogOut className="w-4 h-4 mr-2" /> {t(lang, "logout")}
            </Button>
          ) : (
            <Button
              data-testid="header-login-btn"
              onClick={() => nav("/login")}
              className="hidden md:inline-flex h-11 bg-foreground text-background hover:bg-foreground/90"
            >
              <LogIn className="w-4 h-4 mr-2" /> {t(lang, "login")}
            </Button>
          )}
        </div>

        {/* Desktop tab-bar */}
        <nav data-app-tabbar className="hidden md:block border-t border-border">
          <div className="max-w-[1400px] mx-auto px-10 flex items-center gap-0">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                data-testid={l.testid}
                className={({ isActive }) =>
                  `font-mono-caps px-5 py-4 border-r border-border hover:bg-secondary transition-colors flex items-center gap-2 ${
                    isActive ? "bg-foreground text-background hover:bg-foreground" : ""
                  }`
                }
              >
                <l.icon className="w-4 h-4" />
                {l.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>

      {/* MAIN */}
      <main data-app-main className="max-w-[1400px] mx-auto px-4 md:px-10 py-5 md:py-12 relative z-10 pl-[env(safe-area-inset-left)] pr-[env(safe-area-inset-right)]">
        <Outlet />
      </main>

      {/* MOBILE BOTTOM NAV */}
      <nav
        data-app-bottomnav
        className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-background border-t border-border grid grid-cols-4 pb-[env(safe-area-inset-bottom)] px-[env(safe-area-inset-left)]"
      >
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            data-testid={`mobile-${l.testid}`}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center py-2 gap-0.5 font-mono-caps ${
                isActive ? "text-accent" : "text-muted-foreground"
              }`
            }
          >
            <l.icon className="w-4 h-4" />
            <span className="text-[10px]">{l.label}</span>
          </NavLink>
        ))}
      </nav>

      <InstallPrompt />

      {/* Footer — su mobile lo spazio in fondo evita che la firma finisca sotto la nav fissa */}
      <footer data-app-footer className="border-t border-border mt-10 md:mt-16 pt-6 md:pt-8 pb-[calc(6rem+env(safe-area-inset-bottom))] md:pb-8 max-w-[1400px] mx-auto px-4 md:px-10 relative z-10">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
          <div className="font-mono-caps text-muted-foreground">
            © Lume Veritas — {new Date().getFullYear()}
          </div>
          <div className="text-sm text-muted-foreground max-w-xl">
            {t(lang, "no_data_note")}
          </div>
        </div>

        {/* Firma */}
        <div className="mt-8 pt-6 border-t border-border flex flex-col items-center gap-3 text-center" data-testid="signature">
          <blockquote className="font-serif-display text-xl md:text-2xl italic leading-snug">
            &ldquo;{lang === "it" ? "La verità ci rende liberi" : "The truth sets us free"}&rdquo;
          </blockquote>
          <div className="flex items-center gap-3 text-muted-foreground">
            <span className="h-px w-8 bg-border" />
            <span className="font-mono-caps text-[10px]">
              {lang === "it" ? "Costruito da" : "Built by"}
            </span>
            <span className="h-px w-8 bg-border" />
          </div>
          <div className="font-serif-display text-lg tracking-tight">
            Samuele Contessa
            <span className="text-accent">.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
