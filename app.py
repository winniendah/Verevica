"""Verevica (Verification & Review Assistant) - antarmuka Streamlit."""
import json
import os
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path

import streamlit as st

from core import config
from core.indexer import ingest_pedoman, jumlah_chunk_pedoman

st.set_page_config(page_title="Verevica", page_icon="✅", layout="wide")

st.markdown("""
<style>
:root {
    --cream: #F8F4EC;
    --pink: #FF8FB7;
    --magenta: #E83C91;
    --plum: #43334C;
}
.stApp { background: var(--cream); color: var(--plum); }
[data-testid="stSidebar"] { background: var(--plum); }
[data-testid="stSidebar"] * { color: #FFFFFF; }
[data-testid="stSidebar"] input {
    background: #FFFFFF;
    color: #000000;
}
[data-testid="stSidebar"] button {
    border-color: var(--pink);
    color: var(--plum);
}
[data-testid="stSidebar"] button:hover {
    border-color: var(--magenta);
    color: var(--magenta);
}
div.stButton > button[kind="primary"] {
    background: var(--magenta);
    border-color: var(--magenta);
    color: #FFFFFF;
}
div.stButton > button[kind="primary"]:hover {
    background: var(--plum);
    border-color: var(--plum);
}
h1, h2, h3, h4, p, label { color: var(--plum); }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
    color: #FFFFFF;
}
</style>
""", unsafe_allow_html=True)

LABEL = {"PATUH": "✅ :green[PATUH]", "PERLU_REVISI": "⚠️ :orange[PERLU REVISI]", "TIDAK_LENGKAP": "❔ :gray[TIDAK LENGKAP / belum dapat ditentukan]"}


def rahasia(nama: str) -> str:
    try:
        v = st.secrets.get(nama)
    except Exception:
        v = None
    return v or os.getenv(nama, "")


api_key = rahasia("GEMINI_API_KEY")
model = config.DEFAULT_MODEL
top_k = config.DEFAULT_TOP_K
max_dist = config.DEFAULT_MAX_DISTANCE

if "indeks_dijalankan" not in st.session_state:
    try:
        if jumlah_chunk_pedoman() == 0:
            st.session_state["lap_ingest"] = ingest_pedoman()
        st.session_state["indeks_dijalankan"] = True
    except Exception as e:
        st.session_state["indeks_error"] = str(e)
        st.session_state["indeks_dijalankan"] = True

st.title("Verevica")
st.caption("Verification & Review Assistant: pemeriksa awal draf proposal berdasarkan pedoman dan SOP. "
           "Hasilnya rekomendasi awal; keputusan akhir tetap pada penanggung jawab.")

tab_periksa, tab_riwayat = st.tabs(["Periksa proposal", "Riwayat"])

# ---------------- Pemeriksaan proposal ----------------
def tampilkan(lap: dict):
    st.subheader("Hasil pemeriksaan")
    if lap["status_proses"] == "GAGAL":
        st.error(f"Pemeriksaan gagal: {lap['pesan_kegagalan']}")
    elif lap["status_proses"] == "SEBAGIAN_GAGAL":
        st.warning(lap["pesan_kegagalan"])
    for p in lap["peringatan"]:
        st.warning(p)

    c = Counter(h["status_kepatuhan"] for h in lap["hasil_pemeriksaan"])
    k = st.columns(4)
    k[0].metric("Patuh", c["PATUH"])
    k[1].metric("Perlu revisi", c["PERLU_REVISI"])
    k[2].metric("Belum dapat ditentukan", c["TIDAK_LENGKAP"])
    k[3].metric("Gagal divalidasi", len(lap["komponen_gagal"]))

    for h in lap["hasil_pemeriksaan"]:
        with st.container(border=True):
            st.markdown(f"#### {h['komponen_proposal']}  \n{LABEL[h['status_kepatuhan']]}")
            st.markdown("**Bukti dari proposal**")
            st.markdown(f"> {h['bukti_teks_proposal']}" if h["bukti_teks_proposal"] else "_Tidak ada kutipan (komponen tidak ditemukan atau tidak terbaca)._")
            st.markdown(f"**Rujukan pedoman:** {h['pasal_pedoman_rujukan'] or '_tidak ada_'}")
            st.markdown(f"**Catatan revisi:** {h['catatan_revisi_sekretaris']}")
            if h["alasan_tidak_dapat_ditentukan"]:
                st.markdown(f"**Alasan belum dapat ditentukan:** `{h['alasan_tidak_dapat_ditentukan']}`")
            jejak = lap["jejak_retrieval"].get(h["komponen_proposal"], [])
            if jejak:
                with st.expander("Aturan yang diambil sistem"):
                    for j in jejak:
                        st.markdown(f"**{j['rujukan']}** (jarak {j['jarak']})")
                        st.caption(j["cuplikan"])
    for g in lap["komponen_gagal"]:
        st.error(f"**{g['komponen']}**: output model tidak lolos validasi setelah satu kali perbaikan, "
                 f"jadi tidak ditampilkan sebagai hasil. Penyebab: {g['penyebab']}")
    if lap["metrik"]:
        m = lap["metrik"]
        st.caption(f"Model {m.get('model')} · {m.get('jumlah_panggilan_llm')} panggilan · "
                   f"token masuk/keluar {m.get('token_input')}/{m.get('token_output')} · {m.get('durasi_detik')} detik")
    st.download_button("Unduh laporan JSON", json.dumps(lap, ensure_ascii=False, indent=2),
                       file_name="laporan_verevica.json", mime="application/json")


with tab_periksa:
    try:
        siap = jumlah_chunk_pedoman() > 0
    except Exception:
        siap = False
    if not siap:
        st.warning("Indeks pedoman belum siap. Pastikan dokumen tersedia di backend.")
    if "indeks_error" in st.session_state:
        st.error(f"Pengindeksan pedoman gagal: {st.session_state['indeks_error']}")
    if not api_key:
        st.info("Konfigurasi Gemini belum tersedia di backend.")

    proposal = st.file_uploader("Draf proposal (PDF atau DOCX)", type=["pdf", "docx"], key="up_proposal")
    simpan = st.checkbox("Simpan hasil ke riwayat (opsional)", value=True)
    if st.button("Mulai pemeriksaan", type="primary", disabled=not (proposal and api_key and siap)):
        from core.auditor import audit
        from core.llm import GeminiClient
        bar = st.progress(0.0, text="Menyiapkan…")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / f"proposal{Path(proposal.name).suffix.lower()}"
            p.write_bytes(proposal.getbuffer())
            try:
                lap = audit(str(p), GeminiClient(api_key, model), top_k, max_dist,
                            progres=lambda f, t: bar.progress(min(f, 1.0), text=t))
                lap["nama_file"] = proposal.name
                st.session_state["laporan"] = lap
                if simpan and lap["status_proses"] != "GAGAL":
                    config.RIWAYAT_DIR.mkdir(exist_ok=True)
                    nama = f"{datetime.now():%Y%m%d_%H%M%S}_{Path(proposal.name).stem}.json"
                    (config.RIWAYAT_DIR / nama).write_text(json.dumps(lap, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")
        bar.empty()
    if "laporan" in st.session_state:
        tampilkan(st.session_state["laporan"])

# ---------------- Riwayat ----------------
with tab_riwayat:
    berkas = sorted(config.RIWAYAT_DIR.glob("*.json"), reverse=True) if config.RIWAYAT_DIR.exists() else []
    if not berkas:
        st.info("Belum ada riwayat.")
    else:
        pilih = st.selectbox("Pilih laporan", berkas, format_func=lambda p: p.name)
        tampilkan(json.loads(pilih.read_text(encoding="utf-8")))
