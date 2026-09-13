"use client";

import { hasPlan, type BrandOk, type ConceptOk, type VerifyErr } from "@/lib/types";

function Section({ title, step, children }: { title: string; step: string; children: React.ReactNode }) {
  return (
    <section className="paper fade-up mt-8 rounded-[2rem] p-6 sm:p-10">
      <p className="text-xs tracking-[0.28em] text-[#8a8072]">{step}</p>
      <h3 className="mt-2 font-display text-3xl sm:text-4xl">{title}</h3>
      <div className="mt-6">{children}</div>
    </section>
  );
}

function MockBadge({ source, note }: { source: string; note?: string }) {
  if (source !== "mock") return null;
  return (
    <p className="mt-6 border-l-2 border-[#c4841d]/50 pl-4 text-xs leading-6 text-[#7a7266]">
      규칙 기반으로 만든 예시다. {note ?? ""}
    </p>
  );
}

export function ConceptPanel({ concept }: { concept: ConceptOk | VerifyErr }) {
  if (!hasPlan(concept)) return null;
  const { one_liner, target, differentiator, tone } = concept.concept;

  return (
    <Section step="STEP 2 · 컨셉과 메뉴" title={one_liner}>
      <dl className="grid gap-6 sm:grid-cols-2">
        <div>
          <dt className="text-xs tracking-widest text-[#8a8072]">주 손님층</dt>
          <dd className="mt-1 text-sm leading-7 text-[#4f4a42]">{target}</dd>
        </div>
        <div>
          <dt className="text-xs tracking-widest text-[#8a8072]">전략</dt>
          <dd className="mt-1 text-sm leading-7 text-[#4f4a42]">{differentiator}</dd>
        </div>
      </dl>

      <div className="mt-6 flex flex-wrap gap-2">
        {tone.map((word) => (
          <span key={word} className="rounded-full border border-[#12100c]/15 px-3 py-1 text-xs text-[#4f4a42]">
            {word}
          </span>
        ))}
      </div>

      <ul className="mt-8 divide-y divide-[#12100c]/10 border-y border-[#12100c]/10">
        {concept.menu.map((item) => (
          <li key={item.name} className="flex items-baseline justify-between gap-4 py-3">
            <span className="text-sm">
              {item.name}
              {item.role === "signature" ? (
                <span className="ml-2 text-xs tracking-widest text-[#c4841d]">대표</span>
              ) : null}
            </span>
            <span className="font-display text-lg tabular-nums">{item.price_krw.toLocaleString("ko-KR")}원</span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-[#7a7266]">
        가격대 {concept.price_band.low_krw.toLocaleString("ko-KR")}~
        {concept.price_band.high_krw.toLocaleString("ko-KR")}원 · 평균{" "}
        {concept.price_band.average_krw.toLocaleString("ko-KR")}원
      </p>

      <div className="mt-8">
        <p className="text-xs tracking-widest text-[#8a8072]">근거</p>
        <ul className="mt-2 space-y-1">
          {concept.grounds.map((line) => (
            <li key={line} className="text-xs leading-6 text-[#6e675c]">
              {line}
            </li>
          ))}
        </ul>
      </div>

      <MockBadge source={concept.source} note={concept.note} />
    </Section>
  );
}

export function BrandPanel({ brand }: { brand: BrandOk | VerifyErr }) {
  if (!hasPlan(brand)) return null;

  return (
    <Section step="STEP 3 · 이름과 로고" title="브랜딩 초안">
      <div className="grid gap-8 sm:grid-cols-[10rem_minmax(0,1fr)]">
        <div>
          <div
            className="aspect-square w-40 max-w-full overflow-hidden rounded-2xl border border-[#12100c]/10"
            /* SVG는 서버의 sanitize_svg를 통과한 것만 온다 (src/branding/svg.py) */
            dangerouslySetInnerHTML={{ __html: brand.logo_svg }}
          />
          <div className="mt-3 flex gap-2">
            {Object.entries(brand.palette).map(([key, color]) => (
              <span
                key={key}
                title={`${key} ${color}`}
                className="h-6 w-6 rounded-full border border-[#12100c]/15"
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
        </div>

        <ul className="space-y-4">
          {brand.names.map((item) => (
            <li key={item.name}>
              <p className="font-display text-2xl">{item.name}</p>
              <p className="mt-1 text-sm leading-6 text-[#4f4a42]">{item.reason}</p>
              <p className="mt-1 text-xs leading-5 text-[#8a8072]">{item.risk}</p>
            </li>
          ))}
        </ul>
      </div>

      <MockBadge source={brand.source} note={brand.note} />
    </Section>
  );
}
