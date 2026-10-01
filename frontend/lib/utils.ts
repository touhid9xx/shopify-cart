export { cn } from "cn"
export function resolveImageUrl(
  url: string | null | undefined,
): string | null {
  if (!url) return null;

  // Already absolute
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }

  const backendUrl =
    process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

  const path = url.startsWith("/") ? url : `/${url}`;
  return `${backendUrl}${path}`;
}
