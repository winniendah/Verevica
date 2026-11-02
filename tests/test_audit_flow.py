"""Uji alur audit() dengan LLM & retrieval tiruan (tanpa API key / vector DB)."""
import json

from core import auditor

RUJ = "pedoman.pdf, BAB III RAB, halaman 12"
ATURAN = {"ditemukan": True, "catatan": "", "hasil": [
    {"teks": "RAB wajib memuat harga per unit.", "rujukan": RUJ, "jarak": 0.3,
     "dokumen": "pedoman.pdf", "judul": "BAB III RAB", "halaman": 12, "chunk_id": "x"}]}


class FakeLLM:
    def __init__(self, evaluasi):
        self.evaluasi = list(evaluasi)
        self.jumlah_panggilan = 0

    def generate_json(self, system, prompt):
        self.jumlah_panggilan += 1
        if "mengidentifikasi komponen" in system:
            return json.dumps({"komponen": []})
        return self.evaluasi.pop(0)

    def statistik(self):
        return {"model": "fake", "jumlah_panggilan_llm": self.jumlah_panggilan, "token_input": 0, "token_output": 0}


def _ok(nama):
    return json.dumps(dict(komponen_proposal=nama, status_kepatuhan="PERLU_REVISI",
                           bukti_teks_proposal="Pembelian alat tulis | Rp500.000", pasal_pedoman_rujukan=RUJ,
                           catatan_revisi_sekretaris="Lengkapi harga per unit.", dapat_ditentukan="YA",
                           alasan_tidak_dapat_ditentukan=None))


def _dua_komponen():
    return auditor.config.KOMPONEN[:2]


def test_berhasil(monkeypatch):
    monkeypatch.setattr(auditor, "cari_aturan_pedoman", lambda *a, **k: ATURAN)
    lap = auditor.audit("data/contoh_proposal/02_proposal_rab_tanpa_harga_satuan.docx",
                        FakeLLM([_ok("a"), _ok("b")]), komponen=_dua_komponen())
    assert lap["status_proses"] == "BERHASIL" and len(lap["hasil_pemeriksaan"]) == 2


def test_perbaikan_satu_kali_lalu_berhasil(monkeypatch):
    monkeypatch.setattr(auditor, "cari_aturan_pedoman", lambda *a, **k: ATURAN)
    lap = auditor.audit("data/contoh_proposal/02_proposal_rab_tanpa_harga_satuan.docx",
                        FakeLLM(["bukan json", _ok("a"), _ok("b")]), komponen=_dua_komponen())
    assert lap["status_proses"] == "BERHASIL"


def test_gagal_eksplisit_setelah_perbaikan(monkeypatch):
    monkeypatch.setattr(auditor, "cari_aturan_pedoman", lambda *a, **k: ATURAN)
    lap = auditor.audit("data/contoh_proposal/02_proposal_rab_tanpa_harga_satuan.docx",
                        FakeLLM(["x", "y", _ok("b")]), komponen=_dua_komponen())
    assert lap["status_proses"] == "SEBAGIAN_GAGAL" and len(lap["komponen_gagal"]) == 1
    assert len(lap["hasil_pemeriksaan"]) == 1


def test_aturan_tidak_ditemukan_tanpa_memanggil_llm(monkeypatch):
    monkeypatch.setattr(auditor, "cari_aturan_pedoman",
                        lambda *a, **k: {"ditemukan": False, "hasil": [], "catatan": "kosong"})
    llm = FakeLLM([])
    lap = auditor.audit("data/contoh_proposal/02_proposal_rab_tanpa_harga_satuan.docx", llm, komponen=_dua_komponen())
    h = lap["hasil_pemeriksaan"][0]
    assert h["status_kepatuhan"] == "TIDAK_LENGKAP" and h["alasan_tidak_dapat_ditentukan"] == "ATURAN_TIDAK_DITEMUKAN"
    assert h["pasal_pedoman_rujukan"] is None and lap["status_proses"] == "BERHASIL"


def test_file_tidak_terbaca_gagal(monkeypatch, tmp_path):
    from docx import Document
    d = Document(); d.add_paragraph("pendek"); p = tmp_path / "x.docx"; d.save(p)
    lap = auditor.audit(str(p), FakeLLM([]))
    assert lap["status_proses"] == "GAGAL" and lap["pesan_kegagalan"]
