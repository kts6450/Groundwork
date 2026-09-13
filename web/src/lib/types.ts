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
