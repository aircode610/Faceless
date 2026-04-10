import { Info } from "lucide-react";

interface Props {
  text: string;
  size?: number;
}

export default function InfoTip({ text, size = 14 }: Props) {
  return (
    <span className="relative inline-flex items-center group cursor-help ml-0.5">
      <Info
        className="text-[var(--color-muted)] opacity-40 group-hover:opacity-80 transition-opacity"
        style={{ width: size, height: size }}
      />
      <span
        className="absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 px-2.5 py-1.5
                   text-[11px] leading-snug rounded-lg shadow-lg border
                   whitespace-normal w-56 text-left z-50
                   opacity-0 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto
                   transition-opacity"
        style={{
          background: "var(--color-surface)",
          borderColor: "var(--color-border)",
          color: "var(--color-ink)",
        }}
      >
        {text}
      </span>
    </span>
  );
}
