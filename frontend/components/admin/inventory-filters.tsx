"use client";

import { Search, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export interface InventoryFilterValues {
  search: string;
  location: string;
  lowStockOnly: boolean;
  outOfStockOnly: boolean;
}

interface Props {
  values: InventoryFilterValues;
  onChange: (next: InventoryFilterValues) => void;
  className?: string;
}

const DEFAULTS: InventoryFilterValues = {
  search: "",
  location: "",
  lowStockOnly: false,
  outOfStockOnly: false,
};

export function InventoryFilters({ values, onChange, className }: Props) {
  const [searchInput, setSearchInput] = useState(values.search);

  const hasActive =
    values.search !== "" ||
    values.location !== "" ||
    values.lowStockOnly ||
    values.outOfStockOnly;

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onChange({ ...values, search: searchInput.trim() });
  };

  const clearAll = () => {
    setSearchInput("");
    onChange(DEFAULTS);
  };

  return (
    <div className={cn("space-y-3 rounded-lg border bg-muted/20 p-4", className)}>
      <form onSubmit={submitSearch} className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by SKU or name…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-8"
          />
        </div>
        <Button type="submit" variant="outline">
          Search
        </Button>
        {hasActive && (
          <Button type="button" variant="ghost" onClick={clearAll}>
            <X className="mr-1 h-4 w-4" />
            Clear
          </Button>
        )}
      </form>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="filter-low-stock"
            checked={values.lowStockOnly}
            onChange={(e) =>
              onChange({ ...values, lowStockOnly: e.target.checked })
            }
            className="h-4 w-4 rounded border-gray-300 text-primary"
          />
          <Label htmlFor="filter-low-stock" className="cursor-pointer text-sm">
            Low stock only
          </Label>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="filter-oos"
            checked={values.outOfStockOnly}
            onChange={(e) =>
              onChange({ ...values, outOfStockOnly: e.target.checked })
            }
            className="h-4 w-4 rounded border-gray-300 text-primary"
          />
          <Label htmlFor="filter-oos" className="cursor-pointer text-sm">
            Out of stock only
          </Label>
        </div>

        <div className="flex items-center gap-2">
          <Label htmlFor="filter-location" className="text-sm text-muted-foreground">
            Location:
          </Label>
          <Input
            id="filter-location"
            value={values.location}
            onChange={(e) => onChange({ ...values, location: e.target.value })}
            placeholder="all"
            className="h-8 w-32"
          />
        </div>
      </div>
    </div>
  );
}
