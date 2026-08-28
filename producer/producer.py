import json
import os
import time

import numpy as np
import pandas as pd
from kafka import KafkaProducer


KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "kafka:9092")
SEND_DELAY = float(os.environ.get("SEND_DELAY", "0.5"))
MAX_TXNS = int(os.environ.get("MAX_TXNS", "0"))


def to_json_safe(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    return value


def wait_for_kafka(broker, timeout=120, interval=2):
    print(f"Attente de Kafka ({broker})...")
    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        try:
            producer = KafkaProducer(
                bootstrap_servers=broker,
                api_version=(3, 4, 0),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )

            producer.close()
            print("Kafka pret !")
            return

        except Exception as exc:
            last_error = exc
            print(f"Kafka pas encore pret : {exc}")
            time.sleep(interval)

    raise TimeoutError(
        f"Kafka indisponible apres {timeout}s : {last_error}"
    )


wait_for_kafka(KAFKA_BROKER)


print("Chargement des donnees...")
df = pd.read_csv("/app/data/creditcard.csv")

if MAX_TXNS > 0:
    df = df.head(MAX_TXNS)


transactions = [
    {key: to_json_safe(value) for key, value in row.items()}
    for row in df.to_dict("records")
]


producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)


print(f"Envoi de {len(transactions)} transactions vers Kafka...")

for txn in transactions:
    try:
        producer.send("transactions", txn)

        print(
            f"Envoye -> Montant: {txn['Amount']:.2f} | "
            f"Fraude: {txn['Class']}"
        )

        if SEND_DELAY > 0:
            time.sleep(SEND_DELAY)

    except Exception as exc:
        print(f"Erreur envoi : {exc}")


producer.flush()
producer.close()

print("Envoi termine.")