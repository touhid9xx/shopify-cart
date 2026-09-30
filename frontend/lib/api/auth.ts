import { api, tokenStore } from "./client";
import type {
  LoginPayload,
  RegisterPayload,
  TokenPair,
  User,
} from "@/lib/api-types";

export const authApi = {
  register: (payload: RegisterPayload) =>
    api.post<User>("/auth/register", payload, { skipAuth: true }),

  login: async (payload: LoginPayload): Promise<TokenPair> => {
    const tokens = await api.post<TokenPair>("/auth/login", payload, {
      skipAuth: true,
    });
    tokenStore.set(tokens);
    return tokens;
  },

  refresh: async (refresh: string): Promise<TokenPair> => {
    const tokens = await api.post<TokenPair>(
      `/auth/refresh?token=${encodeURIComponent(refresh)}`,
      undefined,
      { skipAuth: true, skipRefresh: true }
    );
    tokenStore.set(tokens);
    return tokens;
  },

  me: () => api.get<User>("/auth/me"),

  logout: () => {
    tokenStore.clear();
  },
};
