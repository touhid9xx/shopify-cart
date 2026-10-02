import type { Metadata } from "next";
import { ProductsTable } from "@/components/admin/products-table";

export const metadata: Metadata = {
  title: "Products · Admin · Shopify Cart",
};

export default function AdminProductsPage() {
  return (
    <div className="container mx-auto max-w-6xl px-4 py-8">
      <ProductsTable />
    </div>
  );
}
