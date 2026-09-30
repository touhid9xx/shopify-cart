import { api } from "./client";
import type {
  Page,
  Product,
  ProductWithStock,
} from "@/lib/api-types";

export interface ListProductsParams {
  page?: number;
  size?: number;
  category_id?: number;
  q?: string;
  active_only?: boolean;
}

export const productsApi = {
  list: (params: ListProductsParams = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set("page", String(params.page));
    if (params.size) qs.set("size", String(params.size));
    if (params.category_id) qs.set("category_id", String(params.category_id));
    if (params.q) qs.set("q", params.q);
    if (params.active_only !== undefined)
      qs.set("active_only", String(params.active_only));
    return api.get<Page<Product>>(`/products?${qs}`);
  },

  get: (id: number) => api.get<ProductWithStock>(`/products/${id}`),
};
