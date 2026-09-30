# Shopify Cart 🛒
![CI](https://github.com/touhid9xx/shopify-cart/actions/workflows/ci.yml/badge.svg)

A full-stack e-commerce backend with an **ML-powered product auto-categorizer**.
Admin uploads a product photo → a PyTorch classifier predicts the category → the
product is auto-routed to the right inventory.

## Tech Stack
- **API:** FastAPI + Uvicorn, Pydantic v2
- **DB:** MySQL 8 + SQLAlchemy 2.0 + Alembic
- **Auth:** JWT (HS256) + Argon2
- **Events:** Kafka (aiokafka)
- **ML:** PyTorch 2.6 (cu118), torchvision, HuggingFace datasets, MLflow, Optuna
- **UI:** Streamlit (customer + admin)
- **Ops:** Docker, GitHub Actions, Ruff, Mypy (strict), Pytest, Structlog

## Quick Start
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn shopify_cart.main:app --reload
