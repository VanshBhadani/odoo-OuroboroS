export interface User { id: string; email: string; name: string; role: string; }
export interface Product { id: string; sku: string; name: string; category: string; uom: string; stock_quantity?: number; min_stock_alert?: number; is_active?: boolean; }
export interface OperationLine { id: string; product_id: string; quantity: number; source_location_id: string; dest_location_id: string; }
export interface Operation { id: string; reference: string; operation_type: 'RECEIPT' | 'DELIVERY' | 'INTERNAL' | 'ADJUSTMENT'; status: 'DRAFT' | 'WAITING' | 'READY' | 'DONE' | 'CANCELED'; partner_name?: string; notes?: string; source_location_id?: string; dest_location_id?: string; created_by_id?: string; created_at: string; updated_at?: string; validated_at?: string; lines: OperationLine[]; }
export interface Move { id: string; reference: string; product_name: string; quantity: number; from_location_code: string; to_location_code: string; created_at: string; user_name: string; }
export interface Location { id: string; name: string; code: string; location_type: 'INTERNAL' | 'VENDOR' | 'CUSTOMER' | 'INVENTORY_LOSS'; warehouse_id?: string; }
export interface PaginatedOperations { total: number; page: number; page_size: number; items: Operation[]; }
