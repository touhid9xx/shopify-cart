import type { Metadata } from "next";
import { OrdersTable } from "@/components/admin/orders-table";

export const metadata: Metadata = {
  title: "Orders · Admin · Shopify Cart",
};

export default function AdminOrdersPage() {
  return (
    <div className="container mx-auto max-w-7xl px-4 py-8">
      <OrdersTable />
    </div>
  );
}
