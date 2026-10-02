import { SiteHeader } from "@/components/layout/site-header";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main className="flex-1 bg-muted/20">{children}</main>
    </div>
  );
}
