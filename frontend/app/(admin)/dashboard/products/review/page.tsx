import type { Metadata } from "next";
import { ProductReviewQueue } from "@/components/admin/product-review-queue";

export const metadata: Metadata = {
  title: "Review Queue · Admin · Shopify Cart",
};

export default function ProductReviewPage() {
  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <ProductReviewQueue />
    </div>
  );
}
