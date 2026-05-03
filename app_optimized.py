import fitz  # PyMuPDF
import easyocr
import re
import os
import io
import time
import numpy as np
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading

# Inicialização do leitor de OCR (Carregado uma única vez)
# gpu=False para compatibilidade geral, mude para True se tiver NVIDIA GPU
reader = easyocr.Reader(['pt'], gpu=False)
ultima_rotacao_sucesso = 0

def buscar_data_otimizado(page):
    """
    Busca data com 3 níveis de prioridade:
    1. Texto nativo (Instantâneo)
    2. OCR na última rotação de sucesso (Rápido)
    3. OCR em outras rotações (Lento - fallback)
    """
    global ultima_rotacao_sucesso
    
    # --- NÍVEL 1: BUSCA NATIVA (0ms) ---
    # Muitos PDFs têm camada de texto, mesmo que pareçam scan.
    texto_nativo = page.get_text()
    datas = re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', texto_nativo)
    if datas:
        return datas[0].replace('/', '-')

    # --- NÍVEL 2: OCR OTIMIZADO ---
    # Reduzimos Matrix para 1.5 (Equilíbrio entre velocidade e precisão)
    # 3.0 é excessivo para leitura de datas.
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    # Convertemos para 'L' (Grayscale) para o OCR processar apenas 1 canal de cor
    img_pil = Image.open(io.BytesIO(pix.tobytes("png"))).convert('L')

    outros_angulos = [0, 90, 180, 270]
    if ultima_rotacao_sucesso in outros_angulos:
        outros_angulos.remove(ultima_rotacao_sucesso)
    
    ordem_teste = [ultima_rotacao_sucesso] + outros_angulos
    
    for angulo in ordem_teste:
        if angulo == 0:
            img_temp = img_pil
        else:
            img_temp = img_pil.rotate(angulo, expand=True)
            
        img_array = np.array(img_temp)
        
        # detail=0 retorna apenas o texto, ignorando coordenadas (mais rápido)
        resultados = reader.readtext(img_array, detail=0)
        texto_ocr = " ".join(resultados)
        datas_ocr = re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', texto_ocr)

        if datas_ocr:
            ultima_rotacao_sucesso = angulo
            return datas_ocr[0].replace('/', '-')
            
    return None

def salvar_unico(pasta, data, prefixo):
    data_str = data if data else "DATA_NAO_LIDA"
    # Garante que o prefixo termine com espaço ou traço se preenchido
    pref = f"{prefixo}-" if prefixo else ""
    nome_base = f"{pref}{data_str}"
    caminho = os.path.join(pasta, f"{nome_base}.pdf")
    
    contador = 1
    while os.path.exists(caminho):
        caminho = os.path.join(pasta, f"{nome_base}_{contador}.pdf")
        contador += 1
    return caminho

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Processador Inteligente de PDF v2.0")
        self.geometry("600x500")
        ctk.set_appearance_mode("dark")

        # Layout
        self.btn_arquivo = ctk.CTkButton(self, text="Selecionar PDF de Origem", command=self.selecionar_pdf)
        self.btn_arquivo.pack(pady=15)

        self.btn_destino = ctk.CTkButton(self, text="Selecionar Pasta de Destino", command=self.selecionar_pasta)
        self.btn_destino.pack(pady=5)

        self.entry_prefixo = ctk.CTkEntry(self, placeholder_text="Prefixo opcional (ex: NF, RECIBO)")
        self.entry_prefixo.pack(pady=15)

        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=20)

        self.label_status = ctk.CTkLabel(self, text="Aguardando arquivos...")
        self.label_status.pack()

        self.label_metrics = ctk.CTkLabel(self, text="Velocidade: -- | Restante: --", font=("Arial", 11))
        self.label_metrics.pack(pady=10)

        self.btn_processar = ctk.CTkButton(self, text="INICIAR PROCESSAMENTO", 
                                         fg_color="#27ae60", hover_color="#2ecc71",
                                         command=self.iniciar_thread)
        self.btn_processar.pack(pady=20)

        self.pdf_path = ""
        self.dest_path = ""

    def selecionar_pdf(self):
        self.pdf_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if self.pdf_path: 
            self.btn_arquivo.configure(text=f"✔ {os.path.basename(self.pdf_path)}", fg_color="gray")

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
        start_time_total = time.time()
        
        try:
            doc = fitz.open(self.pdf_path)
            total_paginas = len(doc)
            prefixo = self.entry_prefixo.get()

            for i in range(total_paginas):
                # UI Update
                progresso = (i + 1) / total_paginas
                self.progress_bar.set(progresso)
                self.label_status.configure(text=f"Analisando página {i+1} de {total_paginas}...")

                # Lógica Otimizada
                data = buscar_data_otimizado(doc[i])
                caminho = salvar_unico(self.dest_path, data, prefixo)
                
                # Extração e salvamento físico
                novo_pdf = fitz.open()
                novo_pdf.insert_pdf(doc, from_page=i, to_page=i)
                novo_pdf.save(caminho)
                novo_pdf.close()

                # Métricas em Tempo Real
                elapsed = time.time() - start_time_total
                pag_per_sec = (i + 1) / elapsed
                eta_sec = (total_paginas - (i + 1)) / pag_per_sec
                
                minutos, segundos = divmod(int(eta_sec), 60)
                self.label_metrics.configure(
                    text=f"Velocidade: {pag_per_sec*60:.1f} pág/min | ETA: {minutos:02d}:{segundos:02d}"
                )

            doc.close()
            messagebox.showinfo("Sucesso", f"Concluído!\n{total_paginas} páginas processadas em {time.time()-start_time_total:.1f}s")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Falha no processamento: {str(e)}")
        finally:
            self.btn_processar.configure(state="normal")
            self.label_status.configure(text="Aguardando novos arquivos...")
            self.progress_bar.set(0)

if __name__ == "__main__":
    app = App()
    app.mainloop()