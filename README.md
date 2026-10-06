# 🛍️ Shopify Cart

> A production-grade e-commerce platform with **ML-powered product auto-categorization**, human-in-the-loop review workflow, event-driven backend, and full order management — built as a portfolio project.

[![CI](https://github.com/touhid9xx/shopify-cart/actions/workflows/ci.yml/badge.svg)](https://github.com/touhid9xx/shopify-cart/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16.3-black.svg)](https://nextjs.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6-ee4c2c.svg)](https://pytorch.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docs.docker.com/compose/)
[![MySQL 8](https://img.shields.io/badge/MySQL-8.0-4479A1.svg)](https://www.mysql.com/)
[![Kafka](https://img.shields.io/badge/Kafka-7.6-231F20.svg)](https://kafka.apache.org/)
[![MLflow](https://img.shields.io/badge/MLflow-2.19-0194E2.svg)](https://mlflow.org/)

**🎬 [Watch demo](docs/demo.gif)** · **📸 [Screenshots](#-screenshots)** · **📖 [Docs](docs/)**

---

## 📸 Screenshots

### Customer experience

| Landing | Products | Cart |
|---------|----------|------|
| ![Landing](docs/screenshots/01-landing.png) | ![Products](docs/screenshots/02-products.png) | ![Cart](docs/screenshots/04-cart.png) |

| Product detail | Checkout | Orders |
|---------------|----------|--------|
| ![Product detail](docs/screenshots/03-product-detail.png) | ![Checkout](docs/screenshots/05-checkout.png) | ![Orders](docs/screenshots/06-orders.png) |

### Admin experience

| Dashboard | ML upload & classify | Review queue |
|-----------|---------------------|--------------|
| ![Admin dashboard](docs/screenshots/07-admin-dashboard.png) | ![ML upload](docs/screenshots/08-admin-upload-ml.png) | ![Review queue](docs/screenshots/09-admin-review.png) |

| ML Insights | Inventory |
|-------------|-----------|
| ![ML Insights](docs/screenshots/10-admin-ml-insights.png) | ![Inventory](docs/screenshots/11-admin-inventory.png) |

### MLflow tracking

![MLflow experiments](docs/screenshots/12-mlflow.png)
_Training runs, hyperparameters, metrics — all tracked._

---

## ✨ Highlights

- 🤖 **ML auto-categorization** — Admin uploads a product image; a fine-tuned ResNet-18 classifier predicts the category with confidence
- 👀 **Human-in-the-loop review** — Low-confidence predictions land in a review queue; admin can **Approve**, **Reject**, or **Recategorize**
- 🛒 **Full shopping cart** — Browse, add to cart, checkout, place orders (atomic transactions)
- 📦 **Order management** — Admin accepts/rejects/ships orders with audit trail
- 📨 **Event-driven** — Kafka events for `product.created`, `cart.updated`, `order.placed`, `inventory.low`
- 📊 **Analytics** — Daily sales, low-stock alerts, ML-based reorder suggestions, demand forecasting, anomaly detection
- 🐳 **Fully containerized** — Docker Compose for one-command deployment
- 🎨 **Modern frontend** — Next.js 16 App Router, TanStack Query v5, shadcn/ui (Base UI), dark mode

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CUSTOMER BROWSER                         │
│  Next.js 16 (React 19) · TypeScript · Tailwind v4 · shadcn/ui   │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTPS
┌─────────────────────────────▼───────────────────────────────────┐
│                        ADMIN BROWSER                            │
│  Same Next.js app — route groups: (shop) · (admin) · (auth)     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                     FASTAPI BACKEND (8000)                      │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │   Auth       │  Products    │    Cart      │   Orders     │  │
│  │  (JWT/RBAC)  │  + Inventory │  + Checkout  │  + Admin     │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
│  ┌──────────────────┬────────────────────────────────────────┐  │
│  │  ML Predictor    │  ML Insights (summary · forecast ·    │  │
│  │  (ResNet-18)     │   anomaly detection)                   │  │
│  └──────────────────┴────────────────────────────────────────┘  │
└──────┬─────────────────────┬───────────────────────┬────────────┘
       │                     │                       │
       ▼                     ▼                       ▼
  ┌─────────┐         ┌───────────┐           ┌───────────┐
  │ MySQL 8 │         │  Kafka    │           │  MLflow   │
  │ (data)  │         │ (events)  │           │ (models)  │
  └─────────┘         └───────────┘           └───────────┘
```

### Request flow — product upload with ML

```
Admin uploads image
        │
        ▼
POST /admin/products/upload (multipart)
        │
        ├──► Save image to data/uploads/
        ├──► ML classifier predicts category + confidence
        │
        ▼
  Confidence ≥ 0.75?
        │
   ┌────┴────┐
   │         │
  YES       NO
   │         │
   ▼         ▼
Create    Return needs_review
product   + top-3 suggestions
(PENDING)
   │         │
   └────┬────┘
        ▼
  Kafka: product.created
        │
        ▼
  Admin review queue
        │
   ┌────┼────┬──────────┐
   ▼    ▼    ▼          ▼
Approve Reject Recat.  Later
   │    │    │
   ▼    ▼    ▼
publish hide override
        + reason + publish
```

---

## 🧠 ML Auto-Categorization — The Differentiator

| Aspect | Detail |
|--------|--------|
| **Model** | ResNet-18 (transfer learning, ImageNet pretrained) |
| **Dataset** | [`ashraq/fashion-product-images-small`](https://huggingface.co/datasets/ashraq/fashion-product-images-small) |
| **Classes** | shirt, trouser, shoe, bag |
| **Training** | PyTorch 2.6 + CUDA 11.8 (GTX 1060, 6 GB VRAM) |
| **Tracking** | MLflow 2.19 (metrics, artifacts, model registry) |
| **Tuning** | Optuna (TPE sampler) — lr, batch size, augmentation |
| **Serving** | FastAPI `/predict`, LRU-cached, top-K + confidence |
| **Threshold** | `ML_CONFIDENCE_THRESHOLD=0.75` (configurable) |

### Why human-in-the-loop?

Real-world ML classifiers make mistakes. Instead of silently trusting the model, we surface every prediction for human review. **The model assists; humans decide.** This is production-grade ML workflow — the model provides scale, humans provide judgment.

---

## 🛠️ Tech Stack

### Backend

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.115 + Uvicorn |
| Validation | Pydantic v2 + pydantic-settings |
| ORM | SQLAlchemy 2.0 (`Mapped`, `mapped_column`) |
| Migrations | Alembic |
| Database | MySQL 8 (pymysql) |
| Auth | PyJWT (HS256) + passlib[argon2] |
| Logging | structlog (JSON in prod, colored console in dev) |
| Events | aiokafka (graceful degradation when disabled) |
| ML | PyTorch 2.6 + torchvision + MLflow + Optuna |
| Quality | Ruff, Mypy (strict), Pytest |

### Frontend

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 16 App Router (React 19) |
| Language | TypeScript (strict) |
| Styling | Tailwind v4 + shadcn/ui (Base UI primitives) |
| State | TanStack Query v5 |
| Forms | React Hook Form + Zod v4 |
| Charts | Chart.js + react-chartjs-2 |
| Theme | next-themes (dark mode) |
| Notifications | Sonner |
| Icons | Lucide React |

### Infra

- **Docker** + Docker Compose (multi-stage builds)
- **GitHub Actions** CI (backend · frontend · docker)
- **Pre-commit** hooks (ruff, mypy, hygiene)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12
- Node.js 20+ & pnpm 12+
- MySQL 8 (local or Docker)
- Docker Desktop (optional, for full stack)

### Option A — Docker Compose (recommended)

```bash
git clone https://github.com/touhid9xx/shopify-cart.git
cd shopify-cart

# Create .env from template
cp .env.example .env
# Edit .env — set MYSQL_ROOT_PASSWORD and JWT_SECRET_KEY

# Boot everything
docker compose up -d

# Wait ~90s for ML model to load, then:
docker compose ps
```

**Access:**
- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>
- MLflow: <http://localhost:5000>

### Option B — Local development

**Backend:**

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -e ".[dev]"

Copy-Item .env.example .env
# Edit .env with your MySQL credentials

alembic upgrade head
python scripts\seed_categories.py
python scripts\seed_categories_bulk.py    # optional — 30 categories
python scripts\seed_products_bulk.py --count 1000   # optional — demo data
python scripts\seed_daily_sales_bulk.py --days 30   # optional — analytics data

uvicorn shopify_cart.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**

```powershell
cd frontend
pnpm install
Copy-Item .env.example .env.local
# Edit .env.local — NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
pnpm dev
```

**MLflow (for training):**

```powershell
cd backend
.\venv\Scripts\Activate.ps1
mlflow server `
  --backend-store-uri sqlite:///mlruns/mlflow.db `
  --serve-artifacts `
  --artifacts-destination ./mlartifacts `
  --host 127.0.0.1 `
  --port 5000
```

---

## 🤖 ML Training

```powershell
cd backend
.\venv\Scripts\Activate.ps1

# Download + preprocess dataset (once)
python -m shopify_cart.ml.dataset --download --max-per-class 500
python -m shopify_cart.ml.preprocess

# Train
$env:MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
python -m shopify_cart.ml.train --epochs 25 --batch-size 32

# Register best model to MLflow registry
python -m shopify_cart.ml.register

# (Optional) Optuna hyperparameter tuning
python -m shopify_cart.ml.tune --n-trials 20
```

Expected: ~20-30 min on GTX 1060, best validation accuracy logged in MLflow.

---

## 📡 API Endpoints

| Category | Endpoints |
|----------|-----------|
| **Public** | `/health`, `/ready`, `GET /api/v1/products`, `GET /api/v1/categories`, `GET /api/v1/products/{id}` |
| **Auth** | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me` |
| **Cart** | `GET/POST/PATCH/DELETE /cart`, `/cart/items` |
| **Orders** | `POST /orders/checkout`, `GET /orders`, `POST /orders/{id}/cancel` |
| **Admin · Products** | CRUD + `POST /upload`, `POST /{id}/image`, `GET /pending-review`, `POST /{id}/approve`, `/reject`, `PATCH /{id}/recategorize` |
| **Admin · Orders** | `GET /admin/orders`, `POST /{id}/accept`, `/reject`, `/ship` |
| **Admin · Inventory** | `GET /admin/inventory`, `/stats`, `/alerts`, `/reorder-suggestions`, `POST /admin/inventory/adjust` |
| **Admin · Analytics** | `GET /admin/analytics/sales`, `/alerts` |
| **Admin · ML Insights** | `GET /admin/ml/summary`, `/demand-forecast`, `/anomalies` |
| **ML** | `POST /predict` |

Full OpenAPI docs: <http://localhost:8000/docs>

---

## 🧪 Testing

```powershell
cd backend
.\venv\Scripts\Activate.ps1

# All tests
pytest

# With coverage
pytest --cov=shopify_cart --cov-report=term-missing --cov-report=html

# Unit tests only (no DB needed)
pytest tests/unit

# Integration tests (needs DB)
pytest tests/integration
```

**Frontend:**

```powershell
cd frontend
pnpm tsc --noEmit
pnpm lint
pnpm build
```

---

## 📊 Feature Matrix

| Feature | Status |
|---------|--------|
| User registration + JWT auth | ✅ |
| Role-based access (customer / admin) | ✅ |
| Product catalog + search + pagination | ✅ |
| Category hierarchy (parent/child) | ✅ |
| Shopping cart with stock validation | ✅ |
| Atomic checkout (cart → order) | ✅ |
| Order history + cancellation | ✅ |
| Admin product CRUD | ✅ |
| Product image upload on edit | ✅ |
| ML auto-categorization on upload | ✅ |
| Review queue (approve / reject / recategorize) | ✅ |
| Admin order management (accept / reject / ship) | ✅ |
| Inventory tracking + alerts | ✅ |
| Reorder suggestions (ML-based) | ✅ |
| Sales analytics (Chart.js) | ✅ |
| Demand forecasting (exponential smoothing) | ✅ |
| Anomaly detection (rolling z-score) | ✅ |
| Kafka events | ✅ |
| MLflow tracking + model registry | ✅ |
| Docker + Compose | ✅ |
| GitHub Actions CI | ✅ |
| Pre-commit hooks | ✅ |

---

## 📁 Project Structure

```
shopify-cart/
├── .github/workflows/          # CI pipeline
├── .pre-commit-config.yaml     # Pre-commit hooks
├── docker-compose.yml          # Full-stack orchestration
├── backend/
│   ├── Dockerfile              # Multi-stage Python build
│   ├── alembic/                # DB migrations
│   ├── scripts/                # Seed / lint / test scripts
│   ├── src/shopify_cart/
│   │   ├── api/v1/             # Route handlers
│   │   ├── core/               # Security, pagination, money
│   │   ├── kafka/              # Producer + consumer + events
│   │   ├── ml/                 # Dataset, train, tune, predict
│   │   ├── models/             # SQLAlchemy ORM
│   │   ├── schemas/            # Pydantic v2
│   │   └── services/           # Business logic layer
│   └── tests/                  # Unit + integration
└── frontend/
    ├── Dockerfile              # Multi-stage Next.js build
    └── src/
        ├── app/                # App Router (route groups)
        │   ├── (marketing)/    # Landing page
        │   ├── (shop)/         # Customer pages
        │   ├── (auth)/         # Login/register
        │   └── (admin)/        # Admin dashboard
        ├── components/         # UI + feature components
        ├── hooks/              # TanStack Query hooks
        └── lib/                # API client, types, utils
```

---

## 🎯 Design Decisions

### Why human-in-the-loop ML?

Real-world ML classifiers make mistakes. Instead of silently trusting the model, we surface every prediction for review. The model assists; humans decide. This is production-grade ML workflow.

### Why Kafka (even locally)?

Event-driven architecture decouples services. `product.created` triggers analytics, search indexing, notifications — without blocking the HTTP response. Graceful degradation when disabled.

### Why MLflow?

Experiment tracking + model registry. Every training run logged with hyperparameters, metrics, artifacts. Model versions promote through stages.

### Why Next.js 16 App Router?

Route groups `(marketing)`, `(shop)`, `(auth)`, `(admin)` give clean layout separation — each group has its own header/sidebar without URL clutter.

### Why `MlflowClient.download_artifacts(run_id=, path=)` instead of `mlflow.artifacts`?

The module-level function uses an old API path that 500s on MLflow 2.19+ servers. `MlflowClient` is stable.

### Why Decimal everywhere?

Money must never be float. `Numeric(10, 2)` in DB, `Decimal` in Pydantic, sum via a single service helper.

---

## 🐛 Common Pitfalls (Gotchas We Solved)

| Gotcha | Fix |
|--------|-----|
| **Next.js 16 + Base UI** — no `asChild` | Use `buttonVariants()` + `Link`, or `router.push()` in dropdowns |
| **`useSearchParams` needs Suspense** | Wrap in `<Suspense>` boundary |
| **Pydantic v2 recursive models** | Never `model_validate()` on ORM with nested — build explicitly |
| **SQLAlchemy Enum + StrEnum** | `values_callable=lambda e: [m.value for m in e]` stores VALUES not NAMES |
| **Alembic NOT NULL columns** | Always provide `server_default` |
| **MySQL + Alpine `wget`** | Use `node -e "fetch(...)"` for healthcheck (IPv6 issue) |

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Ensure `pre-commit run --all-files` passes
4. Commit with a clear message (`git commit -m "feat: add amazing feature"`)
5. Push and open a PR

CI will run lint, type-check, tests, and Docker builds.

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **Dataset** — [ashraq/fashion-product-images-small](https://huggingface.co/datasets/ashraq/fashion-product-images-small) (HuggingFace)
- **ResNet-18** — He et al. (2015)
- **Sample images** — [Picsum Photos](https://picsum.photos/) (bulk seed)
- **UI inspiration** — shadcn/ui examples

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/touhid9xx">Touhid</a></sub>
</p>
