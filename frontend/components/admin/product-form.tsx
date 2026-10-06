"use client";

import { useRouter } from "next/navigation";
import { ImageOff, ImagePlus, Loader2, Upload, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCreateProduct,
  useUpdateProduct,
  useUploadProductImageForProduct,
} from "@/hooks/use-admin-products";
import { useCategoryTree } from "@/hooks/use-categories";
import { resolveImageUrl } from "@/lib/utils";
import type {
  CategoryTreeNode,
  Product,
  ProductCreatePayload,
} from "@/lib/api-types";

// ══════════════════════════════════════════════════════════════
// Helpers
// ══════════════════════════════════════════════════════════════
function flatten(
  nodes: CategoryTreeNode[],
  depth = 0,
): { id: number; name: string; depth: number }[] {
  const out: { id: number; name: string; depth: number }[] = [];
  for (const n of nodes) {
    out.push({ id: n.id, name: n.name, depth });
    if (n.children?.length) out.push(...flatten(n.children, depth + 1));
  }
  return out;
}

const MAX_FILE_MB = 5;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

// ══════════════════════════════════════════════════════════════
// Main
// ══════════════════════════════════════════════════════════════
interface Props {
  product?: Product;
}

export function ProductForm({ product }: Props) {
  const router = useRouter();
  const isEdit = !!product;

  // Form state
  const [name, setName] = useState(product?.name ?? "");
  const [sku, setSku] = useState(product?.sku ?? "");
  const [description, setDescription] = useState(product?.description ?? "");
  const [price, setPrice] = useState(product?.price ?? "");
  const [categoryId, setCategoryId] = useState<number | null>(
    product?.category_id ?? null,
  );
  const [imageUrl, setImageUrl] = useState(product?.image_url ?? "");
  const [isActive, setIsActive] = useState(product?.is_active ?? true);

  const { data: tree } = useCategoryTree();
  const flatCats = tree ? flatten(tree) : [];

  const create = useCreateProduct();
  const update = useUpdateProduct();
  const uploadImage = useUploadProductImageForProduct();

  // ──────────────────────────────────────────────────────────
  // Image upload state
  // ──────────────────────────────────────────────────────────
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [pendingPreview, setPendingPreview] = useState<string | null>(null);

  // Clear preview when component unmounts or file changes
  useEffect(() => {
    return () => {
      if (pendingPreview) URL.revokeObjectURL(pendingPreview);
    };
  }, [pendingPreview]);

  function handleFile(f: File) {
    if (!ACCEPTED_TYPES.includes(f.type)) {
      alert("Please upload a JPEG, PNG, or WebP image.");
      return;
    }
    if (f.size > MAX_FILE_MB * 1024 * 1024) {
      alert(`File too large. Max ${MAX_FILE_MB} MB.`);
      return;
    }
    if (pendingPreview) URL.revokeObjectURL(pendingPreview);
    setPendingFile(f);
    setPendingPreview(URL.createObjectURL(f));
  }

  function clearPendingFile() {
    if (pendingPreview) URL.revokeObjectURL(pendingPreview);
    setPendingFile(null);
    setPendingPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  // ──────────────────────────────────────────────────────────
  // Submit
  // ──────────────────────────────────────────────────────────
  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name || !sku || !price) return;

    const payload: ProductCreatePayload = {
      name: name.trim(),
      sku: sku.trim(),
      description: description.trim() || null,
      price: price.trim(),
      category_id: categoryId,
      image_url: imageUrl.trim() || null,
      is_active: isActive,
    };

    if (isEdit && product) {
      // Update JSON first
      update.mutate(
        { id: product.id, payload },
        {
          onSuccess: async () => {
            // If a new file was staged, upload it after JSON update
            if (pendingFile) {
              await uploadImage.mutateAsync({
                id: product.id,
                image: pendingFile,
              });
              clearPendingFile();
            }
            router.push("/dashboard/products");
          },
        },
      );
    } else {
      // Create — no image upload here (use /upload tab for ML flow, or set URL)
      create.mutate(payload, {
        onSuccess: () => {
          router.push("/dashboard/products");
        },
      });
    }
  }

  const submitting =
    create.isPending || update.isPending || uploadImage.isPending;

  // Current image to display: pending preview > product image_url
  const currentImage = pendingPreview
    ? pendingPreview
    : resolveImageUrl(imageUrl || product?.image_url || null);

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      {/* ─── Image section (edit mode only) ─── */}
      {isEdit && (
        <div className="rounded-lg border p-4">
          <Label className="mb-3 block text-sm font-medium">
            Replace product image
          </Label>

          <div className="flex flex-col gap-4 sm:flex-row">
            {/* Current preview */}
            <div className="h-32 w-32 shrink-0 overflow-hidden rounded border bg-muted">
              {currentImage ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={currentImage}
                  alt="Product preview"
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full items-center justify-center">
                  <ImageOff className="h-8 w-8 text-muted-foreground" />
                </div>
              )}
            </div>

            {/* Upload controls */}
            <div className="flex flex-1 flex-col justify-center gap-2">
              <p className="text-sm text-muted-foreground">
                Upload a new image from your computer, or leave as-is. JPEG,
                PNG, or WebP · max {MAX_FILE_MB} MB.
              </p>

              <div className="flex flex-wrap items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED_TYPES.join(",")}
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleFile(f);
                  }}
                  disabled={submitting}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={submitting}
                >
                  <ImagePlus className="mr-2 h-4 w-4" />
                  Choose file
                </Button>
                {pendingFile && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={clearPendingFile}
                    disabled={submitting}
                  >
                    <X className="mr-1 h-4 w-4" />
                    Cancel
                  </Button>
                )}
              </div>

              {pendingFile && (
                <p className="text-xs text-muted-foreground">
                  Staged: <span className="font-mono">{pendingFile.name}</span>{" "}
                  ({(pendingFile.size / 1024).toFixed(0)} KB) — will upload on
                  save.
                </p>
              )}

              {/* URL fallback */}
              <Separator className="my-2" />
              <p className="text-xs text-muted-foreground">
                Or paste an image URL:
              </p>
              <Input
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                placeholder="https://..."
                disabled={submitting}
                className="text-xs"
              />
            </div>
          </div>
        </div>
      )}

      {/* ─── Basic fields ─── */}
      <div className="space-y-2">
        <Label htmlFor="product-name">
          Product name <span className="text-destructive">*</span>
        </Label>
        <Input
          id="product-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          disabled={submitting}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="product-sku">
          SKU <span className="text-destructive">*</span>
        </Label>
        <Input
          id="product-sku"
          value={sku}
          onChange={(e) => setSku(e.target.value)}
          required
          disabled={submitting}
          className="font-mono"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="product-description">Description</Label>
        <Textarea
          id="product-description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          disabled={submitting}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="product-price">
            Price (USD) <span className="text-destructive">*</span>
          </Label>
          <Input
            id="product-price"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            inputMode="decimal"
            required
            disabled={submitting}
          />
        </div>

        <div className="space-y-2">
          <Label>Category</Label>
          <Select
            value={categoryId ? String(categoryId) : ""}
            onValueChange={(v) => setCategoryId(Number(v))}
            disabled={submitting}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select category" />
            </SelectTrigger>
            <SelectContent>
              {flatCats.map((c) => (
                <SelectItem key={c.id} value={String(c.id)}>
                  {"\u00A0".repeat(c.depth * 2)}
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Image URL — only for CREATE mode (edit mode has its own section above) */}
      {!isEdit && (
        <div className="space-y-2">
          <Label htmlFor="product-image">Image URL (optional)</Label>
          <Input
            id="product-image"
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            placeholder="https://... or leave empty"
            disabled={submitting}
          />
          <p className="text-xs text-muted-foreground">
            Leave empty and use the &ldquo;Upload image&rdquo; tab for
            ML-powered categorization.
          </p>
        </div>
      )}

      {/* ─── Active toggle ─── */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="product-active"
          checked={isActive}
          onChange={(e) => setIsActive(e.target.checked)}
          disabled={submitting}
          className="h-4 w-4 rounded border-gray-300"
        />
        <Label htmlFor="product-active" className="cursor-pointer text-sm">
          Active (visible to customers)
        </Label>
      </div>

      {/* ─── Actions ─── */}
      <Separator />
      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => router.push("/dashboard/products")}
          disabled={submitting}
        >
          Cancel
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isEdit ? "Save changes" : "Create product"}
        </Button>
      </div>
    </form>
  );
}
