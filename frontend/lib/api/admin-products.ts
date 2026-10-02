import { api } from "./client";
import type {
  AutoCategorizeResponse,
  Page,
  Product,
  ProductCreatePayload,
  ProductUpdatePayload,
  ProductWithStock,
} from "@/lib/api-types";

export const adminProductsApi = {
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
};
