"use client";

import { useQuery } from "@tanstack/react-query";
import { categoriesApi } from "@/lib/api/categories";

export const categoriesKeys = {
  all: ["categories"] as const,
  tree: ["categories", "tree"] as const,
  detail: (id: number) => ["categories", "detail", id] as const,
};

export function useCategoryTree() {
  return useQuery({
    queryKey: categoriesKeys.tree,
    queryFn: () => categoriesApi.tree(),
    staleTime: 10 * 60_000, // categories rarely change
  });
}
