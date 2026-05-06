import fitz  # PyMuPDF
import easyocr
import re
import os
import io
import time
import cv2
import numpy as np
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading

# ─── OCR ─────────────────────────────────────────────────────────────────────
reader = easyocr.Reader(['pt'], gpu=False)
ultima_rotacao_sucesso = 0

# ─── DESKEW VIA TRANSFORMADA DE HOUGH ────────────────────────────────────────

def detectar_angulo_hough(img_array: np.ndarray) -> float:
    """
    Usa a Transformada de Hough Probabilística para detectar o ângulo de
    inclinação dominante das linhas de texto na imagem.

    Estratégia:
      1. Binarização adaptativa — lida melhor com variações de iluminação do scanner
      2. Canny — detecta bordas das linhas de texto
      3. HoughLinesP — encontra segmentos de linha retos
      4. Filtra ângulos próximos do horizontal (< 45°) para ignorar bordas
         verticais e ruído
      5. Retorna a mediana dos ângulos — robusta contra outliers
    """
    # Garante que a imagem é uint8 grayscale
    if img_array.dtype != np.uint8:
        img_array = (img_array * 255).astype(np.uint8)

    # Binarização adaptativa (mais robusta que threshold fixo para documentos)
    binarizada = cv2.adaptiveThreshold(
        img_array, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=15, C=10
    )

    # Detecção de bordas
    edges = cv2.Canny(binarizada, 50, 150, apertureSize=3)

    # Hough Probabilístico — mais eficiente que o clássico para documentos
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=80,       # Mínimo de votos para considerar uma linha
        minLineLength=60,   # Ignora segmentos curtos (ruído, pontuação)
        maxLineGap=15       # Tolerância para gaps dentro de uma linha de texto
    )

    if lines is None:
        return 0.0

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 == x1:
            continue  # Linha vertical — ignorar
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Filtra apenas ângulos próximos ao horizontal (linhas de texto)
        if abs(angle) < 45:
            angles.append(angle)

    if not angles:
        return 0.0

    return float(np.median(angles))


def aplicar_deskew_hough(img_array: np.ndarray) -> np.ndarray:
    """
    Corrige a inclinação da imagem usando o ângulo detectado pela Hough.
    Limiar mínimo de 0.3° para não processar imagens já retas.
    Preenche bordas com branco (255) após a rotação.
    """
    angle = detectar_angulo_hough(img_array)

    if abs(angle) < 0.3:
        return img_array

    h, w = img_array.shape[:2]
    centro = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(centro, angle, 1.0)
    corrected = cv2.warpAffine(
        img_array, M, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255
    )
    return corrected

# ─── LÓGICA PRINCIPAL ────────────────────────────────────────────────────────

def buscar_data_otimizado(page) -> str | None:
    """
    Cascata completa:
      1. Texto nativo do PDF         → instantâneo, sem OCR
      2. Rotação conhecida + Hough   → rápido (memória de orientação)
      3. Outras rotações + Hough     → fallback

    A Transformada de Hough detecta as linhas de texto na imagem e calcula
    o ângulo de inclinação real, corrigindo distorções do scanner antes do OCR.
    """
    global ultima_rotacao_sucesso

    # Nível 1: texto digital embutido
    datas = re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', page.get_text())
    if datas:
        return datas[0].replace('/', '-')

    # Renderiza uma única vez — grayscale, Matrix 1.5 (equilíbrio velocidade/precisão)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    img_base = Image.open(io.BytesIO(pix.tobytes("png"))).convert('L')

    # Ordem: última rotação bem-sucedida primeiro
    outros = [0, 90, 180, 270]
    if ultima_rotacao_sucesso in outros:
        outros.remove(ultima_rotacao_sucesso)
    ordem = [ultima_rotacao_sucesso] + outros

    for angulo in ordem:
        # Rotação exata (corrige orientação da folha: vertical/horizontal/invertida)
        img_rot = img_base if angulo == 0 else img_base.rotate(angulo, expand=True)
        arr = np.array(img_rot)

        # Deskew via Hough (corrige inclinação fina do scanner dentro desta orientação)
        arr = aplicar_deskew_hough(arr)

        resultados = reader.readtext(arr, detail=0)
        datas_ocr = re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', " ".join(resultados))

        if datas_ocr:
            ultima_rotacao_sucesso = angulo
            return datas_ocr[0].replace('/', '-')

    return None


def salvar_unico(pasta: str, data: str | None, prefixo: str) -> str:
    data_str = data if data else "DATA_NAO_LIDA"
    pref = f"{prefixo}-" if prefixo else ""
    nome_base = f"{pref}{data_str}"
    caminho = os.path.join(pasta, f"{nome_base}.pdf")
    contador = 1
    while os.path.exists(caminho):
        caminho = os.path.join(pasta, f"{nome_base}_{contador}.pdf")
        contador += 1
    return caminho

# ─── INTERFACE ───────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Processador Inteligente de PDF v2.2  —  CSN GDOP")
        self.geometry("620x560")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.pdf_path = ""
        self.dest_path = ""

        # Arquivo
        self.btn_arquivo = ctk.CTkButton(
            self, text="Selecionar PDF de Origem", command=self.selecionar_pdf
        )
        self.btn_arquivo.pack(pady=(25, 5))

        # Destino
        self.btn_destino = ctk.CTkButton(
            self, text="Selecionar Pasta de Destino", command=self.selecionar_pasta
        )
        self.btn_destino.pack(pady=5)

        # Prefixo
        self.entry_prefixo = ctk.CTkEntry(
            self, placeholder_text="Prefixo opcional (ex: ARM#24, NF, RECIBO)", width=380
        )
        self.entry_prefixo.pack(pady=15)

        # Progress
        self.progress_bar = ctk.CTkProgressBar(self, width=460)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(10, 4))

        # Status
        self.label_status = ctk.CTkLabel(self, text="Aguardando arquivos...")
        self.label_status.pack()

        # Métricas
        self.label_metrics = ctk.CTkLabel(
            self, text="Velocidade: --  |  ETA: --",
            font=("Arial", 11), text_color="gray"
        )
        self.label_metrics.pack(pady=4)

        # Info do método
        self.label_metodo = ctk.CTkLabel(
            self,
            text="✓ Rotação automática  |  ✓ Deskew via Transformada de Hough",
            font=("Arial", 11),
            text_color="#4a9eff"
        )
        self.label_metodo.pack(pady=(0, 12))

        # Log de ângulo detectado (atualizado em tempo real)
        self.label_angulo = ctk.CTkLabel(
            self, text="Ângulo detectado: --",
            font=("Arial", 10), text_color="#3d5a78"
        )
        self.label_angulo.pack()

        # Botão iniciar
        self.btn_processar = ctk.CTkButton(
            self, text="INICIAR PROCESSAMENTO",
            fg_color="#1565c0", hover_color="#1e88e5",
            command=self.iniciar_thread, width=320, height=42
        )
        self.btn_processar.pack(pady=16)

    def selecionar_pdf(self):
        self.pdf_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if self.pdf_path:
            self.btn_arquivo.configure(
                text=f"✔ {os.path.basename(self.pdf_path)}", fg_color="gray"
            )

    def selecionar_pasta(self):
        self.dest_path = filedialog.askdirectory()
        if self.dest_path:
            self.btn_destino.configure(text="✔ Pasta Selecionada", fg_color="gray")

    def iniciar_thread(self):
        if not self.pdf_path or not self.dest_path:
            messagebox.showwarning("Atenção", "Selecione o PDF e a pasta de destino!")
            return
        self.btn_processar.configure(state="disabled")
        threading.Thread(target=self.processar, daemon=True).start()

    def processar(self):
        inicio = time.time()
        try:
            doc = fitz.open(self.pdf_path)
            total = len(doc)
            prefixo = self.entry_prefixo.get()

            for i in range(total):
                self.progress_bar.set((i + 1) / total)
                self.label_status.configure(
                    text=f"Analisando página {i+1} de {total}..."
                )

                # Detecta ângulo para exibir no UI (reutiliza a lógica interna)
                pix = doc[i].get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                arr_preview = np.array(
                    Image.open(io.BytesIO(pix.tobytes("png"))).convert('L')
                )
                angulo_detectado = detectar_angulo_hough(arr_preview)
                self.label_angulo.configure(
                    text=f"Ângulo Hough detectado: {angulo_detectado:+.2f}°"
                )

                data = buscar_data_otimizado(doc[i])
                caminho = salvar_unico(self.dest_path, data, prefixo)

                novo = fitz.open()
                novo.insert_pdf(doc, from_page=i, to_page=i)
                novo.save(caminho)
                novo.close()

                decorrido = time.time() - inicio
                vel = (i + 1) / decorrido
                eta = (total - (i + 1)) / vel
                m, s = divmod(int(eta), 60)
                self.label_metrics.configure(
                    text=f"Velocidade: {vel*60:.1f} pág/min  |  ETA: {m:02d}:{s:02d}"
                )

            doc.close()
            total_s = time.time() - inicio
            messagebox.showinfo(
                "Concluído",
                f"{total} páginas processadas em {total_s:.1f}s\n"
                f"Média: {total_s/total:.1f}s por página"
            )

        except Exception as e:
            messagebox.showerror("Erro", f"Falha no processamento:\n{str(e)}")
        finally:
            self.btn_processar.configure(state="normal")
            self.label_status.configure(text="Aguardando novos arquivos...")
            self.label_metrics.configure(text="Velocidade: --  |  ETA: --")
            self.label_angulo.configure(text="Ângulo detectado: --")
            self.progress_bar.set(0)


if __name__ == "__main__":
    app = App()
    app.mainloop()
