"""Tool 1: baca_draf_proposal. Tool 2: cari_aturan_pedoman. Keduanya read-only."""
from pathlib import Path

from . import config
from .chunking import format_rujukan


def baca_draf_proposal(path: str) -> dict:
    """Return {gagal, pesan, teks, halaman:[{no,teks}], peringatan:[...]}. Tidak mengubah file asli."""
    p = Path(path)
    peringatan, halaman = [], []
    try:
        if p.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            for i, pg in enumerate(PdfReader(str(p)).pages, 1):
                t = (pg.extract_text() or "").strip()
                if len(t) < 20:
                    peringatan.append(f"Halaman {i} hampir tanpa teks (kemungkinan gambar/hasil scan atau tabel tidak terbaca).")
                halaman.append({"no": i, "teks": t})
        elif p.suffix.lower() == ".docx":
            from docx import Document
            from docx.table import Table
            from docx.text.paragraph import Paragraph
            d = Document(str(p))
            baris = []
            for el in d.element.body.iterchildren():  # urutan asli: paragraf & tabel
                if el.tag.endswith("}p"):
                    par = Paragraph(el, d)
                    if par.text.strip():
                        baris.append(par.text)
                elif el.tag.endswith("}tbl"):
                    for r in Table(el, d).rows:
                        baris.append(" | ".join(c.text.strip() for c in r.cells))
            if d.inline_shapes:
                peringatan.append(f"Dokumen memuat {len(d.inline_shapes)} gambar; isi gambar tidak dapat dibaca (OCR belum tersedia).")
            halaman.append({"no": None, "teks": "\n".join(baris)})  # DOCX tidak punya nomor halaman tetap
        else:
            return {"gagal": True, "pesan": "Format harus PDF atau DOCX.", "teks": "", "halaman": [], "peringatan": []}
    except Exception as e:
        return {"gagal": True, "pesan": f"Ekstraksi gagal: {e}", "teks": "", "halaman": [], "peringatan": []}

    teks = "\n\n".join(h["teks"] for h in halaman).strip()
    if len(teks) < 200:
        return {"gagal": True, "teks": teks, "halaman": halaman, "peringatan": peringatan,
                "pesan": "Teks hampir kosong. File kemungkinan hasil scan (OCR belum tersedia). Gunakan file teks."}
    return {"gagal": False, "pesan": "", "teks": teks, "halaman": halaman, "peringatan": peringatan}


def cari_aturan_pedoman(query: str, top_k: int = config.DEFAULT_TOP_K,
                        max_distance: float = config.DEFAULT_MAX_DISTANCE) -> dict:
    """Return {ditemukan, hasil:[{teks, rujukan, dokumen, judul, halaman, chunk_id, jarak}], catatan}."""
    from .indexer import get_collection
    col = get_collection()
    n = col.count()
    if n == 0:
        return {"ditemukan": False, "hasil": [], "catatan": "Indeks pedoman kosong."}
    r = col.query(query_texts=[query], n_results=min(top_k, n))
    hasil = []
    for doc, meta, dist in zip(r["documents"][0], r["metadatas"][0], r["distances"][0]):
        if dist <= max_distance:
            hasil.append({"teks": doc, "rujukan": format_rujukan(meta), "jarak": round(dist, 3), **meta})
    if not hasil:
        return {"ditemukan": False, "hasil": [], "catatan": "Tidak ada potongan yang memenuhi ambang relevansi."}
    return {"ditemukan": True, "hasil": hasil, "catatan": ""}
