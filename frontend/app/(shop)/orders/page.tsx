import type { Metadata } from "next";
import { OrdersListView } from "@/components/orders/orders-list-view";

export const metadata: Metadata = {
  title: "Your orders · Shopify Cart",
  description: "View and track your orders.",
};

export default function OrdersPage() {
  return <OrdersListView />;
}
