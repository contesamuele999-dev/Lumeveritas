import { useEffect } from "react";
import { useLocation, useNavigationType } from "react-router-dom";

/* React Router non riporta la pagina in cima quando cambi sezione: chi arrivava in fondo
   alla home e toccava "Chiedi" si ritrovava a metà della pagina nuova. Il ritorno con il
   tasto Indietro invece deve mantenere la posizione di lettura. */
export default function ScrollToTop() {
  const { pathname } = useLocation();
  const type = useNavigationType();

  useEffect(() => {
    if (type === "POP") return;
    window.scrollTo(0, 0);
  }, [pathname, type]);

  return null;
}
