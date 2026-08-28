import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

print("Chargement des donnees...")
df = pd.read_csv("data/creditcard.csv")
print(f"Dataset charge : {df.shape[0]} transactions")
print(f"Fraudes : {df['Class'].sum()} ({df['Class'].mean() * 100:.2f}%)")

print("\nFeature Engineering...")
amount_mean = float(df.loc[X_train.index, "Amount"].mean())
df["heure_nuit"] = df["Time"].apply(
    lambda t: 1 if (t % 86400) < 21600 else 0
)
df["ratio_montant"] = df["Amount"] / (amount_mean + 1)
df["montant_log"] = np.log1p(df["Amount"])

features = [f"V{i}" for i in range(1, 29)] + [
    "heure_nuit",
    "ratio_montant",
    "montant_log",
]
X = df[features]
y = df["Class"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"Train : {X_train.shape[0]} lignes")
print(f"Test  : {X_test.shape[0]} lignes")

print("\nEntrainement XGBoost...")
model = XGBClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    eval_metric="aucpr",
    random_state=42,
)
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=50,
)

print("\nResultats :")
from sklearn.metrics import average_precision_score, confusion_matrix

for seuil in [0.3, 0.7]:
    y_pred_seuil = (y_proba >= seuil).astype(int)
    print(f"--- Seuil {seuil} ---")
    print(classification_report(y_test, y_pred_seuil, target_names=["Normale", "Fraude"]))

print(f"AUC-PR (Average Precision) : {average_precision_score(y_test, y_proba):.4f}")

Path("model").mkdir(exist_ok=True)
with open("model/xgboost_model.pkl", "wb") as f:
    pickle.dump(model, f)

metadata = {
    "amount_mean": amount_mean,
    "features": features,
    "thresholds": {"suspect": 0.3, "fraud": 0.7},
}
with open("model/metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2)

print("\nModele sauvegarde dans model/xgboost_model.pkl")
print(f"Metadonnees sauvegardees (amount_mean={amount_mean:.6f})")
