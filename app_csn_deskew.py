import streamlit as st
import fitz
import easyocr
import re
import os
import io
import time
import numpy as np
from PIL import Image
from deskew import determine_skew
from skimage.transform import rotate as skimage_rotate
import logging
import tkinter as tk
from tkinter import filedialog

logging.getLogger('streamlit.runtime.scriptrunner_utils').setLevel(logging.ERROR)

st.set_page_config(
    page_title="PDF Organizer — CSN GDOP",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ─── ESTADOS ─────────────────────────────────────────────────────────────────
if 'ultima_rotacao_sucesso' not in st.session_state:
    st.session_state.ultima_rotacao_sucesso = 0
if 'processando' not in st.session_state:
    st.session_state.processando = False
if 'interromper' not in st.session_state:
    st.session_state.interromper = False
if 'pasta_selecionada' not in st.session_state:
    st.session_state.pasta_selecionada = ""

# ─── CSS TEMA CSN ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600;700&family=Barlow+Condensed:wght@600;700&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #0a1628 !important;
    font-family: 'Barlow', sans-serif !important;
    color: #e8edf5 !important;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stDecoration"], [data-testid="stToolbar"], .stDeployButton { display: none !important; }
.block-container { max-width: 680px !important; padding: 2rem 1.5rem 4rem !important; margin: 0 auto !important; }
.csn-header { text-align: center; padding: 2.5rem 0 2rem; }
.csn-logo-bar { display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 1rem; }
.csn-logo-icon { width: 48px; height: 48px; background: linear-gradient(135deg, #1565c0, #1e88e5); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; animation: pulse-blue 3s ease-in-out infinite; }
@keyframes pulse-blue { 0%, 100% { box-shadow: 0 0 20px rgba(30,136,229,0.4); } 50% { box-shadow: 0 0 35px rgba(30,136,229,0.7); } }
.csn-wordmark { font-family: 'Barlow Condensed', sans-serif; font-size: 32px; font-weight: 700; color: #1e88e5; letter-spacing: 0.08em; line-height: 1; }
.csn-title { font-family: 'Barlow Condensed', sans-serif; font-size: 28px; font-weight: 700; color: #e8edf5; text-transform: uppercase; letter-spacing: 0.04em; margin: 0 0 6px; }
.csn-subtitle { font-size: 13px; color: #5c7a9e; letter-spacing: 0.12em; text-transform: uppercase; font-weight: 500; }
.section-label { font-size: 11px; font-weight: 600; color: #1e88e5; letter-spacing: 0.15em; text-transform: uppercase; margin: 1.5rem 0 0.5rem; display: flex; align-items: center; gap: 8px; }
.section-label::after { content: ''; flex: 1; height: 1px; background: #1e3a5f; }
.status-card { background: #0f1f3a; border: 1px solid #1e3a5f; border-radius: 10px; padding: 1rem 1.25rem; margin: 0.75rem 0; font-size: 13px; color: #5c7a9e; display: flex; align-items: center; gap: 10px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #1e88e5; animation: blink 1.2s ease-in-out infinite; flex-shrink: 0; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.2; } }
.badge-deskew { display: inline-flex; align-items: center; gap: 6px; background: #0a2a4a; border: 1px solid #1e3a5f; border-radius: 20px; padding: 4px 14px; font-size: 12px; color: #4a9eff; font-weight: 500; margin-bottom: 1rem; }
[data-testid="stTextInput"] input { background: #0f1f3a !important; border: 1.5px solid #1e3a5f !important; border-radius: 8px !important; color: #e8edf5 !important; font-family: 'Barlow', sans-serif !important; font-size: 14px !important; }
[data-testid="stTextInput"] input:focus { border-color: #1e88e5 !important; box-shadow: 0 0 0 3px rgba(30,136,229,0.12) !important; }
[data-testid="stFileUploader"] { background: #0f1f3a !important; border: 1.5px dashed #1e3a5f !important; border-radius: 12px !important; }
.stButton > button { font-family: 'Barlow Condensed', sans-serif !important; font-weight: 700 !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; border-radius: 8px !important; font-size: 15px !important; border: none !important; transition: all 0.2s ease !important; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #1565c0, #1e88e5) !important; color: white !important; box-shadow: 0 4px 20px rgba(30,136,229,0.35) !important; }
.stButton > button[kind="primary"]:hover { box-shadow: 0 6px 28px rgba(30,136,229,0.5) !important; }
.stButton > button[kind="secondary"] { background: #0f1f3a !important; color: #1e88e5 !important; border: 1.5px solid #1e3a5f !important; }
[data-testid="stProgressBar"] > div { background: #0f1f3a !important; border-radius: 6px !important; height: 6px !important; }
[data-testid="stProgressBar"] > div > div { background: linear-gradient(90deg, #1565c0, #42a5f5) !important; border-radius: 6px !important; }
hr { border-color: #1e3a5f !important; margin: 1.5rem 0 !important; }
.csn-footer { text-align: center; padding: 2rem 0 0; font-size: 11px; color: #253d5a; letter-spacing: 0.08em; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# ─── FUNÇÕES ─────────────────────────────────────────────────────────────────
def escolher_pasta():
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        pasta = filedialog.askdirectory(master=root)
        root.destroy()
        return pasta
    except Exception:
        return None

@st.cache_resource(show_spinner="Carregando motor de OCR...")
def carregar_leitor():
    return easyocr.Reader(['pt'], gpu=False)

def aplicar_deskew(img_array: np.ndarray) -> np.ndarray:
    """
    Corrige inclinação fina causada pelo scanner (ex: ±1° a ±10°).
    Só processa se o ângulo detectado for relevante (>= 0.3°).
    Retorna uint8 pronto para o EasyOCR.
    """
    angle = determine_skew(img_array)
    if angle is None or abs(angle) < 0.3:
        return img_array
    corrected = skimage_rotate(img_array, angle, resize=False, cval=255)
    return (corrected * 255).astype(np.uint8)

def buscar_data_otimizado(page, reader) -> str | None:
    """
    Cascata completa:
      1. Texto nativo do PDF       → 0ms, sem OCR
      2. Rotação conhecida + deskew → mais rápido (memória de orientação)
      3. Outras rotações + deskew  → fallback

    O deskew corrige a inclinação do scanner DENTRO de cada orientação testada,
    garantindo que folhas entortadas (ex: ±5°) sejam lidas corretamente
    independente da orientação original (vertical, horizontal, invertida).
    """
    # Nível 1: texto nativo
    datas = re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', page.get_text())
    if datas:
        return datas[0].replace('/', '-')

    # Renderiza uma vez, grayscale
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    img_base = Image.open(io.BytesIO(pix.tobytes("png"))).convert('L')

    # Ordem de teste: última rotação bem-sucedida primeiro
    outros = [0, 90, 180, 270]
    ultima = st.session_state.ultima_rotacao_sucesso
    if ultima in outros:
        outros.remove(ultima)
    ordem = [ultima] + outros

    for angulo in ordem:
        # Rotação exata (orientação da folha)
        img_rot = img_base if angulo == 0 else img_base.rotate(angulo, expand=True)
        arr = np.array(img_rot)

        # Deskew (inclinação fina do scanner)
        arr = aplicar_deskew(arr)

        resultados = reader.readtext(arr, detail=0)
        datas_ocr = re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', " ".join(resultados))

        if datas_ocr:
            st.session_state.ultima_rotacao_sucesso = angulo
            return datas_ocr[0].replace('/', '-')

    return None

def salvar_unico(pasta: str, data: str | None, prefixo: str) -> str:
    data_str = data if data else "DATA_NAO_LIDA"
    nome_base = f"{prefixo + '-' if prefixo else ''}{data_str}"
    caminho = os.path.join(pasta, f"{nome_base}.pdf")
    contador = 1
    while os.path.exists(caminho):
        caminho = os.path.join(pasta, f"{nome_base}_{contador}.pdf")
        contador += 1
    return caminho

# ─── INTERFACE ───────────────────────────────────────────────────────────────
reader = carregar_leitor()

st.markdown("""
<div class="csn-header">
    <div class="csn-logo-bar">
        <div class="csn-logo-icon">⚙️</div>
        <div style="display:flex; align-items:center; gap:6px;">
            <span class="csn-wordmark">CSN</span>
            <div style="display:flex;flex-direction:column;gap:5px;margin-left:4px;">
                <span style="display:block;width:2px;height:14px;background:#1e88e5;"></span>
                <span style="display:block;width:2px;height:14px;background:#1e88e5;"></span>
            </div>
            <span style="font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:600;color:#5c7a9e;letter-spacing:0.08em;text-transform:uppercase;line-height:1.3;">Companhia<br>Siderúrgica<br>Nacional</span>
        </div>
    </div>
    <div class="csn-title">Intelligent PDF Organizer</div>
    <div class="csn-subtitle">GDOP &nbsp;·&nbsp; Automação de Documentos</div>
</div>
""", unsafe_allow_html=True)

# Badge de capacidades ativas
st.markdown("""
<div style="display:flex; justify-content:center; gap:10px; margin-bottom:1rem;">
    <div class="badge-deskew">✓ Rotação automática (0° 90° 180° 270°)</div>
    <div class="badge-deskew">✓ Correção de inclinação (deskew)</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-label">📄 &nbsp;Arquivo de origem</div>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Selecione o PDF", type="pdf", label_visibility="collapsed")

if uploaded_file:
    st.markdown(f"""
    <div class="status-card">
        <div class="status-dot"></div>
        <span>Arquivo carregado: <strong style="color:#a8c0dc;">{uploaded_file.name}</strong></span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="section-label">📁 &nbsp;Pasta de destino</div>', unsafe_allow_html=True)
col_path, col_btn = st.columns([4, 1])
with col_path:
    caminho_pasta = st.text_input(
        "Caminho", value=st.session_state.pasta_selecionada,
        placeholder="Clique em Procurar ou cole o caminho...",
        label_visibility="collapsed"
    )
    if caminho_pasta:
        st.session_state.pasta_selecionada = caminho_pasta
with col_btn:
    if st.button("📁 Procurar", use_container_width=True):
        pasta = escolher_pasta()
        if pasta:
            st.session_state.pasta_selecionada = pasta
            st.rerun()

st.markdown('<div class="section-label">🏷️ &nbsp;Prefixo do arquivo</div>', unsafe_allow_html=True)
prefixo = st.text_input(
    "Prefixo", placeholder="Ex: ARM#24, NOTA   (opcional)",
    label_visibility="collapsed"
)

st.divider()

btn_col1, btn_col2 = st.columns([3, 1])
with btn_col1:
    if not st.session_state.processando:
        if st.button("▶  INICIAR PROCESSAMENTO", type="primary", use_container_width=True):
            pasta_final = st.session_state.pasta_selecionada or caminho_pasta
            if uploaded_file and pasta_final:
                st.session_state.processando = True
                st.session_state.interromper = False
                st.rerun()
            else:
                st.error("Selecione o arquivo PDF e a pasta de destino.")
    else:
        st.button("⚙️  PROCESSANDO...", disabled=True, use_container_width=True, type="primary")

with btn_col2:
    if st.session_state.processando:
        if st.button("⏹ Parar", use_container_width=True):
            st.session_state.interromper = True

# ─── PROCESSAMENTO ───────────────────────────────────────────────────────────
if st.session_state.processando:
    pasta_destino = st.session_state.pasta_selecionada or caminho_pasta
    try:
        with open("_temp_upload.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())

        doc = fitz.open("_temp_upload.pdf")
        total = len(doc)

        st.markdown(f"""
        <div class="status-card">
            <div class="status-dot"></div>
            <span>Processando <strong style="color:#a8c0dc;">{total} página{'s' if total > 1 else ''}</strong>
            — rotação + deskew ativos</span>
        </div>
        """, unsafe_allow_html=True)

        prog_bar = st.progress(0)
        status_text = st.empty()
        inicio = time.time()

        for i in range(total):
            if st.session_state.interromper:
                st.warning("⏹ Processamento interrompido.")
                break

            with st.spinner(f"Página {i+1} de {total}..."):
                data_doc = buscar_data_otimizado(doc[i], reader)
                caminho = salvar_unico(pasta_destino, data_doc, prefixo)
                novo = fitz.open()
                novo.insert_pdf(doc, from_page=i, to_page=i)
                novo.save(caminho)
                novo.close()

            prog_bar.progress((i + 1) / total)
            decorrido = time.time() - inicio
            vel = (i + 1) / decorrido
            eta = int((total - (i + 1)) / vel) if vel > 0 else 0
            m, s = divmod(eta, 60)
            status_text.markdown(
                f'<div style="font-size:12px;color:#5c7a9e;margin-top:4px;">'
                f'Página {i+1}/{total} &nbsp;·&nbsp; {vel*60:.1f} pág/min &nbsp;·&nbsp; ETA {m:02d}:{s:02d}'
                f'</div>',
                unsafe_allow_html=True
            )

        doc.close()
        if os.path.exists("_temp_upload.pdf"):
            os.remove("_temp_upload.pdf")

        st.session_state.processando = False

        if not st.session_state.interromper:
            total_s = time.time() - inicio
            st.success(f"✅ Concluído! {total} páginas em {total_s:.1f}s ({total/total_s:.1f} pág/s)")
            st.balloons()

        if st.button("↺  Novo processamento"):
            st.session_state.clear()
            st.rerun()

    except Exception as e:
        st.error(f"Erro: {e}")
        if os.path.exists("_temp_upload.pdf"):
            os.remove("_temp_upload.pdf")
        st.session_state.processando = False

st.markdown("""
<div class="csn-footer">
    CSN · GDOP &nbsp;·&nbsp; Automação desenvolvida no estágio &nbsp;·&nbsp; Python + EasyOCR + Deskew
</div>
""", unsafe_allow_html=True)
