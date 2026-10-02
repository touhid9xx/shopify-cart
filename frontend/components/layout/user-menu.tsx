"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LayoutDashboard, LogOut, User as UserIcon } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

import { useAuth } from "@/lib/auth-context";

export function UserMenu() {
  const router = useRouter();
  const { user, isAuthenticated, isAdmin, logout } = useAuth();

  if (!isAuthenticated) {
    return (
      <Link href="/login" className={cn(buttonVariants({ size: "sm" }))}>
        Sign in
      </Link>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(buttonVariants({ variant: "ghost", size: "icon" }))}
        aria-label="Account"
      >
        <UserIcon className="h-5 w-5" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="truncate">
            {user?.email}
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />

        <DropdownMenuItem onClick={() => router.push("/orders")}>
          My orders
        </DropdownMenuItem>

        {isAdmin && (
          <DropdownMenuItem onClick={() => router.push("/dashboard")}>
            <LayoutDashboard className="mr-2 h-4 w-4" />
            Admin dashboard
          </DropdownMenuItem>
        )}

        <DropdownMenuSeparator />

        <DropdownMenuItem onClick={logout}>
          <LogOut className="mr-2 h-4 w-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
