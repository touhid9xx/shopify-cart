"use client";

import { useQuery } from "@tanstack/react-query";

import { productsApi, type ListProductsParams } from "@/lib/api/products";

export const productsKeys = {
  all: ["products"] as const,
  list: (params: ListProductsParams) => ["products", "list", params] as const,
  detail: (id: number) => ["products", "detail", id] as const,
};

export function useProducts(params: ListProductsParams = {}) {
  return useQuery({
    queryKey: productsKeys.list(params),
    queryFn: () => productsApi.list(params),
    placeholderData: (prev) => prev,
  });
}

export function useProduct(id: number) {
  return useQuery({
    queryKey: productsKeys.detail(id),
    queryFn: () => productsApi.get(id),
    enabled: Number.isFinite(id) && id > 0,
  });
}
