import json
import os
import pickle
import time

import numpy as np
import pandas as pd

from kafka import KafkaProducer
from pymongo import MongoClient

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, udf
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StructField,
    StructType,
)


# ============================================================
# CONFIGURATION
# ============================================================

KAFKA_BROKER = os.environ.get(
    "KAFKA_BROKER",
    "kafka:9092"
)

MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb://mongodb:27017"
)

MODEL_PATH = "/app/model/xgboost_model.pkl"

METADATA_PATH = "/app/model/metadata.json"

FRAUD_THRESHOLD = float(
    os.environ.get("FRAUD_THRESHOLD", "0.7")
)

SUSPECT_THRESHOLD = float(
    os.environ.get("SUSPECT_THRESHOLD", "0.3")
)

CHECKPOINT_PATH = "/app/checkpoint"


# ============================================================
# MONGODB CLIENT
# ============================================================

_mongo_client = None


# ============================================================
# CHARGEMENT DU METADATA
# ============================================================

def load_amount_mean():
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        return float(metadata["amount_mean"])

    except (
        FileNotFoundError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        print(
            "metadata.json introuvable ou invalide. "
            "Utilisation de la valeur par défaut."
        )

        return 88.34961925093134


AMOUNT_MEAN = load_amount_mean()


# ============================================================
# ATTENTE DE KAFKA
# ============================================================

def wait_for_kafka(
    broker,
    timeout=120,
    interval=2
):
    print(f"Attente de Kafka ({broker})...")

    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        try:
            producer = KafkaProducer(
                bootstrap_servers=broker,
                api_version=(3, 4, 0),
            )

            producer.close()

            print("Kafka prêt !")
            return

        except Exception as exc:
            last_error = exc

            print(
                f"Kafka pas encore prêt : {exc}"
            )

            time.sleep(interval)

    raise TimeoutError(
        f"Kafka indisponible après {timeout}s : "
        f"{last_error}"
    )


# ============================================================
# ATTENTE DE MONGODB
# ============================================================

def wait_for_mongo(
    uri,
    timeout=60,
    interval=2
):
    print(f"Attente de MongoDB ({uri})...")

    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        try:
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=2000,
            )

            client.admin.command("ping")
            client.close()

            print("MongoDB prêt !")
            return

        except Exception as exc:
            last_error = exc

            print(
                f"MongoDB pas encore prêt : {exc}"
            )

            time.sleep(interval)

    raise TimeoutError(
        f"MongoDB indisponible après {timeout}s : "
        f"{last_error}"
    )


# ============================================================
# CONNEXION MONGODB
# ============================================================

def get_mongo_db():
    global _mongo_client

    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI)

    return _mongo_client["fraud_db"]


# ============================================================
# DÉMARRAGE
# ============================================================

print("=" * 60)
print("DÉMARRAGE DU PIPELINE DE DÉTECTION DE FRAUDE")
print("=" * 60)

print(f"Kafka      : {KAFKA_BROKER}")
print(f"MongoDB    : {MONGO_URI}")
print(f"Model      : {MODEL_PATH}")
print(f"Threshold fraude  : {FRAUD_THRESHOLD}")
print(f"Threshold suspect : {SUSPECT_THRESHOLD}")

wait_for_kafka(KAFKA_BROKER)
wait_for_mongo(MONGO_URI)

print("Toutes les dépendances sont prêtes.")


# ============================================================
# CHARGEMENT DU MODÈLE XGBOOST
# ============================================================

print("Chargement du modèle XGBoost...")

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

print("Modèle XGBoost chargé !")

print(
    f"Nombre de features attendues : "
    f"{len(model.feature_names_in_)}"
)

print(
    f"amount_mean utilisé : "
    f"{AMOUNT_MEAN:.6f}"
)


# ============================================================
# SPARK SESSION
# ============================================================

spark = (
    SparkSession.builder
    .appName("FraudDetection")
    .config(
        "spark.sql.shuffle.partitions",
        "2"
    )
    .config(
        "spark.streaming.stopGracefullyOnShutdown",
        "true"
    )
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# ============================================================
# SCHEMA DES TRANSACTIONS KAFKA
# ============================================================

schema = StructType(
    [
        StructField(
            "Time",
            DoubleType(),
            True
        ),

        *[
            StructField(
                f"V{i}",
                DoubleType(),
                True
            )
            for i in range(1, 29)
        ],

        StructField(
            "Amount",
            DoubleType(),
            True
        ),

        StructField(
            "Class",
            IntegerType(),
            True
        ),
    ]
)


# ============================================================
# KAFKA -> SPARK
# ============================================================

print("=" * 60)
print("CONNEXION À KAFKA")
print("=" * 60)

raw_df = (
    spark.readStream
    .format("kafka")
    .option(
        "kafka.bootstrap.servers",
        KAFKA_BROKER
    )
    .option(
        "subscribe",
        "transactions"
    )
    .option(
        "startingOffsets",
        "earliest"
    )
    .option(
        "failOnDataLoss",
        "false"
    )
    .load()
)


# ============================================================
# DÉCODAGE DU JSON
# ============================================================

transactions = (
    raw_df
    .select(
        from_json(
            col("value").cast("string"),
            schema
        ).alias("data")
    )
    .select("data.*")
)


# ============================================================
# PRÉDICTION FRAUDE
# ============================================================

def predict_fraud(
    v1,
    v2,
    v3,
    v4,
    v5,
    v6,
    v7,
    v8,
    v9,
    v10,
    v11,
    v12,
    v13,
    v14,
    v15,
    v16,
    v17,
    v18,
    v19,
    v20,
    v21,
    v22,
    v23,
    v24,
    v25,
    v26,
    v27,
    v28,
    amount,
    time_val,
):

    try:

        # ----------------------------------------------------
        # Vérification des valeurs
        # ----------------------------------------------------

        if amount is None:
            amount = 0.0

        if time_val is None:
            time_val = 0.0

        # ----------------------------------------------------
        # Feature : transaction nocturne
        # ----------------------------------------------------

        heure_nuit = (
            1
            if (time_val % 86400) < 21600
            else 0
        )

        # ----------------------------------------------------
        # Feature : ratio montant
        # ----------------------------------------------------

        ratio_montant = (
            amount / (AMOUNT_MEAN + 1)
        )

        # ----------------------------------------------------
        # Feature : logarithme montant
        # ----------------------------------------------------

        montant_log = np.log1p(
            max(0.0, amount)
        )

        # ----------------------------------------------------
        # Features finales
        # ----------------------------------------------------

        features = pd.DataFrame(
            [[
                v1,
                v2,
                v3,
                v4,
                v5,
                v6,
                v7,
                v8,
                v9,
                v10,
                v11,
                v12,
                v13,
                v14,
                v15,
                v16,
                v17,
                v18,
                v19,
                v20,
                v21,
                v22,
                v23,
                v24,
                v25,
                v26,
                v27,
                v28,
                heure_nuit,
                ratio_montant,
                montant_log,
            ]],
            columns=model.feature_names_in_,
        )

        # ----------------------------------------------------
        # Prédiction
        # ----------------------------------------------------

        score = float(
            model.predict_proba(features)[0][1]
        )

        return max(
            0.0,
            min(1.0, score)
        )

    except Exception as exc:

        print(
            f"Erreur prediction : "
            f"{type(exc).__name__}: {exc}"
        )

        return 0.0


predict_udf = udf(
    predict_fraud,
    DoubleType()
)


# ============================================================
# APPLICATION DU MODÈLE
# ============================================================

result = transactions.withColumn(
    "score",
    predict_udf(
        col("V1"),
        col("V2"),
        col("V3"),
        col("V4"),
        col("V5"),
        col("V6"),
        col("V7"),
        col("V8"),
        col("V9"),
        col("V10"),
        col("V11"),
        col("V12"),
        col("V13"),
        col("V14"),
        col("V15"),
        col("V16"),
        col("V17"),
        col("V18"),
        col("V19"),
        col("V20"),
        col("V21"),
        col("V22"),
        col("V23"),
        col("V24"),
        col("V25"),
        col("V26"),
        col("V27"),
        col("V28"),
        col("Amount"),
        col("Time"),
    )
)


# ============================================================
# SPARK BATCH -> MONGODB
# ============================================================

def save_to_mongo(
    batch_df,
    batch_id
):

    if batch_df.rdd.isEmpty():
        return

    db = get_mongo_db()

    frauds = []
    suspects = []
    normales = []

    rows = batch_df.collect()

    for row in rows:

        data = row.asDict()

        score = data.get(
            "score",
            0.0
        )

        amount = data.get(
            "Amount",
            0.0
        )

        # ----------------------------------------------------
        # FRAUDE
        # ----------------------------------------------------

        if score >= FRAUD_THRESHOLD:

            frauds.append(data)

            print(
                f"FRAUDE ! "
                f"Score={score:.4f} "
                f"Montant={amount:.2f}"
            )

        # ----------------------------------------------------
        # SUSPECT
        # ----------------------------------------------------

        elif score >= SUSPECT_THRESHOLD:

            suspects.append(data)

            print(
                f"SUSPECT ! "
                f"Score={score:.4f} "
                f"Montant={amount:.2f}"
            )

        # ----------------------------------------------------
        # NORMAL
        # ----------------------------------------------------

        else:

            normales.append(data)

    # ========================================================
    # INSERTIONS MONGODB
    # ========================================================

    if frauds:
        db["fraudes"].insert_many(
            frauds
        )

    if suspects:
        db["suspectes"].insert_many(
            suspects
        )

    if normales:
        db["normales"].insert_many(
            normales
        )

    print(
        f"[Batch {batch_id}] "
        f"Total={len(rows)} | "
        f"Fraudes={len(frauds)} | "
        f"Suspects={len(suspects)} | "
        f"Normales={len(normales)}"
    )


# ============================================================
# SPARK STREAMING
# ============================================================

print("=" * 60)
print("SPARK EN ÉCOUTE DU TOPIC KAFKA : transactions")
print("=" * 60)

query = (
    result.writeStream
    .option(
        "checkpointLocation",
        CHECKPOINT_PATH
    )
    .foreachBatch(
        save_to_mongo
    )
    .trigger(
        processingTime="5 seconds"
    )
    .start()
)


# ============================================================
# ATTENTE DU STREAM
# ============================================================

query.awaitTermination()