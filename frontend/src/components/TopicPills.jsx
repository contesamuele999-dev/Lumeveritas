import { useLang } from "@/context/LangContext";

// Ogni topic porta con sé l'etichetta della sua sezione (section_it/section_en dal backend);
// i topic personalizzati finiscono in una sezione propria.
function groupBySection(topics, lang) {
  const groups = [];
  const byLabel = new Map();
  for (const topic of topics) {
    const label = topic.custom
      ? (lang === "it" ? "I miei argomenti" : "My topics")
      : (lang === "it" ? topic.section_it : topic.section_en) || (lang === "it" ? "Altro" : "Other");
    if (!byLabel.has(label)) {
      byLabel.set(label, { label, items: [] });
      groups.push(byLabel.get(label));
    }
    byLabel.get(label).items.push(topic);
  }
  return groups;
}

export default function TopicPills({ topics, selected, onSelect, testidPrefix = "topic" }) {
  const { lang } = useLang();
  const groups = groupBySection(topics, lang);

  return (
    <div className="space-y-3 md:space-y-4" data-testid="topic-pills">
      {groups.map((g) => (
        <div key={g.label}>
          <div className="font-mono-caps text-muted-foreground text-[10px] mb-1.5">{g.label}</div>
          <div className="flex flex-wrap gap-1.5 md:gap-2">
            {g.items.map((topic) => {
              const label = lang === "it" ? topic.label_it : topic.label_en;
              const active = selected === topic.key;
              return (
                <button
                  key={topic.key}
                  data-testid={`${testidPrefix}-${topic.key}`}
                  onClick={() => onSelect(topic)}
                  className={`px-2.5 md:px-4 h-9 md:h-11 border font-mono-caps transition-colors flex items-center gap-2 ${
                    active
                      ? "bg-foreground text-background border-foreground"
                      : "bg-transparent border-border hover:border-foreground hover:bg-secondary"
                  } ${topic.custom ? "border-dashed" : ""}`}
                >
                  {topic.custom && <span className="w-1.5 h-1.5 rounded-full bg-accent inline-block" />}
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
