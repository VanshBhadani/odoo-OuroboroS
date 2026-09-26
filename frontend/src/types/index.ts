export interface User { id: string; email: string; name: string; role: string; }
export interface Product { id: string; sku: string; name: string; category: string; uom: string; stock_quantity?: number; }
export interface Operation { id: string; reference: string; operation_type: string; status: string; created_at: string; }
export interface Move { id: string; reference: string; product_name: string; quantity: number; from_location_code: string; to_location_code: string; created_at: string; user_name: string; }
