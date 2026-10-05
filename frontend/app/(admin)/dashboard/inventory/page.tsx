"use client";

import { RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { InventoryAdjustDialog } from "@/components/admin/inventory-adjust-dialog";
import { InventoryAlertsCard } from "@/components/admin/inventory-alerts-card";
import {
  InventoryFilters,
  type InventoryFilterValues,
} from "@/components/admin/inventory-filters";
import { InventoryKpis } from "@/components/admin/inventory-kpis";
import { InventoryTable } from "@/components/admin/inventory-table";
import { ReorderSuggestionsCard } from "@/components/admin/reorder-suggestions-card";
import {
  inventoryKeys,
  useAdminInventory,
} from "@/hooks/use-admin-inventory";
import type {
  InventoryWithProduct,
  ListInventoryParams,
} from "@/lib/api-types";

const PAGE_SIZE = 20;

const DEFAULT_FILTERS: InventoryFilterValues = {
  search: "",
  location: "",
  lowStockOnly: false,
  outOfStockOnly: false,
};

export default function InventoryPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<InventoryFilterValues>(DEFAULT_FILTERS);
  const [adjustTarget, setAdjustTarget] =
    useState<InventoryWithProduct | null>(null);

  const qc = useQueryClient();

  const params: ListInventoryParams = useMemo(
    () => ({
      page,
      size: PAGE_SIZE,
      search: filters.search || undefined,
      location: filters.location || undefined,
      low_stock_only: filters.lowStockOnly || undefined,
      out_of_stock_only: filters.outOfStockOnly || undefined,
    }),
    [page, filters],
  );

  const { data, isFetching } = useAdminInventory(params);

  const handleFiltersChange = (next: InventoryFilterValues) => {
    setFilters(next);
    setPage(1);
  };

  const handleRefresh = () => {
    qc.invalidateQueries({ queryKey: inventoryKeys.all });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Inventory</h1>
          <p className="text-sm text-muted-foreground">
            Track stock across all locations and resolve low-stock alerts.
          </p>
        </div>
        <Button variant="outline" onClick={handleRefresh}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* KPIs */}
      <InventoryKpis />

      {/* Alerts + Reorder */}
      <div className="grid gap-6 lg:grid-cols-2">
        <InventoryAlertsCard />
        <ReorderSuggestionsCard />
      </div>

      {/* Filters + Table */}
      <div className="space-y-4">
        <InventoryFilters values={filters} onChange={handleFiltersChange} />

        <InventoryTable params={params} onAdjust={setAdjustTarget} />

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Page {data.page} of {data.pages} · {data.total} rows
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1 || isFetching}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= data.pages || isFetching}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Adjust dialog */}
      <InventoryAdjustDialog
        item={adjustTarget}
        onClose={() => setAdjustTarget(null)}
      />
    </div>
  );
}
