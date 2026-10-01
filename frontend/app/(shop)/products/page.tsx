"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";

import { ProductFilters } from "@/components/products/product-filters";
import { ProductGrid } from "@/components/products/product-grid";
import { Button } from "@/components/ui/button";
import { useProducts } from "@/hooks/use-products";

const PAGE_SIZE = 20;

export default function ProductsPage() {
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
