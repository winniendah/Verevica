"""Pengindeksan pedoman ke vector database (ChromaDB + embedding multilingual lokal)."""
from collections import Counter
from pathlib import Path

from . import config
from .chunking import pecah_dokumen
from .tools import baca_draf_proposal

_col = None


def get_collection():
    global _col
    if _col is None:
        import chromadb
        from chromadb.utils import embedding_functions
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=config.EMBED_MODEL)
        client = chromadb.PersistentClient(path=config.CHROMA_DIR)
        _col = client.get_or_create_collection(config.COLLECTION, embedding_function=ef,
                                               metadata={"hnsw:space": "cosine"})
    return _col


def ingest_pedoman(paths: list[str] | None = None) -> list[dict]:
    """Ekstraksi -> cek -> chunking -> metadata -> embedding -> simpan. Return laporan per file."""
    if paths is None:
        paths = [str(p) for p in sorted(config.DATA_PEDOMAN.glob("*")) if p.suffix.lower() in (".pdf", ".docx")]
    col = get_collection()
    laporan = []
    for path in paths:
        nama = Path(path).name
        hasil = baca_draf_proposal(path)  # fungsi ekstraksi yang sama
        if hasil["gagal"]:
            laporan.append({"file": nama, "status": "DILEWATI", "chunk": 0, "pesan": hasil["pesan"]})
            continue
        chunks = pecah_dokumen(nama, hasil["halaman"])
        if not chunks:
            laporan.append({"file": nama, "status": "DILEWATI", "chunk": 0, "pesan": "Tidak menghasilkan chunk."})
            continue
        col.delete(where={"dokumen": nama})  # hindari sisa chunk dari versi lama
        col.upsert(ids=[c["id"] for c in chunks], documents=[c["teks"] for c in chunks],
                   metadatas=[c["meta"] for c in chunks])
        pesan = "; ".join(hasil["peringatan"][:3])
        laporan.append({"file": nama, "status": "OK", "chunk": len(chunks), "pesan": pesan})
    return laporan


def jumlah_chunk_pedoman() -> int:
    return get_collection().count()


def daftar_dokumen_terindeks() -> dict[str, int]:
    metas = get_collection().get(include=["metadatas"])["metadatas"]
    return dict(Counter(m["dokumen"] for m in metas))


def reset_indeks():
    global _col
    import chromadb
    chromadb.PersistentClient(path=config.CHROMA_DIR).delete_collection(config.COLLECTION)
    _col = None
