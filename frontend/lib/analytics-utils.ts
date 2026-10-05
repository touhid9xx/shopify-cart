import type {
  AnalyticsSummary,
  DailySalesRead,
  TimeSeriesPoint,
  TopProduct,
} from "@/lib/api-types";

// ══════════════════════════════════════════════════════════════
// Summary KPIs
// ══════════════════════════════════════════════════════════════
export function computeSummary(rows: DailySalesRead[]): AnalyticsSummary {
  let total_revenue = 0;
  let total_orders = 0;
  let total_units = 0;
  const products = new Set<number>();
  const days = new Set<string>();

  for (const row of rows) {
    total_revenue += Number(row.revenue);
    total_orders += row.order_count;
    total_units += row.quantity;
    products.add(row.product_id);
    days.add(row.sales_date);
  }

  return {
    total_revenue,
    total_orders,
    total_units,
    avg_order_value: total_orders > 0 ? total_revenue / total_orders : 0,
    distinct_products: products.size,
    day_count: days.size,
  };
}

// ══════════════════════════════════════════════════════════════
// Time series (group by date)
// ══════════════════════════════════════════════════════════════
export function computeTimeSeries(
  rows: DailySalesRead[],
  maxDays = 30,
): TimeSeriesPoint[] {
  const byDate = new Map<string, TimeSeriesPoint>();

  for (const row of rows) {
    const existing = byDate.get(row.sales_date);
    if (existing) {
      existing.revenue += Number(row.revenue);
      existing.quantity += row.quantity;
      existing.orders += row.order_count;
    } else {
      byDate.set(row.sales_date, {
        date: row.sales_date,
        revenue: Number(row.revenue),
        quantity: row.quantity,
        orders: row.order_count,
      });
    }
  }

  return Array.from(byDate.values())
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(-maxDays);
}

// ══════════════════════════════════════════════════════════════
// Top products (group by product_id)
// ══════════════════════════════════════════════════════════════
export function computeTopProducts(
  rows: DailySalesRead[],
  limit = 10,
): TopProduct[] {
  const byProduct = new Map<number, TopProduct>();

  for (const row of rows) {
    const existing = byProduct.get(row.product_id);
    if (existing) {
      existing.revenue += Number(row.revenue);
      existing.quantity += row.quantity;
      existing.orders += row.order_count;
    } else {
      byProduct.set(row.product_id, {
        product_id: row.product_id,
        revenue: Number(row.revenue),
        quantity: row.quantity,
        orders: row.order_count,
      });
    }
  }

  return Array.from(byProduct.values())
    .sort((a, b) => b.revenue - a.revenue)
    .slice(0, limit);
}

// ══════════════════════════════════════════════════════════════
// Formatters
// ══════════════════════════════════════════════════════════════
export function fmtCurrency(n: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
}

export function fmtNumber(n: number): string {
  return new Intl.NumberFormat().format(n);
}

export function fmtDate(iso: string): string {
  // ISO date "2026-10-05" → "Oct 5"
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  const dt = new Date(y, m - 1, d);
  return dt.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
