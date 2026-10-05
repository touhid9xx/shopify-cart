"use client";

import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  type ChartData,
  type ChartOptions,
} from "chart.js";
import { Line } from "react-chartjs-2";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fmtCurrency, fmtDate } from "@/lib/analytics-utils";
import type { TimeSeriesPoint } from "@/lib/api-types";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
);

interface Props {
  points: TimeSeriesPoint[];
  isLoading: boolean;
}

export function SalesTrendChart({ points, isLoading }: Props) {
  const data: ChartData<"line"> = {
    labels: points.map((p) => fmtDate(p.date)),
    datasets: [
      {
        label: "Revenue",
        data: points.map((p) => p.revenue),
        borderColor: "rgb(59, 130, 246)",
        backgroundColor: "rgba(59, 130, 246, 0.1)",
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 5,
      },
    ],
  };

  const options: ChartOptions<"line"> = {
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
        <CardTitle className="text-lg">Revenue Trend</CardTitle>
        <CardDescription>Last 30 days of sales revenue.</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-72 w-full" />
        ) : points.length === 0 ? (
          <EmptyChart message="No sales data available." />
        ) : (
          <div className="h-72">
            <Line data={data} options={options} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex h-72 items-center justify-center text-sm text-muted-foreground">
      {message}
    </div>
  );
}
