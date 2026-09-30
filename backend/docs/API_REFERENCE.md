# 📘 Shopify Cart — API Reference

**Version:** 0.1.0
**Base URL (local):** `http://127.0.0.1:8000`
**Base URL (production):** `https://api.yourdomain.com`

Full-featured shopping cart backend with **ML-powered product auto-categorization**.

---

## 📑 Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [Categories (Public)](#3-categories-public)
4. [Products (Public)](#4-products-public)
5. [Admin: Products](#5-admin-products)
6. [Inventory](#6-inventory)
7. [Cart](#7-cart)
8. [Orders](#8-orders)
9. [Admin: Orders](#9-admin-orders)
10. [Admin: Analytics](#10-admin-analytics)
11. [Admin: Inventory Alerts & Reorder](#11-admin-inventory-alerts--reorder)
12. [ML Predict](#12-ml-predict)
13. [Health & Readiness](#13-health--readiness)
14. [Error Format & Codes](#14-error-format--codes)
15. [Frontend Recipes](#15-frontend-recipes)

---

## 1. Overview

### 1.1 Base URL & Prefix

All endpoints (except `/health` and `/ready`) are prefixed with `/api/v1`.

| Environment | Full base URL |
|-------------|---------------|
| Local | `http://127.0.0.1:8000/api/v1` |
| Staging | `https://staging-api.yourdomain.com/api/v1` |
| Production | `https://api.yourdomain.com/api/v1` |

### 1.2 Authentication

The API uses **JWT Bearer tokens**.

- **Access token** — 15 minutes (default) — used on every protected request
- **Refresh token** — 7 days (default) — used only on `POST /auth/refresh`

**How to send the token:**

```
Authorization: Bearer <access_token>
```

### 1.3 Standard Headers

| Header | Value | When |
|--------|-------|------|
| `Content-Type` | `application/json` | All JSON requests |
| `Content-Type` | `multipart/form-data` | File uploads (predict, upload) |
| `Authorization` | `Bearer <token>` | Authenticated endpoints |
| `X-Request-ID` | (optional, e.g. UUID) | Client-supplied trace ID |

### 1.4 Standard Response Headers

Every response includes:

| Header | Meaning |
|--------|---------|
| `X-Request-ID` | Unique per-request ID (echoed or generated). Log this for debugging. |
| `X-Process-Time-Ms` | Server-side processing time in milliseconds |

### 1.5 Pagination Envelope

All list endpoints return this shape:

```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5
}
```

**Query parameters (any list endpoint):**

| Param | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `page` | int | 1 | ≥ 1 | 1-based page number |
| `size` | int | 20 | 1–100 | Items per page |

---

## 2. Authentication

### 2.1 Register

**`POST /auth/register`** — Public

Create a new user account.

**Request body:**

```json
{
  "email": "alice@example.com",
  "password": "supersecret1",
  "full_name": "Alice Doe"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `email` | string (email) | ✅ | Valid email, unique |
| `password` | string | ✅ | Length 8–128 |
| `full_name` | string \| null | ❌ | Max 255 chars |

**Response — 201 Created:**

```json
{
  "id": 1,
  "email": "alice@example.com",
  "full_name": "Alice Doe",
  "is_active": true,
  "is_admin": false,
  "created_at": "2026-09-30T10:00:00Z",
  "updated_at": "2026-09-30T10:00:00Z"
}
```

**Errors:**

| Status | Error code | Cause |
|--------|-----------|-------|
| 409 | `conflict` | Email already registered |
| 422 | `validation_error` | Invalid email format, weak password |

**Example (JavaScript):**

```javascript
const res = await fetch(`${BASE}/auth/register`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    email: "alice@example.com",
    password: "supersecret1",
    full_name: "Alice Doe",
  }),
});
const user = await res.json();
```

---

### 2.2 Login

**`POST /auth/login`** — Public

**Request body:**

```json
{
  "email": "alice@example.com",
  "password": "supersecret1"
}
```

**Response — 200 OK:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

| Field | Type | Meaning |
|-------|------|---------|
| `access_token` | string | JWT — send in `Authorization: Bearer <token>` |
| `refresh_token` | string | JWT — only for `POST /auth/refresh` |
| `token_type` | string | Always `"bearer"` |
| `expires_in` | int | Access token TTL in seconds (900 = 15 min) |

**Errors:**

| Status | Error code | Cause |
|--------|-----------|-------|
| 401 | `auth_error` | Wrong email or password |
| 401 | `auth_error` | Account disabled |

**⚠️ Security note for frontend:** Never log tokens. Store access token in memory or sessionStorage; refresh token in httpOnly cookie if possible (or secure storage for mobile).

---

### 2.3 Refresh Token

**`POST /auth/refresh?token=<refresh_token>`** — Public

Exchange a refresh token for a fresh token pair.

**Query params:**

| Param | Type | Required |
|-------|------|----------|
| `token` | string | ✅ |

**Response — 200 OK:** (same shape as login)

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors:**

| Status | Error code | Cause |
|--------|-----------|-------|
| 401 | `auth_error` | Invalid/expired refresh token |
| 401 | `auth_error` | Passed an access token instead of refresh |

---

### 2.4 Current User

**`GET /auth/me`** — 🔐 Authenticated

**Response — 200 OK:**

```json
{
  "id": 1,
  "email": "alice@example.com",
  "full_name": "Alice Doe",
  "is_active": true,
  "is_admin": false,
  "created_at": "2026-09-30T10:00:00Z",
  "updated_at": "2026-09-30T10:00:00Z"
}
```

**Errors:**

| Status | Error code | Cause |
|--------|-----------|-------|
| 401 | `auth_error` | Missing / invalid / expired token |

---

## 3. Categories (Public)

### 3.1 List Categories

**`GET /categories`** — Public

**Query params:** standard pagination (`page`, `size`).

**Response — 200 OK:**

```json
{
  "items": [
    {
      "id": 1,
      "name": "Clothing",
      "slug": "clothing",
      "parent_id": null,
      "created_at": "2026-09-30T10:00:00Z",
      "updated_at": "2026-09-30T10:00:00Z"
    }
  ],
  "total": 14,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

---

### 3.2 Category Tree

**`GET /categories/tree`** — Public

Returns nested hierarchy — **use this for a category nav sidebar.**

**Response — 200 OK:**

```json
[
  {
    "id": 1,
    "name": "Clothing",
    "slug": "clothing",
    "parent_id": null,
    "children": [
      {
        "id": 4,
        "name": "Shirt",
        "slug": "shirt",
        "parent_id": 1,
        "children": []
      },
      {
        "id": 5,
        "name": "Trouser",
        "slug": "trouser",
        "parent_id": 1,
        "children": []
      }
    ]
  },
  {
    "id": 2,
    "name": "Footwear",
    "slug": "footwear",
    "parent_id": null,
    "children": [ ... ]
  }
]
```

---

### 3.3 Category Detail

**`GET /categories/{category_id}`** — Public

**Path params:**

| Param | Type | Required |
|-------|------|----------|
| `category_id` | int | ✅ |

**Response — 200 OK:** single category object.

**Errors:** 404 `not_found`.

---

## 4. Products (Public)

### 4.1 List Products

**`GET /products`** — Public

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Pagination |
| `size` | int | 20 | 1–100 |
| `category_id` | int \| null | — | Filter by category |
| `q` | string \| null | — | Search in name/SKU (max 100 chars) |
| `active_only` | bool | true | Only show `is_active=true` products |

**Response — 200 OK:**

```json
{
  "items": [
    {
      "id": 42,
      "name": "Blue Shirt",
      "sku": "SHIRT-001",
      "description": "Classic fit, cotton",
      "price": "19.99",
      "category_id": 4,
      "image_url": "/static/uploads/abc123.jpg",
      "is_active": true,
      "created_at": "2026-09-30T10:00:00Z",
      "updated_at": "2026-09-30T10:00:00Z"
    }
  ],
  "total": 250,
  "page": 1,
  "size": 20,
  "pages": 13
}
```

**⚠️ Money fields are STRINGS.** `"price": "19.99"` — parse with `parseFloat` for display, or better: keep as string and format on the client with the currency library.

---

### 4.2 Product Detail (with Stock)

**`GET /products/{product_id}`** — Public

**Response — 200 OK:**

```json
{
  "id": 42,
  "name": "Blue Shirt",
  "sku": "SHIRT-001",
  "description": "Classic fit, cotton",
  "price": "19.99",
  "category_id": 4,
  "image_url": "/static/uploads/abc123.jpg",
  "is_active": true,
  "created_at": "2026-09-30T10:00:00Z",
  "updated_at": "2026-09-30T10:00:00Z",
  "total_quantity": 87
}
```

**`total_quantity`** = sum of stock across all locations — **use this to disable "Add to Cart" when 0**.

**Errors:** 404 `not_found`.

---

## 5. Admin: Products

**🔐 All endpoints in this section require `is_admin=true`.**

### 5.1 Create Product (Manual)

**`POST /admin/products`** — 🔐 Admin

**Request body:**

```json
{
  "name": "Blue Shirt",
  "sku": "SHIRT-001",
  "description": "Classic fit",
  "price": "19.99",
  "category_id": 4,
  "image_url": "/static/uploads/abc123.jpg",
  "is_active": true
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | ✅ | 1–255 chars |
| `sku` | string | ✅ | 1–64 chars, unique |
| `description` | string \| null | ❌ | Max 10,000 chars |
| `price` | string (Decimal) | ✅ | > 0, ≤ 99,999,999.99, 2 decimals |
| `category_id` | int \| null | ❌ | Must exist |
| `image_url` | string \| null | ❌ | Max 512 chars |
| `is_active` | bool | ❌ | Default `true` |

**Response — 201 Created:** ProductRead object.

**Errors:**

| Status | Error code | Cause |
|--------|-----------|-------|
| 401 | `auth_error` | Not authenticated |
| 403 | `permission_denied` | Not admin |
| 409 | `conflict` | SKU already exists |
| 422 | `validation_error` | Invalid price/category |

---

### 5.2 Update Product

**`PUT /admin/products/{product_id}`** — 🔐 Admin

All fields optional (partial update):

```json
{
  "name": "Updated Name",
  "price": "24.99",
  "is_active": false
}
```

**Response — 200 OK:** Updated ProductRead.

---

### 5.3 Delete Product

**`DELETE /admin/products/{product_id}?hard=false`** — 🔐 Admin

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `hard` | bool | false | `false` = soft delete (`is_active=false`); `true` = permanent |

**Response — 204 No Content**

---

### 5.4 🎯 UPLOAD + AUTO-CATEGORIZE (Core Feature)

**`POST /admin/products/upload`** — 🔐 Admin

**⚠️ Uses `multipart/form-data`, NOT JSON.**

**Form fields:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `image` | file | ✅* | JPEG / PNG / WebP, ≤ 10 MB |
| `name` | string | ✅ | 1–255 chars |
| `price` | string | ✅ | Decimal as string, e.g. `"19.99"` |
| `sku` | string \| null | ❌ | Max 64 chars, unique |
| `description` | string \| null | ❌ | Max 10,000 chars |
| `image_url` | string \| null | ❌ | Max 512 chars |
| `location` | string | ❌ | Default `"default"`, max 80 chars |
| `initial_quantity` | int | ❌ | Default 0, ≥ 0 |
| `low_stock_threshold` | int | ❌ | Default 5, ≥ 0 |
| `force_category_slug` | string \| null | ❌ | Admin override (e.g. `"shirt"`) |

*either `image` file OR `image_url` required

**Two possible responses:**

#### Response A — Auto-categorized (confidence ≥ threshold):

**200 OK**

```json
{
  "status": "created",
  "product_id": 42,
  "name": "Blue Shirt",
  "sku": "SHIR-ABC123",
  "price": "19.99",
  "category_id": 4,
  "category_slug": "shirt",
  "category_name": "Shirt",
  "image_url": "/static/uploads/abc123.jpg",
  "confidence": 0.9234,
  "ml_category": "Shirt",
  "message": "Product created and categorized."
}
```

**Frontend action:** Show success → redirect to product detail.

---

#### Response B — Needs Review (confidence < threshold):

**200 OK**

```json
{
  "status": "needs_review",
  "confidence": 0.52,
  "threshold": 0.70,
  "ml_category": "Accessories",
  "suggestions": [
    { "category": "Accessories", "confidence": 0.52 },
    { "category": "Personal_Care", "confidence": 0.31 },
    { "category": "Apparel", "confidence": 0.17 }
  ],
  "message": "Top prediction 'Accessories' has confidence 0.52 < threshold 0.70. Please confirm or override."
}
```

**Frontend action:** Show suggestion UI. Admin picks a category → **resubmit** with `force_category_slug=<chosen_slug>`.

**⚠️ Note:** `status` field discriminates the two responses. Always check `response.status` first.

**Errors:**

| Status | Error code | Cause |
|--------|-----------|-------|
| 401 | `auth_error` | Not authenticated |
| 403 | `permission_denied` | Not admin |
| 409 | `conflict` | SKU already exists |
| 422 | `validation_error` | Bad content-type, empty file, invalid price, category not found |
| 503 | `ml_model_error` | ML model not loaded / MLflow unreachable |

**Example (JavaScript):**

```javascript
const form = new FormData();
form.append("image", fileInput.files[0]);
form.append("name", "Blue Shirt");
form.append("price", "19.99");
form.append("initial_quantity", "10");

const res = await fetch(`${BASE}/admin/products/upload`, {
  method: "POST",
  headers: { Authorization: `Bearer ${accessToken}` },
  body: form,
});
const data = await res.json();

if (data.status === "created") {
  // Success — show product
} else if (data.status === "needs_review") {
  // Show suggestion picker; on confirm, resubmit with:
  form.append("force_category_slug", chosenSlug);
  const res2 = await fetch(`${BASE}/admin/products/upload`, { ... });
}
```

---

## 6. Inventory

### 6.1 List Inventory for Product

**`GET /inventory/product/{product_id}`** — Public

**Response — 200 OK:**

```json
[
  {
    "id": 100,
    "product_id": 42,
    "location": "default",
    "quantity": 87,
    "low_stock_threshold": 5,
    "created_at": "2026-09-30T10:00:00Z",
    "updated_at": "2026-09-30T10:00:00Z",
    "is_low_stock": false
  }
]
```

Multiple rows possible if multiple locations exist.

---

### 6.2 Adjust Inventory

**`PATCH /inventory/{inventory_id}/adjust`** — 🔐 Admin

**Request body:**

```json
{
  "delta": 50,
  "reason": "restock"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `delta` | int | ✅ | Positive adds stock, negative removes |
| `reason` | string \| null | ❌ | Max 255 chars |

**Response — 200 OK:** Updated InventoryRead.

**Errors:**

| Status | Error code | Cause |
|--------|-----------|-------|
| 400 | `inventory_error` | Would result in negative stock |
| 404 | `not_found` | Inventory ID doesn't exist |

**⚠️ Side effect:** When stock crosses below `low_stock_threshold`, an `inventory.low` Kafka event fires → creates an alert entry.

---

## 7. Cart

**🔐 All cart endpoints require authentication. One active cart per user.**

### 7.1 Get Current Cart

**`GET /cart`** — 🔐 Auth

**Response — 200 OK:**

```json
{
  "id": 1,
  "user_id": 1,
  "items": [
    {
      "id": 501,
      "product_id": 42,
      "quantity": 2,
      "unit_price": "19.99",
      "subtotal": "39.98",
      "created_at": "2026-09-30T10:00:00Z",
      "updated_at": "2026-09-30T10:00:00Z"
    }
  ],
  "item_count": 1,
  "total_quantity": 2,
  "total_amount": "39.98",
  "created_at": "2026-09-30T09:55:00Z",
  "updated_at": "2026-09-30T10:00:00Z"
}
```

**Notes:**
- `item_count` = number of distinct line items
- `total_quantity` = sum of all quantities
- `total_amount` = sum of subtotals
- Cart is auto-created on first access if missing

---

### 7.2 Add Item

**`POST /cart/items`** — 🔐 Auth

**Request body:**

```json
{
  "product_id": 42,
  "quantity": 2
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `product_id` | int | ✅ | Must exist & active |
| `quantity` | int | ✅ | 1–999 |

**Response — 200 OK:** Updated `CartRead`.

**Behavior:**
- If item already in cart → **quantity is incremented** (not replaced)
- Stock is validated against total available (`Inventory.quantity` sum)

**Errors:**

| Status | Error code | Cause |
|--------|-----------|-------|
| 400 | `cart_error` | quantity ≤ 0 |
| 400 | `inventory_error` | Requested qty > available |
| 404 | `not_found` | Product not found / inactive |

---

### 7.3 Update Item

**`PATCH /cart/items/{item_id}`** — 🔐 Auth

**Request body:**

```json
{
  "quantity": 5
}
```

**Quantity = 0 → removes the item** (same as DELETE).

**Response — 200 OK:** Updated `CartRead`.

**Errors:**

| Status | Error code | Cause |
|--------|-----------|-------|
| 400 | `inventory_error` | New quantity > available |
| 404 | `not_found` | Item not in your cart |

---

### 7.4 Remove Item

**`DELETE /cart/items/{item_id}`** — 🔐 Auth

**Response — 200 OK:** Updated `CartRead`.

---

### 7.5 Clear Cart

**`DELETE /cart`** — 🔐 Auth

**Response — 200 OK:** Empty `CartRead`.

---

## 8. Orders

### 8.1 Checkout

**`POST /orders/checkout`** — 🔐 Auth

**⚠️ This is an atomic transaction — either everything succeeds or nothing does.**

**Request body:**

```json
{
  "shipping_address": "123 Main St, Dhaka 1205",
  "notes": "Please deliver after 6 PM"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `shipping_address` | string | ✅ | 5–500 chars |
| `notes` | string \| null | ❌ | Max 1,000 chars |

**Response — 201 Created:**

```json
{
  "id": 1001,
  "user_id": 1,
  "status": "pending",
  "total_amount": "39.98",
  "shipping_address": "123 Main St, Dhaka 1205",
  "notes": "Please deliver after 6 PM",
  "items": [
    {
      "id": 2001,
      "product_id": 42,
      "product_name": "Blue Shirt",
      "product_sku": "SHIRT-001",
      "quantity": 2,
      "unit_price": "19.99",
      "subtotal": "39.98"
    }
  ],
  "item_count": 1,
  "created_at": "2026-09-30T10:05:00Z",
  "updated_at": "2026-09-30T10:05:00Z"
}
```

**Order lifecycle statuses:** `pending → paid → shipped → delivered` (or `cancelled`).

**Side effects:**
- Inventory **decremented** for every item
- Cart **cleared**
- Kafka events: `order.placed`, `inventory.changed` (per item)
- Analytics consumer updates `daily_sales`

**Errors:**

| Status | Error code | Cause |
|--------|-----------|-------|
| 400 | `inventory_error` | Insufficient stock at checkout time |
| 422 | `validation_error` | Empty cart, invalid address |

---

### 8.2 List My Orders

**`GET /orders`** — 🔐 Auth

Returns newest-first array (no pagination — usually small).

**Response — 200 OK:** `OrderRead[]`.

---

### 8.3 Order Detail

**`GET /orders/{order_id}`** — 🔐 Auth

Users see only their own orders (admins see all).

**Errors:** 404 `not_found` (if not owner and not admin — deliberate, doesn't leak existence).

---

### 8.4 Cancel Order

**`POST /orders/{order_id}/cancel`** — 🔐 Auth

**Request body:**

```json
{
  "reason": "changed mind"
}
```

Allowed only in `pending` or `paid` status.

**Side effects:**
- Inventory **restored**
- Kafka event: `order.cancelled`

**Errors:**

| Status | Error code | Cause |
|--------|-----------|-------|
| 404 | `not_found` | Order not yours |
| 409 | `conflict` | Order already shipped/delivered/cancelled |

---

## 9. Admin: Orders

**🔐 Admin only.**

### 9.1 List All Orders

**`GET /admin/orders`** — 🔐 Admin

**Query params:**

| Param | Type | Default |
|-------|------|---------|
| `page`, `size` | int | standard |
| `status` | enum | — | `pending` \| `paid` \| `shipped` \| `delivered` \| `cancelled` |

**Response — 200 OK:** `Page[OrderRead]`.

---

### 9.2 Change Order Status

**`PATCH /admin/orders/{order_id}/status`** — 🔐 Admin

**Request body:**

```json
{
  "status": "paid",
  "reason": "payment received"
}
```

**Allowed transitions:**

| From | To |
|------|-----|
| pending | paid, cancelled |
| paid | shipped, cancelled |
| shipped | delivered |
| delivered | (none) |
| cancelled | (none) |

**Errors:** 409 `conflict` if illegal transition.

---

## 10. Admin: Analytics

**🔐 Admin only.**

### 10.1 Daily Sales

**`GET /admin/analytics/sales`** — 🔐 Admin

**Query params:**

| Param | Type | Description |
|-------|------|-------------|
| `page`, `size` | int | Standard pagination |
| `day` | date \| null | Filter by date (`YYYY-MM-DD`) |

**Response — 200 OK:**

```json
{
  "items": [
    {
      "id": 1,
      "sales_date": "2026-09-30",
      "product_id": 42,
      "quantity": 15,
      "revenue": "299.85",
      "order_count": 8
    }
  ],
  "total": 1, "page": 1, "size": 20, "pages": 1
}
```

**Notes:** Updated by the Kafka consumer from `order.placed` events. Numbers aggregate per `(date, product)`.

---

## 11. Admin: Inventory Alerts & Reorder

**🔐 Admin only.**

### 11.1 List Alerts

**`GET /admin/inventory/alerts`** — 🔐 Admin

**Query params:**

| Param | Type | Default |
|-------|------|---------|
| `page`, `size` | int | standard |
| `unresolved_only` | bool | `true` |

**Response — 200 OK:**

```json
{
  "items": [
    {
      "id": 7,
      "product_id": 42,
      "location": "default",
      "quantity": 3,
      "threshold": 5,
      "resolved_at": null,
      "created_at": "2026-09-30T10:00:00Z"
    }
  ],
  "total": 1, "page": 1, "size": 20, "pages": 1
}
```

---

### 11.2 Resolve Alert

**`POST /admin/inventory/alerts/{alert_id}/resolve`** — 🔐 Admin

No body required. **Idempotent.**

**Response — 200 OK:** Updated alert with `resolved_at` timestamp.

**Errors:** 404 `not_found`.

---

### 11.3 Reorder Suggestions

**`GET /admin/inventory/reorder-suggestions`** — 🔐 Admin

**Query params:**

| Param | Type | Default | Range |
|-------|------|---------|-------|
| `low_stock_only` | bool | `true` | — |
| `lookback_days` | int | 30 | 1–365 |
| `limit` | int | 100 | 1–500 |

**Response — 200 OK:**

```json
{
  "items": [
    {
      "product_id": 42,
      "sku": "SHIRT-001",
      "name": "Blue Shirt",
      "location": "default",
      "current_quantity": 3,
      "low_stock_threshold": 5,
      "avg_daily_demand": 1.5,
      "lookback_days": 30,
      "lead_time_days": 7,
      "safety_multiplier": 1.5,
      "target_stock": 16,
      "suggested_reorder_qty": 13,
      "reason": "low stock (3 <= 5); avg 1.50/day over 30d"
    }
  ],
  "total": 1
}
```

**How to interpret:**
- `suggested_reorder_qty` = how many units to order
- `reason` = human-readable explanation for UI

---

## 12. ML Predict

### 12.1 Predict Category

**`POST /predict?top_k=3`** — Public

**⚠️ Uses `multipart/form-data`.**

**Query params:**

| Param | Type | Default | Range |
|-------|------|---------|-------|
| `top_k` | int | 3 | 1–10 |

**Form field:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `image` | file | ✅ | JPEG / PNG / WebP, ≤ 10 MB |

**Response — 200 OK:**

```json
{
  "category": "Footwear",
  "confidence": 0.9234,
  "top_k": [
    { "category": "Footwear", "category_index": 2, "confidence": 0.9234 },
    { "category": "Apparel", "category_index": 1, "confidence": 0.0521 },
    { "category": "Accessories", "category_index": 0, "confidence": 0.0187 }
  ],
  "model_name": "shopify-category-classifier",
  "model_version": "1",
  "model_stage": "Production",
  "cached": false,
  "inference_ms": 47.3
}
```

**Errors:**

| Status | Error code | Cause |
|--------|-----------|-------|
| 422 | `validation_error` | Wrong content-type / empty file / too large |
| 503 | `ml_model_error` | Model not loaded / MLflow unreachable |

---

### 12.2 Reset Prediction Cache

**`POST /predict/reset-cache`** — Public (dev helper)

**Response — 204 No Content**

---

## 13. Health & Readiness

### 13.1 Health (Liveness)

**`GET /health`** — Public

**Response — 200 OK:**

```json
{
  "status": "ok",
  "app": "Shopify Cart",
  "env": "production",
  "version": "0.1.0",
  "components": {
    "db": "ok",
    "kafka": "ok",
    "predictor": "ok"
  }
}
```

**Frontend use:** Show system status indicator. `components.*` values are `"ok"` or `"error"`.

---

### 13.2 Readiness

**`GET /ready`** — Public

**Response — 200 OK:**

```json
{ "status": "ready" }
```

**Response — 503 Service Unavailable:**

```json
{ "status": "not_ready", "reason": "db_unavailable" }
```

**Frontend use:** Do NOT call from user-facing code — this is for load balancers.

---

### 13.3 DB Health

**`GET /health/db`** — Public

```json
{ "status": "ok", "database": "connected" }
```

---

### 13.4 Kafka Health

**`GET /health/kafka`** — Public

```json
{ "status": "ok", "kafka": "connected", "bootstrap": "kafka:29092" }
```

---

## 14. Error Format & Codes

**Every error response has this shape:**

```json
{
  "error": "not_found",
  "status": 404,
  "detail": "Product 42 not found.",
  "path": "/api/v1/products/42"
}
```

Validation errors add an `extra` field:

```json
{
  "error": "validation_error",
  "status": 422,
  "detail": "Request validation failed.",
  "path": "/api/v1/auth/register",
  "extra": [
    { "loc": ["body", "email"], "msg": "Invalid email", "type": "value_error" }
  ]
}
```

### Complete Error Code Table

| HTTP | `error` | Meaning | Frontend action |
|------|---------|---------|-----------------|
| 400 | `cart_error` | Cart operation invalid | Show detail |
| 400 | `inventory_error` | Stock problem | Show detail ("Only N available") |
| 401 | `auth_error` | Auth failed / expired | Redirect to login |
| 403 | `permission_denied` | Not admin | Show "Access denied" |
| 404 | `not_found` | Resource missing | Show 404 page |
| 409 | `conflict` | Duplicate / illegal state | Show detail |
| 422 | `validation_error` | Request body invalid | Highlight fields |
| 500 | `internal_error` | Server error | Show generic error |
| 503 | `ml_model_error` | ML unavailable | Show retry UI |

---

## 15. Frontend Recipes

### 15.1 Auth Flow (Recommended)

```
┌──────────────────────────────────────────────────────────────┐
│ 1. On app load: check sessionStorage for access_token       │
│ 2. If present, call GET /auth/me to validate                │
│ 3. If 401, attempt POST /auth/refresh?token=<refresh_token> │
│ 4. If refresh fails, redirect to login                      │
└──────────────────────────────────────────────────────────────┘
```

**JavaScript helper:**

```javascript
class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.accessToken = sessionStorage.getItem("access_token");
    this.refreshToken = sessionStorage.getItem("refresh_token");
  }

  async request(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    if (this.accessToken) {
      headers["Authorization"] = `Bearer ${this.accessToken}`;
    }

    let res = await fetch(`${this.baseUrl}${path}`, { ...options, headers });

    // Auto-refresh on 401
    if (res.status === 401 && this.refreshToken) {
      const refreshed = await this.tryRefresh();
      if (refreshed) {
        headers["Authorization"] = `Bearer ${this.accessToken}`;
        res = await fetch(`${this.baseUrl}${path}`, { ...options, headers });
      }
    }
    return res;
  }

  async tryRefresh() {
    const res = await fetch(
      `${this.baseUrl}/auth/refresh?token=${this.refreshToken}`,
      { method: "POST" }
    );
    if (!res.ok) return false;
    const data = await res.json();
    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
    sessionStorage.setItem("access_token", data.access_token);
    sessionStorage.setItem("refresh_token", data.refresh_token);
    return true;
  }

  async login(email, password) {
    const res = await fetch(`${this.baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw new Error((await res.json()).detail);
    const data = await res.json();
    this.accessToken = data.access_token;
    this.refreshToken = data.refresh_token;
    sessionStorage.setItem("access_token", data.access_token);
    sessionStorage.setItem("refresh_token", data.refresh_token);
  }

  async me() {
    const res = await this.request("/auth/me");
    return res.json();
  }
}
```

---

### 15.2 Cart State (Optimistic Updates)

Cart responses return the **full updated cart** — use this to sync state:

```javascript
async function addToCart(productId, quantity) {
  const res = await api.request("/cart/items", {
    method: "POST",
    body: JSON.stringify({ product_id: productId, quantity }),
  });
  if (!res.ok) {
    const err = await res.json();
    if (err.error === "inventory_error") {
      showToast(err.detail, "warning");
      return;
    }
    throw new Error(err.detail);
  }
  const cart = await res.json();
  updateCartUI(cart);          // full cart state from server
  updateBadge(cart.item_count); // header badge
}
```

---

### 15.3 Image Upload (Auto-Categorization)

```javascript
async function uploadProduct(file, name, price) {
  const form = new FormData();
  form.append("image", file);
  form.append("name", name);
  form.append("price", price);
  form.append("initial_quantity", "10");

  const res = await api.request("/admin/products/upload", {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail);
  }

  const data = await res.json();

  if (data.status === "created") {
    return { created: true, product: data };
  }

  // needs_review: show suggestion picker
  return {
    created: false,
    confidence: data.confidence,
    suggestions: data.suggestions,
    resubmit: async (chosenSlug) => {
      form.append("force_category_slug", chosenSlug);
      const res2 = await api.request("/admin/products/upload", {
        method: "POST",
        body: form,
      });
      return res2.json();
    },
  };
}
```

---

### 15.4 Pagination

```javascript
async function listProducts({ page = 1, size = 20, categoryId, q } = {}) {
  const params = new URLSearchParams({ page, size });
  if (categoryId) params.set("category_id", categoryId);
  if (q) params.set("q", q);

  const res = await api.request(`/products?${params}`);
  const page_data = await res.json();
  return {
    items: page_data.items,
    hasNext: page_data.page < page_data.pages,
    hasPrev: page_data.page > 1,
    total: page_data.total,
  };
}
```

---

### 15.5 Money Handling

**⚠️ Never do `parseFloat(price) * quantity` for cart totals.** Server returns `subtotal` and `total_amount` — trust those.

**For display:**

```javascript
function formatMoney(amountString, currency = "USD") {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(parseFloat(amountString));
}

formatMoney("19.99");  // "$19.99"
```

---

### 15.6 Admin Guard

```javascript
async function requireAdmin() {
  const user = await api.me();
  if (!user.is_admin) {
    window.location.href = "/403";
    return null;
  }
  return user;
}
```

---

## Appendix A: Full Endpoint Quick List

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/auth/register` | — | Create account |
| POST | `/auth/login` | — | Get tokens |
| POST | `/auth/refresh` | — | Rotate tokens |
| GET | `/auth/me` | 🔐 | Current user |
| GET | `/categories` | — | List categories |
| GET | `/categories/tree` | — | Category hierarchy |
| GET | `/categories/{id}` | — | Category detail |
| GET | `/products` | — | List products |
| GET | `/products/{id}` | — | Product detail + stock |
| POST | `/admin/products` | 🔐 Admin | Create product |
| PUT | `/admin/products/{id}` | 🔐 Admin | Update product |
| DELETE | `/admin/products/{id}` | 🔐 Admin | Delete product |
| POST | `/admin/products/upload` | 🔐 Admin | 🎯 Upload + auto-classify |
| GET | `/inventory/product/{id}` | — | Stock for product |
| PATCH | `/inventory/{id}/adjust` | 🔐 Admin | Adjust stock |
| GET | `/cart` | 🔐 | Get cart |
| POST | `/cart/items` | 🔐 | Add item |
| PATCH | `/cart/items/{id}` | 🔐 | Update qty |
| DELETE | `/cart/items/{id}` | 🔐 | Remove item |
| DELETE | `/cart` | 🔐 | Clear cart |
| POST | `/orders/checkout` | 🔐 | Place order |
| GET | `/orders` | 🔐 | My orders |
| GET | `/orders/{id}` | 🔐 | Order detail |
| POST | `/orders/{id}/cancel` | 🔐 | Cancel order |
| GET | `/admin/orders` | 🔐 Admin | All orders |
| PATCH | `/admin/orders/{id}/status` | 🔐 Admin | Change status |
| GET | `/admin/analytics/sales` | 🔐 Admin | Daily sales |
| GET | `/admin/inventory/alerts` | 🔐 Admin | Alerts list |
| POST | `/admin/inventory/alerts/{id}/resolve` | 🔐 Admin | Resolve alert |
| GET | `/admin/inventory/reorder-suggestions` | 🔐 Admin | Reorder qty |
| POST | `/predict?top_k=3` | — | Classify image |
| POST | `/predict/reset-cache` | — | Clear cache |
| GET | `/health` | — | Liveness |
| GET | `/ready` | — | Readiness |
| GET | `/health/db` | — | DB health |
| GET | `/health/kafka` | — | Kafka health |

---

## Appendix B: Data Models Cheat Sheet

### User
```typescript
interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string; // ISO 8601
  updated_at: string;
}
```

### Category
```typescript
interface Category {
  id: number;
  name: string;
  slug: string;        // [a-z0-9-]+
  parent_id: number | null;
  created_at: string;
  updated_at: string;
}
```

### Product
```typescript
interface Product {
  id: number;
  name: string;
  sku: string;
  description: string | null;
  price: string;       // Decimal as string
  category_id: number | null;
  image_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  total_quantity?: number; // only on detail endpoint
}
```

### CartItem
```typescript
interface CartItem {
  id: number;
  product_id: number;
  quantity: number;
  unit_price: string;  // Decimal
  subtotal: string;    // Decimal
  created_at: string;
  updated_at: string;
}
```

### Cart
```typescript
interface Cart {
  id: number;
  user_id: number;
  items: CartItem[];
  item_count: number;
  total_quantity: number;
  total_amount: string; // Decimal
  created_at: string;
  updated_at: string;
}
```

### Order
```typescript
interface Order {
  id: number;
  user_id: number;
  status: "pending" | "paid" | "shipped" | "delivered" | "cancelled";
  total_amount: string;
  shipping_address: string;
  notes: string | null;
  items: OrderItem[];
  item_count: number;
  created_at: string;
  updated_at: string;
}
```

### OrderItem
```typescript
interface OrderItem {
  id: number;
  product_id: number | null;  // null if product was hard-deleted
  product_name: string;       // snapshot
  product_sku: string;        // snapshot
  quantity: number;
  unit_price: string;         // snapshot
  subtotal: string;
}
```

### InventoryAlert
```typescript
interface InventoryAlert {
  id: number;
  product_id: number;
  location: string;
  quantity: number;
  threshold: number;
  resolved_at: string | null;
  created_at: string;
}
```

### Prediction
```typescript
interface Prediction {
  category: string;
  confidence: number;      // 0..1
  top_k: Array<{
    category: string;
    category_index: number;
    confidence: number;
  }>;
  model_name: string;
  model_version: string | null;
  model_stage: string | null;
  cached: boolean;
  inference_ms: number;
}
```

### Paginated
```typescript
interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
```

---

## Appendix C: Project Goal Recap

This backend powers a **full shopping cart system** with:

1. **Customers** can:
   - Register / login / refresh tokens
   - Browse products (filter by category, search by name/SKU)
   - Add to cart, adjust quantities, remove items
   - Checkout with shipping address
   - View order history
   - Cancel pending orders

2. **Admins** can:
   - Create / update / delete products
   - **Upload an image → ML auto-categorizes it** (the differentiator)
   - Adjust inventory, view low-stock alerts
   - Get ML-based reorder suggestions
   - View daily sales analytics
   - Manage order statuses

3. **Machine Learning**:
   - ResNet-18 trained on NVIDIA Shopify catalogue
   - Served via `/predict` and `/admin/products/upload`
   - Confidence threshold gates auto-assignment vs human review
   - All training runs tracked in MLflow

4. **Events** flow through Kafka:
   - `product.created`, `product.updated`, `product.deleted`
   - `cart.updated`, `cart.item_added`, `cart.item_removed`, `cart.cleared`
   - `order.placed`, `order.cancelled`
   - `inventory.changed`, `inventory.low`

**Frontend must support both customer and admin flows** to fully realize the project.

---
