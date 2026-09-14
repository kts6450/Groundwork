"use client";

import type { AssetOk, ChangesOk, MonthPoint } from "@/lib/types";
import { useState } from "react";

/** 월별 개·폐업 막대. 라이브러리 없이 SVG로 그린다. */
function MonthlyBars({ rows }: { rows: MonthPoint[] }) {
  if (rows.length === 0) return null;
  const peak = Math.max(1, ...rows.map((r) => Math.max(r.opened, r.closed)));
  const step = 100 / rows.length;

  return (
    <figure className="mt-6">
      <svg viewBox="0 0 100 34" className="w-full" role="img" aria-label="월별 개업과 폐업">
        <line x1="0" y1="17" x2="100" y2="17" stroke="#12100c" strokeWidth="0.2" />
        {rows.map((row, i) => {
          const x = i * step;
          const w = Math.max(step * 0.34, 0.3);
          return (
            <g key={row.month}>
              <rect x={x} y={17 - (row.opened / peak) * 15} width={w} height={(row.opened / peak) * 15} fill="#1c6b4a" />
              <rect x={x + w * 1.2} y={17} width={w} height={(row.closed / peak) * 15} fill="#9b1d2a" />
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-2 flex gap-4 text-xs text-[#7a7266]">
        <span><span className="mr-1 inline-block h-2 w-2 bg-[#1c6b4a]" />개업</span>
        <span><span className="mr-1 inline-block h-2 w-2 bg-[#9b1d2a]" />폐업</span>
        <span className="ml-auto">
          {rows[0].month} ~ {rows[rows.length - 1].month} · 최대 {peak}곳
        </span>
      </figcaption>
    </figure>
  );
}

export function ChangesPanel({
  changes,
  onAsset,
  asset,
  assetLoading,
}: {
  changes: ChangesOk;
  onAsset: (kind: string) => void;
  asset: AssetOk | null;
  assetLoading: boolean;
}) {
  const [kind, setKind] = useState("seasonal_menu");
  const net = changes.net_change;

  return (
    <section className="paper fade-up mt-8 rounded-[2rem] p-6 sm:p-10">
      <p className="text-xs tracking-[0.28em] text-[#8a8072]">STEP 5 · 개업 이후</p>
      <h3 className="mt-2 font-display text-3xl sm:text-4xl">
        {changes.from} 이후 {changes.sgg}
      </h3>
      <p className="mt-4 max-w-xl text-sm leading-7 text-[#4f4a42]">{changes.message}</p>

      <dl className="mt-8 grid grid-cols-2 gap-6 sm:grid-cols-4">
        {[
          { label: "새로 연 곳", value: changes.same_category_opened, tone: "text-[#1c6b4a]" },
          { label: "문 닫은 곳", value: changes.same_category_closed, tone: "text-[#9b1d2a]" },
          { label: "순증", value: net, tone: net > 0 ? "text-[#9b1d2a]" : "text-[#1c6b4a]" },
          { label: "지금 영업 중", value: changes.open_count_now, tone: "" },
        ].map((cell) => (
          <div key={cell.label}>
            <dt className="text-xs tracking-widest text-[#8a8072]">{cell.label}</dt>
            <dd className={`mt-1 font-display text-4xl tabular-nums ${cell.tone}`}>
              {cell.value > 0 && cell.label === "순증" ? "+" : ""}
              {cell.value.toLocaleString("ko-KR")}
            </dd>
          </div>
        ))}
      </dl>

      <MonthlyBars rows={changes.monthly} />

      <div className="mt-10 border-t border-[#12100c]/10 pt-6">
        <p className="text-xs tracking-[0.28em] text-[#8a8072]">홍보물 만들기</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            className="border-b border-[#12100c]/20 bg-transparent py-2 text-sm outline-none focus:border-[#c4841d]"
          >
            <option value="seasonal_menu">시즌 메뉴 알림</option>
            <option value="sns_post">SNS 게시물</option>
            <option value="event_banner">이벤트 배너</option>
          </select>
          <button
            type="button"
            onClick={() => onAsset(kind)}
            disabled={assetLoading}
            className="rounded-full border border-[#12100c] px-5 py-2 text-sm transition hover:bg-[#12100c] hover:text-[#f3ead7] disabled:opacity-50"
          >
            {assetLoading ? "만드는 중…" : "만들기"}
          </button>
        </div>

        {asset ? (
          <div className="mt-6 grid gap-6 sm:grid-cols-[16rem_minmax(0,1fr)]">
            <div
              className="overflow-hidden rounded-xl border border-[#12100c]/10"
              /* SVG는 서버의 sanitize_svg를 통과한 것만 온다 */
              dangerouslySetInnerHTML={{ __html: asset.svg }}
            />
            <div>
              <p className="font-display text-2xl">{asset.title}</p>
              <p className="mt-2 text-sm leading-7 text-[#4f4a42]">{asset.body}</p>
              {asset.source === "mock" ? (
                <p className="mt-3 text-xs leading-6 text-[#7a7266]">규칙 기반으로 만든 예시다. {asset.note ?? ""}</p>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
