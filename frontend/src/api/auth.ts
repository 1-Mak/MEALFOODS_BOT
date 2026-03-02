import { apiFetch, setToken } from "./client";
import type { AuthResponse } from "../types";

export async function authenticate(): Promise<AuthResponse> {
  const webapp = (window as any).WebApp;
  const initData: string = webapp?.initData || "";

  let data: AuthResponse;

  if (initData) {
    // Production: validate initData from MAX Bridge
    data = await apiFetch<AuthResponse>("/api/auth/validate", {
      method: "POST",
      body: JSON.stringify({ init_data: initData }),
    });
  } else {
    // Dev mode: auth with test user
    data = await apiFetch<AuthResponse>("/api/auth/dev", {
      method: "POST",
    });
  }

  setToken(data.token);
  return data;
}
