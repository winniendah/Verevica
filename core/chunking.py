"""Chunking berbasis struktur (bab/pasal/subbab) + overlap + metadata sumber. Tanpa dependensi berat."""
import re

HEAD = re.compile(r"^\s*((?i:BAB)\s+[IVXLC\d]+\b|(?i:Pasal)\s+\d+|(?i:Bagian)\s+\S+|\d+(?:\.\d+)*\.?\s+[A-Z])")


def format_rujukan(meta: dict) -> str:
    """Label rujukan. Halaman hanya ditulis jika diketahui (tidak boleh mengarang)."""
    s = f"{meta['dokumen']}, {meta['judul']}"
    if meta.get("halaman"):
        s += f", halaman {meta['halaman']}"
    return s


def pecah_dokumen(nama_dokumen: str, halaman: list[dict], maks: int = 1500, overlap: int = 150) -> list[dict]:
    """halaman: [{'no': int|None, 'teks': str}]. Return [{'id','teks','meta'}]."""
    chunks: list[dict] = []
    state = {"judul": "Pembuka", "hal": (halaman[0]["no"] if halaman else None) or 0, "buf": []}

    def flush():
        isi = "\n".join(state["buf"]).strip()
        start = 0
        while start < len(isi):
            potong = isi[max(0, start - overlap) if start else 0: start + maks].strip()
            if potong:
                cid = f"{nama_dokumen}-{len(chunks)}"
                chunks.append({"id": cid, "teks": potong, "meta": {
                    "dokumen": nama_dokumen, "judul": state["judul"],
                    "halaman": state["hal"], "chunk_id": cid}})
            start += maks

    for h in halaman:
        for line in h["teks"].splitlines():
            if HEAD.match(line) and len(line.strip()) < 120:
                flush()
                state.update(judul=line.strip(), hal=h["no"] or 0, buf=[])
            state["buf"].append(line)
    flush()
    return chunks
