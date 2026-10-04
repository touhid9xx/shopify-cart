# 🛍️ Shopify Cart

> A production-grade e-commerce backend + frontend with **ML-powered product auto-categorization**, human-in-the-loop review workflow, and full order management.

[![CI](https://github.com/touhid9xx/shopify-cart/actions/workflows/ci.yml/badge.svg)](https://github.com/touhid9xx/shopify-cart/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16.3-black.svg)](https://nextjs.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6-red.svg)](https://pytorch.org/)

---

## ✨ Highlights

- 🤖 **ML auto-categorization** — Admin uploads a product image, a ResNet-18 classifier predicts the category with confidence
- 👀 **Human-in-the-loop review** — Low-confidence predictions land in a review queue; admin can **Approve**, **Reject**, or **Recategorize**
- 🛒 **Full shopping cart** — Browse, add to cart, checkout, place orders (atomic transactions)
- 📦 **Order management** — Admin accepts/rejects/ships orders with audit trail
- 📨 **Event-driven** — Kafka events for product.created, cart.updated, order.placed, inventory.low
- 📊 **Analytics** — Daily sales, low-stock alerts, ML-based reorder suggestions
- 🐳 **Fully containerized** — Docker Compose for one-command deployment
- 🎨 **Modern frontend** — Next.js 16 App Router, TanStack Query v5, shadcn/ui, dark mode

---

## 🏗️ Architecture
CUSTOMER SIDE
        Landing page → Browse → Cart → Checkout → Orders

ADMIN SIDE
        Dashboard → Products → Upload image → ML classify →
        Review Queue → Approve / Reject / Recategorize
        Orders → Accept / Reject / Ship
        Inventory → Alerts → Reorder
BACKEND (FastAPI)
        Auth (JWT), Products, ML Predict
        Cart, Orders, Review

WORKFLOW
        MySQL   Kafka   MLflow
        8.0      7.6     2.19
## 🧠 ML Auto-Categorization — The Differentiator

Admin uploads image
↓
┌─────────────────────────┐
│ ResNet-18 Classifier │
│ (Trained on 3200 imgs) │
│ 4 classes: shirt, │
│ trouser, shoe, bag │
└─────────────────────────┘
↓
Confidence?
│
├── ≥ 0.75 → Map class to Category slug → Create product (PENDING)
│
└── < 0.75 → Return needs_review + top-3 suggestions
↓
Admin review queue
↓
┌───────────────────┼───────────────────┐
│ │ │
Approve Reject Recategorize
│ │ │
publish hide + reason override + publish



**Training stack:** PyTorch 2.6 + CUDA 11.8 (GTX 1060), MLflow tracking, Optuna tuning.

---

## 🛠️ Tech Stack

### Backend
| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 + Uvicorn |
| Validation | Pydantic v2 + pydantic-settings |
| ORM | SQLAlchemy 2.0 (Mapped, mapped_column) |
| Migrations | Alembic |
| Database | MySQL 8 (pymysql) |
| Auth | PyJWT + passlib[argon2] |
| Logging | structlog (JSON in prod, pretty in dev) |
| Events | aiokafka |
| ML | PyTorch 2.6 + torchvision + MLflow + Optuna |
| Quality | Ruff, Mypy (strict), Pytest |

### Frontend
| Layer | Technology |
|---|---|
| Framework | Next.js 16 App Router (React 19) |
| Language | TypeScript (strict) |
| Styling | Tailwind v4 + shadcn/ui (Base UI) |
| State | TanStack Query v5 |
| Forms | React Hook Form + Zod v4 |
| Charts | Chart.js + react-chartjs-2 |
| Theme | next-themes (dark mode) |
| Notifications | Sonner |

### Infra
- Docker + Docker Compose
- GitHub Actions CI
- Pre-commit hooks



## 🚀 Quick Start

### Prerequisites
- Python 3.12
- Node.js 20+ & pnpm 12+
- MySQL 8 (local or Docker)
- (Optional) Docker Desktop

### 1. Clone + setup

git clone https://github.com/touhid9xx/shopify-cart.git
cd shopify-cart

###

cd backend

# Create venv
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install deps
pip install --upgrade pip
pip install -e ".[dev]"

# Configure
Copy-Item .env.example .env
# Edit .env with your MySQL credentials

# Migrate
alembic upgrade head

# Seed categories
python scripts\seed_categories.py

# Run
uvicorn shopify_cart.main:app --reload --host 0.0.0.0 --port 8000

Backend: http://localhost:8000 (docs at /docs)

##  Frontend

cd frontend

# Install deps
pnpm install

# Configure
Copy-Item .env.example .env.local
# Edit .env.local with NEXT_PUBLIC_BACKEND_URL

# Run
pnpm dev

Frontend: http://localhost:3000


cd backend
.\venv\Scripts\Activate.ps1

mlflow server `
  --backend-store-uri sqlite:///mlruns/mlflow.db `
  --default-artifact-root ./mlartifacts `
  --host 127.0.0.1 `
  --port 5000

MLflow UI: http://localhost:5000

## Docker Compose (full stack)
docker compose up -d

##  ML Training

cd backend
.\venv\Scripts\Activate.ps1

# Download + preprocess (once)
python -m shopify_cart.ml.dataset --download --max-per-class 500
python -m shopify_cart.ml.preprocess

## Train

$env:MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
python -m shopify_cart.ml.train --epochs 25 --batch-size 32

Expected: ~20-30 min on GTX 1060, best_val_acc logged in MLflow.

## Register model
python -m shopify_cart.ml.register


## API Endpoints (Summary)


Category	                Endpoints
Public	                    /health, /api/v1/products, /api/v1/categories, /api/v1/products/{id}
Auth	                    POST /auth/register, POST /auth/login, POST /auth/refresh, GET /auth/me
Cart	                    GET/POST/PATCH/DELETE /cart, /cart/items
Orders	                    POST /orders/checkout, GET /orders, POST /orders/{id}/cancel
Admin Products	            CRUD + POST /upload, GET /pending-review, POST /{id}/approve, /reject, /recategorize
Admin Orders	            GET /admin/orders, POST /{id}/accept, /reject, /ship
Admin Inventory	            GET /alerts, POST /alerts/{id}/resolve, GET /reorder-suggestions
Admin Analytics	            GET /sales, GET /alerts
ML	                        POST /predict
Full OpenAPI docs: http://localhost:8000/docs

## Testing

cd backend
.\venv\Scripts\Activate.ps1

# Run all tests
pytest

# With coverage
pytest --cov=shopify_cart --cov-report=html

# Only unit tests (no DB needed)
pytest tests/unit

# Only integration (needs DB)
pytest tests/integration


Feature Matrix                                                  Feature	Status
User registration + JWT auth                                        ✅
Role-based access (customer / admin)                                ✅
Product catalog + search + pagination                               ✅
Category hierarchy (parent/child)                                   ✅
Shopping cart with stock validation                                 ✅
Atomic checkout (cart → order)                                      ✅
Order history + cancellation                                        ✅
Admin product CRUD                                                  ✅
ML auto-categorization on upload                                    ✅
Review queue (approve/reject/recategorize)                          ✅
Admin order management (accept/reject/ship)                         ✅
Inventory tracking + alerts                                         ✅
Reorder suggestions (ML-based)                                      ✅
Sales analytics                                                     ✅
Kafka events                                                        ✅
MLflow tracking                                                     ✅
Docker + Compose                                                    ✅
GitHub Actions CI                                                   ✅



# Design Decisions
### Why human-in-the-loop ML?
Real-world ML classifiers make mistakes. Instead of silently trusting the model, we surface every prediction for review. This is production-grade ML workflow — the model assists, humans decide.

### Why Kafka (even locally)?
Event-driven architecture decouples services. product.created triggers analytics, search indexing, notifications — without blocking the HTTP response.

### Why MLflow?
Experiment tracking + model registry. Every training run logged with hyperparameters, metrics, artifacts. Model versions promote through stages.

### Why Next.js 16?
Server Components + streaming. Landing page uses SSR (fast, SEO-friendly). Dashboard uses client interactivity (TanStack Query).

### Why Next.js 16 App Router?
Route groups (marketing), (shop), (auth), (admin) give clean layout separation — each group has its own header/sidebar without URL clutter.

📝 License
MIT — see LICENSE for details.
