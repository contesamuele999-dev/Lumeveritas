import { useEffect, useState } from "react";
import { useLang } from "@/context/LangContext";
import { Download, X, Share } from "lucide-react";

const DISMISSED = "lv_install_dismissed";
const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent);
const isStandalone = () =>
  window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;

export default function InstallPrompt() {
  const { lang } = useLang();
  const [deferred, setDeferred] = useState(null);
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (isStandalone() || localStorage.getItem(DISMISSED)) return;

    const onPrompt = (e) => { e.preventDefault(); setDeferred(e); setShow(true); };
    window.addEventListener("beforeinstallprompt", onPrompt);
    // iOS non espone beforeinstallprompt: si spiegano i due passaggi a mano
    const timer = isIOS() ? setTimeout(() => setShow(true), 3000) : null;

    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (!show) return null;

  const close = () => { localStorage.setItem(DISMISSED, "1"); setShow(false); };

  const install = async () => {
    if (!deferred) return;
    deferred.prompt();
    await deferred.userChoice;
    setDeferred(null);
    close();
  };

  return (
    <div
      data-testid="install-prompt"
      className="fixed z-50 bottom-20 md:bottom-6 inset-x-3 md:inset-x-auto md:right-6 md:w-96 border border-foreground bg-background shadow-lg p-4"
    >
      <button
        onClick={close}
        data-testid="install-close"
        aria-label={lang === "it" ? "Chiudi" : "Close"}
        className="absolute top-2 right-2 p-1 text-muted-foreground hover:text-foreground"
      >
        <X className="w-4 h-4" />
      </button>
      <div className="font-mono-caps text-accent mb-1">{lang === "it" ? "Installa l'app" : "Install the app"}</div>
      <div className="font-serif-display text-xl leading-tight mb-2">
        {lang === "it" ? "Lume Veritas sul tuo telefono" : "Lume Veritas on your phone"}
      </div>
      <p className="text-sm text-foreground/75 mb-3">
        {deferred
          ? (lang === "it"
              ? "Aggiungila alla schermata home: si apre a tutto schermo, senza browser."
              : "Add it to your home screen: full screen, no browser bar.")
          : (lang === "it"
              ? "Su iPhone: tocca Condividi e poi «Aggiungi a Home»."
              : "On iPhone: tap Share, then “Add to Home Screen”.")}
      </p>
      {deferred ? (
        <button
          onClick={install}
          data-testid="install-btn"
          className="h-11 px-4 w-full bg-accent text-accent-foreground font-mono-caps flex items-center justify-center gap-2 hover:opacity-90"
        >
          <Download className="w-4 h-4" /> {lang === "it" ? "Scarica l'app" : "Get the app"}
        </button>
      ) : (
        <div className="h-11 px-4 border border-border font-mono-caps flex items-center justify-center gap-2 text-muted-foreground">
          <Share className="w-4 h-4" /> {lang === "it" ? "Condividi → Aggiungi a Home" : "Share → Add to Home Screen"}
        </div>
      )}
    </div>
  );
}
