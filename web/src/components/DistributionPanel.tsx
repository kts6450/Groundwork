"use client";

import type { DistributionOk } from "@/lib/types";

/** 전국 평균 대비 배수. 1배를 가운데 둔 발산 막대로 그린다. */
export function DistributionPanel({ data }: { data: DistributionOk }) {
  const rows = data.rows.filter((r) => r.open_count >= 5).sort((a, b) => b.ratio - a.ratio);
  if (rows.length === 0) return null;
  const widest = Math.max(1, ...rows.map((r) => Math.abs(r.ratio - 1)));

  return (
    <section className="paper fade-up mt-8 rounded-[2rem] p-6 sm:p-10">
      <p className="text-xs tracking-[0.28em] text-[#8a8072]">업종 분포</p>
      <h3 className="mt-2 font-display text-3xl sm:text-4xl">
        {data.sgg}에 몰려 있는 업종
      </h3>
      <p className="mt-4 max-w-xl text-sm leading-7 text-[#4f4a42]">{data.summary}</p>

      <ul className="mt-8 space-y-2">
        {rows.map((row) => {
          const delta = row.ratio - 1;
          const width = (Math.abs(delta) / widest) * 42;
          return (
            <li key={row.category} className="grid grid-cols-[6.5rem_minmax(0,1fr)_5.5rem] items-center gap-3">
              <span className="truncate text-sm text-[#4f4a42]">{row.category}</span>
              <span className="relative block h-4">
                <span className="absolute inset-y-0 left-1/2 w-px bg-[#12100c]/25" />
                <span
                  className="absolute inset-y-0 rounded-sm"
                  style={{
                    left: delta >= 0 ? "50%" : `${50 - width}%`,
                    width: `${width}%`,
                    backgroundColor: delta >= 0 ? "#1c6b4a" : "#c98a3c",
                  }}
                />
              </span>
              <span className="text-right text-xs tabular-nums text-[#6e675c]">
                {row.ratio.toFixed(2)}배 · {row.open_count.toLocaleString("ko-KR")}곳
              </span>
            </li>
          );
        })}
      </ul>

      <p className="mt-6 text-xs leading-6 text-[#7a7266]">
        가운데 선이 전국 평균이다. 오른쪽은 이 지역에 더 몰려 있다는 뜻이고, 왼쪽은 덜하다는 뜻이다.
        점포 5곳 미만 업종은 뺐다. 총 {data.total.toLocaleString("ko-KR")}곳 기준.
      </p>
    </section>
  );
}
