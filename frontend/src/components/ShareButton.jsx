import { useState } from "react";
import { Share2, Check } from "lucide-react";
import { toast } from "sonner";
import { useLang } from "@/context/LangContext";

export default function ShareButton({ briefingId, testid = "share-btn" }) {
  const { lang } = useLang();
  const [copied, setCopied] = useState(false);

  const onClick = async () => {
    const url = `${window.location.origin}/s/${briefingId}`;
    try {
      if (navigator.share) {
        await navigator.share({ title: "Lume Veritas", url });
      } else {
        await navigator.clipboard.writeText(url);
      }
      setCopied(true);
      toast.success(lang === "it" ? "Link copiato" : "Link copied");
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      // ignore user-cancel
    }
  };

  return (
    <button
      data-testid={testid}
      onClick={onClick}
      className="h-12 px-5 border border-border hover:border-foreground transition-colors font-mono-caps flex items-center gap-2"
      title={lang === "it" ? "Condividi" : "Share"}
    >
      {copied ? <Check className="w-4 h-4" /> : <Share2 className="w-4 h-4" />}
      {lang === "it" ? "Condividi" : "Share"}
    </button>
  );
}
