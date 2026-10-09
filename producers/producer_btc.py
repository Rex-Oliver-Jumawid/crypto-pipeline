from producer_common import run_producer

if __name__ == "__main__":
    run_producer(
        product_id="BTC-USD",
        topic="crypto-btc-prices",
    )
