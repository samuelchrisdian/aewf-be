# 🤖 Panduan Machine Learning - AEWF Backend (Early Warning System)

Dokumen ini menjelaskan **arsitektur dan flow** sistem Machine Learning untuk Early Warning System (EWS) yang digunakan dalam AEWF.

---

## 🎯 Tujuan Sistem

Sistem ML EWS bertujuan untuk:
1. **Mendeteksi siswa berisiko** (at-risk) secara dini berdasarkan pola kehadiran
2. **Mengklasifikasi risiko** ke dalam 3 tier: 🔴 RED, 🟡 YELLOW, 🟢 GREEN
3. **Memberikan penjelasan** faktor-faktor yang mempengaruhi prediksi

### Success Criteria (Target Thesis)
| Metrik | Target | Dicapai |
|--------|--------|---------|
| Recall (At-Risk) | ≥ 0.70 | ✅ 0.89 |
| F1-Score | ≥ 0.65 | ✅ 0.94 |
| AUC-ROC | ≥ 0.75 | ✅ 1.00 |
| Respons API | < 3 detik | ✅ <100ms |

---

## 🔄 Overview Flow

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  1. PREPROCESSING   │────▶│  2. TRAINING        │────▶│  3. PREDICTION      │────▶│  4. INTERPRETATION  │
│  (Feature Engineer) │     │  (Model Training)   │     │  (Hybrid Engine)    │     │  (Natural Language) │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘     └─────────────────────┘
   src/ml/preprocessing.py     src/ml/training.py      src/services/ml_service.py   src/ml/interpretation.py
           │                          │                          │                          │
           ▼                          ▼                          ▼                          ▼
     Feature DataFrame          models/ews_model.pkl        Risk Prediction          Indonesian Text
                               models/ews_explainer_tree.pkl (RED/YELLOW/GREEN)       (explanation_text)
```

---

## 📌 Komponen 1: Feature Engineering (Preprocessing)

### Lokasi File
```
src/ml/preprocessing.py
```

### Apa yang dilakukan?
Mengubah data kehadiran mentah menjadi **11 fitur** yang siap digunakan untuk model ML.

### Fitur yang Di-generate

| Fitur | Tipe | Deskripsi |
|-------|------|-----------|
| `absent_count` | int | Total ketidakhadiran (**termasuk inferred**) |
| `late_count` | int | Total keterlambatan |
| `present_count` | int | Total hadir tepat waktu |
| `permission_count` | int | Total izin |
| `sick_count` | int | Total sakit |
| `total_days` | int | **Expected** hari sekolah (bukan recorded) |
| `absent_ratio` | float | Rasio ketidakhadiran (0.0-1.0) |
| `late_ratio` | float | Rasio keterlambatan (0.0-1.0) |
| `attendance_ratio` | float | Rasio kehadiran (0.0-1.0) |
| `trend_score` | float | Tren 7 hari terakhir (-1 s/d +1) |
| `is_rule_triggered` | bool | True jika memenuhi rule threshold |

### 🔑 Inferred Absences (Fitur Penting!)

Siswa yang **tidak memiliki record kehadiran** pada hari tertentu dianggap **absent**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PERHITUNGAN INFERRED ABSENCES                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Expected School Days = MAX(recorded_days) dari semua siswa             │
│                       = Hari terbanyak yang di-record                   │
│                                                                         │
│  Contoh: Jika siswa terbaik punya 21 hari record,                      │
│          maka expected_school_days = 21                                 │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Inferred Absent = Expected - Recorded Days                             │
│                                                                         │
│  Contoh:                                                                │
│  - Siswa A: 21 records → Inferred Absent = 0                           │
│  - Siswa B: 5 records  → Inferred Absent = 21 - 5 = 16                 │
│  - Siswa C: 1 record   → Inferred Absent = 21 - 1 = 20                 │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Total Absent = Recorded Absent + Inferred Absent                       │
│                                                                         │
│  Contoh Siswa B:                                                        │
│  - Recorded: 5 days (4 present, 1 late, 0 absent)                      │
│  - Inferred Absent: 16                                                  │
│  - Total Absent: 0 + 16 = 16                                           │
│  - Absent Ratio: 16 / 21 = 76% → 🔴 HIGH RISK!                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Mengapa ini penting?**
- Siswa yang jarang/tidak pernah scan fingerprint tidak boleh dianggap "baik"
- Tanpa fitur ini, siswa dengan 1 hari hadir akan dianggap 100% attendance!
- Inferred absences menangkap siswa yang **completely missing** dari sekolah

### Konstanta Penting
```python
ABSENT_RATIO_THRESHOLD = 0.15   # Jika absent_ratio > 15% → Rule triggered
ABSENT_COUNT_THRESHOLD = 5      # Jika total_absent > 5  → Rule triggered
```

### Cara Penggunaan
```python
from src.ml.preprocessing import (
    engineer_features,              # Dari database
    engineer_features_from_df,      # Dari DataFrame
    engineer_features_for_student,  # Untuk 1 siswa
    FEATURE_COLUMNS                 # List nama fitur
)

# Dari database (untuk training)
features_df = engineer_features()

# Dari DataFrame custom (untuk validasi)
features_df = engineer_features_from_df(my_dataframe)

# Untuk 1 siswa (untuk prediksi)
features_dict = engineer_features_for_student("2024001")
```

### Perhitungan Trend Score
```
                      Minggu Lalu        7 Hari Terakhir
                      (14-7 hari)        (7-0 hari)
                         │                    │
                         ▼                    ▼
    trend_score = (good_rate_recent) - (good_rate_previous)
    
    Nilai:
    - Positif (+) = Membaik (lebih banyak hadir)
    - Negatif (-) = Memburuk (lebih banyak absen)
    - 0           = Stabil
```

---

## 📌 Komponen 2: Model Training

### Lokasi File
```
src/ml/training.py
```

### Apa yang dilakukan?
Melatih model **Logistic Regression** dengan optimisasi untuk mencapai target Recall ≥ 0.70.

### Algoritma yang Digunakan
- **Model**: Logistic Regression dengan `class_weight='balanced'`
- **Handling Imbalance**: SMOTE (Synthetic Minority Over-sampling Technique)
- **Threshold Tuning**: Otomatis menurunkan threshold jika Recall < 0.70

### Flow Training
```
┌──────────────────┐
│      Data        │
│  (DataFrame)     │
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Split 80/20     │
│  (Stratified)    │
└────────┬─────────┘
         ▼
┌──────────────────┐
│     SMOTE        │  ← Oversample minority class
│  (Resample)      │
└────────┬─────────┘
         ▼
┌──────────────────┐
│ LogisticRegression│  ← class_weight='balanced'
│   (Training)     │
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Threshold Tuning │  ← Jika Recall < 0.70, turunkan threshold
│  (0.50 → 0.30)   │
└────────┬─────────┘
         ▼
┌──────────────────┐
│   Save Model     │
│   + Metadata     │
└──────────────────┘
```

### Automatic Threshold Tuning
```python
# Jika Recall < 0.70 pada threshold default (0.50):
while threshold >= 0.30:
    if recall >= 0.70:
        break  # Threshold optimal ditemukan
    threshold -= 0.05  # Turunkan threshold
```

### File Output
| File | Lokasi | Isi |
|------|--------|-----|
| `ews_model.pkl` | `models/` | Model Logistic Regression (pickle) |
| `ews_explainer_tree.pkl` | `models/` | Model Decision Tree untuk explainability |
| `model_metadata.json` | `models/` | Threshold, metrics, feature importance |

### Cara Penggunaan
```python
from src.ml.training import train_and_save_models, load_model

# Training dari database
result = train_and_save_models()
print(result['metrics'])  # {'recall': 1.0, 'f1': 1.0, 'auc_roc': 1.0}

# Training dari DataFrame custom
result = train_and_save_models(my_features_df)

# Load model yang sudah di-train
model, explainer_tree, metadata = load_model()
print(metadata['threshold'])  # 0.5
```

### Feature Importance
Model akan log **feature importance** berdasarkan koefisien Logistic Regression:

```
============================================================
FEATURE IMPORTANCE (LogisticRegression Coefficients)
------------------------------------------------------------
  absent_count        : +1.0345 ↑  (Meningkatkan risiko)
  sick_count          : -0.9704 ↓  (Menurunkan risiko)
  late_count          : +0.8010 ↑
  permission_count    : -0.5651 ↓
  present_count       : -0.2481 ↓
============================================================
```

---

## 📌 Komponen 3: Hybrid Prediction Service

### Lokasi File
```
src/services/ml_service.py
```

### Apa yang dilakukan?
Melakukan **prediksi risiko** dengan logika **HYBRID**:
1. **Rule-Based Check** → Deteksi kasus ekstrem
2. **ML-Based Check** → Klasifikasi probabilitas

### Flow Prediksi Hybrid
```
              ┌───────────────────────────────────────────────┐
              │           predict_risk(nis="2024001")         │
              └───────────────────┬───────────────────────────┘
                                  │
                                  ▼
              ┌───────────────────────────────────────────────┐
              │           Engineer Features                    │
              │   (absent_ratio, late_ratio, trend, dll)      │
              └───────────────────┬───────────────────────────┘
                                  │
                                  ▼
              ┌───────────────────────────────────────────────┐
              │        STEP 1: RULE-BASED CHECK               │
              │                                               │
              │   IF absent_ratio > 0.15  ────▶  🔴 RED       │
              │   OR absent_count > 5     ────▶  (Rule Override)
              └───────────────────┬───────────────────────────┘
                                  │ (jika tidak triggered)
                                  ▼
              ┌───────────────────────────────────────────────┐
              │        STEP 2: ML-BASED CHECK                 │
              │                                               │
              │   probability = model.predict_proba(X)        │
              │                                               │
              │   IF prob > 0.70  ─────────▶  🔴 RED          │
              │   ELIF prob > 0.40  ───────▶  🟡 YELLOW       │
              │   ELSE  ───────────────────▶  🟢 GREEN        │
              └───────────────────────────────────────────────┘
```

### Risk Tier Definition
| Tier | Warna | Threshold | Aksi yang Direkomendasikan |
|------|-------|-----------|---------------------------|
| RED | 🔴 | Prob > 0.70 atau Rule Triggered | Hubungi orang tua segera |
| YELLOW | 🟡 | Prob 0.40 - 0.70 | Monitoring ketat 2 minggu |
| GREEN | 🟢 | Prob < 0.40 | Monitoring rutin |

### Cara Penggunaan
```python
from src.services.ml_service import MLService

# Prediksi 1 siswa
result = MLService.predict_risk("2024001")
print(result)
# Output:
# {
#     "nis": "2024001",
#     "risk_tier": "RED",
#     "risk_probability": 0.85,
#     "is_rule_overridden": False,
#     "prediction_method": "ml",
#     "factors": {
#         "absent_ratio": 0.12,
#         "absent_count": 4,
#         "late_ratio": 0.08,
#         "trend_score": -0.15
#     },
#     "response_time_ms": 12.5
# }

# Prediksi batch (multiple siswa)
results = MLService.predict_risk_batch(["2024001", "2024002", "2024003"])

# Training model
training_result = MLService.train_models()

# Info model saat ini
info = MLService.get_model_info()

# Feature importance
importance = MLService.get_feature_importance()
```

### Response Format
```json
{
    "nis": "2024001",
    "risk_tier": "RED",
    "risk_probability": 0.85,
    "explanation_text": "Faktor Utama Risiko (Berdasarkan Bobot):\n- Total Ketidakhadiran tergolong tinggi (6 hari).\n- Tren Kehadiran memburuk dalam 7 hari terakhir.\n\nLogika Deteksi (Aturan):\n- Rasio Absensi > 0.12",
    "is_rule_overridden": false,
    "prediction_method": "ml",
    "model_threshold": 0.5,
    "factors": {
        "absent_ratio": 0.12,
        "absent_count": 4,
        "late_ratio": 0.08,
        "late_count": 3,
        "trend_score": -0.15,
        "total_days": 30,
        "attendance_ratio": 0.75
    },
    "response_time_ms": 12.5
}
```

---

## 📌 Komponen 4: Validation Script

### Lokasi File
```
src/ml/validation_script.py
```

### Apa yang dilakukan?
Script untuk **testing dan validasi** pipeline ML secara end-to-end.

### Fitur
1. Generate mock data (100 siswa: 10 at-risk, 90 normal)
2. Jalankan training pipeline
3. Validasi metrics terhadap target
4. Test hybrid logic dengan 5 test case

### Cara Menjalankan
```bash
# Full validation
py -m src.ml.validation_script

# Quick test (20 siswa, tanpa assertions)
py -m src.ml.validation_script --quick
```

### Test Cases yang Di-validasi
| Case | Deskripsi | Expected |
|------|-----------|----------|
| 1 | Siswa normal (95% hadir) | 🟢 GREEN |
| 2 | Siswa sering terlambat | 🟡 YELLOW |
| 3 | Siswa absen tinggi (>15%) | 🔴 RED (Rule) |
| 4 | Edge case (12% absen) | 🟡 YELLOW |
| 5 | Trend memburuk | 🟡/🔴 ML-based |

---

## 🗂️ Struktur File

```
src/
├── ml/
│   ├── preprocessing.py      # Feature engineering
│   ├── training.py          # Model training (LR + DT)
│   ├── interpretation.py    # Natural language explanation (Indonesian)
│   └── validation_script.py # Testing & validation
├── services/
│   └── ml_service.py        # Prediction service (API layer)
└── ...

models/
├── ews_model.pkl            # Trained Logistic Regression model
├── ews_explainer_tree.pkl   # Trained Decision Tree for explainability
└── model_metadata.json      # Metadata (threshold, metrics, features)
```

---

## 🔗 API Endpoints

### Training
```http
POST /api/v1/models/train
Authorization: Bearer <token>

Response:
{
    "status": "success",
    "message": "Models trained successfully",
    "metrics": {
        "recall": 1.0,
        "f1": 1.0,
        "auc_roc": 1.0
    },
    "threshold": 0.5
}
```

### Prediction
```http
POST /api/v1/models/predict
Authorization: Bearer <token>
Content-Type: application/json

{
    "nis": "2024001"
}

Response:
{
    "nis": "2024001",
    "risk_tier": "RED",
    "risk_probability": 0.85,
    "factors": {...}
}
```

### Model Info
```http
GET /api/v1/models/info
Authorization: Bearer <token>

Response:
{
    "status": "available",
    "trained_at": "2025-12-26T12:07:17",
    "model_type": "LogisticRegression",
    "threshold": 0.5,
    "metrics": {...}
}
```

---

## ⚠️ Troubleshooting

### Error: "Model not loaded"
**Penyebab**: Model belum di-train atau file `.pkl` tidak ditemukan  
**Solusi**: Jalankan training terlebih dahulu:
```python
MLService.train_models()
```

### Error: "Not enough class diversity"
**Penyebab**: Semua siswa memiliki label yang sama (semua at-risk atau semua normal)  
**Kemungkinan Penyebab**:
1. Status di database lowercase (`present`, `late`) tapi kode expect capitalized (`Present`, `Late`)
2. Semua siswa memiliki attendance sempurna
3. Tidak ada siswa dengan absences yang terdeteksi

**Solusi**: 
1. Pastikan preprocessing sudah menormalisasi status ke Title Case (sudah diimplementasi)
2. Pastikan ada siswa dengan late_count > 3 atau absent_count > 0
3. Cek apakah inferred absences sudah dihitung

### Error: "sqlite:///aewf.db" instead of PostgreSQL
**Penyebab**: `DATABASE_URL` tidak ter-load dari `.env`  
**Solusi**: Pastikan `load_dotenv()` dipanggil SEBELUM config di-import (sudah diperbaiki di `src/app/__init__.py`)

### Recall rendah (< 0.70)
**Penyebab**: Data sangat imbalanced atau fitur tidak cukup diskriminatif  
**Solusi**: 
1. Tambah threshold tuning (sudah otomatis)
2. Tambah data at-risk
3. Review fitur engineering

### Prediksi selalu GREEN
**Penyebab**: Model belum di-train atau threshold terlalu tinggi  
**Solusi**: 
1. Pastikan model sudah di-train
2. Cek `model_metadata.json` untuk threshold

### Siswa dengan sedikit record dianggap "normal"
**Penyebab**: Inferred absences tidak dihitung  
**Solusi**: Pastikan menggunakan versi terbaru `preprocessing.py` yang menghitung inferred absences

---

## 📊 Interpretasi Hasil

### Feature Importance (Urutan Pengaruh)

Berdasarkan data real dengan inferred absences:

| Ranking | Fitur | Coefficient | Interpretasi |
|---------|-------|-------------|--------------|
| 1 | `absent_count` | +2.08 ↑ | **Paling penting** - termasuk inferred absences |
| 2 | `present_count` | -0.81 ↓ | Kehadiran menurunkan risiko |
| 3 | `is_rule_triggered` | +0.25 ↑ | Rule-based override aktif |
| 4 | `absent_ratio` | +0.08 ↑ | Rasio ketidakhadiran |
| 5 | `late_ratio` | -0.04 ↓ | Rasio keterlambatan |

> **Note**: Koefisien bisa berubah setiap training tergantung data

### Kapan Rule Override Aktif?
Rule override akan memaksa prediksi **RED** tanpa melihat ML jika:
- `absent_ratio > 15%` (lebih dari 15% ketidakhadiran)
- `absent_count > 5` (lebih dari 5 hari absen absolut)

Ini memastikan **siswa dengan absensi ekstrem tidak terlewat** (minimize False Negatives).

### Inferred Absences dalam Rule Override
Karena `absent_count` sekarang termasuk **inferred absences**:
- Siswa dengan hanya 5 hari record dari 21 hari sekolah = 16 inferred absences
- 16 > 5 → **Rule triggered** → 🔴 RED

---

## 📅 Rekomendasi Penggunaan

| Aktivitas | Frekuensi | Catatan |
|-----------|-----------|---------|
| Training Model | Per semester | Atau saat ada perubahan signifikan |
| Prediksi Batch | Mingguan | Untuk monitoring seluruh siswa |
| Prediksi Individual | On-demand | Saat guru/BK ingin cek siswa tertentu |
| Validasi Metrics | Setelah training | Pastikan Recall ≥ 0.70 |

---

### v1.2 (2025-12-26)
- ✅ Added **Explainability Module** (`src/ml/interpretation.py`)
- ✅ Added Decision Tree explainer model (`ews_explainer_tree.pkl`)
- ✅ Added `explanation_text` field with Indonesian natural language
- ✅ Feature name mapping (English → Indonesian)

### v1.1 (2025-12-26)
- ✅ Added **Inferred Absences** calculation
- ✅ Fixed status normalization (lowercase → Title Case)
- ✅ Fixed `load_dotenv()` placement for DATABASE_URL
- ✅ Adjusted at-risk thresholds for `late_count > 3` and `late_ratio > 15%`
- ✅ Updated metrics: Recall 0.89, F1 0.94, AUC-ROC 1.00

### v1.0 (2025-12-26)
- Initial ML EWS implementation
- Hybrid prediction (Rule + ML)
- SMOTE + threshold tuning

---

*Dokumen ini di-generate untuk AEWF Backend v1.2 - Machine Learning Module*
