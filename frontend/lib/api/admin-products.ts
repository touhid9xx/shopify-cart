import { api } from "./client";
import type {
  ApprovePayload,
  AutoCategorizeResponse,
  Page,
  Product,
  ProductCreatePayload,
  ProductReadWithReview,
  ProductUpdatePayload,
  RecategorizePayload,
  RejectPayload,
  ReviewActionResponse,
} from "@/lib/api-types";

export const adminProductsApi = {
  /** Fetch a single product with review + ML metadata (admin) */
  getById: (id: number) =>
    api.get<ProductReadWithReview>(`/admin/products/${id}`),
  /** Create a new product (admin) */
  create: (payload: ProductCreatePayload) =>
    api.post<Product>("/admin/products", payload),

  /** Update an existing product (admin) */
  update: (id: number, payload: ProductUpdatePayload) =>
    api.put<Product>(`/admin/products/${id}`, payload),

  /** Delete a product (admin) */
  delete: (id: number) => api.delete<void>(`/admin/products/${id}`),

  /**
   * Upload an image → ML auto-categorize → create product.
   * Returns either { status: "created", ... } or
   *               { status: "needs_review", ... }
   */
  uploadImage: async (params: {
    image: File;
    name: string;
    price: string;
    sku?: string;
    description?: string;
    category_id?: number;
    is_active?: boolean;
  }): Promise<AutoCategorizeResponse> => {
    const form = new FormData();
    form.append("image", params.image);
    form.append("name", params.name);
    form.append("price", params.price);
    if (params.sku) form.append("sku", params.sku);
    if (params.description) form.append("description", params.description);
    if (params.category_id != null) {
      form.append("category_id", String(params.category_id));
    }
    if (params.is_active != null) {
      form.append("is_active", String(params.is_active));
    }
    return api.upload<AutoCategorizeResponse>("/admin/products/upload", form);
  },

  // ══════════════════════════════════════════════════════════════
  // Review workflow
  // ══════════════════════════════════════════════════════════════

  /** List products pending admin review */
  listPendingReview: (params: { page?: number; size?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set("page", String(params.page));
    if (params.size) qs.set("size", String(params.size));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return api.get<Page<ProductReadWithReview>>(
      `/admin/products/pending-review${suffix}`,
    );
  },

  /** Approve a pending product */
  approve: (id: number, payload: ApprovePayload = {}) =>
    api.post<ReviewActionResponse>(`/admin/products/${id}/approve`, payload),

  /** Reject a pending product with reason */
  reject: (id: number, payload: RejectPayload) =>
    api.post<ReviewActionResponse>(`/admin/products/${id}/reject`, payload),

  /** Override ML category and approve */
  recategorize: (id: number, payload: RecategorizePayload) =>
    api.patch<ReviewActionResponse>(
      `/admin/products/${id}/recategorize`,
      payload,
    ),
};
