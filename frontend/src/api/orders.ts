import { apiFetch } from "./client";
import type { Order } from "../types";

export interface OrderItemIn {
  product_guid: string;
  quantity: number;
}

export interface OrderCreateIn {
  counterparty_guid: string;
  delivery_point_guid: string;
  delivery_date: string;
  items: OrderItemIn[];
}

export interface OrderUpdateIn {
  delivery_point_guid?: string;
  delivery_date?: string;
  items?: OrderItemIn[];
}

export async function getOrders(counterpartyGuid: string): Promise<Order[]> {
  return apiFetch<Order[]>(`/api/orders/?counterparty_guid=${counterpartyGuid}`);
}

export async function getOrder(orderId: number): Promise<Order> {
  return apiFetch<Order>(`/api/orders/${orderId}`);
}

export async function createOrder(body: OrderCreateIn): Promise<Order> {
  return apiFetch<Order>("/api/orders/", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateOrder(orderId: number, body: OrderUpdateIn): Promise<Order> {
  return apiFetch<Order>(`/api/orders/${orderId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function cancelOrder(orderId: number): Promise<Order> {
  return apiFetch<Order>(`/api/orders/${orderId}/cancel`, {
    method: "POST",
  });
}
