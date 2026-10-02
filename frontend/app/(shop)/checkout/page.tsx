import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckoutForm } from "@/components/checkout/checkout-form";
import { OrderSummary } from "@/components/checkout/order-summary";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Checkout · Shopify Cart",
  description: "Complete your order.",
};

export default function CheckoutPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      {/* Back link */}
      <Link
        href="/cart"
        className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "mb-6")}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to cart
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl font-bold">Checkout</h1>
        <p className="mt-2 text-muted-foreground">
          Review your order and enter shipping details.
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* ── Left: Shipping form ── */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Shipping details</CardTitle>
            </CardHeader>
            <CardContent>
              <CheckoutForm />
            </CardContent>
          </Card>
        </div>

        {/* ── Right: Order summary ── */}
        <div className="lg:col-span-1">
          <Card className="sticky top-24">
            <CardHeader>
              <CardTitle>Order summary</CardTitle>
            </CardHeader>
            <CardContent>
              <OrderSummary />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
