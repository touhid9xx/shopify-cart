"use client";

import { useRouter } from "next/navigation";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ShoppingBag } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

import { useCheckout } from "@/hooks/use-orders";
import { useCart } from "@/hooks/use-cart";
import { useAuth } from "@/lib/auth-context";
import { checkoutSchema, type CheckoutInput } from "@/lib/validators";

export function CheckoutForm() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const { data: cart, isLoading: cartLoading } = useCart(isAuthenticated);
  const checkout = useCheckout();

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<CheckoutInput>({
    resolver: zodResolver(checkoutSchema),
    defaultValues: { shipping_address: "", notes: "" },
  });

  const onSubmit = (values: CheckoutInput) => {
    checkout.mutate({
      shipping_address: values.shipping_address,
      notes: values.notes || null,
    });
  };

  const isEmpty = !cartLoading && (!cart || cart.items.length === 0);

  // ── Empty cart guard ──
  if (isEmpty) {
    return (
      <div className="rounded-lg border p-8 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-muted">
          <ShoppingBag className="h-7 w-7 text-muted-foreground" />
        </div>
        <h2 className="text-lg font-semibold">Your cart is empty</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Add some products before checking out.
        </p>
        <Button
          onClick={() => router.push("/products")}
          className="mt-6"
        >
          Browse products
        </Button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Shipping address */}
      <div className="space-y-2">
        <Label htmlFor="shipping_address">
          Shipping address <span className="text-destructive">*</span>
        </Label>
        <Controller
          name="shipping_address"
          control={control}
          render={({ field }) => (
            <Textarea
              id="shipping_address"
              placeholder="House #, Street, City, Postal code, Country"
              rows={4}
              {...field}
              disabled={checkout.isPending}
            />
          )}
        />
        {errors.shipping_address && (
          <p className="text-sm text-destructive">
            {errors.shipping_address.message}
          </p>
        )}
      </div>

      {/* Notes (optional) */}
      <div className="space-y-2">
        <Label htmlFor="notes">Order notes (optional)</Label>
        <Controller
          name="notes"
          control={control}
          render={({ field }) => (
            <Textarea
              id="notes"
              placeholder="Any special instructions for delivery"
              rows={2}
              {...field}
              value={field.value ?? ""}
              disabled={checkout.isPending}
            />
          )}
        />
        {errors.notes && (
          <p className="text-sm text-destructive">{errors.notes.message}</p>
        )}
      </div>

      <Button
        type="submit"
        size="lg"
        className="w-full"
        disabled={checkout.isPending}
      >
        <ShoppingBag className="mr-2 h-5 w-5" />
        {checkout.isPending ? "Placing order…" : "Place order"}
      </Button>

      <p className="text-center text-xs text-muted-foreground">
        By placing this order, you agree to our terms of service.
      </p>
    </form>
  );
}
