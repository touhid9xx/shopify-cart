"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";

import { ProductFilters } from "@/components/products/product-filters";
import { ProductGrid } from "@/components/products/product-grid";
import { Button } from "@/components/ui/button";
import { useProducts } from "@/hooks/use-products";

const PAGE_SIZE = 20;

// ──────────────────────────────────────────────────────────────
// Page shell
// ──────────────────────────────────────────────────────────────
export default function ProductsPage() {
  return (
    <Suspense fallback={<ProductsSkeleton />}>
      <ProductsContent />
    </Suspense>
  );
}

// ──────────────────────────────────────────────────────────────
// Fallback
// ──────────────────────────────────────────────────────────────
function ProductsSkeleton() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <div className="h-8 w-48 animate-pulse rounded bg-muted" />
        <div className="mt-2 h-4 w-32 animate-pulse rounded bg-muted" />
      </div>
      <div className="mb-6 flex gap-3">
        <div className="h-10 flex-1 animate-pulse rounded bg-muted" />
        <div className="h-10 w-64 animate-pulse rounded bg-muted" />
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="aspect-square animate-pulse rounded bg-muted" />
        ))}
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────
// The real content — uses useSearchParams
// ──────────────────────────────────────────────────────────────
function ProductsContent() {
  const params = useSearchParams();
  const initialCat = params.get("category_id");

  const [categoryId, setCategoryId] = useState<number | null>(
    initialCat ? Number(initialCat) : null
  );
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isFetching } = useProducts({
    page,
    size: PAGE_SIZE,
    category_id: categoryId ?? undefined,
    q: query || undefined,
  });

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Products</h1>
        <p className="text-muted-foreground">Browse our catalog</p>
      </div>

      <div className="mb-6">
        <ProductFilters
          categoryId={categoryId}
          query={query}
          onCategoryChange={(id) => {
            setCategoryId(id);
            setPage(1);
          }}
          onQueryChange={(q) => {
            setQuery(q);
            setPage(1);
          }}
        />
      </div>

      <ProductGrid
        products={data?.items ?? []}
        isLoading={isLoading || (isFetching && !data)}
      />

      {data && data.pages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <Button
            variant="outline"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {data.page} of {data.pages} · {data.total} items
          </span>
          <Button
            variant="outline"
            disabled={page >= data.pages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
