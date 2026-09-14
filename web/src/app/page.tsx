"use client";

import { NationChart } from "@/components/NationChart";
import { ChangesPanel } from "@/components/ChangesPanel";
import { BrandPanel, ConceptPanel } from "@/components/PlanPanel";
import { ResultPanel } from "@/components/ResultPanel";
import { EXAMPLES } from "@/lib/examples";
import {
  isOk,
  type AssetOk,
  type Catalog,
  type ChangesOk,
  type PlanResult,
  type VerifyResult,
} from "@/lib/types";
import { FormEvent, useEffect, useMemo, useState } from "react";

export default function HomePage() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [catalogError, setCatalogError] = useState("");
  const [address, setAddress] = useState<string>(EXAMPLES[0].address);
  const [businessType, setBusinessType] = useState<string>(EXAMPLES[0].business_type);
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [plan, setPlan] = useState<PlanResult | null>(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [changes, setChanges] = useState<ChangesOk | null>(null);
  const [changesLoading, setChangesLoading] = useState(false);
  const [asset, setAsset] = useState<AssetOk | null>(null);
  const [assetLoading, setAssetLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [shake, setShake] = useState(0);

  useEffect(() => {
    if (!result) return;
    document.getElementById("verify-result")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [result]);

  useEffect(() => {
    fetch("/backend/catalog")
      .then((res) => {
        if (!res.ok) throw new Error("catalog");
        return res.json();
      })
      .then(setCatalog)
      .catch(() => setCatalogError("API가 꺼져 있다. 루트에서 uvicorn api.main:app --reload"));
  }, []);

  const grouped = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const row of catalog?.business_types ?? []) {
      const list = map.get(row.category) ?? [];
      list.push(row.business_type);
      map.set(row.category, list);
    }
    return [...map.entries()];
  }, [catalog]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setResult(null);
    setPlan(null);
    setProjectId(null);
    setChanges(null);
    setAsset(null);
    try {
      const res = await fetch("/backend/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address, business_type: businessType }),
      });
      const payload = (await res.json()) as VerifyResult;
      setResult(payload);
      setShake((n) => n + 1);
    } finally {
      setLoading(false);
    }
  }

  /** 저장한 뒤 그 프로젝트로 개업 이후 변화를 불러온다.
   *  computed_at을 2년 전으로 두어 "열고 나서 어떻게 변했나"를 바로 보여준다. */
  async function onTrack() {
    setChangesLoading(true);
    setAsset(null);
    try {
      const twoYearsAgo = new Date();
      twoYearsAgo.setFullYear(twoYearsAgo.getFullYear() - 2);
      const saved = await fetch("/backend/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "demo",
          address,
          business_type: businessType,
          computed_at: twoYearsAgo.toISOString().slice(0, 10),
        }),
      }).then((res) => res.json());

      setProjectId(saved.project_id);
      const res = await fetch("/backend/changes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: saved.project_id,
          as_of: new Date().toISOString().slice(0, 10),
        }),
      });
      const payload = (await res.json()) as ChangesOk;
      if (!("error" in payload)) setChanges(payload);
    } finally {
      setChangesLoading(false);
    }
  }

  async function onAsset(kind: string) {
    if (!projectId) return;
    setAssetLoading(true);
    try {
      const res = await fetch("/backend/assets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, asset: kind, context: "" }),
      });
      setAsset((await res.json()) as AssetOk);
    } finally {
      setAssetLoading(false);
    }
  }

  async function onPlan() {
    setPlanLoading(true);
    try {
      const res = await fetch("/backend/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address, business_type: businessType }),
      });
      setPlan((await res.json()) as PlanResult);
    } finally {
      setPlanLoading(false);
    }
  }

  return (
    <main className="relative z-10 mx-auto max-w-6xl px-5 pb-24 pt-10 sm:px-8 sm:pt-16">
      <header className="fade-up flex items-end justify-between gap-6">
        <div>
          <p className="text-xs tracking-[0.42em] text-[#c4841d]">SURVIVAL SEAL</p>
          <h1 className="mt-3 font-display text-6xl tracking-tight sm:text-8xl">남음</h1>
          <p className="mt-4 max-w-md text-base leading-7 text-[#b8ad96]">
            이 자리에서, 이 업종이, 얼마나 남았나.
            <br />
            매출 예측이 아니라 인허가 개·폐 이력의 3년 생존.
          </p>
        </div>
        <p className="hidden text-right text-xs leading-5 text-[#7a7266] sm:block">
          시군구 − 전국 ≥ +5%p 합격
          <br />
          ±5%p 주의 · ≤ −5%p 위험
        </p>
      </header>

      <section
        key={shake}
        className={`paper fade-up mt-12 rounded-[2rem] p-6 sm:p-10 ${shake ? "shake-paper" : ""}`}
        style={{ animationDelay: "80ms" }}
      >
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
          <form onSubmit={onSubmit} className="space-y-6">
            <label className="block">
              <span className="text-xs tracking-[0.28em] text-[#8a8072]">ADDRESS</span>
              <input
                required
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="서울특별시 종로구 대학로11길 22"
                className="mt-2 w-full border-b border-[#12100c]/20 bg-transparent py-3 text-lg outline-none placeholder:text-[#b5aa96] focus:border-[#c4841d]"
              />
            </label>
            <label className="block">
              <span className="text-xs tracking-[0.28em] text-[#8a8072]">LICENSE TYPE</span>
              <select
                required
                value={businessType}
                onChange={(e) => setBusinessType(e.target.value)}
                className="mt-2 w-full border-b border-[#12100c]/20 bg-transparent py-3 text-lg outline-none focus:border-[#c4841d]"
              >
                {grouped.length === 0 ? (
                  <option value={businessType}>{businessType}</option>
                ) : (
                  grouped.map(([category, types]) => (
                    <optgroup key={category} label={category}>
                      {types.map((name) => (
                        <option key={name} value={name}>
                          {name}
                        </option>
                      ))}
                    </optgroup>
                  ))
                )}
              </select>
            </label>
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => {
                const on = address === ex.address && businessType === ex.business_type;
                return (
                  <button
                    key={ex.label}
                    type="button"
                    onClick={() => {
                      setAddress(ex.address);
                      setBusinessType(ex.business_type);
                    }}
                    className={`rounded-full border px-3 py-1.5 text-xs tracking-wide transition hover:-translate-y-0.5 ${
                      on
                        ? "border-[#12100c] bg-[#12100c] text-[#f3ead7]"
                        : "border-[#12100c]/15 text-[#4f4a42] hover:border-[#c4841d] hover:text-[#12100c]"
                    }`}
                    title={ex.hint}
                  >
                    {ex.label}
                  </button>
                );
              })}
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-full bg-[#12100c] py-4 font-display text-xl text-[#f3ead7] transition hover:bg-[#1c6b4a] disabled:opacity-50"
            >
              {loading ? "찍는 중…" : "도장 찍기"}
            </button>
            {catalogError ? <p className="text-sm text-[#9b1d2a]">{catalogError}</p> : null}
          </form>
          <ResultPanel result={result} loading={loading} />
        </div>
      </section>

      {result && isOk(result) && !plan ? (
        <div className="mt-8 text-center">
          <button
            type="button"
            onClick={onPlan}
            disabled={planLoading}
            className="rounded-full border border-[#12100c] px-8 py-3 font-display text-lg transition hover:bg-[#12100c] hover:text-[#f3ead7] disabled:opacity-50"
          >
            {planLoading ? "기획안 만드는 중…" : "이 자리로 기획안 만들기"}
          </button>
          <p className="mt-3 text-xs text-[#7a7266]">컨셉·메뉴·가격대와 이름·로고 초안을 만든다.</p>
        </div>
      ) : null}

      {plan ? (
        <>
          <ConceptPanel concept={plan.concept} />
          <BrandPanel brand={plan.brand} />
        </>
      ) : null}

      {plan && !changes ? (
        <div className="mt-8 text-center">
          <button
            type="button"
            onClick={onTrack}
            disabled={changesLoading}
            className="rounded-full border border-[#12100c] px-8 py-3 font-display text-lg transition hover:bg-[#12100c] hover:text-[#f3ead7] disabled:opacity-50"
          >
            {changesLoading ? "불러오는 중…" : "2년 전에 열었다면, 그 뒤 상권 변화"}
          </button>
          <p className="mt-3 text-xs text-[#7a7266]">기획안을 저장하고 같은 업종이 몇 곳 열고 닫았는지 본다.</p>
        </div>
      ) : null}

      {changes ? (
        <ChangesPanel changes={changes} onAsset={onAsset} asset={asset} assetLoading={assetLoading} />
      ) : null}

      {catalog ? <NationChart rows={catalog.nation} /> : null}

      <footer className="mt-20 text-xs leading-6 text-[#6e675c]">
        인허가 2015.01–2023.06 개업, 기준일 2026.09.09. n&lt;10 칸은 시도·전국으로 내려간다.
        통닭(치킨) 업태가 2016년경 폐지돼 치킨은 호프와 한 묶음이다. 매출이 아니라 개·폐 이력만 본다.
      </footer>
    </main>
  );
}
