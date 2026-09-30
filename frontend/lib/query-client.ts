import { QueryClient } from "@tanstack/react-query";

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,           // 30s — cart/products refetch cadence
        gcTime: 5 * 60_000,          // 5 min garbage collection
        retry: (failureCount, error) => {
          // Don't retry auth / validation
          if (typeof error === "object" && error !== null && "status" in error) {
            const status = (error as { status: number }).status;
            if (status === 401 || status === 403 || status === 422) return false;
          }
          return failureCount < 2;
        },
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}
