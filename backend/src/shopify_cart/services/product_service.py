"""Product business logic — CRUD + Kafka events."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from shopify_cart.exceptions import ConflictError, NotFoundError, ValidationError
from shopify_cart.kafka.events import (
    ProductCreatedEvent,
    ProductDeletedEvent,
    ProductUpdatedEvent,
)
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.logging_config import get_logger
from shopify_cart.models.category import Category
from shopify_cart.models.inventory import Inventory
from shopify_cart.models.product import Product
from shopify_cart.schemas.product import ProductCreate, ProductUpdate

logger = get_logger(__name__)


class ProductService:
    """Stateless — pass Session + producer per call."""

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    @staticmethod
    def get_by_id(db: Session, product_id: int) -> Product:
        product = db.get(Product, product_id)
        if product is None:
            raise NotFoundError(f"Product {product_id} not found.")
        return product

    @staticmethod
    def get_by_sku(db: Session, sku: str) -> Product | None:
        return db.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none()

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------
    @staticmethod
    async def create(
        db: Session,
        producer: KafkaProducer,
        payload: ProductCreate,
    ) -> Product:
        # Validate SKU uniqueness
        if ProductService.get_by_sku(db, payload.sku) is not None:
            raise ConflictError(f"A product with SKU {payload.sku!r} already exists.")

        # Validate category if provided
        if payload.category_id is not None:
            cat = db.get(Category, payload.category_id)
            if cat is None:
                raise ValidationError(f"Category {payload.category_id} not found.")

        product = Product(
            name=payload.name,
            sku=payload.sku,
            description=payload.description,
            price=payload.price,
            category_id=payload.category_id,
            image_url=payload.image_url,
            is_active=payload.is_active,
        )
        db.add(product)
        db.flush()  # assigns id without committing

        # Auto-create default inventory row
        inv = Inventory(
            product_id=product.id,
            location="default",
            quantity=0,
            low_stock_threshold=5,
        )
        db.add(inv)

        db.commit()
        db.refresh(product)

        # Publish event AFTER commit — if Kafka fails, DB stays consistent.
        event = ProductCreatedEvent(
            product_id=product.id,
            name=product.name,
            sku=product.sku,
            category_id=product.category_id,
            price=product.price,
        )
        await producer.publish("product.created", event, key=str(product.id))

        logger.info("product_created", product_id=product.id, sku=product.sku)
        return product

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    @staticmethod
    async def update(
        db: Session,
        producer: KafkaProducer,
        product_id: int,
        payload: ProductUpdate,
    ) -> Product:
        product = ProductService.get_by_id(db, product_id)
        changed: list[str] = []

        data = payload.model_dump(exclude_unset=True)

        # SKU uniqueness check if SKU is being changed
        new_sku = data.get("sku")
        if new_sku is not None and new_sku != product.sku:
            existing = ProductService.get_by_sku(db, new_sku)
            if existing is not None:
                raise ConflictError(f"A product with SKU {new_sku!r} already exists.")

        # Category validation if provided
        if "category_id" in data and data["category_id"] is not None:
            cat = db.get(Category, data["category_id"])
            if cat is None:
                raise ValidationError(f"Category {data['category_id']} not found.")

        for field, value in data.items():
            if getattr(product, field) != value:
                setattr(product, field, value)
                changed.append(field)

        if not changed:
            return product

        db.commit()
        db.refresh(product)

        event = ProductUpdatedEvent(
            product_id=product.id,
            changed_fields=changed,
        )
        await producer.publish("product.updated", event, key=str(product.id))

        logger.info("product_updated", product_id=product.id, changed=changed)
        return product

    # ------------------------------------------------------------------
    # Delete (soft by default)
    # ------------------------------------------------------------------
    @staticmethod
    async def delete(
        db: Session,
        producer: KafkaProducer,
        product_id: int,
        *,
        hard: bool = False,
    ) -> None:
        """Soft-delete by default (marks inactive, preserves order history).

        `hard=True` permanently deletes the row. It will fail with
        IntegrityError if the product appears in any order_items, because
        order_items.product_id has ondelete="RESTRICT". Only use for
        products with zero order history (test cleanup, etc.).
        """
        product = ProductService.get_by_id(db, product_id)

        if hard:
            db.delete(product)
        else:
            product.is_active = False

        db.commit()

        event = ProductDeletedEvent(product_id=product_id)
        await producer.publish("product.deleted", event, key=str(product_id))

        logger.info("product_deleted", product_id=product_id, hard=hard)

    # ------------------------------------------------------------------
    # Stock aggregation helper
    # ------------------------------------------------------------------
    @staticmethod
    def total_quantity(db: Session, product_id: int) -> int:
        rows = (
            db.execute(select(Inventory.quantity).where(Inventory.product_id == product_id))
            .scalars()
            .all()
        )
        return int(sum(rows))

    # ------------------------------------------------------------------
    # Update product image (from uploaded file bytes)
    # ------------------------------------------------------------------
    @staticmethod
    async def update_image(
        db: Session,
        producer: KafkaProducer,
        product_id: int,
        *,
        image_bytes: bytes,
        content_type: str,
    ) -> Product:
        """
        Replace a product's image with an uploaded file.

        Saves the file to data/uploads/, updates product.image_url,
        and publishes product.updated.
        """
        from shopify_cart.models.product import Product
        from shopify_cart.services.autocat_service import _save_uploaded_image

        product = db.get(Product, product_id)
        if product is None:
            raise NotFoundError(f"Product {product_id} not found.")

        # Validate content type
        allowed = {"image/jpeg", "image/png", "image/webp"}
        if content_type not in allowed:
            raise ValidationError(
                f"Unsupported content type {content_type!r}. Allowed: {sorted(allowed)}"
            )

        if not image_bytes:
            raise ValidationError("Empty image file uploaded.")

        # Save file (reuse autocat's helper — same storage layout)
        old_url = product.image_url
        new_url = _save_uploaded_image(image_bytes)
        product.image_url = new_url

        db.commit()
        db.refresh(product)

        # Publish update event (best-effort)
        try:
            event = ProductUpdatedEvent(product_id=product.id, changed_fields=["image_url"])
            await producer.publish("product.updated", event, key=str(product.id))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "product_image_update_publish_failed",
                product_id=product.id,
                error=str(exc),
            )

        logger.info(
            "product_image_updated",
            product_id=product.id,
            old_url=old_url,
            new_url=new_url,
        )
        return product
