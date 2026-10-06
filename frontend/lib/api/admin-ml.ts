import { api } from "./client";
import type {
  ListAnomaliesParams,
  ListDemandForecastParams,
  MLSummary,
  PaginatedAnomalies,
  PaginatedDemandForecast,
} from "@/lib/api-types";

export const adminMlApi = {
  /** Aggregated ML model health + review outcome KPIs */
  summary: () => api.get<MLSummary>("/admin/ml/summary"),

  /** Per-product demand forecast (exponential smoothing) */
  demandForecast: (params: ListDemandForecastParams = {}) => {
    const qs = new URLSearchParams();
    qs.set("page", String(params.page ?? 1));
    qs.set("size", String(params.size ?? 20));
    if (params.lookback_days) {
      qs.set("lookback_days", String(params.lookback_days));
    }
    if (params.only_low_stock) qs.set("only_low_stock", "true");
    return api.get<PaginatedDemandForecast>(
      `/admin/ml/demand-forecast?${qs.toString()}`,
    );
  },

  /** Detected sales anomalies (rolling z-score) */
  anomalies: (params: ListAnomaliesParams = {}) => {
    const qs = new URLSearchParams();
    qs.set("page", String(params.page ?? 1));
    qs.set("size", String(params.size ?? 20));
    if (params.lookback_days) {
      qs.set("lookback_days", String(params.lookback_days));
    }
    if (params.z_threshold) {
      qs.set("z_threshold", String(params.z_threshold));
    }
    return api.get<PaginatedAnomalies>(
      `/admin/ml/anomalies?${qs.toString()}`,
    );
  },
};
