import Link from "next/link";
import { ShoppingBag } from "lucide-react";

import { Button } from "@/components/ui/button";

export function CartEmpty() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
        <ShoppingBag className="h-8 w-8 text-muted-foreground" />
      </div>
      <p className="text-lg font-medium">Your cart is empty</p>
      <p className="mt-1 text-sm text-muted-foreground">
        Add some products to get started.
      </p>
      <Button className="mt-6">
        <Link href="/products">Browse products</Link>
      </Button>
    </div>
  );
}
