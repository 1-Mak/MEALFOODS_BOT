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
