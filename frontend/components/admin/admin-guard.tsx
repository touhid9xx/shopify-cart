"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { useAuth } from "@/lib/auth-context";

interface Props {
  children: React.ReactNode;
}

/**
 * Client-side gate for admin-only routes.
 *
 * Flow:
 *   - while auth is loading → full-page loader
 *   - not authenticated → redirect /login?next=/dashboard
 *   - authenticated but not admin → redirect /
 *   - otherwise → render children
 *
 * ⚠️ Client-side guard is NOT a security boundary. Backend must
 * also enforce admin RBAC on all admin endpoints (it does).
 */
export function AdminGuard({ children }: Props) {
  const router = useRouter();
  const { isAuthenticated, isAdmin, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated) {
      router.replace("/login?next=/dashboard");
    } else if (!isAdmin) {
      router.replace("/");
    }
  }, [isAuthenticated, isAdmin, isLoading, router]);

  // Loading state
  if (isLoading) return <FullPageLoader />;

  // Not authorized (redirect in-flight)
  if (!isAuthenticated || !isAdmin) return <FullPageLoader />;

  return <>{children}</>;
}

function FullPageLoader() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin" />
        <p className="text-sm">Loading admin…</p>
      </div>
    </div>
  );
}
