/**
 * API types — mirrors docs/API_REFERENCE.md.
 * Keep in sync with backend Pydantic schemas.
 */

// ───── Common ─────
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  error: string;
  status: number;
  detail: string;
  path: string;
  extra?: unknown;
}

// ───── Auth ─────
export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string | null;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

// ───── Category ─────
export interface Category {
  id: number;
  name: string;
  slug: string;
  parent_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface CategoryTreeNode extends Category {
  children: CategoryTreeNode[];
}

// ───── Product ─────
export interface Product {
  id: number;
  name: string;
  sku: string;
  description: string | null;
  price: string; // Decimal as string
  category_id: number | null;
  image_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductWithStock extends Product {
  total_quantity: number;
}

export interface ProductCreatePayload {
  name: string;
  sku: string;
  description?: string | null;
  price: string;
  category_id?: number | null;
  image_url?: string | null;
  is_active?: boolean;
}

export interface ProductUpdatePayload extends Partial<ProductCreatePayload> {}

// ───── Admin Upload / Auto-categorize ─────
export interface TopSuggestion {
  category: string;
  confidence: number;
}

export interface ProductCreatedResponse {
  status: "created";
  product_id: number;
  name: string;
  sku: string;
  price: string;
  category_id: number;
  category_slug: string;
  category_name: string;
  image_url: string | null;
  confidence: number | null;
  ml_category: string | null;
  message: string;
}

export interface NeedsReviewResponse {
  status: "needs_review";
  confidence: number;
  threshold: number;
  ml_category: string;
  suggestions: TopSuggestion[];
  message: string;
}

export type AutoCategorizeResponse =
  | ProductCreatedResponse
  | NeedsReviewResponse;

// ───── Inventory ─────
export interface InventoryItem {
  id: number;
  product_id: number;
  location: string;
  quantity: number;
  low_stock_threshold: number;
  created_at: string;
  updated_at: string;
  is_low_stock: boolean;
}

export interface InventoryAdjustPayload {
  delta: number;
  reason?: string | null;
}

// ───── Cart ─────
export interface CartItem {
  id: number;
  product_id: number;
  quantity: number;
  unit_price: string;
  subtotal: string;
  created_at: string;
  updated_at: string;
}

export interface Cart {
  id: number;
  user_id: number;
  items: CartItem[];
  item_count: number;
  total_quantity: number;
  total_amount: string;
  created_at: string;
  updated_at: string;
}

export interface CartItemAddPayload {
  product_id: number;
  quantity: number;
}

export interface CartItemUpdatePayload {
  quantity: number; // 0 = remove
}

// ───── Orders ─────
export type OrderStatus =
  | "pending"
  | "paid"
  | "shipped"
  | "delivered"
  | "cancelled";

export interface OrderItem {
  id: number;
  product_id: number | null;
  product_name: string;
  product_sku: string;
  quantity: number;
  unit_price: string;
  subtotal: string;
}

export interface Order {
  id: number;
  user_id: number;
  status: OrderStatus;
  total_amount: string;
  shipping_address: string;
  notes: string | null;
  items: OrderItem[];
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface CheckoutPayload {
  shipping_address: string;
  notes?: string | null;
}

export interface OrderCancelPayload {
  reason?: string | null;
}

export interface OrderStatusUpdatePayload {
  status: OrderStatus;
  reason?: string | null;
}

// ───── Analytics ─────
export interface DailySales {
  id: number;
  sales_date: string; // YYYY-MM-DD
  product_id: number;
  quantity: number;
  revenue: string;
  order_count: number;
}

export interface InventoryAlert {
  id: number;
  product_id: number;
  location: string;
  quantity: number;
  threshold: number;
  resolved_at: string | null;
  created_at: string;
}

export interface ReorderSuggestion {
  product_id: number;
  sku: string;
  name: string;
  location: string;
  current_quantity: number;
  low_stock_threshold: number;
  avg_daily_demand: number;
  lookback_days: number;
  lead_time_days: number;
  safety_multiplier: number;
  target_stock: number;
  suggested_reorder_qty: number;
  reason: string;
}

export interface ReorderListResponse {
  items: ReorderSuggestion[];
  total: number;
}

// ───── ML Predict ─────
export interface PredictionItem {
  category: string;
  category_index: number;
  confidence: number;
}

export interface PredictionResponse {
  category: string;
  confidence: number;
  top_k: PredictionItem[];
  model_name: string;
  model_version: string | null;
  model_stage: string | null;
  cached: boolean;
  inference_ms: number;
}

// ───── Health ─────
export interface HealthResponse {
  status: string;
  app: string;
  env: string;
  version: string;
  components?: Record<string, string>;
}

// ───── Cart  ─────
export interface CartItemProductSnapshot {
  id: number;
  name: string;
  sku: string;
  price: string; // Decimal as string
  image_url: string | null;
  is_active: boolean;
}

export interface CartItemWithProduct extends CartItem {
  product: CartItemProductSnapshot;
}

export interface CartWithProducts {
  id: number;
  user_id: number;
  items: CartItemWithProduct[];
  item_count: number;
  total_quantity: number;
  total_amount: string;
  created_at: string;
  updated_at: string;
}
