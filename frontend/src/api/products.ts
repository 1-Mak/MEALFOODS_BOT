import { apiFetch } from "./client";
import type { Product } from "../types";

export async function getProducts(counterpartyGuid: string): Promise<Product[]> {
  return apiFetch<Product[]>(`/api/products/?counterparty_guid=${counterpartyGuid}`);
}
