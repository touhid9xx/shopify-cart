from __future__ import annotations

from fastapi import APIRouter

from shopify_cart.api.v1 import (
    admin_analytics,
    admin_inventory,
    admin_ml_insights,
    admin_orders,
    admin_products,
    auth,
    cart,
    categories,
    inventory,
    orders,
    predict,
    products,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(products.router)
api_router.include_router(admin_products.router)
api_router.include_router(inventory.router)
api_router.include_router(cart.router)
api_router.include_router(orders.router)
api_router.include_router(admin_orders.router)
api_router.include_router(admin_analytics.router)
api_router.include_router(admin_inventory.router)
api_router.include_router(admin_ml_insights.router)
api_router.include_router(predict.router)

__all__ = ["api_router"]
