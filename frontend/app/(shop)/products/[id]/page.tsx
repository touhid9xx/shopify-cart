"use client";

import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ImageOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { AddToCartButton } from "@/components/cart/add-to-cart-button";

import { useProduct } from "@/hooks/use-products";
import { formatMoney } from "@/lib/formatters";

export default function ProductDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = Number(params.id);

  const { data: product, isLoading, isError } = useProduct(id);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Skeleton className="mb-6 h-6 w-32" />
        <div className="grid gap-8 md:grid-cols-2">
          <Skeleton className="aspect-square w-full" />
          <div className="space-y-4">
            <Skeleton className="h-8 w-3/4" />
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-20 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (isError || !product) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <p className="text-lg font-medium">Product not found</p>
        <Button variant="outline" className="mt-4" onClick={() => router.push("/products")}>
          Back to products
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <Button variant="ghost" onClick={() => router.back()} className="mb-6">
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back
      </Button>

      <div className="grid gap-8 md:grid-cols-2">
        <div className="aspect-square overflow-hidden rounded-lg bg-muted">
          {product.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={product.image_url}
              alt={product.name}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <ImageOff className="h-16 w-16 text-muted-foreground" />
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold">{product.name}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{product.sku}</p>
          </div>

          <p className="text-2xl font-semibold">{formatMoney(product.price)}</p>

          <div className="flex gap-2">
            {product.total_quantity > 0 ? (
              <Badge variant="secondary">
                {product.total_quantity} in stock
              </Badge>
            ) : (
              <Badge variant="destructive">Out of stock</Badge>
            )}
            {!product.is_active && <Badge variant="outline">Inactive</Badge>}
          </div>

          {product.description && (
            <>
              <Separator />
              <p className="whitespace-pre-line text-muted-foreground">
                {product.description}
              </p>
            </>
          )}

          <Separator />

          <AddToCartButton
            productId={product.id}
            maxQuantity={product.total_quantity}
          />
        </div>
      </div>
    </div>
  );
}
