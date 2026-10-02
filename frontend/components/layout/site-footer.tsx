import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t bg-muted/30">
      <div className="container mx-auto px-4 py-10">
        <div className="grid gap-8 md:grid-cols-4">
          <div className="md:col-span-2">
            <h3 className="text-lg font-semibold">Shopify Cart</h3>
            <p className="mt-2 max-w-md text-sm text-muted-foreground">
              Smart shopping, powered by ML auto-categorization. A portfolio
              project built with FastAPI, Next.js, Kafka, and PyTorch.
            </p>
          </div>

          <div>
            <h4 className="mb-3 text-sm font-semibold">Shop</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link href="/products" className="hover:text-foreground">
                  All products
                </Link>
              </li>
              <li>
                <Link href="/cart" className="hover:text-foreground">
                  Cart
                </Link>
              </li>
              <li>
                <Link href="/orders" className="hover:text-foreground">
                  Orders
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="mb-3 text-sm font-semibold">Account</h4>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link href="/login" className="hover:text-foreground">
                  Sign in
                </Link>
              </li>
              <li>
                <Link href="/register" className="hover:text-foreground">
                  Register
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 border-t pt-6 text-center text-xs text-muted-foreground">
          © {new Date().getFullYear()} Shopify Cart · Built with Next.js,
          FastAPI, and PyTorch
        </div>
      </div>
    </footer>
  );
}
