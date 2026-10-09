
CREATE KEYSPACE IF NOT EXISTS crypto_market
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 1
};

CREATE TABLE IF NOT EXISTS crypto_market.market_ticks (
    product_id text,
    trade_date date,
    event_time timestamp,
    trade_id bigint,

    kafka_topic text,
    source text,

    price_usd decimal,
    open_24h_usd decimal,
    high_24h_usd decimal,
    low_24h_usd decimal,

    volume_24h decimal,
    best_bid_usd decimal,
    best_ask_usd decimal,

    price_change_pct_24h decimal,
    ingested_at timestamp,

    PRIMARY KEY (
        (product_id, trade_date),
        event_time,
        trade_id
    )
)
WITH CLUSTERING ORDER BY (
    event_time DESC,
    trade_id DESC
);

