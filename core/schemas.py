from typing import Literal, Optional

from pydantic import BaseModel, model_validator

Status = Literal["PATUH", "PERLU_REVISI", "TIDAK_LENGKAP"]
Ditentukan = Literal["YA", "TIDAK"]
Alasan = Literal["ATURAN_TIDAK_DITEMUKAN", "BUKTI_PROPOSAL_TIDAK_MEMADAI", "ATURAN_BERTENTANGAN"]


class HasilKomponen(BaseModel):
    """Skema 4.2-4.4 rancangan. Field boleh null tetapi key wajib ada."""
    komponen_proposal: str
    status_kepatuhan: Status
    bukti_teks_proposal: Optional[str]
    pasal_pedoman_rujukan: Optional[str]
    catatan_revisi_sekretaris: str
    dapat_ditentukan: Ditentukan
    alasan_tidak_dapat_ditentukan: Optional[Alasan]

    @model_validator(mode="after")
    def cek_kombinasi(self):
        """Tabel kombinasi yang diperbolehkan (4.4)."""
        if self.status_kepatuhan in ("PATUH", "PERLU_REVISI"):
            if self.dapat_ditentukan != "YA" or self.alasan_tidak_dapat_ditentukan is not None:
                raise ValueError(f"{self.status_kepatuhan} harus dapat_ditentukan=YA dan alasan_tidak_dapat_ditentukan=null")
        else:  # TIDAK_LENGKAP
            if self.dapat_ditentukan != "TIDAK" or self.alasan_tidak_dapat_ditentukan is None:
                raise ValueError("TIDAK_LENGKAP harus dapat_ditentukan=TIDAK dan alasan_tidak_dapat_ditentukan terisi")
        return self


class KomponenGagal(BaseModel):
    komponen: str
    penyebab: str


class LaporanAudit(BaseModel):
    status_proses: Literal["BERHASIL", "SEBAGIAN_GAGAL", "GAGAL"]
    pesan_kegagalan: Optional[str] = None
    hasil_pemeriksaan: list[HasilKomponen] = []
    komponen_gagal: list[KomponenGagal] = []
    peringatan: list[str] = []
    jejak_retrieval: dict[str, list[dict]] = {}
    metrik: dict = {}
