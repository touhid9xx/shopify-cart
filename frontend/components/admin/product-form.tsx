"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";

import {
  useCreateProduct,
  useUpdateProduct,
} from "@/hooks/use-admin-products";
import { useCategoryTree } from "@/hooks/use-categories";
import { productFormSchema, type ProductFormInput } from "@/lib/validators";
import type { Product } from "@/lib/api-types";

interface Props {
  product?: Product; // edit mode if present
}

export function ProductForm({ product }: Props) {
  const router = useRouter();
  const isEdit = !!product;

  const create = useCreateProduct();
  const update = useUpdateProduct();
  const { data: tree } = useCategoryTree();

  // Flatten categories for the dropdown
  const flatCategories = flattenTree(tree ?? []);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ProductFormInput>({
    resolver: zodResolver(productFormSchema),
    defaultValues: {
      name: product?.name ?? "",
      sku: product?.sku ?? "",
      description: product?.description ?? "",
      price: product?.price ?? "",
      category_id: product?.category_id ?? null,
      image_url: product?.image_url ?? "",
    },
  });

  // When product prop changes (edit), reset form
  useEffect(() => {
    if (product) {
      reset({
        name: product.name,
        sku: product.sku,
        description: product.description ?? "",
        price: product.price,
        category_id: product.category_id ?? null,
        image_url: product.image_url ?? "",
      });
    }
  }, [product, reset]);

  const onSubmit = (values: ProductFormInput) => {
    const payload = {
      name: values.name,
      sku: values.sku,
      description: values.description || null,
      price: values.price,
      category_id: values.category_id ?? null,
      image_url: values.image_url || null,
    };

    if (isEdit && product) {
      update.mutate(
        { id: product.id, payload },
        {
          onSuccess: () =>
            router.push("/dashboard/products"),
        },
      );
    } else {
      create.mutate(payload, {
        onSuccess: (created) =>
          router.push(`/dashboard/products/${created.id}/edit`),
      });
    }
  };

  const isPending = create.isPending || update.isPending;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Name */}
      <div className="space-y-2">
        <Label htmlFor="name">
          Product name <span className="text-destructive">*</span>
        </Label>
        <Controller
          name="name"
          control={control}
          render={({ field }) => (
            <Input
              id="name"
              placeholder="e.g. Classic Cotton T-Shirt"
              {...field}
              disabled={isPending}
            />
          )}
        />
        {errors.name && (
          <p className="text-sm text-destructive">{errors.name.message}</p>
        )}
      </div>

      {/* SKU */}
      <div className="space-y-2">
        <Label htmlFor="sku">
          SKU <span className="text-destructive">*</span>
        </Label>
        <Controller
          name="sku"
          control={control}
          render={({ field }) => (
            <Input
              id="sku"
              placeholder="e.g. SKU-TSHIRT-001"
              className="font-mono"
              {...field}
              disabled={isPending}
            />
          )}
        />
        {errors.sku && (
          <p className="text-sm text-destructive">{errors.sku.message}</p>
        )}
      </div>

      {/* Description */}
      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Controller
          name="description"
          control={control}
          render={({ field }) => (
            <Textarea
              id="description"
              rows={4}
              placeholder="Product details, materials, sizing…"
              {...field}
              value={field.value ?? ""}
              disabled={isPending}
            />
          )}
        />
        {errors.description && (
          <p className="text-sm text-destructive">
            {errors.description.message}
          </p>
        )}
      </div>

      {/* Price + Category (2 columns) */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="price">
            Price (USD) <span className="text-destructive">*</span>
          </Label>
          <Controller
            name="price"
            control={control}
            render={({ field }) => (
              <Input
                id="price"
                placeholder="29.99"
                inputMode="decimal"
                {...field}
                disabled={isPending}
              />
            )}
          />
          {errors.price && (
            <p className="text-sm text-destructive">{errors.price.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label>Category</Label>
          <Controller
            name="category_id"
            control={control}
            render={({ field }) => (
              <Select
                value={field.value ? String(field.value) : "none"}
                onValueChange={(v) =>
                  field.onChange(v === "none" ? null : Number(v))
                }
                disabled={isPending}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Uncategorized</SelectItem>
                  {flatCategories.map((cat) => (
                    <SelectItem key={cat.id} value={String(cat.id)}>
                      {"\u00A0".repeat(cat.depth * 2)}
                      {cat.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
          {errors.category_id && (
            <p className="text-sm text-destructive">
              {errors.category_id.message}
            </p>
          )}
        </div>
      </div>

      {/* Image URL (optional) */}
      <div className="space-y-2">
        <Label htmlFor="image_url">Image URL (optional)</Label>
        <Controller
          name="image_url"
          control={control}
          render={({ field }) => (
            <Input
              id="image_url"
              placeholder="https://… or /static/uploads/…"
              {...field}
              value={field.value ?? ""}
              disabled={isPending}
            />
          )}
        />
        <p className="text-xs text-muted-foreground">
          Leave empty and use the &ldquo;Upload image&rdquo; tab for
          ML-powered categorization.
        </p>
      </div>

      {/* Submit */}
      <div className="flex justify-end gap-3 border-t pt-6">
        <Button
          type="button"
          variant="outline"
          onClick={() => router.push("/dashboard/products")}
          disabled={isPending}
        >
          Cancel
        </Button>
        <Button type="submit" disabled={isPending}>
          {isPending
            ? isEdit
              ? "Saving…"
              : "Creating…"
            : isEdit
              ? "Save changes"
              : "Create product"}
        </Button>
      </div>
    </form>
  );
}

// ──────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────
interface CategoryNode {
  id: number;
  name: string;
  children?: CategoryNode[];
}

function flattenTree(
  nodes: CategoryNode[],
  depth = 0,
): { id: number; name: string; depth: number }[] {
  const out: { id: number; name: string; depth: number }[] = [];
  for (const n of nodes) {
    out.push({ id: n.id, name: n.name, depth });
    if (n.children?.length) {
      out.push(...flattenTree(n.children, depth + 1));
    }
  }
  return out;
}
