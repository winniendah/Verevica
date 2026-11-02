import json

import pytest
from pydantic import ValidationError

from core.schemas import HasilKomponen
from core.validator import ValidasiError, validasi_isi, validasi_struktur

PROPOSAL = "BAB IV RAB\nNo | Uraian | Total\n2 | Pembelian alat tulis | Rp500.000"
RUJ = {"pedoman.pdf, BAB III, halaman 12"}


def raw(**kw):
    d = dict(komponen_proposal="Format RAB", status_kepatuhan="PERLU_REVISI",
             bukti_teks_proposal="Pembelian alat tulis | Rp500.000",
             pasal_pedoman_rujukan="pedoman.pdf, BAB III, halaman 12",
             catatan_revisi_sekretaris="Lengkapi harga per unit.",
             dapat_ditentukan="YA", alasan_tidak_dapat_ditentukan=None)
    d.update(kw)
    return json.dumps(d)


def test_valid_dengan_fence_markdown():
    h = validasi_struktur("```json\n" + raw() + "\n```")
    validasi_isi(h, PROPOSAL, RUJ)


@pytest.mark.parametrize("kw", [
    dict(status_kepatuhan="PATUH", dapat_ditentukan="TIDAK"),
    dict(status_kepatuhan="TIDAK_LENGKAP", dapat_ditentukan="YA"),
    dict(status_kepatuhan="TIDAK_LENGKAP", dapat_ditentukan="TIDAK", alasan_tidak_dapat_ditentukan=None),
    dict(status_kepatuhan="PERLU_REVISI", alasan_tidak_dapat_ditentukan="ATURAN_TIDAK_DITEMUKAN"),
    dict(status_kepatuhan="LULUS"),
])
def test_kombinasi_tidak_valid(kw):
    with pytest.raises(ValidasiError):
        validasi_struktur(raw(**kw))


def test_field_wajib_hilang():
    d = json.loads(raw()); del d["catatan_revisi_sekretaris"]
    with pytest.raises(ValidasiError):
        validasi_struktur(json.dumps(d))


def test_bukan_json():
    with pytest.raises(ValidasiError):
        validasi_struktur("maaf, tidak bisa")


def test_bukti_dikarang():
    with pytest.raises(ValidasiError):
        validasi_isi(validasi_struktur(raw(bukti_teks_proposal="kutipan palsu")), PROPOSAL, RUJ)


def test_rujukan_dikarang():
    with pytest.raises(ValidasiError):
        validasi_isi(validasi_struktur(raw(pasal_pedoman_rujukan="Pasal 99")), PROPOSAL, RUJ)


def test_patuh_tanpa_bukti():
    with pytest.raises(ValidasiError):
        validasi_isi(validasi_struktur(raw(status_kepatuhan="PATUH", bukti_teks_proposal=None)), PROPOSAL, RUJ)


def test_tidak_lengkap_aturan_tidak_ditemukan_lolos():
    h = validasi_struktur(raw(status_kepatuhan="TIDAK_LENGKAP", dapat_ditentukan="TIDAK",
                              pasal_pedoman_rujukan=None, bukti_teks_proposal=None,
                              alasan_tidak_dapat_ditentukan="ATURAN_TIDAK_DITEMUKAN"))
    validasi_isi(h, PROPOSAL, RUJ)
