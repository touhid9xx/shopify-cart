import { formatMoney } from "@/lib/formatters";
import type { CartWithProducts } from "@/lib/api-types";

interface Props {
  cart: CartWithProducts;
  showShipping?: boolean;
}

export function CartSummary({ cart, showShipping = true }: Props) {
  const subtotal = cart.total_amount;
  const shipping = "0.00";
  const tax = "0.00";
  const total = (
    parseFloat(subtotal) +
    parseFloat(shipping) +
    parseFloat(tax)
  ).toFixed(2);

  return (
    <div className="space-y-2 text-sm">
      <div className="flex justify-between">
        <span className="text-muted-foreground">
          Subtotal ({cart.total_quantity} item
          {cart.total_quantity === 1 ? "" : "s"})
        </span>
        <span>{formatMoney(subtotal)}</span>
      </div>

      {showShipping && (
        <>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Shipping</span>
            <span>Free</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Tax</span>
            <span>{formatMoney(tax)}</span>
          </div>
        </>
      )}

      <div className="flex justify-between border-t pt-2 text-base font-semibold">
        <span>Total</span>
        <span>{formatMoney(total)}</span>
      </div>
    </div>
  );
}
