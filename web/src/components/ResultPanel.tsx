"use client";

import { CountUp } from "@/components/CountUp";
import { Stamp } from "@/components/Stamp";
import { isOk, type VerifyResult } from "@/lib/types";

export function ResultPanel({
  result,
  loading,
}: {
  result: VerifyResult | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="grid min-h-[28rem] place-items-center">
        <div className="text-center">
          <div className="loading-blot mx-auto h-16 w-16 rounded-full bg-[#9b1d2a]/70" />
          <p className="mt-5 font-display text-2xl">도장을 찍는 중</p>
          <p className="mt-1 text-sm text-[#7a7266]">시군구 표에서 같은 업종을 찾는다</p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="grid min-h-[28rem] place-items-center text-center">
        <div>
          <p className="font-display text-4xl leading-tight">아직 찍히지 않았다</p>
          <p className="mt-3 max-w-xs text-sm leading-6 text-[#7a7266]">
            왼쪽 주소와 업태를 넣으면, 그 칸의 3년 생존이 전국보다 높은지 도장으로 답한다.
          </p>
        </div>
      </div>
    );
  }

  if (!isOk(result)) {
    return (
      <div className="grid min-h-[28rem] place-items-center text-center">
        <div>
          <p className="font-display text-4xl text-[#9b1d2a]">검증 불가</p>
          <p className="mt-4 max-w-sm text-sm leading-6 text-[#5c564c]">
            {result.reason ?? "이 조건으로는 생존률을 계산하지 못했다."}
          </p>
        </div>
      </div>
    );
  }

  const local = result.surv_3y * 100;
  const nation = result.nation_3y * 100;
  const diff = result.diff_3y * 100;
  const sign = diff >= 0 ? "+" : "";

  return (
    <div id="verify-result" className="relative min-h-0 scroll-mt-8 sm:min-h-[28rem]">
      <div className="mb-6 flex justify-center sm:mb-0 sm:absolute sm:right-4 sm:top-2 sm:z-10">
        <Stamp grade={result.grade} />
      </div>
      <p className="text-xs tracking-[0.22em] text-[#8a8072]">
        {result.level} · 표본 {result.n.toLocaleString("ko-KR")}곳
      </p>
      <h3 className="mt-3 font-display text-4xl leading-[1.15] sm:pr-44 sm:text-5xl">
        <span className="block">{result.sido}</span>
        <span className="block">{result.sgg}</span>
      </h3>
      <p className="mt-2 text-sm text-[#6e675c]">
        {result.business_type} → {result.category}
      </p>
      <dl className="mt-10 grid grid-cols-2 gap-6 pr-4 sm:pr-40">
        <div>
          <dt className="text-xs tracking-widest text-[#8a8072]">이 자리 3년</dt>
          <dd className="mt-1 font-display text-5xl tabular-nums">
            <CountUp value={local} suffix="%" />
          </dd>
        </div>
        <div>
          <dt className="text-xs tracking-widest text-[#8a8072]">전국 {result.category}</dt>
          <dd className="mt-1 font-display text-5xl tabular-nums text-[#7a7266]">
            <CountUp value={nation} suffix="%" />
          </dd>
        </div>
      </dl>
      <p className="mt-6 font-display text-2xl">
        전국 대비 {sign}
        <CountUp value={diff} suffix="%p" />
      </p>
      <p className="mt-5 max-w-md text-sm leading-7 text-[#4f4a42]">{result.reason}</p>
      {result.evidence ? (
        <p className="mt-4 max-w-md border-l-2 border-[#c4841d]/50 pl-4 text-sm leading-7 text-[#6e675c]">
          {result.evidence}
        </p>
      ) : null}
    </div>
  );
}
