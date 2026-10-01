// product-filters.tsx

"use client";

import { useState } from "react";
import { Search, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { useCategoryTree } from "@/hooks/use-categories";

// ──────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────
interface CategoryNode {
  id: number;
  name: string;
  children?: CategoryNode[];
}

interface Props {
  categoryId: number | null;
  query: string;
  onCategoryChange: (id: number | null) => void;
  onQueryChange: (q: string) => void;
}

// ──────────────────────────────────────────────────────────────
// Flatten category tree into a list of { id, name, depth }
// ──────────────────────────────────────────────────────────────
function flattenCategories(
  nodes: CategoryNode[],
  depth = 0,
  parentPath = "",
): { id: number; name: string; depth: number; path: string }[] {
  const result: { id: number; name: string; depth: number; path: string }[] = [];
  for (const node of nodes) {
    const path = parentPath ? `${parentPath}-${node.id}` : String(node.id);
    result.push({ id: node.id, name: node.name, depth, path });
    if (node.children?.length) {
      result.push(...flattenCategories(node.children, depth + 1, path));
    }
  }
  return result;
}

// ──────────────────────────────────────────────────────────────
// ProductFilters
// ──────────────────────────────────────────────────────────────
export function ProductFilters({
  categoryId,
  query,
  onCategoryChange,
  onQueryChange,
}: Props) {
  const { data: tree } = useCategoryTree();
  const [inputValue, setInputValue] = useState(query);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onQueryChange(inputValue.trim());
  };

  // Flatten once — no more nested maps
  const flatCategories = tree ? flattenCategories(tree) : [];

  return (
    <div className="flex flex-col gap-3 md:flex-row md:items-center">
      <form onSubmit={handleSearch} className="flex flex-1 items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Search products..."
            className="pl-9"
          />
          {inputValue && (
            <button
              type="button"
              onClick={() => {
                setInputValue("");
                onQueryChange("");
              }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <Button type="submit">Search</Button>
      </form>

      <Select
        value={categoryId ? String(categoryId) : "all"}
        onValueChange={(v) => onCategoryChange(v === "all" ? null : Number(v))}
      >
        <SelectTrigger className="w-full md:w-64">
          <SelectValue placeholder="All categories" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All categories</SelectItem>
          {flatCategories.map((cat) => (
            <SelectItem key={`cat-${cat.path}`} value={String(cat.id)}>
              {"\u00A0".repeat(cat.depth * 2)}
              {cat.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
