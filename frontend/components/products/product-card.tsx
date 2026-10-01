// product-card.tsx

import Link from "next/link";
import { ImageOff } from "lucide-react";

import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

import type { Product } from "@/lib/api-types";
import { formatMoney } from "@/lib/formatters";
import { resolveImageUrl } from "@/lib/utils";

interface Props {
  product: Product;
}

export function ProductCard({ product }: Props) {
  const imageUrl = resolveImageUrl(product.image_url);

  return (
    <Link href={`/products/${product.id}`} className="group">
      <Card className="overflow-hidden transition-shadow hover:shadow-md">
        <div className="aspect-square overflow-hidden bg-muted">
          {imageUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={imageUrl}
              alt={product.name}
              className="h-full w-full object-cover transition-transform group-hover:scale-105"
              loading="lazy"
            />
          ) : (
            <div className="flex h-full items-center justify-center">
              <ImageOff className="h-12 w-12 text-muted-foreground" />
            </div>
          )}
        </div>
        <CardContent className="pt-4">
          <p className="line-clamp-1 font-medium">{product.name}</p>
          <p className="text-xs text-muted-foreground">{product.sku}</p>
        </CardContent>
        <CardFooter className="justify-between pt-0">
          <span className="font-semibold">{formatMoney(product.price)}</span>
          {!product.is_active && <Badge variant="secondary">Inactive</Badge>}
        </CardFooter>
      </Card>
    </Link>
  );
}
