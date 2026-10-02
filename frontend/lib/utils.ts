import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind classes with conditional logic.
 * Standard shadcn helper — uses clsx for conditionals and
 * tailwind-merge to deduplicate conflicting classes.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Resolve an image URL to an absolute one pointing at the backend.
 * Handles:
 *   - null / undefined → null
 *   - already-absolute URLs (http:// or https://) → unchanged
 *   - relative paths (/static/uploads/foo.jpg) → prefixed with backend
 */
export function resolveImageUrl(
  url: string | null | undefined,
): string | null {
  if (!url) return null;

  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }

  const backendUrl =
    process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

  const path = url.startsWith("/") ? url : `/${url}`;
  return `${backendUrl}${path}`;
}
