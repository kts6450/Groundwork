"use client";

import type { NationRate } from "@/lib/types";

export function NationChart({ rows }: { rows: NationRate[] }) {
  const max = Math.max(...rows.map((row) => row.surv_3y), 0.01);
  return (
    <section className="mt-16">
      <p className="text-xs tracking-[0.28em] text-[#b8ad96]">NATION · 3YEAR SURVIVAL</p>
      <h2 className="mt-2 font-display text-3xl text-[#f3ead7]">전국, 업종마다 얼마나 남았나</h2>
      <p className="mt-2 max-w-xl text-sm leading-6 text-[#9a9183]">
        2015–2023년 개업 코호트의 3년 생존. 검증기는 이 숫자와 시군구 숫자를 빼서 합격·주의·위험을
        찍는다.
      </p>
      <ol className="mt-8 space-y-4">
        {rows.map((row, i) => (
          <li key={row.category} className="grid grid-cols-[7.5rem_1fr_4.5rem] items-center gap-4">
            <span className="text-sm text-[#e8dcc4]">{row.category}</span>
            <div className="h-3 overflow-hidden rounded-full bg-white/10">
              <div
                className="bar-fill h-full rounded-full bg-gradient-to-r from-[#c4841d] to-[#f3ead7]"
                style={{
                  width: `${(row.surv_3y / max) * 100}%`,
                  animationDelay: `${i * 60}ms`,
                }}
              />
            </div>
            <span className="text-right font-display text-lg tabular-nums text-[#f3ead7]">
              {(row.surv_3y * 100).toFixed(1)}%
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
