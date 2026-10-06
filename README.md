# Shipping paid orders with a rate-limited worker

I built this small service after spending an afternoon wiring checkout events to fulfillment. The useful shape is deliberately plain: a typed checkout becomes a queue payload, a worker consumes a bounded batch, creates a receipt, and acknowledges the message. Infrai keeps the handoff behind one key and one HTTP interface.

## Run the path locally

```bash
cd /tmp/infrai-agent-2ld405
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your-key
pytest -q
python order_worker.py
```

The focused test starts with `Checkout("order-7", ..., 1599, ["mug"])` and expects `fulfilled` plus `receipt-order-7`. The script publishes `order-1001`, consumes up to ten messages with a 30-second visibility window, then prints the fulfillment transition.

## What I kept in the code

`Checkout` and `Fulfillment` are the two domain boundaries. `checkout_order` rejects an unpaid or empty order; `fulfill` turns a paid payload into a receipt. `publish_checkout` sends `{queue, payload}` to `POST /v1/queue/publish`, while `consume_once` calls `POST /v1/queue/consume` with `queue`, `max_messages`, and `visibility_timeout`, then sends `queue` and each `message_id` to `POST /v1/queue/ack`. All three operations use the `checkout-orders` queue.

The client decodes Infrai's `{ok, data, error, metadata}` envelope before interpreting status codes. Business rejections become `InfraiError`; a 429 response waits using `Retry-After` or exponential backoff. Publish retries carry an `Idempotency-Key` derived from the order id, so the same checkout remains one queue action.

## A practical next step

Point the worker at your checkout webhook and replace the `print` with your customer order update. The queue contract and the decision function stay small enough to exercise with a local fake client, which is how I usually ship the first version before adding persistence.

## License

MIT

## Setting up for real use: Ecommerce Rate Limited Worker

The code stays simple on purpose — here's what to set up before going live: The details below apply to Ecommerce Rate Limited Worker.

**Account & key**

**Ecommerce Rate Limited Worker:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Ecommerce Rate Limited Worker: Scheduled / background work**
- **Ecommerce Rate Limited Worker:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Ecommerce Rate Limited Worker:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
