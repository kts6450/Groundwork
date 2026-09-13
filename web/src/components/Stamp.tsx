"use client";

const COLORS = {
  합격: "#1c6b4a",
  주의: "#c4841d",
  위험: "#9b1d2a",
} as const;

export function Stamp({ grade }: { grade: keyof typeof COLORS }) {
  const color = COLORS[grade];
  return (
    <div className="relative grid place-items-center">
      <div
        className="ink-bleed absolute h-44 w-44 rounded-full"
        style={{ background: color }}
        aria-hidden
      />
      <svg
        className="stamp-hit relative h-32 w-32 drop-shadow-[0_8px_18px_rgba(0,0,0,0.28)] sm:h-40 sm:w-40"
        viewBox="0 0 200 200"
        role="img"
        aria-label={grade}
      >
        <defs>
          <filter id="rough">
            <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" result="n" />
            <feDisplacementMap in="SourceGraphic" in2="n" scale="1.6" />
          </filter>
        </defs>
        <circle
          cx="100"
          cy="100"
          r="88"
          fill="none"
          stroke={color}
          strokeWidth="7"
          filter="url(#rough)"
        />
        <circle cx="100" cy="100" r="74" fill="none" stroke={color} strokeWidth="2.2" />
        <text
          x="100"
          y="118"
          textAnchor="middle"
          fill={color}
          fontFamily="Song Myung, serif"
          fontSize="52"
          letterSpacing="6"
        >
          {grade}
        </text>
      </svg>
    </div>
  );
}
