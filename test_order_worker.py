import pytest

from order_worker import Checkout, checkout_order, fulfill


def test_paid_checkout_becomes_fulfilled_receipt():
    order = Checkout("order-7", "buyer@example.com", 1599, ["mug"])
    paid = checkout_order(order)
    result = fulfill(paid)
    assert result.status == "fulfilled"
    assert result.receipt == "receipt-order-7"


def test_empty_checkout_is_rejected():
    with pytest.raises(ValueError):
        checkout_order(Checkout("order-8", "buyer@example.com", 0, []))
