import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useLang } from "@/context/LangContext";
import { Loader2, ShieldCheck, AlertTriangle, CheckCircle2, XCircle, Info } from "lucide-react";
import ClickableText from "@/components/ClickableText";

const CRITERIA_LABELS = {
  it: {
    factuality: "Fattualità",
    source_traceability: "Tracciabilità delle fonti",
    data_specificity: "Specificità dei dati",
    independence: "Indipendenza",
    recency: "Attualità",
    bias_transparency: "Trasparenza",
    controversy_check: "Controversia",
  },
  en: {
    factuality: "Factuality",
    source_traceability: "Source traceability",
    data_specificity: "Data specificity",
    independence: "Independence",
    recency: "Recency",
    bias_transparency: "Transparency",
    controversy_check: "Controversy check",
  },
};

function scoreClass(score) {
  if (score >= 80) return "bg-emerald-600 text-white";
  if (score >= 60) return "bg-yellow-500 text-black";
  if (score >= 40) return "bg-orange-500 text-white";
  return "bg-accent text-accent-foreground";
}

function ringClass(score) {
  if (score >= 80) return "border-emerald-600";
  if (score >= 60) return "border-yellow-500";
  if (score >= 40) return "border-orange-500";
  return "border-accent";
}

export default function VerifyPanel({ briefingId }) {
  const { lang } = useLang();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [criteria, setCriteria] = useState(null);

  const load = async (refresh = false) => {
    if (refresh) setRefreshing(true); else setLoading(true);
    try {
      const { data: d } = refresh
        ? await api.post(`/news/${briefingId}/verify?refresh=true`)
        : await (async () => {
            try {
              return await api.get(`/news/${briefingId}/verify`);
            } catch (e) {
              return await api.post(`/news/${briefingId}/verify`);
            }
          })();
      setData(d);
    } catch (e) {
      // keep last
    } finally { setLoading(false); setRefreshing(false); }
  };

  useEffect(() => { load(false); /* eslint-disable-next-line */ }, [briefingId]);
  useEffect(() => {
    api.get(`/verify/criteria?language=${lang}`).then(({ data: d }) => setCriteria(d.criteria)).catch(() => {});
  }, [lang]);

  if (loading) {
    return (
      <div className="py-8 flex items-center gap-3 text-muted-foreground" data-testid="verify-loading">
        <Loader2 className="w-5 h-5 animate-spin" />
        {lang === "it" ? "Sto incrociando dati e fonti…" : "Cross-checking data & sources…"}
      </div>
    );
  }

  if (!data) return null;
  const labels = CRITERIA_LABELS[lang] || CRITERIA_LABELS.it;

  return (
    <div className="space-y-8" data-testid="verify-panel">
      {/* Overall score */}
      <div className="flex flex-col md:flex-row md:items-center gap-6 border border-foreground p-6">
        <div className={`w-24 h-24 rounded-full border-4 ${ringClass(data.overall_score)} flex items-center justify-center shrink-0`}>
          <div className="text-3xl font-serif-display tabular font-semibold">{data.overall_score}</div>
        </div>
        <div className="flex-1">
          <div className="font-mono-caps text-accent flex items-center gap-2 mb-2">
            <ShieldCheck className="w-4 h-4" />
            {lang === "it" ? "PUNTEGGIO DI VERIDICITÀ" : "TRUTHFULNESS SCORE"}
          </div>
          <div className="font-serif-display text-2xl md:text-3xl leading-tight" data-testid="verify-verdict">{data.verdict}</div>
          <div className="text-xs text-muted-foreground mt-2">
            {lang === "it" ? "Su una scala 0–100. Vedi criteri qui sotto." : "0–100 scale. See criteria below."}
          </div>
        </div>
        <button
          data-testid="verify-refresh-btn"
          onClick={() => load(true)}
          disabled={refreshing}
          className="h-11 px-4 border border-border hover:border-foreground font-mono-caps text-xs flex items-center gap-2"
        >
          {refreshing && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          {lang === "it" ? "Rianalizza" : "Re-analyze"}
        </button>
      </div>

      {/* Criteria bars */}
      <section>
        <div className="font-mono-caps text-accent mb-4">
          {lang === "it" ? "CRITERI DI VALUTAZIONE" : "EVALUATION CRITERIA"}
        </div>
        <div className="space-y-4">
          {data.criteria.map((c) => (
            <div key={c.key} data-testid={`verify-criterion-${c.key}`}>
              <div className="flex items-baseline justify-between mb-1">
                <div className="font-serif-display text-lg" title={criteria?.find(x => x.key === c.key)?.description}>
                  {labels[c.key] || c.key}
                </div>
                <div className={`font-mono-caps text-xs px-2 py-0.5 tabular ${scoreClass(c.score)}`}>{c.score}</div>
              </div>
              <div className="w-full h-1.5 bg-secondary relative overflow-hidden">
                <div className={`absolute inset-y-0 left-0 ${scoreClass(c.score).split(" ")[0]}`} style={{ width: `${c.score}%` }} />
              </div>
              {c.rationale && <div className="text-sm text-foreground/75 mt-1.5 leading-relaxed"><ClickableText text={c.rationale} /></div>}
            </div>
          ))}
        </div>
      </section>

      {/* Flagged claims */}
      {data.flagged_claims?.length > 0 && (
        <section>
          <div className="flex items-center gap-2 font-mono-caps text-accent mb-3">
            <AlertTriangle className="w-4 h-4" /> {lang === "it" ? "AFFERMAZIONI DA VERIFICARE" : "CLAIMS TO VERIFY"}
          </div>
          <ul className="space-y-2 col-rule">
            {data.flagged_claims.map((c, i) => (
              <li key={i} className="pt-2 text-sm md:text-base flex gap-3">
                <span className="font-mono-caps text-accent shrink-0 mt-1">!</span>
                <span><ClickableText text={c} /></span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Sources */}
      <section className="grid md:grid-cols-2 gap-6">
        {data.corroborating_sources?.length > 0 && (
          <div>
            <div className="flex items-center gap-2 font-mono-caps text-emerald-700 mb-3">
              <CheckCircle2 className="w-4 h-4" /> {lang === "it" ? "FONTI CHE CONFERMANO" : "CORROBORATING SOURCES"}
            </div>
            <ul className="space-y-2 text-sm">
              {data.corroborating_sources.map((s, i) => (
                <li key={i} className="flex gap-2"><span className="text-emerald-600">→</span><span>{s}</span></li>
              ))}
            </ul>
          </div>
        )}
        {data.contradicting_sources?.length > 0 && (
          <div>
            <div className="flex items-center gap-2 font-mono-caps text-accent mb-3">
              <XCircle className="w-4 h-4" /> {lang === "it" ? "FONTI CHE CONTRADDICONO" : "CONTRADICTING SOURCES"}
            </div>
            <ul className="space-y-2 text-sm">
              {data.contradicting_sources.map((s, i) => (
                <li key={i} className="flex gap-2"><span className="text-accent">→</span><span>{s}</span></li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Method notes */}
      {data.method_notes && (
        <section className="border-t border-border pt-6">
          <div className="flex items-center gap-2 font-mono-caps text-muted-foreground mb-2">
            <Info className="w-3.5 h-3.5" /> {lang === "it" ? "METODO & LIMITI" : "METHOD & LIMITS"}
          </div>
          <div className="text-sm text-foreground/80 leading-relaxed"><ClickableText text={data.method_notes} /></div>
        </section>
      )}
    </div>
  );
}

export function VerifyBadge({ score, testid = "verify-badge" }) {
  return (
    <span data-testid={testid} className={`inline-flex items-center gap-1 px-2 py-0.5 font-mono-caps text-[10px] tabular ${scoreClass(score)}`}>
      <ShieldCheck className="w-3 h-3" /> {score}
    </span>
  );
}
