import json
import logging
import time
from datetime import datetime, timezone

import websocket
from kafka import KafkaProducer

COINBASE_URL = "wss://ws-feed.exchange.coinbase.com"
KAFKA_BROKER = "127.0.0.1:9092"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


def run_producer(product_id: str, topic: str):
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        acks="all",
        retries=5,
    )

    retry_delay = 2

    try:
        while True:
            ws = None

            try:
                ws = websocket.create_connection(
                    COINBASE_URL,
                    timeout=30,
                )

                subscription = {
                    "type": "subscribe",
                    "product_ids": [product_id],
                    "channels": ["ticker_batch"],
                }

                ws.send(json.dumps(subscription))

                logging.info("Subscribed to Coinbase: %s", product_id)

                while True:
                    raw_message = ws.recv()

                    if not raw_message:
                        raise ConnectionError("WebSocket connection closed")

                    message = json.loads(raw_message)

                    if message.get("type") == "error":
                        raise RuntimeError(str(message))

                    if (
                        message.get("type") != "ticker"
                        or message.get("product_id") != product_id
                    ):
                        continue

                    if not all(
                        message.get(field) is not None
                        for field in ("price", "time", "trade_id")
                    ):
                        continue

                    payload = {
                        "source": "coinbase_exchange",
                        "product_id": product_id,
                        "price_usd": message.get("price"),
                        "open_24h_usd": message.get("open_24h"),
                        "high_24h_usd": message.get("high_24h"),
                        "low_24h_usd": message.get("low_24h"),
                        "volume_24h": message.get("volume_24h"),
                        "best_bid_usd": message.get("best_bid"),
                        "best_ask_usd": message.get("best_ask"),
                        "trade_id": message.get("trade_id"),
                        "event_time": message.get("time"),
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                    }

                    result = producer.send(
                        topic,
                        value=payload,
                    ).get(timeout=15)

                    logging.info(
                        "SENT | %s | Price: $%s | Topic: %s | Offset: %s",
                        product_id,
                        payload["price_usd"],
                        topic,
                        result.offset,
                    )

                    retry_delay = 2

            except Exception as error:
                logging.warning("Connection error: %s", error)
                logging.info(
                    "Reconnecting in %s seconds",
                    retry_delay,
                )
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)

            finally:
                if ws is not None:
                    ws.close()

    except KeyboardInterrupt:
        logging.info("Stopping %s producer", product_id)

    finally:
        producer.close()
