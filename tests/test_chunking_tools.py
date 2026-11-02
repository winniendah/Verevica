import subprocess
import sys

from core.chunking import format_rujukan, pecah_dokumen
from core.tools import baca_draf_proposal

HAL = [{"no": 1, "teks": "BAB I PENDAHULUAN\nIsi bab satu.\nBAB II RAB\nRAB wajib memuat harga per unit."},
       {"no": 2, "teks": "Lanjutan bab dua."}]


def test_chunk_per_bab_dengan_metadata():
    ch = pecah_dokumen("p.pdf", HAL)
    judul = [c["meta"]["judul"] for c in ch]
    assert "BAB I PENDAHULUAN" in judul and "BAB II RAB" in judul
    bab2 = next(c for c in ch if c["meta"]["judul"] == "BAB II RAB")
    assert bab2["meta"]["halaman"] == 1 and "harga per unit" in bab2["teks"]


def test_rujukan_tanpa_halaman_tidak_mengarang():
    assert "halaman" not in format_rujukan({"dokumen": "a.docx", "judul": "BAB I", "halaman": 0})
    assert format_rujukan({"dokumen": "a.pdf", "judul": "BAB I", "halaman": 3}).endswith("halaman 3")


def test_baca_docx_contoh(tmp_path):
    subprocess.run([sys.executable, "gen_contoh.py"], check=True)
    r = baca_draf_proposal("data/contoh_proposal/02_proposal_rab_tanpa_harga_satuan.docx")
    assert not r["gagal"] and "Pembelian alat tulis" in r["teks"]


def test_file_hampir_kosong_ditandai_gagal(tmp_path):
    from docx import Document
    d = Document(); d.add_paragraph("pendek"); p = tmp_path / "x.docx"; d.save(p)
    assert baca_draf_proposal(str(p))["gagal"]
