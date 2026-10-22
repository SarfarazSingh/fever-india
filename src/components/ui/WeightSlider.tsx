export function WeightSlider({
  label,
  value,
  min,
  max,
  step,
  display,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  display: string;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1 flex items-baseline justify-between gap-3 text-[15px]">
        <span>{label}</span>
        <span className="tabular text-gold">{display}</span>
      </span>
      <input
        className="focus-ring h-2 w-full cursor-pointer appearance-none rounded-full bg-white/10 accent-fever"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        aria-valuetext={display}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}
