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
