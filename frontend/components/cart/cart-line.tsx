"use client";

import Link from "next/link";
import { Minus, Plus, Trash2, ImageOff } from "lucide-react";

import { Button } from "@/components/ui/button";

import type { CartItemWithProduct } from "@/lib/api-types";
import { formatMoney } from "@/lib/formatters";
import { resolveImageUrl } from "@/lib/utils";
import { useUpdateCartItem, useRemoveCartItem } from "@/hooks/use-cart";

interface Props {
  item: CartItemWithProduct;
}

export function CartLine({ item }: Props) {
  const update = useUpdateCartItem();
  const remove = useRemoveCartItem();
  const imageUrl = resolveImageUrl(item.product.image_url);

  const handleQuantity = (delta: number) => {
    const newQty = item.quantity + delta;
    if (newQty < 1) return;
    update.mutate({ id: item.id, quantity: newQty });
  };

  return (
    <div className="flex gap-4">
      <Link
        href={`/products/${item.product_id}`}
        className="h-20 w-20 flex-shrink-0 overflow-hidden rounded bg-muted"
      >
        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt={item.product.name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <ImageOff className="h-6 w-6 text-muted-foreground" />
          </div>
        )}
      </Link>

      <div className="flex flex-1 flex-col">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <Link
              href={`/products/${item.product_id}`}
              className="line-clamp-1 font-medium hover:underline"
            >
              {item.product.name}
            </Link>
            <p className="text-xs text-muted-foreground">
              {formatMoney(item.unit_price)} each
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={() => remove.mutate(item.id)}
            disabled={remove.isPending}
            aria-label={`Remove ${item.product.name}`}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>

        <div className="mt-auto flex items-center justify-between pt-2">
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => handleQuantity(-1)}
              disabled={item.quantity <= 1 || update.isPending}
              aria-label="Decrease quantity"
            >
              <Minus className="h-3 w-3" />
            </Button>
            <span className="w-8 text-center text-sm font-medium tabular-nums">
              {update.isPending ? "…" : item.quantity}
            </span>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => handleQuantity(1)}
              disabled={update.isPending}
              aria-label="Increase quantity"
            >
              <Plus className="h-3 w-3" />
            </Button>
          </div>
          <span className="text-sm font-semibold tabular-nums">
            {formatMoney(item.subtotal)}
          </span>
        </div>
      </div>
    </div>
  );
}
