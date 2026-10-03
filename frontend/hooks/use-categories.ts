"use client";

import { useQuery } from "@tanstack/react-query";

import { categoriesApi } from "@/lib/api/categories";

export const categoriesKeys = {
  all: ["categories"] as const,
  tree: ["categories", "tree"] as const,
  list: ["categories", "list"] as const,
  detail: (id: number) => ["categories", "detail", id] as const,
};

export function useCategoryTree() {
  return useQuery({
    queryKey: categoriesKeys.tree,
    queryFn: () => categoriesApi.tree(),
    staleTime: 10 * 60_000,
  });
}

export function useCategories() {
  return useQuery({
    queryKey: categoriesKeys.list,
    queryFn: () => categoriesApi.list(),
    staleTime: 10 * 60_000,
  });
}
