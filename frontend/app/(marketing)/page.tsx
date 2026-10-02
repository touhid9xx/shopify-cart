import Link from "next/link";
import { ArrowRight, ShoppingBag, Sparkles, Zap } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ProductGrid } from "@/components/products/product-grid";
import { cn } from "@/lib/utils";
import type { Page, Product } from "@/lib/api-types";

// ──────────────────────────────────────────────────────────────
// Data fetch — server-side
// ──────────────────────────────────────────────────────────────
async function getFeaturedProducts(): Promise<Product[]> {
  const backendUrl =
    process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

  try {
    const res = await fetch(
      `${backendUrl}/api/v1/products?size=8&active_only=true`,
      { next: { revalidate: 60 } },
    );
    if (!res.ok) return [];
    const data = (await res.json()) as Page<Product>;
    return data.items ?? [];
  } catch {
    return [];
  }
}

// ──────────────────────────────────────────────────────────────
// Page
// ──────────────────────────────────────────────────────────────
export default async function LandingPage() {
  const products = await getFeaturedProducts();

  return (
    <>
      {/* ── HERO ── */}
      <section className="relative overflow-hidden border-b bg-gradient-to-b from-background to-muted/30">
        <div className="container mx-auto max-w-4xl px-4 py-20 text-center md:py-28">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border bg-background px-4 py-1.5 text-sm">
            <Sparkles className="h-4 w-4 text-primary" />
            <span>Powered by ML auto-categorization</span>
          </div>

          <h1 className="text-4xl font-bold tracking-tight md:text-6xl">
            Shop Smarter.
            <br />
            <span className="bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
              Sell Faster.
            </span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground md:text-xl">
            Shopping cart with ML-powered product auto-categorization.
            Upload a photo, get category suggestions in seconds.
          </p>

          <div className="mt-10 flex flex-col justify-center gap-3 sm:flex-row">
            <Link
              href="/products"
              className={cn(buttonVariants({ size: "lg" }))}
            >
              Browse Products
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link
              href="/login"
              className={cn(buttonVariants({ size: "lg", variant: "outline" }))}
            >
              Sign In
            </Link>
          </div>
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section className="border-b py-16">
        <div className="container mx-auto px-4">
          <div className="grid gap-6 md:grid-cols-3">
            <Feature
              icon={<Zap className="h-6 w-6" />}
              title="ML Auto-categorize"
              description="Upload a photo, get category suggestions automatically."
            />
            <Feature
              icon={<ShoppingBag className="h-6 w-6" />}
              title="Fast Checkout"
              description="Atomic transactions, real-time stock validation."
            />
            <Feature
              icon={<Sparkles className="h-6 w-6" />}
              title="Admin Analytics"
              description="Daily sales, low-stock alerts, and reorder suggestions."
            />
          </div>
        </div>
      </section>

      {/* ── FEATURED PRODUCTS ── */}
      <section className="py-16">
        <div className="container mx-auto px-4">
          <div className="mb-8 flex items-end justify-between gap-4">
            <div>
              <h2 className="text-3xl font-bold">Featured products</h2>
              <p className="mt-2 text-muted-foreground">
                A glimpse of what&apos;s in our catalog
              </p>
            </div>
            <Link
              href="/products"
              className={cn(
                buttonVariants({ variant: "ghost" }),
                "hidden sm:inline-flex",
              )}
            >
              View all
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </div>

          {products.length === 0 ? (
            <div className="rounded-lg border border-dashed p-12 text-center">
              <p className="text-muted-foreground">
                No products yet. Check back soon!
              </p>
            </div>
          ) : (
            <>
              <ProductGrid products={products} />
              <div className="mt-8 text-center sm:hidden">
                <Link
                  href="/products"
                  className={cn(buttonVariants({ variant: "ghost" }))}
                >
                  View all products
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </div>
            </>
          )}
        </div>
      </section>
    </>
  );
}

// ──────────────────────────────────────────────────────────────
// Helper — Feature card
// ──────────────────────────────────────────────────────────────
function Feature({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </div>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent />
    </Card>
  );
}
