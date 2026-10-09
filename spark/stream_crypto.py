from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    from_json,
    to_date,
    to_timestamp,
    when,
)
from pyspark.sql.functions import (
    round as spark_round,
)
from pyspark.sql.types import (
    DecimalType,
    LongType,
    StringType,
    StructField,
    StructType,
)

schema = StructType(
    [
        StructField("source", StringType()),
        StructField("product_id", StringType()),
        StructField("price_usd", StringType()),
        StructField("open_24h_usd", StringType()),
        StructField("high_24h_usd", StringType()),
        StructField("low_24h_usd", StringType()),
        StructField("volume_24h", StringType()),
        StructField("best_bid_usd", StringType()),
        StructField("best_ask_usd", StringType()),
        StructField("trade_id", LongType()),
        StructField("event_time", StringType()),
        StructField("ingested_at", StringType()),
    ]
)

spark = (
    SparkSession.builder.appName("CryptoMarketStreaming")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

kafka_stream = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", "kafka:19092")
    .option(
        "subscribe",
        "crypto-btc-prices,crypto-eth-prices",
    )
    .option("startingOffsets", "earliest")
    .option("maxOffsetsPerTrigger", 200)
    .load()
)

parsed = kafka_stream.select(
    col("topic").alias("kafka_topic"),
    from_json(col("value").cast("string"), schema).alias("data"),
).select("kafka_topic", "data.*")

valid = parsed.filter(
    ((col("kafka_topic") == "crypto-btc-prices") & (col("product_id") == "BTC-USD"))
    | ((col("kafka_topic") == "crypto-eth-prices") & (col("product_id") == "ETH-USD"))
)

price_fields = [
    "price_usd",
    "open_24h_usd",
    "high_24h_usd",
    "low_24h_usd",
    "best_bid_usd",
    "best_ask_usd",
]

processed = valid

for field in price_fields:
    processed = processed.withColumn(field, col(field).cast(DecimalType(20, 8)))

processed = (
    processed.withColumn(
        "volume_24h",
        col("volume_24h").cast(DecimalType(28, 8)),
    )
    .withColumn(
        "event_time",
        to_timestamp("event_time"),
    )
    .withColumn(
        "ingested_at",
        to_timestamp("ingested_at"),
    )
    .filter(
        col("price_usd").isNotNull()
        & col("event_time").isNotNull()
        & col("trade_id").isNotNull()
    )
    .withColumn(
        "trade_date",
        to_date("event_time"),
    )
    .withColumn(
        "price_change_pct_24h",
        when(
            col("open_24h_usd") > 0,
            spark_round(
                ((col("price_usd") - col("open_24h_usd")) / col("open_24h_usd")) * 100,
                2,
            ),
        ).cast(DecimalType(18, 4)),
    )
)


def save_to_cassandra(batch_df, batch_id):
    if batch_df.isEmpty():
        return

    (
        batch_df.select(
            "product_id",
            "trade_date",
            "event_time",
            "trade_id",
            "kafka_topic",
            "source",
            "price_usd",
            "open_24h_usd",
            "high_24h_usd",
            "low_24h_usd",
            "volume_24h",
            "best_bid_usd",
            "best_ask_usd",
            "price_change_pct_24h",
            "ingested_at",
        )
        .write.format("org.apache.spark.sql.cassandra")
        .mode("append")
        .options(
            keyspace="crypto_market",
            table="market_ticks",
        )
        .save()
    )

    print(
        f"Batch {batch_id}: Saved to Cassandra",
        flush=True,
    )


query = (
    processed.writeStream.foreachBatch(save_to_cassandra)
    .option(
        "checkpointLocation",
        "/tmp/crypto-cassandra-checkpoint",
    )
    .trigger(processingTime="10 seconds")
    .start()
)

query.awaitTermination()
