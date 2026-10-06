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
import type { ConfidenceBucket } from "@/lib/api-types";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

interface Props {
  buckets: ConfidenceBucket[];
  isLoading: boolean;
}

export function MlConfidenceChart({ buckets, isLoading }: Props) {
  const data: ChartData<"bar"> = {
    labels: buckets.map((b) => b.range_label),
    datasets: [
      {
        label: "Products",
        data: buckets.map((b) => b.count),
        backgroundColor: buckets.map((b) => {
          const mid = (b.range_min + b.range_max) / 2;
          if (mid >= 0.85) return "rgba(16, 185, 129, 0.75)";   // green
          if (mid >= 0.75) return "rgba(59, 130, 246, 0.75)";   // blue
          if (mid >= 0.70) return "rgba(245, 158, 11, 0.75)";   // amber
          return "rgba(239, 68, 68, 0.75)";                     // red
        }),
        borderColor: buckets.map((b) => {
          const mid = (b.range_min + b.range_max) / 2;
          if (mid >= 0.85) return "rgb(16, 185, 129)";
          if (mid >= 0.75) return "rgb(59, 130, 246)";
          if (mid >= 0.70) return "rgb(245, 158, 11)";
          return "rgb(239, 68, 68)";
        }),
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
          label: (ctx) => `${ctx.parsed.y} products`,
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { precision: 0 },
      },
      x: {
        grid: { display: false },
      },
    },
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Confidence Distribution</CardTitle>
        <CardDescription>
          Model confidence across all ML-predicted products. Green = high trust.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : buckets.length === 0 ? (
          <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
            No confidence data.
          </div>
        ) : (
          <div className="h-64">
            <Bar data={data} options={options} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
