from dataclasses import asdict, dataclass
from typing import Any, Dict

from infrai_client import InfraiClient


@dataclass
class Checkout:
    order_id: str
    customer_email: str
    total_cents: int
    items: list[str]


@dataclass
class Fulfillment:
    order_id: str
    status: str
    receipt: str


def checkout_order(order: Checkout) -> Dict[str, Any]:
    if order.total_cents <= 0 or not order.items:
        raise ValueError("checkout needs a positive total and at least one item")
    return {"order_id": order.order_id, "customer_email": order.customer_email,
            "total_cents": order.total_cents, "items": order.items, "state": "paid"}


def fulfill(payload: Dict[str, Any]) -> Fulfillment:
    if payload.get("state") != "paid":
        raise ValueError("only paid checkouts enter fulfillment")
    receipt = f"receipt-{payload['order_id']}"
    return Fulfillment(payload["order_id"], "fulfilled", receipt)


def publish_checkout(client: InfraiClient, order: Checkout) -> Dict[str, Any]:
    return client.publish(checkout_order(order), order.order_id)


def consume_once(client: InfraiClient) -> list[Fulfillment]:
    data = client.consume(max_messages=10, visibility_timeout=30)
    messages = data.get("messages") or []
    completed = []
    for message in messages:
        result = fulfill(message["payload"])
        client.ack(message["message_id"])
        completed.append(result)
        print(f"{result.order_id}: {result.status}; {result.receipt}")
    return completed


if __name__ == "__main__":
    client = InfraiClient()
    sample = Checkout("order-1001", "buyer@example.com", 4299, ["coffee-grinder"])
    publish_checkout(client, sample)
    consume_once(client)
