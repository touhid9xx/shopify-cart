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
  ApprovePayload,
  AutoCategorizeResponse,
  ProductCreatePayload,
  ProductUpdatePayload,
  RecategorizePayload,
  RejectPayload,
} from "@/lib/api-types";

// ══════════════════════════════════════════════════════════════
// Query keys
// ══════════════════════════════════════════════════════════════
export const adminProductsKeys = {
  all: ["admin", "products"] as const,
  pendingReview: (params: { page?: number; size?: number } = {}) =>
    ["admin", "products", "pending-review", params] as const,
};

// ══════════════════════════════════════════════════════════════
// Queries
// ══════════════════════════════════════════════════════════════
export function useAdminProducts(params: ListProductsParams = {}) {
  return useQuery({
    queryKey: [...productsKeys.all, "admin", params],
    queryFn: () => productsApi.list(params),
    placeholderData: (prev) => prev,
    refetchOnMount: "always",
  });
}

export function usePendingReviewProducts(
  params: { page?: number; size?: number } = {},
) {
  return useQuery({
    queryKey: adminProductsKeys.pendingReview(params),
    queryFn: () => adminProductsApi.listPendingReview(params),
    placeholderData: (prev) => prev,
    refetchOnMount: "always",
  });
}

// ══════════════════════════════════════════════════════════════
// Single product (with review + ML metadata)
// ══════════════════════════════════════════════════════════════
export function useAdminProduct(id: number) {
  return useQuery({
    queryKey: ["admin", "products", id],
    queryFn: () => adminProductsApi.getById(id),
    enabled: Number.isFinite(id) && id > 0,
    staleTime: 30_000,
  });
}

// ══════════════════════════════════════════════════════════════
// Helpers
// ══════════════════════════════════════════════════════════════
function errMsg(err: unknown, fallback: string): string {
  if (err instanceof HttpError) return err.payload?.detail ?? err.message;
  return fallback;
}

// ══════════════════════════════════════════════════════════════
// CRUD mutations
// ══════════════════════════════════════════════════════════════
export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProductCreatePayload) =>
      adminProductsApi.create(payload),
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
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: ProductUpdatePayload;
    }) => adminProductsApi.update(id, payload),
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
      qc.invalidateQueries({ queryKey: adminProductsKeys.all });

      if (result.status === "created") {
        toast.success("Product created — pending review", {
          description: `Auto-categorized as ${result.category_name} (${Math.round(
            (result.confidence ?? 0) * 100,
          )}% confidence). Awaiting admin review.`,
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

// ══════════════════════════════════════════════════════════════
// Review mutations
// ══════════════════════════════════════════════════════════════
function invalidateReviewData(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: adminProductsKeys.all });
  qc.invalidateQueries({ queryKey: productsKeys.all });
}

export function useApproveProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload?: ApprovePayload }) =>
      adminProductsApi.approve(id, payload ?? {}),
    onSuccess: () => {
      invalidateReviewData(qc);
      toast.success("Product approved");
    },
    onError: (err) => toast.error(errMsg(err, "Could not approve product")),
  });
}

export function useRejectProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: RejectPayload }) =>
      adminProductsApi.reject(id, payload),
    onSuccess: () => {
      invalidateReviewData(qc);
      toast.success("Product rejected");
    },
    onError: (err) => toast.error(errMsg(err, "Could not reject product")),
  });
}

export function useRecategorizeProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: RecategorizePayload;
    }) => adminProductsApi.recategorize(id, payload),
    onSuccess: () => {
      invalidateReviewData(qc);
      toast.success("Product recategorized and approved");
    },
    onError: (err) =>
      toast.error(errMsg(err, "Could not recategorize product")),
  });
}
export function useUploadProductImageForProduct() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, image }: { id: number; image: File }) =>
      adminProductsApi.uploadProductImage(id, image),
    onSuccess: (data) => {
      toast.success("Product image updated");
      // Invalidate this product + list
      qc.invalidateQueries({ queryKey: ["admin", "products", data.id] });
      qc.invalidateQueries({ queryKey: ["admin", "products"] });
    },
    onError: (error: unknown) => {
      const message =
        error instanceof Error ? error.message : "Failed to upload image";
      toast.error(message);
    },
  });
}
