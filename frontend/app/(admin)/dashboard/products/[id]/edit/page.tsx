"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, ImageOff } from "lucide-react";

import { ProductForm } from "@/components/admin/product-form";
import { ProductMLMetadata } from "@/components/admin/product-ml-metadata";
import { ProductReviewPanel } from "@/components/admin/product-review-panel";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminProduct } from "@/hooks/use-admin-products";
import { cn, resolveImageUrl } from "@/lib/utils";

export default function EditProductPage() {
  const params = useParams<{ id: string }>();
  const productId = Number(params.id);

  const { data: product, isLoading, isError } = useAdminProduct(productId);

  // ─── Loading ───
  if (isLoading) {
    return (
      <div className="container mx-auto max-w-6xl px-4 py-8">
        <Skeleton className="mb-6 h-8 w-32" />
        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          <div className="space-y-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-64 w-full rounded-lg" />
            <Skeleton className="h-48 w-full rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  // ─── Error ───
  if (isError || !product) {
    return (
      <div className="container mx-auto max-w-3xl px-4 py-8 text-center">
        <p className="text-lg font-medium">Product not found</p>
        <Link
          href="/dashboard/products"
          className={cn(buttonVariants({ variant: "outline" }), "mt-4")}
        >
          Back to products
        </Link>
      </div>
    );
  }

  // ─── Success ───
  const imageUrl = resolveImageUrl(product.image_url);

  return (
    <div className="container mx-auto max-w-6xl px-4 py-8">
      <Link
        href="/dashboard/products"
        className={cn(
          buttonVariants({ variant: "ghost", size: "sm" }),
          "mb-6",
        )}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to products
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl font-bold">Edit product</h1>
        <p className="mt-2 text-muted-foreground">
          Update &ldquo;{product.name}&rdquo; details and review its ML
          classification.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        {/* ─── Left: edit form + image preview ─── */}
        <div className="space-y-6">
          {/* Image preview */}
          <div className="rounded-lg border p-4">
            <p className="mb-3 text-sm font-medium text-muted-foreground">
              Product image
            </p>
            <div className="h-64 w-full overflow-hidden rounded bg-muted">
              {imageUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={imageUrl}
                  alt={product.name}
                  className="h-full w-full object-contain"
                />
              ) : (
                <div className="flex h-full items-center justify-center">
                  <ImageOff className="h-10 w-10 text-muted-foreground" />
                </div>
              )}
            </div>
          </div>

          {/* Edit form */}
          <ProductForm product={product} />
        </div>

        {/* ─── Right: ML metadata + review panel ─── */}
        <aside className="space-y-6 lg:sticky lg:top-6 lg:self-start">
          <ProductMLMetadata product={product} />
          <ProductReviewPanel product={product} />
        </aside>
      </div>
    </div>
  );
}
