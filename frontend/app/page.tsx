import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ThemeToggle } from "@/components/layout/theme-toggle";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container flex h-16 items-center justify-between px-4">
          <h1 className="text-xl font-semibold">Shopify Cart</h1>
          <ThemeToggle />
        </div>
      </header>

      <section className="container mx-auto max-w-4xl px-4 py-20 text-center">
        <h2 className="text-5xl font-bold tracking-tight">
          Shop Smarter. Sell Faster.
        </h2>
        <p className="mt-4 text-lg text-muted-foreground">
          Shopping cart with ML-powered product auto-categorization.
        </p>

        <div className="mt-10 flex justify-center gap-3">
          <Button size="lg">
            <Link href="/products">Browse Products</Link>
          </Button>
          <Button size="lg" variant="outline">
            <Link href="/login">Sign In</Link>
          </Button>
        </div>

        <div className="mt-16 grid gap-6 md:grid-cols-3">
          {[
            { title: "ML Auto-categorize", desc: "Upload a photo, get category suggestions." },
            { title: "Fast Checkout", desc: "Atomic transactions, real-time stock." },
            { title: "Admin Analytics", desc: "Daily sales, low-stock alerts, reorder." },
          ].map((f) => (
            <Card key={f.title}>
              <CardHeader>
                <CardTitle>{f.title}</CardTitle>
                <CardDescription>{f.desc}</CardDescription>
              </CardHeader>
              <CardContent />
            </Card>
          ))}
        </div>
      </section>
    </main>
  );
}
