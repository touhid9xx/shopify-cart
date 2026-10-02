import type { Metadata } from "next";
import { OrderDetailView } from "@/components/orders/order-detail-view";

export const metadata: Metadata = {
  title: "Order details · Shopify Cart",
};

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function OrderDetailPage({ params }: PageProps) {
  const { id } = await params;
  const orderId = Number(id);

  return <OrderDetailView orderId={orderId} />;
}
