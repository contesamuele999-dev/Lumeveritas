import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useLang } from "@/context/LangContext";
import { Loader2, Play, Pause, Volume2 } from "lucide-react";
import { toast } from "sonner";

export default function AudioButton({ briefingId = null, text = null, testid = "audio-btn" }) {
  const { lang } = useLang();
  const [state, setState] = useState("idle"); // idle | loading | playing | paused
  const audioRef = useRef(null);
  const urlRef = useRef(null);

  useEffect(() => () => {
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
  }, []);

  const load = async () => {
    setState("loading");
    try {
      const payload = briefingId ? { briefing_id: briefingId, language: lang } : { text, language: lang };
      const { data } = await api.post("/tts", payload);
      const bin = atob(data.audio_base64);
      const buf = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
      const blob = new Blob([buf], { type: data.mime || "audio/mpeg" });
      const url = URL.createObjectURL(blob);
      urlRef.current = url;
      const a = new Audio(url);
      audioRef.current = a;
      a.onended = () => setState("idle");
      a.onpause = () => { if (!a.ended) setState("paused"); };
      a.onplay = () => setState("playing");
      await a.play();
    } catch (e) {
      toast.error(e?.response?.data?.detail || (lang === "it" ? "Errore audio" : "Audio error"));
      setState("idle");
    }
  };

  const onClick = async () => {
    if (state === "idle") return load();
    if (state === "playing") { audioRef.current?.pause(); return; }
    if (state === "paused") { audioRef.current?.play(); return; }
  };

  return (
    <button
      data-testid={testid}
      onClick={onClick}
      disabled={state === "loading"}
      className="h-12 px-5 border border-border hover:border-foreground transition-colors font-mono-caps flex items-center gap-2"
      title={lang === "it" ? "Ascolta" : "Listen"}
    >
      {state === "loading" ? <Loader2 className="w-4 h-4 animate-spin" /> :
       state === "playing" ? <Pause className="w-4 h-4" /> :
       state === "paused"  ? <Play className="w-4 h-4" /> :
                             <Volume2 className="w-4 h-4" />}
      {lang === "it" ? "Ascolta" : "Listen"}
    </button>
  );
}
