"use client";

import { useState } from "react";
import { Minus, Plus, ShoppingBag } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAddToCart } from "@/hooks/use-cart";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";

interface Props {
  productId: number;
  maxQuantity: number;
}

export function AddToCartButton({ productId, maxQuantity }: Props) {
  const [quantity, setQuantity] = useState(1);
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const addToCart = useAddToCart();

  if (maxQuantity <= 0) {
    return (
      <Button disabled size="lg" className="w-full">
        Out of stock
      </Button>
    );
  }

  const handleAdd = () => {
    if (!isAuthenticated) {
      router.push(`/login?next=/products/${productId}`);
      return;
    }
    addToCart.mutate({ product_id: productId, quantity });
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setQuantity((q) => Math.max(1, q - 1))}
          disabled={quantity <= 1}
        >
          <Minus className="h-4 w-4" />
        </Button>
        <span className="w-12 text-center font-medium">{quantity}</span>
        <Button
          variant="outline"
          size="icon"
          onClick={() => setQuantity((q) => Math.min(maxQuantity, q + 1))}
          disabled={quantity >= maxQuantity}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      <Button
        size="lg"
        className="w-full"
        onClick={handleAdd}
        disabled={addToCart.isPending}
      >
        <ShoppingBag className="mr-2 h-5 w-5" />
        {addToCart.isPending ? "Adding..." : "Add to cart"}
      </Button>
    </div>
  );
}
