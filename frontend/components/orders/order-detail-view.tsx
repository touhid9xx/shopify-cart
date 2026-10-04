"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Info, MapPin, XCircle } from "lucide-react";
import { useState } from "react";

import { buttonVariants } from "@/components/ui/button";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

import { OrderStatusBadge } from "./order-status-badge";
import { OrderItemsList } from "./order-items-list";

import { useOrder, useCancelOrder } from "@/hooks/use-orders";
import { useAuth } from "@/lib/auth-context";
import { formatDateTime } from "@/lib/formatters";
import { cn } from "@/lib/utils";

interface Props {
  orderId: number;
}

export function OrderDetailView({ orderId }: Props) {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { data: order, isLoading, isError } = useOrder(
    orderId,
    isAuthenticated,
  );
  const cancelOrder = useCancelOrder();
  const [cancelOpen, setCancelOpen] = useState(false);

  // ── Loading ──
  if (authLoading || isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Skeleton className="mb-6 h-8 w-40" />
        <div className="space-y-6">
          <Skeleton className="h-24 w-full rounded-lg" />
          <Skeleton className="h-64 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  // ── Not logged in ──
  if (!isAuthenticated) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <p className="text-lg font-medium">Sign in to view this order</p>
        <Link
          href={`/login?next=/orders/${orderId}`}
          className={cn(buttonVariants({ size: "lg" }), "mt-6")}
        >
          Sign in
        </Link>
      </div>
    );
  }

  // ── Not found / error ──
  if (isError || !order) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <p className="text-lg font-medium">Order not found</p>
        <Button
          variant="outline"
          className="mt-4"
          onClick={() => router.push("/orders")}
        >
          Back to orders
        </Button>
      </div>
    );
  }

  const canCancel =
    order.status === "pending" || order.status === "confirmed";

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Back */}
      <Link
        href="/orders"
        className={cn(
          buttonVariants({ variant: "ghost", size: "sm" }),
          "mb-6",
        )}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to orders
      </Link>

      {/* Header */}
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Order #{order.id}</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Placed on {formatDateTime(order.created_at)}
          </p>
        </div>
        <OrderStatusBadge status={order.status} className="text-sm" />
      </div>

      {/* Admin message banner */}
      {order.admin_message && (
        <Card
          className={cn(
            "mb-6",
            order.status === "rejected"
              ? "border-destructive/50 bg-destructive/5"
              : "border-primary/50 bg-primary/5",
          )}
        >
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Info className="h-4 w-4" />
              {order.status === "rejected"
                ? "Order rejected by admin"
                : "Message from admin"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-line text-sm">
              {order.admin_message}
            </p>
            {order.reviewed_at && (
              <p className="mt-2 text-xs text-muted-foreground">
                {formatDateTime(order.reviewed_at)}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: Items + shipping */}
        <div className="space-y-6 lg:col-span-2">
          {/* Items */}
          <Card>
            <CardHeader>
              <CardTitle>Items</CardTitle>
            </CardHeader>
            <CardContent>
              <OrderItemsList
                items={order.items}
                totalAmount={order.total_amount}
              />
            </CardContent>
          </Card>

          {/* Shipping address */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5" />
                Shipping address
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-line text-sm">
                {order.shipping_address}
              </p>
              {order.notes && (
                <>
                  <Separator className="my-4" />
                  <p className="text-xs font-medium uppercase text-muted-foreground">
                    Order notes
                  </p>
                  <p className="mt-1 whitespace-pre-line text-sm">
                    {order.notes}
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Actions */}
        <div className="lg:col-span-1">
          <Card className="sticky top-24">
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Link
                href="/products"
                className={cn(
                  buttonVariants({ variant: "outline" }),
                  "w-full",
                )}
              >
                Continue shopping
              </Link>

              {canCancel && (
                <Dialog open={cancelOpen} onOpenChange={setCancelOpen}>
                  <DialogTrigger
                    render={
                      <Button
                        variant="outline"
                        className="w-full text-destructive hover:text-destructive"
                      >
                        <XCircle className="mr-2 h-4 w-4" />
                        Cancel order
                      </Button>
                    }
                  />
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Cancel order #{order.id}?</DialogTitle>
                      <DialogDescription>
                        This will cancel the order and restore inventory. This
                        action cannot be undone.
                      </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                      <Button
                        variant="outline"
                        onClick={() => setCancelOpen(false)}
                        disabled={cancelOrder.isPending}
                      >
                        Keep order
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={() =>
                          cancelOrder.mutate(
                            { id: order.id },
                            {
                              onSuccess: () => setCancelOpen(false),
                            },
                          )
                        }
                        disabled={cancelOrder.isPending}
                      >
                        {cancelOrder.isPending
                          ? "Cancelling…"
                          : "Yes, cancel order"}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              )}

              {!canCancel && (
                <p className="text-xs text-muted-foreground">
                  This order can no longer be cancelled.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
