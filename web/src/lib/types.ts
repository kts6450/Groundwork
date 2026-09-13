export type BusinessChoice = {
  business_type: string;
  category: string;
};

export type NationRate = {
  category: string;
  n: number;
  surv_1y: number;
  surv_3y: number;
};

export type Catalog = {
  business_types: BusinessChoice[];
  nation: NationRate[];
};

export type VerifyOk = {
  sido: string;
  sgg: string;
  business_type: string;
  category: string;
  level: string;
  n: number;
  surv_1y: number;
  surv_3y: number;
  nation_3y: number;
  diff_3y: number;
  grade: "합격" | "주의" | "위험";
  reason: string;
  evidence?: string;
};

export type VerifyErr = {
  error: string;
  business_type?: string;
  category?: string;
  reason?: string;
};

export type VerifyResult = VerifyOk | VerifyErr;

export function isOk(result: VerifyResult): result is VerifyOk {
  return !("error" in result);
}

export type MenuItem = {
  name: string;
  price_krw: number;
  role: "signature" | "core" | "side";
};

export type ConceptOk = {
  source: "llm" | "mock";
  concept: {
    one_liner: string;
    target: string;
    differentiator: string;
    tone: string[];
  };
  menu: MenuItem[];
  price_band: { low_krw: number; high_krw: number; average_krw: number };
  grounds: string[];
  note?: string;
};

export type BrandName = { name: string; reason: string; risk: string };

export type BrandOk = {
  source: "llm" | "mock";
  names: BrandName[];
  palette: { primary: string; secondary: string; background: string };
  logo_svg: string;
  note?: string;
};

export type PlanResult = {
  verdict: VerifyResult;
  concept: ConceptOk | VerifyErr;
  brand: BrandOk | VerifyErr;
};

export function hasPlan(value: ConceptOk | BrandOk | VerifyErr): value is ConceptOk & BrandOk {
  return !("error" in value);
}
