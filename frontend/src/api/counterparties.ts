import { apiFetch } from "./client";
import type { DeliveryPoint } from "../types";

export async function getDeliveryPoints(
  counterpartyGuid: string,
): Promise<DeliveryPoint[]> {
  return apiFetch<DeliveryPoint[]>(
    `/api/counterparties/${counterpartyGuid}/delivery-points`,
  );
}
