export function LanguageSwitch({
  language,
  onChange,
}: {
  language: "en" | "hi";
  onChange: (language: "en" | "hi") => void;
}) {
  return (
    <div className="inline-flex rounded-full border border-white/15 bg-white/5 p-1" role="group" aria-label="Experience language">
      {(
        [
          ["en", "EN"],
          ["hi", "हिंदी"],
        ] as const
      ).map(([id, label]) => (
        <button
          key={id}
          type="button"
          className={`focus-ring rounded-full px-4 py-1.5 text-[15px] ${language === id ? "bg-fever text-white" : "text-soft"}`}
          aria-pressed={language === id}
          onClick={() => onChange(id)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
