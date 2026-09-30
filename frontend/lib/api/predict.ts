import { api } from "./client";
import type { PredictionResponse } from "@/lib/api-types";

export const predictApi = {
  predict: (file: File, topK = 3): Promise<PredictionResponse> => {
    const form = new FormData();
    form.append("image", file);
    return api.upload<PredictionResponse>(`/predict?top_k=${topK}`, form);
  },

  resetCache: () => api.post<void>("/predict/reset-cache"),
};
