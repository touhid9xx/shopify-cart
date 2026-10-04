"use client";

import { Fragment, useState } from "react";
import Link from "next/link";
import { ChevronDown, Package, ShoppingCart } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { OrderStatusBadge } from "@/components/orders/order-status-badge";
import { OrderActions } from "./order-actions";

import { useAdminOrders } from "@/hooks/use-admin-orders";
import { formatDateTime, formatMoney } from "@/lib/formatters";
import type { OrderStatus } from "@/lib/api-types";

const PAGE_SIZE = 20;

const STATUS_OPTIONS: { value: OrderStatus | "all"; label: string }[] = [
  { value: "all", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "confirmed", label: "Confirmed" },
  { value: "shipped", label: "Shipped" },
  { value: "delivered", label: "Delivered" },
  { value: "rejected", label: "Rejected" },
  { value: "cancelled", label: "Cancelled" },
];

export function OrdersTable() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<OrderStatus | "all">(
    "pending",
  );
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const { data, isLoading, isFetching } = useAdminOrders({
    page,
    size: PAGE_SIZE,
    status: statusFilter === "all" ? undefined : statusFilter,
  });

  const orders = data?.items ?? [];

  const toggle = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ShoppingCart className="h-6 w-6 text-primary" />
            Orders
          </h1>
          <p className="text-sm text-muted-foreground">
            Review and manage customer orders.
            {data ? ` ${data.total} total.` : ""}
          </p>
        </div>
      </div>

      {/* Filter */}
      <div className="flex flex-wrap items-center gap-3">
        <Select
          value={statusFilter}
          onValueChange={(v) => {
            setStatusFilter(v as OrderStatus | "all");
            setPage(1);
          }}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 w-full rounded-lg" />
          ))}
        </div>
      ) : orders.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-muted">
            <Package className="h-7 w-7 text-muted-foreground" />
          </div>
          <h2 className="text-lg font-semibold">No orders</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {statusFilter === "all"
              ? "No orders yet."
              : `No orders with status "${statusFilter}".`}
          </p>
        </div>
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16"></TableHead>
                <TableHead>Order</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Placed</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {orders.map((order) => {
                const isExpanded = expanded.has(order.id);
                return (
                  <Fragment key={order.id}>
                    <TableRow>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => toggle(order.id)}
                          aria-label="Toggle details"
                        >
                          <ChevronDown
                            className={`h-4 w-4 transition-transform ${
                              isExpanded ? "rotate-180" : ""
                            }`}
                          />
                        </Button>
                      </TableCell>
                      <TableCell>
                        <Link
                          href={`/orders/${order.id}`}
                          className="font-medium hover:underline"
                        >
                          #{order.id}
                        </Link>
                      </TableCell>
                      <TableCell className="text-sm">
                        User #{order.user_id}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatMoney(order.total_amount)}
                      </TableCell>
                      <TableCell>
                        <OrderStatusBadge status={order.status} />
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDateTime(order.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <OrderActions order={order} />
                      </TableCell>
                    </TableRow>

                    {/* Expanded row — items + admin message */}
                    {isExpanded && (
                      <TableRow>
                        <TableCell colSpan={7} className="bg-muted/30">
                          <div className="space-y-3 p-2">
                            <p className="text-xs font-semibold uppercase text-muted-foreground">
                              Items ({order.item_count})
                            </p>
                            <ul className="space-y-1">
                              {order.items.map((item) => (
                                <li
                                  key={item.id}
                                  className="flex justify-between text-sm"
                                >
                                  <span>
                                    {item.product_name} —{" "}
                                    <span className="text-muted-foreground">
                                      {formatMoney(item.unit_price)} ×{" "}
                                      {item.quantity}
                                    </span>
                                  </span>
                                  <span className="tabular-nums">
                                    {formatMoney(item.subtotal)}
                                  </span>
                                </li>
                              ))}
                            </ul>

                            <p className="text-xs font-semibold uppercase text-muted-foreground mt-2">
                              Shipping address
                            </p>
                            <p className="whitespace-pre-line text-sm">
                              {order.shipping_address}
                            </p>

                            {order.notes && (
                              <>
                                <p className="text-xs font-semibold uppercase text-muted-foreground mt-2">
                                  Customer notes
                                </p>
                                <p className="whitespace-pre-line text-sm">
                                  {order.notes}
                                </p>
                              </>
                            )}

                            {order.admin_message && (
                              <>
                                <p className="text-xs font-semibold uppercase text-muted-foreground mt-2">
                                  Admin message
                                </p>
                                <p className="whitespace-pre-line text-sm">
                                  {order.admin_message}
                                </p>
                              </>
                            )}

                            {order.reviewed_at && (
                              <p className="text-xs text-muted-foreground">
                                Reviewed by admin #{order.reviewed_by} at{" "}
                                {formatDateTime(order.reviewed_at)}
                              </p>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {data.page} of {data.pages} · {data.total} orders
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || isFetching}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.pages || isFetching}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
