FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    default-jdk \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN pip install \
    pyspark==3.5.0 \
    xgboost==2.0.0 \
    scikit-learn==1.4.0 \
    pymongo==4.6.0 \
    pandas==2.2.0 \
    numpy==1.26.0 \
    kafka-python==2.0.2

# Télécharger le connecteur Kafka pour Spark
RUN wget -P /usr/local/lib/python3.10/site-packages/pyspark/jars/ \
    https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.0/spark-sql-kafka-0-10_2.12-3.5.0.jar

RUN wget -P /usr/local/lib/python3.10/site-packages/pyspark/jars/ \
    https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.1/kafka-clients-3.4.1.jar

RUN wget -P /usr/local/lib/python3.10/site-packages/pyspark/jars/ \
    https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.0/spark-token-provider-kafka-0-10_2.12-3.5.0.jar

RUN wget -P /usr/local/lib/python3.10/site-packages/pyspark/jars/ \
    https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar

COPY pipeline.py /app/pipeline.py

CMD ["python", "/app/pipeline.py"]