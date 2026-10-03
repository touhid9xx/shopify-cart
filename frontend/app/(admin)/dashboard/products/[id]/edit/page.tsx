"use client";

import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ProductForm } from "@/components/admin/product-form";

import { useProduct } from "@/hooks/use-products";
import { cn } from "@/lib/utils";

export default function EditProductPage() {
  const params = useParams<{ id: string }>();
  const productId = Number(params.id);

  const { data: product, isLoading, isError } = useProduct(productId);

  if (isLoading) {
    return (
      <div className="container mx-auto max-w-3xl px-4 py-8">
        <Skeleton className="mb-6 h-8 w-32" />
        <div className="space-y-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      </div>
    );
  }

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

  return (
    <div className="container mx-auto max-w-3xl px-4 py-8">
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
          Update &ldquo;{product.name}&rdquo; details.
        </p>
      </div>

      <ProductForm product={product} />
    </div>
  );
}
