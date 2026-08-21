from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from azure.storage.blob import BlobClient
import joblib
import os
from urllib.request import urlretrieve

app = FastAPI()

AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER")
AZURE_MODEL_URL = os.environ.get("AZURE_MODEL_URL")
AZURE_MODEL_BLOB = "models/latest/model.pkl"
MODEL_PATH = os.path.expanduser("~/models/model.pkl")


def download_model():
    """
    Tai file model.pkl tu Azure Blob Storage ve may khi server khoi dong.

    Ham nay duoc goi mot lan khi module duoc import. Su dung
    AZURE_STORAGE_CONNECTION_STRING de xac thuc (duoc dat trong systemd service).
    """
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    if AZURE_MODEL_URL:
        urlretrieve(AZURE_MODEL_URL, MODEL_PATH)
        print("Downloaded model from AZURE_MODEL_URL")
        return

    if not AZURE_STORAGE_CONNECTION_STRING:
        raise RuntimeError("Missing required environment variable AZURE_STORAGE_CONNECTION_STRING")
    if not AZURE_STORAGE_CONTAINER:
        raise RuntimeError("Missing required environment variable AZURE_STORAGE_CONTAINER")

    blob = BlobClient.from_connection_string(
        conn_str=AZURE_STORAGE_CONNECTION_STRING,
        container_name=AZURE_STORAGE_CONTAINER,
        blob_name=AZURE_MODEL_BLOB,
    )
    with open(MODEL_PATH, "wb") as f:
        f.write(blob.download_blob().readall())

    print(f"Downloaded model from azure://{AZURE_STORAGE_CONTAINER}/{AZURE_MODEL_BLOB}")


download_model()
model = joblib.load(MODEL_PATH)


class PredictRequest(BaseModel):
    features: list[float]


@app.get("/health")
def health():
    """
    Endpoint kiem tra suc khoe server.
    GitHub Actions goi endpoint nay sau khi deploy de xac nhan server dang chay.

    Tra ve: {"status": "ok"}
    """
    return {"status": "ok"}


@app.post("/predict")
def predict(req: PredictRequest):
    """
    Endpoint suy luan chinh.

    Dau vao : JSON {"features": [f1, f2, ..., f12]}
    Dau ra  : JSON {"prediction": <0|1|2>, "label": <"thap"|"trung_binh"|"cao">}

    Thu tu 12 dac trung (khop voi thu tu trong FEATURE_NAMES cua test):
        fixed_acidity, volatile_acidity, citric_acid, residual_sugar,
        chlorides, free_sulfur_dioxide, total_sulfur_dioxide, density,
        pH, sulphates, alcohol, wine_type
    """
    if len(req.features) != 12:
        raise HTTPException(
            status_code=400,
            detail="Expected 12 features (wine quality)",
        )

    pred = int(model.predict([req.features])[0])
    labels = {0: "thap", 1: "trung_binh", 2: "cao"}
    return {"prediction": pred, "label": labels.get(pred, "unknown")}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
