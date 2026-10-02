import Link from "next/link";
import { ArrowRight, Package } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { OrderStatusBadge } from "./order-status-badge";

import type { Order } from "@/lib/api-types";
import { formatDate, formatMoney } from "@/lib/formatters";

interface Props {
  order: Order;
}

export function OrderCard({ order }: Props) {
  return (
    <Link href={`/orders/${order.id}`} className="block group">
      <Card className="transition-shadow hover:shadow-md">
        <CardContent className="p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Package className="h-6 w-6" />
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">Order #{order.id}</h3>
                  <OrderStatusBadge status={order.status} />
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  Placed on {formatDate(order.created_at)}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {order.item_count} item{order.item_count === 1 ? "" : "s"} ·{" "}
                  <span className="font-medium text-foreground">
                    {formatMoney(order.total_amount)}
                  </span>
                </p>
              </div>
            </div>

            <ArrowRight className="h-5 w-5 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
