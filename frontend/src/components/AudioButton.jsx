import { useEffect, useRef, useState } from "react";
import { useLang } from "@/context/LangContext";
import { Play, Pause, Volume2, Loader2 } from "lucide-react";
import { toast } from "sonner";

const synth = typeof window !== "undefined" ? window.speechSynthesis : null;

/* Le voci del browser si caricano in modo asincrono: al primo click getVoices() è quasi
   sempre vuoto e l'utterance parte con la voce sbagliata o non parte affatto. */
function loadVoices(timeout = 1500) {
  return new Promise((resolve) => {
    if (!synth) return resolve([]);
    const now = synth.getVoices();
    if (now.length) return resolve(now);
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      synth.onvoiceschanged = null;
      resolve(synth.getVoices() || []);
    };
    synth.onvoiceschanged = finish;
    setTimeout(finish, timeout);
  });
}

function pickVoice(voices, lang) {
  const want = lang === "it" ? "it" : "en";
  const inLang = voices.filter((v) => v.lang?.toLowerCase().replace("_", "-").startsWith(want));
  if (!inLang.length) return null;
  // le voci locali sono le più affidabili: quelle di rete si interrompono senza connessione
  return inLang.find((v) => v.localService) || inLang[0];
}

/* Chrome tronca gli utterance lunghi (~200-300 caratteri) senza emettere errori.
   Si spezza il testo su confini di frase e si accodano pezzi brevi. */
function chunkText(text, max = 200) {
  const parts = String(text)
    .replace(/\s+/g, " ")
    .trim()
    .split(/(?<=[.!?;:…])\s+/);
  const out = [];
  let buf = "";
  for (const p of parts) {
    if (!p) continue;
    if ((buf + " " + p).trim().length <= max) {
      buf = (buf + " " + p).trim();
      continue;
    }
    if (buf) out.push(buf);
    if (p.length <= max) {
      buf = p;
    } else {
      // frase singola più lunga del limite: si taglia sugli spazi
      const words = p.split(" ");
      let w = "";
      for (const word of words) {
        if ((w + " " + word).trim().length > max) { out.push(w.trim()); w = word; }
        else w = (w + " " + word).trim();
      }
      buf = w;
    }
  }
  if (buf) out.push(buf);
  return out.filter(Boolean);
}

export default function AudioButton({ item = null, text = null, testid = "audio-btn" }) {
  const { lang } = useLang();
  const [state, setState] = useState("idle"); // idle | loading | playing | paused
  const queue = useRef([]);
  const idx = useRef(0);
  const voiceRef = useRef(null);
  const keepAlive = useRef(null);
  const stopped = useRef(false);

  const cleanup = () => {
    stopped.current = true;
    if (keepAlive.current) { clearInterval(keepAlive.current); keepAlive.current = null; }
    try { synth?.cancel(); } catch (_) {}
  };

  useEffect(() => cleanup, []);

  // cambiare lingua a metà lettura darebbe una voce sbagliata sul resto del testo
  const firstRun = useRef(true);
  useEffect(() => {
    if (firstRun.current) { firstRun.current = false; return; }
    cleanup();
    setState("idle");
  }, [lang]);

  const speakFrom = (i) => {
    if (stopped.current || i >= queue.current.length) {
      if (!stopped.current) setState("idle");
      if (keepAlive.current) { clearInterval(keepAlive.current); keepAlive.current = null; }
      return;
    }
    idx.current = i;
    const u = new SpeechSynthesisUtterance(queue.current[i]);
    u.lang = lang === "it" ? "it-IT" : "en-US";
    if (voiceRef.current) u.voice = voiceRef.current;
    u.rate = 1;
    u.onend = () => speakFrom(i + 1);
    u.onerror = (e) => {
      // "interrupted"/"canceled" sono conseguenza di uno stop volontario, non un guasto
      if (stopped.current || ["interrupted", "canceled"].includes(e?.error)) return;
      console.warn("TTS error", e?.error);
      speakFrom(i + 1);
    };
    synth.speak(u);
  };

  const start = async () => {
    if (!synth || typeof SpeechSynthesisUtterance === "undefined") {
      toast.error(lang === "it"
        ? "La sintesi vocale non è disponibile su questo browser."
        : "Speech synthesis is not available in this browser.");
      return;
    }
    const content = text || [item?.headline, item?.summary, item?.real_reasons, item?.context]
      .filter(Boolean).join(". ");
    if (!content?.trim()) return;

    stopped.current = false;
    setState("loading");

    // iOS/Android richiedono che la prima speak() parta dentro il gesto dell'utente:
    // un utterance vuoto sblocca il motore prima dell'await sulle voci.
    try { synth.cancel(); synth.speak(new SpeechSynthesisUtterance("")); } catch (_) {}

    const voices = await loadVoices();
    if (stopped.current) return;
    voiceRef.current = pickVoice(voices, lang);
    if (voices.length && !voiceRef.current) {
      toast.message(lang === "it"
        ? "Nessuna voce italiana installata: uso la voce predefinita del dispositivo."
        : "No voice for this language installed: using the device default.");
    }

    queue.current = chunkText(content.slice(0, 8000));
    if (!queue.current.length) { setState("idle"); return; }

    try { synth.cancel(); } catch (_) {}
    setState("playing");
    speakFrom(0);

    // Chrome desktop mette in pausa da solo dopo ~15s: un resume periodico lo tiene sveglio
    if (keepAlive.current) clearInterval(keepAlive.current);
    keepAlive.current = setInterval(() => {
      if (stopped.current || !synth.speaking) return;
      if (!synth.paused) { synth.pause(); synth.resume(); }
    }, 10000);

    // se dopo 1,5s non è partito nulla, il motore è bloccato: meglio dirlo che restare muti
    setTimeout(() => {
      if (!stopped.current && !synth.speaking && !synth.pending) {
        cleanup();
        setState("idle");
        toast.error(lang === "it"
          ? "Il browser non è riuscito ad avviare la lettura. Prova a ricaricare la pagina o usa Chrome/Safari aggiornato."
          : "The browser could not start playback. Try reloading, or use an up-to-date Chrome/Safari.");
      }
    }, 1500);
  };

  const onClick = () => {
    if (state === "idle") return start();
    if (state === "loading") { cleanup(); setState("idle"); return; }
    if (state === "playing") { synth.pause(); setState("paused"); return; }
    if (state === "paused") { synth.resume(); setState("playing"); return; }
  };

  const label = state === "playing"
    ? (lang === "it" ? "Pausa" : "Pause")
    : state === "paused"
      ? (lang === "it" ? "Riprendi" : "Resume")
      : (lang === "it" ? "Ascolta" : "Listen");

  return (
    <button
      data-testid={testid}
      onClick={onClick}
      aria-label={label}
      className="h-10 md:h-12 px-3 md:px-5 border border-border hover:border-foreground transition-colors font-mono-caps flex items-center gap-2"
      title={label}
    >
      {state === "loading" ? <Loader2 className="w-4 h-4 animate-spin" /> :
       state === "playing" ? <Pause className="w-4 h-4" /> :
       state === "paused"  ? <Play className="w-4 h-4" /> :
                             <Volume2 className="w-4 h-4" />}
      {label}
    </button>
  );
}
