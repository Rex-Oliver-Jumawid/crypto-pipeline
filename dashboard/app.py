
from datetime import datetime, timedelta, timezone

from cassandra.cluster import Cluster
from cassandra.util import Date
from flask import Flask, jsonify, render_template


# Initialize Flask application.
app = Flask(__name__)


# Connect to Apache Cassandra.
cluster = Cluster(["127.0.0.1"], port=9042)
session = cluster.connect("crypto_market")


# Prepare a query for recent cryptocurrency records.
latest_prices_query = session.prepare("""
    SELECT
        product_id,
        event_time,
        price_usd,
        open_24h_usd,
        high_24h_usd,
        low_24h_usd,
        volume_24h,
        price_change_pct_24h
    FROM market_ticks
    WHERE product_id = ?
      AND trade_date = ?
    LIMIT 40
""")


def as_number(value):
    """Convert Cassandra decimal values into JSON numbers."""
    return float(value) if value is not None else None


def format_timestamp(value):
    """Convert a Cassandra timestamp into UTC ISO format."""
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    return value.isoformat()


def get_recent_prices(product_id):
    """Retrieve recent market records for one cryptocurrency."""

    today = datetime.now(timezone.utc).date()

    # Query today's UTC records, then yesterday's if necessary.
    dates = [
        today,
        today - timedelta(days=1),
    ]

    for trade_date in dates:
        rows = session.execute(
            latest_prices_query,
            (product_id, Date(trade_date)),
        )

        records = []

        for row in rows:
            records.append({
                "product_id": row.product_id,
                "event_time": format_timestamp(
                    row.event_time
                ),
                "price_usd": as_number(
                    row.price_usd
                ),
                "open_24h_usd": as_number(
                    row.open_24h_usd
                ),
                "high_24h_usd": as_number(
                    row.high_24h_usd
                ),
                "low_24h_usd": as_number(
                    row.low_24h_usd
                ),
                "volume_24h": as_number(
                    row.volume_24h
                ),
                "price_change_pct_24h": as_number(
                    row.price_change_pct_24h
                ),
            })

        if records:
            return records

    return []


# Serve the cryptocurrency dashboard homepage.
@app.get("/")
def index():
    return render_template("index.html")


# API endpoint for Bitcoin and Ethereum market data.
@app.get("/api/prices")
def get_prices():
    try:
        bitcoin = get_recent_prices("BTC-USD")
        ethereum = get_recent_prices("ETH-USD")

        return jsonify({
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "BTC-USD": bitcoin,
            "ETH-USD": ethereum,
        })

    except Exception:
        app.logger.exception(
            "Failed to retrieve cryptocurrency market data"
        )

        return jsonify({
            "error": "Unable to retrieve market data"
        }), 500


# Run the Flask development server.
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5050,
        debug=False,
    )
