"""Alur: baca proposal -> identifikasi komponen -> cari aturan -> evaluasi AI -> validasi -> laporan."""
import json
import time

from . import config
from .prompts import (SYSTEM_EVALUASI, SYSTEM_IDENTIFIKASI, prompt_evaluasi, prompt_identifikasi,
                      prompt_perbaikan)
from .schemas import HasilKomponen, KomponenGagal, LaporanAudit
from .tools import baca_draf_proposal, cari_aturan_pedoman
from .validator import ValidasiError, bersihkan_json, norm, validasi_isi, validasi_struktur


def _identifikasi(klien, komponen, teks) -> dict:
    """Return {nama: (ditemukan|None, kutipan|None)}. Jika gagal, kembali ke teks penuh."""
    kosong = {k["nama"]: (None, None) for k in komponen}
    try:
        raw = klien.generate_json(SYSTEM_IDENTIFIKASI, prompt_identifikasi(komponen, teks))
        data = json.loads(bersihkan_json(raw))
        out = dict(kosong)
        for item in data.get("komponen", []):
            nama, kut = item.get("nama"), item.get("kutipan")
            if nama in out:
                valid = bool(kut) and norm(kut) in norm(teks)  # kutipan harus benar-benar ada di proposal
                out[nama] = (bool(item.get("ditemukan")), kut if valid else None)
        return out
    except Exception:
        return kosong


def _evaluasi(klien, komp, teks, kutipan, ditemukan, aturan) -> HasilKomponen:
    rujukan_valid = {a["rujukan"] for a in aturan}
    konteks = kutipan if kutipan else teks
    prompt = prompt_evaluasi(komp["nama"], ditemukan, aturan, konteks)
    raw, err = "", ""
    for percobaan in range(2):  # 1x percobaan + 1x perbaikan
        raw = klien.generate_json(SYSTEM_EVALUASI, prompt if percobaan == 0 else prompt_perbaikan(prompt, raw, err))
        try:
            h = validasi_struktur(raw)
            validasi_isi(h, teks, rujukan_valid)
            return h
        except ValidasiError as e:
            err = str(e)
    raise ValidasiError(err)


def _tidak_ditemukan(nama, catatan) -> HasilKomponen:
    return HasilKomponen(
        komponen_proposal=nama, status_kepatuhan="TIDAK_LENGKAP", bukti_teks_proposal=None,
        pasal_pedoman_rujukan=None, dapat_ditentukan="TIDAK",
        alasan_tidak_dapat_ditentukan="ATURAN_TIDAK_DITEMUKAN",
        catatan_revisi_sekretaris=("Aturan relevan tidak ditemukan pada pedoman yang tersedia, sehingga status belum dapat "
                                   "ditentukan. Ini bukan berarti proposal melanggar. Lakukan pemeriksaan manual atau "
                                   f"tambahkan dokumen pedoman. ({catatan})"))


def audit(path_proposal: str, klien, top_k: int = config.DEFAULT_TOP_K,
          max_distance: float = config.DEFAULT_MAX_DISTANCE, komponen: list | None = None,
          progres=None) -> dict:
    t0 = time.time()
    komponen = komponen or config.KOMPONEN
    lap = LaporanAudit(status_proses="GAGAL")

    doc = baca_draf_proposal(path_proposal)
    lap.peringatan = list(doc["peringatan"])
    if doc["gagal"]:
        lap.pesan_kegagalan = doc["pesan"]
        return lap.model_dump(mode="json")

    teks = doc["teks"]
    if len(teks) > config.MAX_KARAKTER_PROPOSAL:
        lap.peringatan.append(f"Proposal dipotong ke {config.MAX_KARAKTER_PROPOSAL} karakter pertama untuk pemeriksaan.")
        teks = teks[:config.MAX_KARAKTER_PROPOSAL]

    if progres:
        progres(0.05, "Mengidentifikasi komponen proposal…")
    ident = _identifikasi(klien, komponen, teks)

    for i, komp in enumerate(komponen):
        if progres:
            progres(0.1 + 0.85 * i / len(komponen), f"Memeriksa: {komp['nama']}")
        ditemukan, kutipan = ident[komp["nama"]]
        query = komp["query"] + (" " + kutipan[:300] if kutipan else "")
        r = cari_aturan_pedoman(query, top_k, max_distance)
        lap.jejak_retrieval[komp["nama"]] = [
            {"rujukan": a["rujukan"], "jarak": a["jarak"], "cuplikan": a["teks"][:400]} for a in r["hasil"]]
        if not r["ditemukan"]:
            lap.hasil_pemeriksaan.append(_tidak_ditemukan(komp["nama"], r["catatan"]))
            continue
        try:
            lap.hasil_pemeriksaan.append(_evaluasi(klien, komp, teks, kutipan, ditemukan, r["hasil"]))
        except ValidasiError as e:  # kegagalan eksplisit, bukan laporan yang seolah-olah valid
            lap.komponen_gagal.append(KomponenGagal(komponen=komp["nama"], penyebab=str(e)))
        except Exception as e:
            lap.komponen_gagal.append(KomponenGagal(komponen=komp["nama"], penyebab=f"Kesalahan pemanggilan model: {e}"))

    if not lap.komponen_gagal:
        lap.status_proses = "BERHASIL"
    elif lap.hasil_pemeriksaan:
        lap.status_proses = "SEBAGIAN_GAGAL"
        lap.pesan_kegagalan = "Sebagian komponen gagal divalidasi dan tidak ditampilkan sebagai hasil."
    else:
        lap.status_proses = "GAGAL"
        lap.pesan_kegagalan = "Semua komponen gagal diproses."
    lap.metrik = {**klien.statistik(), "durasi_detik": round(time.time() - t0, 1)}
    if progres:
        progres(1.0, "Selesai")
    return lap.model_dump(mode="json")
