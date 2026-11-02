# Verevica (Verification & Review Assistant)

Pemeriksa awal draf proposal berbasis RAG + Gemini API (free tier), antarmuka Streamlit.

## Struktur
```
verevica/
├── app.py                  # Streamlit: periksa proposal dan riwayat
├── core/
│   ├── config.py           # setting + daftar KOMPONEN yang diperiksa
│   ├── schemas.py          # skema JSON + tabel kombinasi status (4.2-4.4)
│   ├── tools.py            # baca_draf_proposal, cari_aturan_pedoman (read-only)
│   ├── chunking.py         # chunking per bab/pasal + overlap + metadata
│   ├── indexer.py          # ingest_pedoman(), jumlah_chunk_pedoman(), ChromaDB
│   ├── llm.py              # pembungkus Gemini (retry saat kuota habis)
│   ├── prompts.py          # system prompt (anti prompt injection) + prompt perbaikan
│   ├── validator.py        # validasi struktur + validasi isi (bukti & rujukan)
│   └── auditor.py          # audit(): alur lengkap + kegagalan eksplisit
├── tests/                  # pytest
├── data/pedoman/           # pedoman backend yang diindeks otomatis
├── data/contoh_proposal/   # 4 contoh proposal fiktif untuk pengujian
├── catatan_pengujian_template.csv   # format pencatatan 7.4
└── gen_contoh.py           # pembuat contoh proposal
```

## Menjalankan
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env                                  # Windows; isi GEMINI_API_KEY
streamlit run app.py
```
1. Isi `GEMINI_API_KEY` di `.env`. Nama model dapat diatur melalui `GEMINI_MODEL`; jika tidak diisi, aplikasi memakai model default.
2. Letakkan PDF/DOCX pedoman di `data/pedoman/`. Aplikasi mengindeksnya otomatis dari backend saat mulai.
3. Halaman utama langsung menyediakan unggah proposal (contoh ada di `data/contoh_proposal/`). Klik **Mulai pemeriksaan**, lalu unduh JSON.
4. Uji otomatis (tanpa API key): `python -m pytest -q`

## Kesesuaian dengan rancangan
| Rancangan | Implementasi |
|---|---|
| 3.5 Antarmuka (8 butir) | `app.py` |
| 4.2-4.4 Skema, nilai, kombinasi | `core/schemas.py` |
| 4.5 Validasi → perbaikan 1x → gagal eksplisit | `core/auditor.py::_evaluasi`, `komponen_gagal` |
| 4.6 Validasi isi (bukti & rujukan) | `core/validator.py::validasi_isi` |
| 5.1-5.2 Tool read-only | `core/tools.py` |
| 5.4 Pengindeksan backend | `data/pedoman/` diindeks otomatis saat aplikasi mulai |
| 6.3 Chunking struktur + overlap | `core/chunking.py` |
| 6.4 Retrieval + ambang | `cari_aturan_pedoman` dengan konfigurasi internal |
| 6.6 Aturan tidak ditemukan | `_tidak_ditemukan()` |
| 8.1 Prompt injection | `core/prompts.py` (tag pembatas, sanitasi, instruksi data tidak tepercaya) |
| 7.5 Waktu & biaya | `metrik` pada laporan (durasi, panggilan, token) |

## Catatan
- Free tier punya batas permintaan per menit/hari; satu pemeriksaan memakai sekitar 6 panggilan (1 identifikasi + 1 per komponen, tambah 1 bila ada perbaikan). Saat kena kuota, kode menunggu lalu mencoba lagi.
- Pemeriksaan satu proposal bisa makan 1-2 menit.
- OCR belum ada (sesuai rancangan: belum boleh diklaim). PDF scan akan ditandai gagal ekstraksi.
- Embedding berjalan lokal (sentence-transformers) dan butuh unduhan model sekitar 450 MB pada pengindeksan pertama.
- Deploy: jalankan lokal/Docker/VPS. Streamlit Community Cloud memakai disk sementara sehingga `chroma_db/` hilang saat restart, dan dependensi torch cukup berat.
