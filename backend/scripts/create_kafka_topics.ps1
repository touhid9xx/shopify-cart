# Create all Kafka topics declared in events.py.
# Idempotent — safe to run multiple times.
#
# Usage:
#   .\scripts\create_kafka_topics.ps1

$ErrorActionPreference = "Stop"

$container = "shopify-kafka"
$broker = "localhost:9092"

# Must match src/shopify_cart/kafka/events.py TOPIC_* constants
$topics = @(
    "product.created",
    "product.updated",
    "product.deleted",
    "cart.updated",
    "cart.item_added",
    "cart.item_removed",
    "order.placed",
    "order.cancelled",
    "inventory.changed",
    "inventory.low",
    "health.check"
)

Write-Host "Creating Kafka topics..." -ForegroundColor Cyan

foreach ($topic in $topics) {
    # --if-not-exists makes the command idempotent
    docker exec -it $container kafka-topics `
        --bootstrap-server $broker `
        --create `
        --if-not-exists `
        --topic $topic `
        --partitions 1 `
        --replication-factor 1 `
        --config retention.ms=604800000 `
        --config cleanup.policy=delete | Out-Null

    Write-Host "$topic" -ForegroundColor Green
}

Write-Host "`n Current topics:" -ForegroundColor Cyan
docker exec -it $container kafka-topics --bootstrap-server $broker --list
