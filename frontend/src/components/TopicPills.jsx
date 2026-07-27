import { useLang } from "@/context/LangContext";

export default function TopicPills({ topics, selected, onSelect, testidPrefix = "topic" }) {
  const { lang } = useLang();
  return (
    <div className="flex flex-wrap gap-2" data-testid="topic-pills">
      {topics.map((topic) => {
        const label = lang === "it" ? topic.label_it : topic.label_en;
        const active = selected === topic.key;
        return (
          <button
            key={topic.key}
            data-testid={`${testidPrefix}-${topic.key}`}
            onClick={() => onSelect(topic)}
            className={`px-4 h-11 border font-mono-caps transition-colors flex items-center gap-2 ${
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
  );
}
