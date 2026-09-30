import { api } from "./client";
import type {
  AutoCategorizeResponse,
  Product,
  ProductCreatePayload,
  ProductUpdatePayload,
} from "@/lib/api-types";

export const adminProductsApi = {
  create: (payload: ProductCreatePayload) =>
    api.post<Product>("/admin/products", payload),

  update: (id: number, payload: ProductUpdatePayload) =>
    api.put<Product>(`/admin/products/${id}`, payload),

  delete: (id: number, hard = false) =>
    api.delete<void>(`/admin/products/${id}?hard=${hard}`),

  /**
   * Upload + auto-categorize.
   *
   * @param file - image file (JPEG/PNG/WebP, ≤10MB)
   * @param name - product name
   * @param price - string decimal e.g. "19.99"
   * @param opts - optional form fields
   */
  uploadAndClassify: (
    file: File,
    name: string,
    price: string,
    opts?: {
      sku?: string;
      description?: string;
      image_url?: string;
      location?: string;
      initial_quantity?: number;
      low_stock_threshold?: number;
      force_category_slug?: string;
    }
  ): Promise<AutoCategorizeResponse> => {
    const form = new FormData();
    form.append("image", file);
    form.append("name", name);
    form.append("price", price);
    if (opts?.sku) form.append("sku", opts.sku);
    if (opts?.description) form.append("description", opts.description);
    if (opts?.image_url) form.append("image_url", opts.image_url);
    if (opts?.location) form.append("location", opts.location);
    if (opts?.initial_quantity !== undefined)
      form.append("initial_quantity", String(opts.initial_quantity));
    if (opts?.low_stock_threshold !== undefined)
      form.append("low_stock_threshold", String(opts.low_stock_threshold));
    if (opts?.force_category_slug)
      form.append("force_category_slug", opts.force_category_slug);

    return api.upload<AutoCategorizeResponse>("/admin/products/upload", form);
  },
};
