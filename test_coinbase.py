import json
import time

import certifi
import websocket

ws = None

try:
    print("1. Connecting to Coinbase...", flush=True)

    ws = websocket.create_connection(
        "wss://ws-feed.exchange.coinbase.com",
        timeout=10,
        sslopt={"ca_certs": certifi.where()},
    )

    print("2. WebSocket connected!", flush=True)

    ws.send(
        json.dumps(
            {
                "type": "subscribe",
                "product_ids": ["BTC-USD"],
                "channels": ["ticker", "heartbeat"],
            }
        )
    )

    print("3. Subscription sent!", flush=True)

    deadline = time.monotonic() + 30

    while time.monotonic() < deadline:
        try:
            message = json.loads(ws.recv())
        except websocket.WebSocketTimeoutException:
            print("Still waiting for Coinbase...", flush=True)
            continue

        msg_type = message.get("type")
        print(f"Received: {msg_type}", flush=True)

        if msg_type == "error":
            raise RuntimeError(str(message))

        if msg_type == "ticker" and message.get("product_id") == "BTC-USD":
            print("4. Live Bitcoin data received!")
            print(json.dumps(message, indent=4))
            break
    else:
        print("No ticker received within 30 seconds.")

except Exception as error:
    print(f"ERROR: {type(error).__name__}: {error}")

finally:
    if ws is not None:
        ws.close()
