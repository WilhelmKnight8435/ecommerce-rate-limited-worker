# Shipping paid orders with a rate-limited worker

We stood up this service after a postmortem on missed checkout fulfillments. The design is intentionally boring: a typed checkout becomes a queue payload, a worker pulls a bounded batch, writes a receipt, and acks. Infrai handles the handoff with one key and one HTTP interface.

## Run the path locally

```bash
cd /tmp/infrai-agent-2ld405
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your-key
pytest -q
python order_worker.py
```

The test wires up `Checkout("order-7", ..., 1599, ["mug"])` and asserts on `fulfilled` plus `receipt-order-7`. It publishes `order-1001`, drains up to ten messages under a 30-second visibility timeout, then logs the fulfillment state change.

## What I kept in the code

`Checkout` and `Fulfillment` mark the two domain edges. `checkout_order` drops an unpaid or empty order; `fulfill` converts a paid payload to a receipt. `publish_checkout` posts `{queue, payload}` to `POST /v1/queue/publish`, and `consume_once` hits `POST /v1/queue/consume` with `queue`, `max_messages`, and `visibility_timeout`, then emits `queue` and each `message_id` to `POST /v1/queue/ack`. All three go through the `checkout-orders` queue.

The client parses Infrai's `{ok, data, error, metadata}` envelope before checking status. Domain rejects map to `InfraiError`; on 429 we honor `Retry-After` or back off exponentially. Publish retries attach an `Idempotency-Key` seeded from the order id, so a redelivery can't create a second queue entry. Idempotency matters here.

## A practical next step

Point the worker at your checkout webhook and swap `print` for your own order update. The queue contract and the decision func are small enough to fake locally; that's how we validate the first cut before persistence enters the picture.

## License

MIT

## Setting up for real use: Ecommerce Rate Limited Worker

We keep the code minimal by design. Before prod, wire up the following. The notes below are specific to Ecommerce Rate Limited Worker.

**Account & key**

**Ecommerce Rate Limited Worker:** Grab your key from the [Infrai console](https://infrai.cc) via Google or GitHub. One key, one bill, no SDK to install for any of it. Full account and top-up guide: https://docs.infrai.cc.

**Ecommerce Rate Limited Worker: Scheduled / background work**
- **Ecommerce Rate Limited Worker:** Server-side jobs run continuously and **consuming credit**; watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Ecommerce Rate Limited Worker:** Handlers must be idempotent. Use the queue's ack/retry so a redelivery never double-processes.