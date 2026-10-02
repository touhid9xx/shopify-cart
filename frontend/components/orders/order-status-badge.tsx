import { Badge } from "@/components/ui/badge";
import type { OrderStatus } from "@/lib/api-types";
import { cn } from "@/lib/utils";

interface Props {
  status: OrderStatus;
  className?: string;
}

const STATUS_STYLES: Record<OrderStatus, string> = {
  pending:
    "bg-yellow-100 text-yellow-800 hover:bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-400",
  paid: "bg-blue-100 text-blue-800 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400",
  shipped:
    "bg-purple-100 text-purple-800 hover:bg-purple-100 dark:bg-purple-900/30 dark:text-purple-400",
  delivered:
    "bg-green-100 text-green-800 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-400",
  cancelled:
    "bg-red-100 text-red-800 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-400",
};

const STATUS_LABELS: Record<OrderStatus, string> = {
  pending: "Pending",
  paid: "Paid",
  shipped: "Shipped",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

export function OrderStatusBadge({ status, className }: Props) {
  return (
    <Badge
      variant="secondary"
      className={cn(STATUS_STYLES[status], "border-transparent", className)}
    >
      {STATUS_LABELS[status]}
    </Badge>
  );
}
