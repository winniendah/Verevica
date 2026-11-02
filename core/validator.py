"""Validasi struktur (skema + kombinasi) dan validasi isi (bukti & rujukan dapat ditelusuri)."""
import json
import re

from pydantic import ValidationError

from .schemas import HasilKomponen


class ValidasiError(Exception):
    pass


def norm(s: str) -> str:
    s = re.sub(r"[|\u2022]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def bersihkan_json(raw: str) -> str:
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    a, b = raw.find("{"), raw.rfind("}")
    return raw[a:b + 1] if a != -1 and b != -1 else raw


def validasi_struktur(raw: str) -> HasilKomponen:
    try:
        data = json.loads(bersihkan_json(raw))
    except json.JSONDecodeError as e:
        raise ValidasiError(f"Respons bukan JSON valid: {e}")
    try:
        return HasilKomponen.model_validate(data)
    except ValidationError as e:
        pesan = "; ".join(f"{'.'.join(map(str, x['loc'])) or 'objek'}: {x['msg']}" for x in e.errors())
        raise ValidasiError(f"Skema tidak sesuai: {pesan}")


def validasi_isi(h: HasilKomponen, teks_proposal: str, rujukan_valid: set[str]) -> None:
    if h.bukti_teks_proposal is not None and norm(h.bukti_teks_proposal) not in norm(teks_proposal):
        raise ValidasiError("bukti_teks_proposal tidak ditemukan persis pada teks hasil ekstraksi proposal")
    if h.status_kepatuhan == "PATUH" and h.bukti_teks_proposal is None:
        raise ValidasiError("status PATUH wajib disertai bukti_teks_proposal")
    r = h.pasal_pedoman_rujukan
    if r is not None and r not in rujukan_valid:
        raise ValidasiError(f"pasal_pedoman_rujukan harus salah satu label berikut persis: {sorted(rujukan_valid)}")
    if h.dapat_ditentukan == "YA" and r is None:
        raise ValidasiError("dapat_ditentukan=YA wajib memiliki pasal_pedoman_rujukan")
    if h.alasan_tidak_dapat_ditentukan == "ATURAN_TIDAK_DITEMUKAN" and r is not None:
        raise ValidasiError("alasan ATURAN_TIDAK_DITEMUKAN mengharuskan pasal_pedoman_rujukan=null")
