export interface Counterparty {
  e4_guid: string;
  name: string;
}

export interface DeliveryPoint {
  e4_guid: string;
  counterparty_guid: string;
  address: string;
}

export interface Product {
  e4_guid: string;
  name: string;
  unit: string;
  box_multiplicity: number;
  net_weight: number;
  gross_weight: number;
  price: number;
  vat_rate: number;
}

export interface AuthResponse {
  token: string;
  user_id: number;
  counterparties: Counterparty[];
}

export interface OrderItem {
  id: number;
  product_guid: string;
  product_name: string;
  quantity: number;
  price: number;
  box_multiplicity: number;
  net_weight: number;
  gross_weight: number;
}

export interface Order {
  id: number;
  e4_guid: string | null;
  counterparty_guid: string;
  delivery_point_guid: string;
  delivery_date: string;
  status: string;
  stage: string;
  total_price: number;
  created_at: string;
  items: OrderItem[];
}
