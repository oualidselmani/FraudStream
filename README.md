# FraudStream
# Real-Time Bank Fraud Detection System

A Big Data pipeline for real-time bank fraud detection, combining Apache Kafka,
Spark Structured Streaming, MongoDB, and a machine learning model (XGBoost)
exposed through a live monitoring dashboard.

## Description

This project aims to detect fraudulent bank transactions as they happen, rather
than after the fact. Transactions are ingested continuously via **Apache Kafka**,
processed and transformed (feature engineering) by **Spark Structured Streaming**,
then scored by an **XGBoost** model trained on historical transaction data
anonymized via PCA. Each transaction receives a risk score, classified using a
two-threshold strategy. Results are stored in **MongoDB** and displayed through a
real-time monitoring dashboard.

## Architecture

```
Transactions --> Kafka --> Spark Structured Streaming --> XGBoost Model --> MongoDB --> Dashboard
```

## Tech Stack

- **Apache Kafka** -- transaction stream ingestion
- **Spark Structured Streaming** -- real-time processing and feature engineering
- **XGBoost** -- fraud classification / scoring
- **MongoDB** -- storage of results and scores
- **Docker / Docker Compose** -- containerization of all services
- **[Dashboard framework, e.g. Streamlit / Dash / Grafana]** -- monitoring dashboard

## Model Performance

| Metric | Value |
|---|---|
| AUC-ROC | 0.972 |
| AUC-PR | 0.876 |

## Dataset

This project uses the **Credit Card Fraud Detection** dataset (ULB, available on
Kaggle): 284,807 transactions, including 492 fraudulent ones, with 28 features
derived from Principal Component Analysis (PCA) for confidentiality reasons.

The dataset is **not included** in this repository due to its size. To reproduce
the project:

1. Download the dataset from Kaggle:
   [https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud)
2. Place the `creditcard.csv` file in the `data/raw/` folder
3. Follow the installation instructions below

## Installation

```bash
# Clone the repository
git clone https://github.com/[your-username]/[repo-name].git
cd [repo-name]

# Create a Python virtual environment
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the services (Kafka, Spark, MongoDB) via Docker
docker-compose up -d
```

## Usage

```bash
# Start the Kafka producer (transaction stream simulation)
python src/producer.py

# Run the Spark Structured Streaming job
python src/streaming_job.py

# Launch the monitoring dashboard
python src/dashboard.py
```

## Project Structure

```
.
├── data/
│   └── raw/              # dataset (not versioned, must be downloaded)
├── src/
│   ├── producer.py       # Kafka producer
│   ├── streaming_job.py  # Spark Structured Streaming processing
│   ├── model/            # XGBoost training and inference
│   └── dashboard.py      # monitoring dashboard
├── notebooks/            # exploratory analysis, model training
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Author

**Oualid Selmani**

Project completed as part of the Year-End Internship Report (PFA) --
Computer Science and Networks Engineering.


## License

This project was carried out in an academic context.
