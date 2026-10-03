"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";

import { adminProductsApi } from "@/lib/api/admin-products";
import { productsApi, type ListProductsParams } from "@/lib/api/products";
import { HttpError } from "@/lib/api/client";
import { productsKeys } from "@/hooks/use-products";
import type {
  AutoCategorizeResponse,
  ProductCreatePayload,
  ProductUpdatePayload,
} from "@/lib/api-types";

// ──────────────────────────────────────────────────────────────
// Queries
// ──────────────────────────────────────────────────────────────
export function useAdminProducts(params: ListProductsParams = {}) {
  return useQuery({
    queryKey: [...productsKeys.all, "admin", params],
    queryFn: () => productsApi.list(params),
    placeholderData: (prev) => prev,
    refetchOnMount: "always",
  });
}

// ──────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────
function errMsg(err: unknown, fallback: string): string {
  if (err instanceof HttpError) return err.payload?.detail ?? err.message;
  return fallback;
}

// ──────────────────────────────────────────────────────────────
// Mutations
// ──────────────────────────────────────────────────────────────
export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProductCreatePayload) => adminProductsApi.create(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: productsKeys.all });
      toast.success("Product created");
    },
    onError: (err) => toast.error(errMsg(err, "Could not create product")),
  });
}

export function useUpdateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ProductUpdatePayload }) =>
      adminProductsApi.update(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: productsKeys.all });
      toast.success("Product updated");
    },
    onError: (err) => toast.error(errMsg(err, "Could not update product")),
  });
}

export function useDeleteProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => adminProductsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: productsKeys.all });
      toast.success("Product deleted");
    },
    onError: (err) => toast.error(errMsg(err, "Could not delete product")),
  });
}

export function useUploadProductImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: adminProductsApi.uploadImage,
    onSuccess: (result: AutoCategorizeResponse) => {
      qc.invalidateQueries({ queryKey: productsKeys.all });
      if (result.status === "created") {
        toast.success("Product created", {
          description: `Auto-categorized as ${result.category_name} (${Math.round(
            (result.confidence ?? 0) * 100,
          )}% confidence).`,
        });
      } else {
        toast.warning("Needs review", {
          description: `Classifier returned ${result.ml_category} with only ${Math.round(
            result.confidence * 100,
          )}% confidence.`,
        });
      }
    },
    onError: (err) => {
      // ── Handle ML unavailable (503) gracefully ──
      if (err instanceof HttpError && err.status === 503) {
        toast.error("ML classifier unavailable", {
          description:
            "Use the Manual entry tab to create this product, or ask admin to start MLflow.",
          duration: 8000,
        });
        return;
      }
      toast.error(errMsg(err, "Upload failed"));
    },
  });
}
