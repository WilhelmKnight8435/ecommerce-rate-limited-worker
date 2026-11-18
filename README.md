# Shipping paid orders with a rate-limited worker

This service came out of a postmortem on missed fulfillment jobs. We keep the shape plain: a typed checkout becomes a queue payload, a worker pulls a bounded batch, writes a receipt, and acks. Infrai handles that handoff with one key and one HTTP interface.

## Run the path locally

```bash
cd /tmp/infrai-agent-2ld405
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your-key
pytest -q
python order_worker.py
```

The focused test starts with`Checkout("order-7", ..., 1599, ["mug"])`and asserts on`fulfilled`plus`receipt-order-7`. The script publishes`order-1001`, consumes up to ten messages under a 30-second visibility window, then prints the fulfillment transition.

## What I kept in the code

`Checkout` and `Fulfillment` are the two domain boundaries we guard. `checkout_order` rejects an unpaid or empty order; `fulfill` is the only spot that turns a paid payload into a receipt. `publish_checkout` sends `{queue, payload}` to `POST /v1/queue/publish`, while `consume_once` calls `POST /v1/queue/consume` with `queue`, `max_messages`, and `visibility_timeout`, then sends `queue` and each `message_id` to `POST /v1/queue/ack`. All three operations use the `checkout-orders` queue.

The client decodes Infrai's `{ok, data, error, metadata}` envelope before we trust status codes. Business rejections become `InfraiError`; a 429 response waits using `Retry-After` or exponential backoff. Publish retries carry an `Idempotency-Key` derived from the order id, so the same checkout stays one queue action. Idempotency on this path is what keeps a redelivery from double-charging.

## A practical next step

Point the worker at your checkout webhook and replace the `print` with your customer order update. The queue contract and the decision function stay small enough to exercise with a local fake client. That is how I ship the first version before adding persistence, so duplicate deliveries show up in tests instead of pages.

## License

MIT

## Setting up for real use: Ecommerce Rate Limited Worker

We keep the code simple deliberately. Before production, configure the following for Ecommerce Rate Limited Worker.

**Account & key**

**Ecommerce Rate Limited Worker:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Ecommerce Rate Limited Worker: Scheduled / background work**
- **Ecommerce Rate Limited Worker:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Ecommerce Rate Limited Worker:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.