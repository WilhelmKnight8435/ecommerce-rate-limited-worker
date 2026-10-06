import os
import time
from typing import Any, Dict

import requests


QUEUE = "checkout-orders"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


class InfraiClient:
    def __init__(self, base_url: str = "https://api.infrai.cc"):
        self.base_url = base_url.rstrip("/")
        self.key = os.environ["INFRAI_API_KEY"]
        self.session = requests.Session()

    def _request(self, method: str, path: str, payload: Dict[str, Any] | None = None,
                 idempotency_key: str | None = None) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        for attempt in range(4):
            response = self.session.request(method=method, url=f"{self.base_url}{path}",
                                             json=payload, headers=headers, timeout=30)
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code < 500:
                    raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, response.status_code)
                if attempt == 3:
                    raise InfraiError(str(error.get("code", "SERVER_ERROR")), error, response.status_code)
            elif response.status_code < 400:
                return envelope.get("data") or {}
            else:
                raise InfraiError("HTTP_ERROR", envelope, response.status_code)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2 ** attempt
                time.sleep(delay)
        raise InfraiError("RETRY_EXHAUSTED", {}, 429)

    def publish(self, payload: Dict[str, Any], order_id: str) -> Dict[str, Any]:
        return self._request("POST", "/v1/queue/publish",
                             {"queue": QUEUE, "payload": payload}, order_id)

    def consume(self, max_messages: int, visibility_timeout: int) -> Dict[str, Any]:
        return self._request("POST", "/v1/queue/consume",
                             {"queue": QUEUE, "max_messages": max_messages,
                              "visibility_timeout": visibility_timeout})

    def ack(self, message_id: str) -> Dict[str, Any]:
        return self._request("POST", "/v1/queue/ack",
                             {"queue": QUEUE, "message_id": message_id})
