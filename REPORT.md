# Báo Cáo Kết Quả Thực Hành MLOps Lab

**Học viên:** Phạm Thị Thùy Linh  
**Mã học viên:** 2A202601181  
**Repository GitHub:** [K3-Track2-2A202601181-PhamThiThuyLinh-Day21-CI-CD-for-AI-Systems](https://github.com/linhpt111/K3-Track2-2A202601181-PhamThiThuyLinh-Day21-CI-CD-for-AI-Systems)

---

## 1. Kết Quả Thử Nghiệm & Lựa Chọn Siêu Tham Số (Bước 1)

Tôi đã tiến hành huấn luyện và theo dõi nhiều lần chạy bằng MLflow trên tập dữ liệu Wine Quality. Các lần thử nghiệm ban đầu dùng `RandomForestClassifier` với các cấu hình khác nhau trên `train_phase1.csv`, sau đó tiếp tục thử nghiệm mô hình mở rộng khi bổ sung dữ liệu mới ở Bước 3.

Một số kết quả chính:

- **Thử nghiệm 1:** `RandomForestClassifier`, `n_estimators=100`, `max_depth=5`, `min_samples_split=2` -> Accuracy: **0.5640**
- **Thử nghiệm 2:** `RandomForestClassifier`, `n_estimators=50`, `max_depth=3`, `min_samples_split=2` -> Accuracy: **0.5580**
- **Thử nghiệm 3:** `RandomForestClassifier`, `n_estimators=200`, `max_depth=10`, `min_samples_split=5` -> Accuracy: **0.6440**
- **Thử nghiệm cuối sau khi bổ sung dữ liệu Phase 2:** `ExtraTreesClassifier`, `n_estimators=500`, `max_depth=null`, `min_samples_split=2`, `n_jobs=-1` -> Accuracy: **0.7640**, F1-score: **0.7632**

### Quyết định lựa chọn siêu tham số

Tôi đã cập nhật `params.yaml` với cấu hình tốt nhất sau khi so sánh các lần chạy:

```yaml
model_type: extra_trees
n_estimators: 500
max_depth: null
min_samples_split: 2
n_jobs: -1
```

Lý do lựa chọn: mô hình `ExtraTreesClassifier` sau khi gộp thêm dữ liệu `train_phase2.csv` vào `train_phase1.csv` đạt kết quả tốt nhất trên tập đánh giá giữ riêng (`eval.csv`), vượt ngưỡng Eval Gate `0.70` của pipeline CI/CD.

---

## 2. Khó Khăn Gặp Phải & Cách Giải Quyết

### Khó khăn 1: Môi trường local dùng Python 3.13 không tương thích hoàn toàn với dependency gốc

- **Chi tiết:** File `requirements.txt` ban đầu ghim `mlflow==2.13.0` và `scikit-learn==1.4.2`. Trên Python 3.13, một số package cũ không cài đặt hoặc chạy ổn định.
- **Giải quyết:** Tôi dùng phiên bản tương thích hơn cho môi trường local khi thực nghiệm, đồng thời vẫn giữ workflow GitHub Actions chạy bằng Python 3.10 theo yêu cầu lab để đảm bảo pipeline tái lập được.

### Khó khăn 2: Azure không tạo được VM do giới hạn region/size

- **Chi tiết:** Khi thử tạo Azure VM, nhiều region và size nhỏ bị từ chối do `SkuNotAvailable` hoặc giới hạn subscription.
- **Giải quyết:** Tôi chuyển sang sử dụng AWS EC2 cho phần serving, đúng với yêu cầu lab cho phép dùng một trong các cloud VM như GCE, EC2 hoặc Azure VM. Dữ liệu và model artifact vẫn được quản lý trên Azure Blob Storage.

### Khó khăn 3: Cấu hình DVC với Azure Blob Storage và GitHub Actions

- **Chi tiết:** DVC cần remote cloud để CI runner có thể pull dữ liệu thay vì commit trực tiếp file CSV vào Git. Nếu thiếu connection string hoặc cấu hình remote không đúng, job Train sẽ lỗi ở bước `dvc pull`.
- **Giải quyết:** Tôi cấu hình DVC remote là `azure://mlops/dvc`, lưu connection string trong `.dvc/config.local` ở máy local và đưa connection string lên GitHub Actions dưới secret `CLOUD_CREDENTIALS`. Các file CSV được ignore, chỉ commit các file con trỏ `.dvc`.

### Khó khăn 4: FastAPI trên EC2 cần tải model từ Azure Blob bằng SAS URL

- **Chi tiết:** EC2 chạy trên AWS nên không nên lưu connection string Azure đầy đủ trên máy chủ inference. Ngoài ra, systemd xử lý ký tự `%` trong SAS URL như specifier, làm biến môi trường `AZURE_MODEL_URL` bị bỏ qua.
- **Giải quyết:** Tôi tạo SAS URL chỉ đọc cho blob `models/latest/model.pkl`, lưu URL này vào systemd environment của service `mlops-serve` và escape ký tự `%` thành `%%` để systemd đọc đúng. Service sau đó tải model thành công khi khởi động.

### Khó khăn 5: GitHub Actions Deploy không SSH được vào EC2

- **Chi tiết:** Security group ban đầu chỉ mở port SSH cho IP cá nhân, trong khi GitHub Actions runner dùng IP khác nên job Deploy bị timeout.
- **Giải quyết:** Tôi mở tạm thời port `22` cho GitHub Actions trong lúc rerun Deploy, sau khi workflow xanh thì đóng lại ngay. Trạng thái cuối cùng của security group chỉ còn mở `22` và `8000` cho IP cá nhân.

---

## 3. Kết Quả CI/CD & Triển Khai

Pipeline GitHub Actions gồm 4 job:

- **Unit Test:** chạy `pytest tests/ -v`
- **Train:** pull dữ liệu bằng DVC, train model, ghi `metrics.json`, upload model lên Azure Blob
- **Eval:** kiểm tra accuracy phải đạt ít nhất `0.70`
- **Deploy:** SSH vào EC2, restart service `mlops-serve`, kiểm tra `/health`

Run GitHub Actions đã hoàn thành thành công:

- **Run URL:** https://github.com/linhpt111/K3-Track2-2A202601181-PhamThiThuyLinh-Day21-CI-CD-for-AI-Systems/actions/runs/32502234033
- **Kết quả:** 4 job đều xanh: `Unit Test`, `Train`, `Eval`, `Deploy`
- **Artifact:** `metrics`, gồm `outputs/metrics.json` và `outputs/report.txt`

Thông tin triển khai:

| Thành phần | Giá trị |
|---|---|
| Object Storage | Azure Blob Storage |
| Container | `mlops` |
| DVC remote | `azure://mlops/dvc` |
| Model artifact | `models/latest/model.pkl` |
| Cloud VM | AWS EC2 |
| Region | `ap-southeast-1` |
| Instance ID | `i-0b07d50787ab1c06d` |
| Public IP | `18.143.157.230` |
| Service | `mlops-serve` |

Kết quả kiểm thử endpoint sau deploy:

```text
GET /health -> {"status":"ok"}
POST /predict -> {"prediction":0,"label":"thap"}
```

---

## 4. Hoàn Thành Các Thách Thức Nâng Cao (Bonus)

Tôi đã hoàn thành **3 trên 5** thách thức nâng cao trong rubric.

### Bonus 2: Thí nghiệm với nhiều thuật toán (+4 điểm)

- **Cấu hình:** Cập nhật `src/train.py` để hỗ trợ tham số `model_type` trong `params.yaml`.
- **Hỗ trợ:** Có thể chọn giữa `random_forest`, `extra_trees`, `gradient_boosting` và `logistic_regression`.
- **Kết quả:** Mô hình tốt nhất trong bài là `extra_trees`.

### Bonus 3: Báo cáo hiệu suất tự động (+4 điểm)

- **Tính toán:** Sau mỗi lần train, script tự động sinh confusion matrix và classification report gồm precision, recall, F1-score cho từng lớp.
- **Lưu trữ:** Báo cáo được ghi vào `outputs/report.txt` và upload cùng `outputs/metrics.json` dưới dạng artifact của GitHub Actions.

### Bonus 5: Cảnh báo lệch phân phối dữ liệu (+4 điểm)

- **Kiểm tra:** `src/train.py` tính phân phối nhãn của tập train cho các lớp `0`, `1`, `2`.
- **Cảnh báo:** Nếu một lớp chiếm dưới 10% tổng số mẫu, script in cảnh báo trong log.
- **Lưu trữ:** Phân phối nhãn được lưu trong `outputs/metrics.json` bên cạnh `accuracy` và `f1_score`.

---

## 5. Kết Luận

Bài lab đã hoàn thành đầy đủ luồng MLOps từ thực nghiệm local đến CI/CD và triển khai inference:

- MLflow theo dõi nhiều lần thử nghiệm mô hình.
- DVC quản lý dữ liệu với remote trên Azure Blob Storage.
- GitHub Actions tự động test, train, eval và deploy.
- Eval Gate đảm bảo chỉ deploy khi accuracy đạt ngưỡng `0.70`.
- FastAPI chạy trên AWS EC2 và phục vụ model mới nhất từ Azure Blob.

Kết quả cuối cùng đạt accuracy **0.7640**, vượt ngưỡng yêu cầu của lab và API inference hoạt động ổn định sau deploy.
