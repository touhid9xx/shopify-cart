import type { OrderItem } from "@/lib/api-types";
import { formatMoney } from "@/lib/formatters";
import { Separator } from "@/components/ui/separator";

interface Props {
  items: OrderItem[];
  totalAmount: string;
}

export function OrderItemsList({ items, totalAmount }: Props) {
  return (
    <div className="space-y-4">
      <ul className="space-y-4">
        {items.map((item) => (
          <li key={item.id} className="flex items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <p className="font-medium">{item.product_name}</p>
              <p className="text-xs text-muted-foreground">
                SKU: {item.product_sku}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                {formatMoney(item.unit_price)} × {item.quantity}
              </p>
            </div>
            <div className="text-right font-medium tabular-nums">
              {formatMoney(item.subtotal)}
            </div>
          </li>
        ))}
      </ul>

      <Separator />

      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Shipping</span>
          <span>Free</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Tax</span>
          <span>{formatMoney("0.00")}</span>
        </div>
      </div>

      <Separator />

      <div className="flex justify-between text-base font-semibold">
        <span>Total</span>
        <span className="tabular-nums">{formatMoney(totalAmount)}</span>
      </div>
    </div>
  );
}
