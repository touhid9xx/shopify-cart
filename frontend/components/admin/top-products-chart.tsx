"use client";

import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Title,
  Tooltip,
  type ChartData,
  type ChartOptions,
} from "chart.js";
import { Bar } from "react-chartjs-2";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fmtCurrency } from "@/lib/analytics-utils";
import type { TopProduct } from "@/lib/api-types";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
);

interface Props {
  products: TopProduct[];
  isLoading: boolean;
}

export function TopProductsChart({ products, isLoading }: Props) {
  const data: ChartData<"bar"> = {
    labels: products.map((p) => `#${p.product_id}`),
    datasets: [
      {
        label: "Revenue",
        data: products.map((p) => p.revenue),
        backgroundColor: "rgba(16, 185, 129, 0.7)",
        borderColor: "rgb(16, 185, 129)",
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  };

  const options: ChartOptions<"bar"> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => `Revenue: ${fmtCurrency(ctx.parsed.y ?? 0)}`,
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: (v) => fmtCurrency(Number(v)),
        },
      },
      x: {
        grid: { display: false },
      },
    },
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Top Products by Revenue</CardTitle>
        <CardDescription>Top 10 products over the period.</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-72 w-full" />
        ) : products.length === 0 ? (
          <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
            No product sales data available.
          </div>
        ) : (
          <div className="h-72">
            <Bar data={data} options={options} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
