import { SiteHeader } from "@/components/layout/site-header";
import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { AdminGuard } from "@/components/admin/admin-guard";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <AdminGuard>
        <div className="flex flex-1">
          <AdminSidebar />
          <main className="flex-1 bg-muted/10">{children}</main>
        </div>
      </AdminGuard>
    </div>
  );
}
