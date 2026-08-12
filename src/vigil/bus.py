"""Pub/Sub access.

Stages are decoupled through the bus rather than calling each other directly, so
a worker crash can never take the API down with it and a stuck message ends up in
the dead-letter topic instead of retrying forever.
"""

from __future__ import annotations

import json
from functools import lru_cache

from google.api_core import exceptions as gexc
from google.cloud import pubsub_v1

from vigil.config import get_settings
from vigil.telemetry import log

_log = log("vigil.bus")


@lru_cache(maxsize=1)
def publisher() -> pubsub_v1.PublisherClient:
    return pubsub_v1.PublisherClient()


@lru_cache(maxsize=1)
def subscriber() -> pubsub_v1.SubscriberClient:
    return pubsub_v1.SubscriberClient()


def topic_path(topic: str) -> str:
    return publisher().topic_path(get_settings().project_id, topic)


def subscription_path(subscription: str) -> str:
    return subscriber().subscription_path(get_settings().project_id, subscription)


def ensure_topic(topic: str) -> str:
    path = topic_path(topic)
    try:
        publisher().create_topic(request={"name": path})
        _log.info("topic.created", topic=topic)
    except gexc.AlreadyExists:
        pass
    return path


def ensure_subscription(subscription: str, topic: str, dlq_topic: str | None = None) -> str:
    path = subscription_path(subscription)
    request: dict = {"name": path, "topic": ensure_topic(topic), "ack_deadline_seconds": 60}
    if dlq_topic:
        # Five failed deliveries and the message stops costing us money and starts
        # being evidence instead.
        request["dead_letter_policy"] = {
            "dead_letter_topic": ensure_topic(dlq_topic),
            "max_delivery_attempts": 5,
        }
    try:
        subscriber().create_subscription(request=request)
        _log.info("subscription.created", subscription=subscription, topic=topic)
    except gexc.AlreadyExists:
        pass
    return path


def publish(topic: str, payload: dict, **attributes: str) -> str:
    data = json.dumps(payload, separators=(",", ":")).encode()
    future = publisher().publish(topic_path(topic), data, **attributes)
    message_id = future.result(timeout=30)
    _log.info("event.published", topic=topic, message_id=message_id)
    return message_id
