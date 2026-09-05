/** Model A v1.0 — a transparent household prioritisation index, not a probability. */
export const FIELDS = ["affected", "severe", "needs", "served", "vulnerable"];
export const PRESETS = {
  balanced: [1, 1, 1], gap: [1, 2, 1], damage: [2, 1, 1], vulnerability: [1, 1, 2]
};
export const LABELS = {
  affected: "홍수의 영향을 받은 가구", severe: "집에 거주할 수 없는 가구", needs: "식수·위생 지원이 필요한 가구",
  served: "정해진 지원을 받은 가구", vulnerable: "지원 필요 가구 중 취약가구"
};
export function normaliseWeights(weights) {
  if (!Array.isArray(weights) || weights.length !== 3 || weights.some(v => typeof v !== "number" || !Number.isFinite(v) || v < 0) || weights.reduce((a,b) => a+b,0) <= 0) {
    throw new Error("가중치는 0 이상의 숫자이며 합계가 0보다 커야 합니다.");
  }
  const total = weights.reduce((a,b) => a+b,0);
  if (!Number.isFinite(total)) throw new Error("가중치 합계가 유효한 숫자 범위를 벗어났습니다.");
  return weights.map(v => v / total);
}
export function assess(inputs = {}, weights = PRESETS.balanced) {
  const w = normaliseWeights(weights), errors = [], missing = [];
  const values = {};
  for (const field of FIELDS) {
    const v = inputs[field];
    if (v === null || v === undefined || v === "") { missing.push(field); continue; }
    if (typeof v !== "number" || !Number.isSafeInteger(v) || v < 0) {
      errors.push(`${LABELS[field]}: 0 이상의 정수를 입력하세요.`); continue;
    }
    values[field] = v;
  }
  for (const [child,parent] of [["severe","affected"],["needs","affected"],["served","needs"],["vulnerable","needs"]]) {
    if (values[child] !== undefined && values[parent] !== undefined && values[child] > values[parent]) {
      errors.push(`${LABELS[child]}가 ${LABELS[parent]}보다 클 수 없습니다. 같은 평가구역·가구집단인지 확인하세요.`);
    }
  }
  const base = {score:null, components:null, unmet:null, errors, missing, weights:w};
  if (errors.length) return {...base,status:"invalid"};
  if (missing.length) return {...base,status:"missing"};
  const {affected,severe,needs,served,vulnerable} = values;
  if (needs === 0) return {...base,status:"no_need",unmet:0};
  const unmet = needs - served;
  if (unmet === 0) return {...base,status:"covered",unmet:0};
  const components = [severe / affected, unmet / needs, vulnerable / needs];
  const score = 100 * components.reduce((sum,v,i) => sum + v*w[i],0);
  return {...base,status:"ready",score,components,unmet};
}
export function evaluateRegions(regions, weights = PRESETS.balanced, {mode="public"} = {}) {
  const ids = new Set();
  const results = regions.map(row => {
    if (!row.id || ids.has(row.id)) throw new Error("지역 식별자는 비어 있거나 중복될 수 없습니다.");
    ids.add(row.id);
    const result = assess(row.inputs,weights);
    // Public results additionally need a reviewed, common cohort/time and per-field provenance.
    if (mode !== "scenario" && ["ready","covered","no_need"].includes(result.status)) {
      const review = row.review;
      const date = /^\d{4}-\d{2}-\d{2}$/.test(review?.asOf || "") ? new Date(review.asOf + 'T00:00:00Z') : null;
      const validDate = date && Number.isFinite(date.getTime()) && date.toISOString().slice(0,10) === review.asOf;
      if (review?.approved !== true || typeof review.cohort !== "string" || !review.cohort.trim() || !validDate || !FIELDS.every(f => typeof row.inputSources?.[f] === "string" && row.inputSources[f].trim())) {
        return {...result,id:row.id,name:row.name,status:"review_needed",score:null,rank:null};
      }
    }
    return {...result,id:row.id,name:row.name,rank:null};
  });
  // Never compare public assessments with different dates or cohort definitions.
  if (mode !== "scenario") {
    const eligible = regions.filter((r,i) => results[i].status === "ready");
    const cohorts = new Set(eligible.map(r => `${r.review.asOf}|${r.review.cohort}`));
    if (cohorts.size > 1) return results.map(r => r.status === "ready" ? {...r,status:"incomparable",score:null,rank:null} : r);
  }
  const ranked = results.filter(r => r.status === "ready").sort((a,b) => b.score-a.score || a.id.localeCompare(b.id));
  ranked.forEach((r,i) => { r.rank = i > 0 && Math.abs(r.score-ranked[i-1].score) < 1e-9 ? ranked[i-1].rank : i+1; });
  return results;
}
export function sensitivity(regions, options = {}) {
  const runs = Object.values(PRESETS).map(w => evaluateRegions(regions,w,options));
  return regions.map(row => {
    const values = runs.map(run => run.find(r => r.id === row.id)).filter(r => r.rank !== null);
    return {id:row.id,best:values.length ? Math.min(...values.map(v=>v.rank)) : null,worst:values.length ? Math.max(...values.map(v=>v.rank)) : null};
  });
}
