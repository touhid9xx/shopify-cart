import { api } from "./client";
import type { Category, CategoryTreeNode, Page } from "@/lib/api-types";

export const categoriesApi = {
  list: (params?: { page?: number; size?: number }) => {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.size) qs.set("size", String(params.size));
    return api.get<Page<Category>>(`/categories${qs.toString() ? `?${qs}` : ""}`);
  },

  tree: () => api.get<CategoryTreeNode[]>("/categories/tree"),

  get: (id: number) => api.get<Category>(`/categories/${id}`),
};
