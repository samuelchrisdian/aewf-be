# 📋 Panduan Import Data - AEWF Backend

Dokumen ini menjelaskan **urutan (flow)** yang benar untuk mengimpor data ke sistem AEWF.

---

## 🔄 Overview Flow

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  1. MASTER DATA     │────▶│  2. SYNC MESIN      │────▶│  3. MAPPING         │────▶│  4. IMPORT LOG      │
│  (Daftar Siswa)     │     │  (User Fingerprint) │     │  (Pencocokan)       │     │  (Absensi Harian)   │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘     └─────────────────────┘
        students                  machine_users             student_machine_map         attendance_raw_log
                                                                                        attendance_daily
```

---

## 📌 Langkah 1: Import Master Data Siswa

### Apa yang dilakukan?
Mengisi tabel `students`, `classes`, dan `teachers` dari file rekap absensi manual sekolah.

### Service yang digunakan
```python
from src.services.master_data_service import MasterDataService

# Untuk file Excel (XLS/XLSX) dengan multiple sheets
result = MasterDataService.import_from_excel("path/to/RekapManual.xls")

# Untuk file CSV per kelas
result = MasterDataService.import_from_csv("path/to/Kelas7A.csv")
```

### Format File yang Didukung
**Excel (XLS/XLSX):**
- Setiap sheet = Grade (Kls 7, Kls 8, Kls 9)
- Satu sheet bisa berisi **multiple kelas** (7A, 7B, dst)
- Format row:
  - Row dengan "Kls / Smt" = Penanda awal kelas
  - Row dengan "Wali Kelas" = Nama guru
  - Row dengan "NO. INDUK" = Header tabel siswa

**CSV:**
- Row 5: `Kls / Smt,,: 7 ( Tujuh ) - A /`
- Row 6: `Wali Kelas,,: Nama Guru, S.Pd`
- Row 8: Header tabel (`NO, NO. INDUK, NAMA...`)

### Tabel yang Terisi
| Tabel | Kolom |
|-------|-------|
| `teachers` | teacher_id, name, role |
| `classes` | class_id, class_name, wali_kelas_id |
| `students` | nis, name, class_id |

### API Endpoint
```http
POST /api/v1/import/master-data
Content-Type: multipart/form-data

file: <file>
```

---

## 📌 Langkah 2: Sync User Mesin (Fingerprint)

### Apa yang dilakukan?
Mengisi tabel `machine_users` dari file report mesin absensi fingerprint.

### Service yang digunakan
```python
from src.services.machine_service import MachineService

result = MachineService.sync_users_from_excel(
    file_path="path/to/AttendanceReport.xls",
    machine_code="MACHINE_01",
    auto_create_machine=False  # Set True untuk auto-create machine
)
```

### Format File
- Sheet: "Att. Stat." atau sheet dengan kata "stat"
- Kolom wajib: `ID`, `Name`/`Nama`, `Department`

### ⚠️ Filter Penting
**Hanya user dengan `Department = 'SMP'` yang akan di-import!**

User dari department lain (GTT, GTY, OB, dll) akan di-skip untuk menghindari data guru/staff masuk ke mapping siswa.

### Tabel yang Terisi
| Tabel | Kolom |
|-------|-------|
| `machines` | machine_code, location, status, last_sync |
| `machine_users` | machine_user_id, machine_user_name, department, machine_id |

### API Endpoint
```http
POST /api/v1/machines/{machine_code}/sync
Content-Type: multipart/form-data

file: <file>
```

---

## 📌 Langkah 3: Mapping (Pencocokan ID Mesin ↔ NIS Siswa)

### Mengapa Perlu Mapping?
- Data di **mesin**: `ID: 195, Name: Valanchio`
- Data di **master**: `NIS: 2024099, Name: Valanchio Putra`
- **Mesin hanya mencatat ID!** Sistem perlu tahu ID 195 = NIS 2024099

### Service yang digunakan
```python
from src.services.mapping_service import MappingService

# Jalankan auto-mapping dengan fuzzy logic
result = MappingService.run_auto_mapping(confidence_threshold=90)

# Mendapatkan saran mapping untuk verifikasi manual
suggestions = MappingService.get_mapping_suggestions()

# Verifikasi mapping oleh admin
MappingService.verify_mapping(
    mapping_id=123,
    admin_user_id=1,
    status='verified'  # atau 'rejected'
)
```

### Cara Mapping
1. **Otomatis (Fuzzy Logic)**
   - Sistem mencocokkan nama mesin dengan nama master data
   - Threshold default: 90% similarity
   - Hasil: `status = 'pending'` (perlu verifikasi admin)

2. **Manual**
   - Admin verifikasi/reject suggestion
   - Berguna jika nama berbeda jauh (misal: "Boy" → "Bambang")

### Tabel yang Terisi
| Tabel | Kolom |
|-------|-------|
| `student_machine_map` | machine_user_id, student_nis, confidence_score, status, verified_by |

### Status Mapping
| Status | Deskripsi |
|--------|-----------|
| `pending` | Hasil auto-mapping, belum diverifikasi |
| `verified` | Sudah diverifikasi oleh admin |
| `rejected` | Ditolak oleh admin (salah pasangan) |

### API Endpoints
```http
# Get unmapped users dengan suggestions
GET /api/v1/mapping/unmapped

# Run auto-mapping
POST /api/v1/mapping/auto-map

# Get mapping suggestions
GET /api/v1/mapping/suggestions

# Verify/Reject mapping
PUT /api/v1/mapping/{id}/verify
```

---

## 📌 Langkah 4: Import Log Absensi

### Apa yang dilakukan?
Upload data jam scan fingerprint harian ke sistem.

### Service yang digunakan
```python
from src.services.ingestion_service import IngestionService

result = IngestionService.import_logs_from_excel(
    file_path="path/to/AttendanceLog.xls",
    filename="AttendanceLog_Aug2024.xls",
    machine_code="MACHINE_01"
)
# Result includes:
# - logs_imported: jumlah raw logs
# - daily_records_created: jumlah attendance_daily terisi
```

### Format File yang Didukung
1. **Matrix Format** (Attendance Log Report)
   - Header: `Att. Time  2025-08-01 ~ 2025-08-31` (untuk periode)
   - User ID per block: `ID: 75 Name: Stanley Dept.: SMP`
   - Kolom per tanggal (1-31)
   - Isi: Jam scan mashed (contoh: `06:5815:03`)

2. **Flat Format** (Transactional Log)
   - Kolom: ID, DateTime/Waktu
   - 1 baris = 1 scan event

### ⚠️ Filter Penting
**Hanya user dengan `Department = 'SMP'` yang akan di-import!**

User dari department lain (GTT, GTY, OB, dll) akan di-skip.

### Proses Internal (Otomatis)
```
1. Baca log: "ID 75 scan jam 06:47 pada tanggal 1"
2. Ekstrak periode dari "Att. Time: 2025-08-01 ~ 2025-08-31" → Agustus 2025
3. Filter: Skip jika Department != 'SMP'
4. Cari di machine_users: ID 75 → MachineUser (id=12)
5. Simpan ke attendance_raw_log

-- AGREGASI OTOMATIS --
6. Cari mapping: MachineUser 12 → Student NIS 273  
7. Hitung: check_in = 06:47 (earliest), check_out = 13:55 (latest)
8. Tentukan status: Hadir (sebelum 07:00)
9. Simpan ke attendance_daily
```

### Tabel yang Terisi
| Tabel | Kolom |
|-------|-------|
| `import_batch` | filename, file_path, machine_code, status |
| `attendance_raw_log` | batch_id, machine_user_id_fk, event_time |
| `attendance_daily` | student_nis, attendance_date, check_in, check_out, status |

### API Endpoint
```http
POST /api/v1/import/attendance-logs
Content-Type: multipart/form-data

file: <file>
machine_code: MACHINE_01
```

---

## ⚠️ Troubleshooting

### Error: "User ID XXX not found in machine"
**Penyebab**: Log absensi memiliki ID yang belum di-sync ke `machine_users`  
**Solusi**: Jalankan Langkah 2 (Sync User Mesin) terlebih dahulu

### Error: "Student mapping not found for machine user"
**Penyebab**: ID Mesin belum di-mapping ke NIS Siswa  
**Solusi**: Jalankan Langkah 3 (Mapping)

### Error: "Nama kelas tidak ditemukan"
**Penyebab**: Format file master data tidak sesuai  
**Solusi**: Pastikan ada baris dengan format `Kls / Smt : 7 ( Tujuh ) - A`

### Siswa dari kelas tertentu tidak ter-import
**Penyebab**: Multiple kelas dalam satu sheet tidak ter-deteksi  
**Solusi**: Pastikan setiap kelas diawali baris `Kls / Smt`

---

## 📊 Ringkasan Tabel Database

```
┌─────────────┐     ┌─────────────────┐     ┌────────────────────┐
│  students   │◄────│ student_machine │────▶│   machine_users    │
│  (NIS)      │     │     _map        │     │   (machine ID)     │
└─────────────┘     └─────────────────┘     └────────────────────┘
       │                                              │
       │                                              │
       ▼                                              ▼
┌─────────────────┐                         ┌────────────────────┐
│ attendance_daily│◄────────────────────────│ attendance_raw_log │
│   (per siswa)   │                         │   (per scan)       │
└─────────────────┘                         └────────────────────┘
```

---

## 📅 Rekomendasi Jadwal Import

| Langkah | Frekuensi | Keterangan |
|---------|-----------|------------|
| 1. Master Data | Per semester | Saat ada siswa baru/naik kelas |
| 2. Sync Mesin | Saat ada user baru di mesin | Admin register siswa baru |
| 3. Mapping | Setelah sync mesin | Pastikan semua user ter-mapping |
| 4. Log Absensi | Harian/Mingguan | Semakin sering, data semakin akurat |

---

*Dokumen ini di-generate untuk AEWF Backend v1.0*
