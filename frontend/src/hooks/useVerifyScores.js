import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/* Un'unica chiamata per tutta la lista.
   Prima ogni notizia chiedeva il proprio punteggio con una GET separata: sei richieste
   a ogni cambio di argomento, quasi tutte con esito 404 (la verifica parte solo se
   l'utente la richiede) e con il risultato che non veniva nemmeno mostrato. */
export default function useVerifyScores(items) {
  const [scores, setScores] = useState({});
  const ids = (items || []).map((i) => i.id).join(",");

  useEffect(() => {
    if (!ids) { setScores({}); return; }
    let cancel = false;
    api
      .post("/news/verify/scores", { ids: ids.split(",") })
      .then(({ data }) => { if (!cancel) setScores(data.scores || {}); })
      .catch(() => { if (!cancel) setScores({}); });
    return () => { cancel = true; };
  }, [ids]);

  return scores;
}
