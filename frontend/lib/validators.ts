import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

export const registerSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .max(128, "Password is too long"),
  full_name: z.string().max(255).optional().or(z.literal("")),
});

export const checkoutSchema = z.object({
  shipping_address: z
    .string()
    .min(5, "Address must be at least 5 characters")
    .max(500),
  notes: z.string().max(1000).optional().or(z.literal("")),
});

export const productFormSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  sku: z.string().min(1, "SKU is required").max(64),
  description: z.string().max(10_000).optional().or(z.literal("")),
  price: z
    .string()
    .regex(/^\d+(\.\d{1,2})?$/, "Must be a positive number with up to 2 decimals"),
  category_id: z.number().int().positive().nullable().optional(),
  image_url: z.string().max(512).optional().or(z.literal("")),
});


export type LoginInput = z.infer<typeof loginSchema>;
export type RegisterInput = z.infer<typeof registerSchema>;
export type CheckoutInput = z.infer<typeof checkoutSchema>;
export type ProductFormInput = z.infer<typeof productFormSchema>;
