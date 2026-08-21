# MLOps Lab Report

## Best hyperparameters

Best local configuration after MLflow experiments:

```yaml
model_type: extra_trees
n_estimators: 500
max_depth: null
min_samples_split: 2
n_jobs: -1
```

Reason: the initial RandomForest experiments on `train_phase1.csv` reached `0.5580` to `0.6440` accuracy. After Step 3 merged `train_phase2.csv` into `train_phase1.csv`, ExtraTrees with 500 estimators reached the best held-out result:

| Stage | Training rows | Accuracy | F1 score |
|---|---:|---:|---:|
| Step 2 baseline | 2998 | 0.6440 | 0.6417 |
| Step 3 final | 5996 | 0.7640 | 0.7632 |

## Notes

- `outputs/metrics.json` stores `accuracy`, `f1_score`, and label distribution.
- `outputs/report.txt` stores the confusion matrix and per-class precision/recall/F1 report.
- `models/model.pkl` is the deployable model artifact.
- DVC remote is configured on Azure Blob Storage at `azure://mlops/dvc`.
- The latest model artifact is uploaded to Azure Blob Storage at `mlops/models/latest/model.pkl`.
- FastAPI is deployed on AWS EC2 and loads the model through a read-only Azure Blob SAS URL stored only on the VM service environment.

## Deployment

Current deployment target:

| Item | Value |
|---|---|
| Cloud VM | AWS EC2 |
| Region | `ap-southeast-1` |
| Instance ID | `i-0b07d50787ab1c06d` |
| Public IP | `18.143.157.230` |
| SSH user | `ubuntu` |
| Service | `mlops-serve` |

Validation:

```text
GET /health -> {"status":"ok"}
POST /predict -> {"prediction":2,"label":"cao"}
```

GitHub Actions deployment needs these repository secrets:

| Secret | Value |
|---|---|
| `CLOUD_BUCKET` | `mlops` |
| `CLOUD_CREDENTIALS` | Azure Storage connection string |
| `VM_HOST` | `18.143.157.230` |
| `VM_USER` | `ubuntu` |
| `VM_SSH_KEY` | Private key for the `mlops-deploy` EC2 key pair |
