import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
import json
import joblib
import os
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

EVAL_THRESHOLD = 0.70
TARGET_COLUMN = "target"


def build_model(params: dict):
    model_params = dict(params)
    model_type = model_params.pop("model_type", "random_forest")

    if model_type == "random_forest":
        return RandomForestClassifier(**model_params, random_state=42)
    if model_type == "extra_trees":
        return ExtraTreesClassifier(**model_params, random_state=42)
    if model_type == "gradient_boosting":
        return GradientBoostingClassifier(**model_params, random_state=42)
    if model_type == "logistic_regression":
        return LogisticRegression(**model_params, random_state=42, max_iter=2000)

    raise ValueError(f"Unsupported model_type: {model_type}")


def train(
    params: dict,
    data_path: str = "data/train_phase1.csv",
    eval_path: str = "data/eval.csv",
) -> float:
    """
    Huan luyen mo hinh va ghi nhan ket qua vao MLflow.

    Tham so:
        params     : dict chua cac sieu tham so cho RandomForestClassifier.
        data_path  : duong dan den file du lieu huan luyen.
        eval_path  : duong dan den file du lieu danh gia.

    Tra ve:
        accuracy (float): do chinh xac tren tap danh gia.
    """

    df_train = pd.read_csv(data_path)
    df_eval = pd.read_csv(eval_path)

    X_train = df_train.drop(columns=[TARGET_COLUMN])
    y_train = df_train[TARGET_COLUMN]
    X_eval = df_eval.drop(columns=[TARGET_COLUMN])
    y_eval = df_eval[TARGET_COLUMN]

    label_distribution = (
        y_train.value_counts(normalize=True)
        .reindex([0, 1, 2], fill_value=0.0)
        .to_dict()
    )
    label_distribution = {str(k): float(v) for k, v in label_distribution.items()}
    low_classes = [label for label, ratio in label_distribution.items() if ratio < 0.10]
    if low_classes:
        print(
            "WARNING: Low label distribution for classes "
            f"{', '.join(low_classes)} (< 10%)."
        )

    with mlflow.start_run():
        mlflow.log_params(params)

        model = build_model(params)
        model.fit(X_train, y_train)

        preds = model.predict(X_eval)
        acc = accuracy_score(y_eval, preds)
        f1 = f1_score(y_eval, preds, average="weighted")

        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1_score", f1)
        mlflow.sklearn.log_model(model, "model")

        print(f"Accuracy: {acc:.4f} | F1: {f1:.4f}")

        os.makedirs("outputs", exist_ok=True)
        metrics = {
            "accuracy": float(acc),
            "f1_score": float(f1),
            "label_distribution": label_distribution,
        }
        with open("outputs/metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        report = classification_report(y_eval, preds, labels=[0, 1, 2], zero_division=0)
        matrix = confusion_matrix(y_eval, preds, labels=[0, 1, 2])
        with open("outputs/report.txt", "w", encoding="utf-8") as f:
            f.write("Confusion matrix (labels: 0, 1, 2)\n")
            f.write(f"{matrix.tolist()}\n\n")
            f.write("Classification report\n")
            f.write(report)

        os.makedirs("models", exist_ok=True)
        joblib.dump(model, "models/model.pkl")

    return float(acc)


if __name__ == "__main__":
    with open("params.yaml") as f:
        params = yaml.safe_load(f)
    train(params)
