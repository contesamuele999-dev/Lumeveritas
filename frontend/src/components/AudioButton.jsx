import { useEffect, useState } from "react";
import { useLang } from "@/context/LangContext";
import { Play, Pause, Volume2 } from "lucide-react";
import { toast } from "sonner";

const synth = typeof window !== "undefined" ? window.speechSynthesis : null;

// Voce di sistema: preferisce una voce nella lingua giusta, altrimenti la default.
function pickVoice(lang) {
  const want = lang === "it" ? "it" : "en";
  const voices = synth?.getVoices?.() || [];
  return voices.find((v) => v.lang?.toLowerCase().startsWith(want)) || null;
}

export default function AudioButton({ item = null, text = null, testid = "audio-btn" }) {
  const { lang } = useLang();
  const [state, setState] = useState("idle"); // idle | playing | paused

  useEffect(() => () => synth?.cancel(), []);

  const speak = (content) => {
    synth.cancel();
    const u = new SpeechSynthesisUtterance(content.slice(0, 6000));
    u.lang = lang === "it" ? "it-IT" : "en-US";
    const v = pickVoice(lang);
    if (v) u.voice = v;
    u.onend = () => setState("idle");
    u.onerror = () => setState("idle");
    setState("playing");
    synth.speak(u);
  };

  const start = () => {
    if (!synth) {
      toast.error(lang === "it" ? "Audio non supportato dal browser" : "Audio not supported");
      return;
    }
    const content = text || [item?.headline, item?.summary, item?.real_reasons, item?.context]
      .filter(Boolean).join(". ");
    if (!content) return;
    speak(content);
  };

  const onClick = () => {
    if (state === "idle") return start();
    if (state === "playing") { synth.pause(); setState("paused"); return; }
    if (state === "paused") { synth.resume(); setState("playing"); return; }
  };

  return (
    <button
      data-testid={testid}
      onClick={onClick}
      className="h-12 px-5 border border-border hover:border-foreground transition-colors font-mono-caps flex items-center gap-2"
      title={lang === "it" ? "Ascolta" : "Listen"}
    >
      {state === "playing" ? <Pause className="w-4 h-4" /> :
       state === "paused"  ? <Play className="w-4 h-4" /> :
                             <Volume2 className="w-4 h-4" />}
      {lang === "it" ? "Ascolta" : "Listen"}
    </button>
  );
}
