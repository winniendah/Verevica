import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE = Path(__file__).resolve().parent.parent
DATA_PEDOMAN = BASE / "data" / "pedoman"
CHROMA_DIR = str(BASE / "chroma_db")
RIWAYAT_DIR = BASE / "riwayat"

EMBED_MODEL = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
# Alias "latest" mengikuti model Flash terbaru. Ganti sesuai daftar model gratis di Google AI Studio.
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
COLLECTION = "pedoman_verevica"

DEFAULT_TOP_K = 4
DEFAULT_MAX_DISTANCE = 0.65  # cosine distance; makin kecil makin ketat
MAX_KARAKTER_PROPOSAL = 60000

# Komponen yang diperiksa. Ubah/tambah sesuai pedoman yang kamu pakai.
KOMPONEN = [
    {"nama": "Format susunan bab",
     "query": "susunan bab sistematika penulisan proposal kegiatan",
     "petunjuk": "Daftar bab/bagian proposal (latar belakang, tujuan, waktu dan tempat, kepanitiaan, anggaran, penutup)."},
    {"nama": "Format RAB",
     "query": "rencana anggaran biaya rincian jumlah satuan harga per unit",
     "petunjuk": "Tabel anggaran/biaya: uraian, jumlah, satuan, harga per unit, total."},
    {"nama": "Susunan kepanitiaan",
     "query": "susunan kepanitiaan struktur panitia divisi penanggung jawab",
     "petunjuk": "Daftar panitia: ketua, sekretaris, bendahara, koordinator divisi. Nama divisi bisa berupa istilah kiasan atau singkatan."},
    {"nama": "Lampiran",
     "query": "lampiran proposal kelengkapan dokumen",
     "petunjuk": "Bagian lampiran atau daftar dokumen pendukung (rundown, surat, CV pemateri, dll)."},
    {"nama": "Surat pengantar",
     "query": "surat pengantar permohonan format surat proposal",
     "petunjuk": "Surat pengantar/permohonan di awal atau lampiran proposal."},
]
