# Kafka Team Consumer Demos

Three independent programs simulating real teams that receive
Kafka events from the Shopify Cart backend.

| Program | Group ID | Topics | Simulates |
|---|---|---|---|
| `sales_consumer.py` | `sales-team` | product.created, order.placed | Sales team notifications |
| `marketing_consumer.py` | `marketing-team` | product.created | Slack/social media posting |
| `analytics_consumer.py` | `analytics-team` | product.created, order.placed, cart.updated | Data warehouse ingestion |

## Run

Open **3 separate terminals** in `backend/`:

```powershell
# Terminal 1 — Sales
.\venv\Scripts\Activate.ps1
python -m scripts.teams.sales_consumer

# Terminal 2 — Marketing
.\venv\Scripts\Activate.ps1
python -m scripts.teams.marketing_consumer

# Terminal 3 — Analytics
.\venv\Scripts\Activate.ps1
python -m scripts.teams.analytics_consumer
