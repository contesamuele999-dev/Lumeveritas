import { useEffect, useRef } from "react";

/**
 * Overlay aperto = una voce in più nella history del browser.
 * Così il tasto Indietro (o la gesture su mobile) chiude l'overlay e riporta alla
 * pagina precedente, invece di uscire dal sito.
 */
export default function useBackClose(open, onClose) {
  const pushed = useRef(false);
  const cb = useRef(onClose);
  cb.current = onClose;

  useEffect(() => {
    if (open && !pushed.current) {
      pushed.current = true;
      window.history.pushState({ lvOverlay: true }, "");
    } else if (!open && pushed.current) {
      pushed.current = false;
      if (window.history.state?.lvOverlay) window.history.back();
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onPop = () => { pushed.current = false; cb.current(); };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [open]);
}
