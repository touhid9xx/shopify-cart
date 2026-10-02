import Link from "next/link";
import {
  BarChart3,
  Package,
  ShoppingCart,
  Sparkles,
  TrendingUp,
  Upload,
} from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

export default function DashboardPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Admin dashboard</h1>
        <p className="mt-2 text-muted-foreground">
          Manage products, inventory, orders, and analytics.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <DashboardCard
          icon={<Upload className="h-6 w-6" />}
          title="Upload product"
          description="Upload an image — the ML classifier auto-assigns the category."
          href="/dashboard/products/new"
          cta="Upload"
        />
        <DashboardCard
          icon={<Package className="h-6 w-6" />}
          title="Products"
          description="Browse, edit, and manage your product catalog."
          href="/dashboard/products"
          cta="Manage"
        />
        <DashboardCard
          icon={<ShoppingCart className="h-6 w-6" />}
          title="Orders"
          description="View customer orders and update their status."
          href="/dashboard/orders"
          cta="View orders"
        />
        <DashboardCard
          icon={<TrendingUp className="h-6 w-6" />}
          title="Inventory"
          description="Monitor stock levels and reorder suggestions."
          href="/dashboard/inventory"
          cta="Monitor"
        />
        <DashboardCard
          icon={<BarChart3 className="h-6 w-6" />}
          title="Analytics"
          description="Sales trends, daily revenue, and product performance."
          href="/dashboard/analytics"
          cta="View analytics"
        />
        <DashboardCard
          icon={<Sparkles className="h-6 w-6" />}
          title="ML insights"
          description="Model performance, prediction history, and tuning runs."
          href="/dashboard/ml"
          cta="View ML"
        />
      </div>
    </div>
  );
}

function DashboardCard({
  icon,
  title,
  description,
  href,
  cta,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  href: string;
  cta: string;
}) {
  return (
    <Card className="flex flex-col">
      <CardHeader>
        <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </div>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="mt-auto">
        <Link
          href={href}
          className={cn(buttonVariants({ variant: "outline" }), "w-full")}
        >
          {cta}
        </Link>
      </CardContent>
    </Card>
  );
}
