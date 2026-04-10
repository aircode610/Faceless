import InfoTip from "./InfoTip";

interface Props {
  label: string;
  value: string | number;
  sub?: string;
  tip?: string;
}

export default function MetricCard({ label, value, sub, tip }: Props) {
  return (
    <div className="panel-surface text-center">
      <div className="text-[var(--color-muted)] text-sm mb-1">
        {label}
        {tip && <InfoTip text={tip} />}
      </div>
      <div className="text-3xl font-semibold" style={{ color: "var(--color-ink)" }}>
        {value}
      </div>
      {sub && <div className="text-xs mt-1" style={{ color: "var(--color-muted)" }}>{sub}</div>}
    </div>
  );
}
