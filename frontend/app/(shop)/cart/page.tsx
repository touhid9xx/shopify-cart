import type { Metadata } from "next";

import { CartFullView } from "@/components/cart/cart-full-view";

export const metadata: Metadata = {
  title: "Your cart · Shopify Cart",
  description: "Review items in your shopping cart.",
};

export default function CartPage() {
  return <CartFullView />;
}
