import fitz  # PyMuPDF
import easyocr
import re
import os
import io
import numpy as np
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading

# Inicializa o leitor globalmente
reader = easyocr.Reader(['pt'], gpu=False)
ultima_rotacao_sucesso = 0

def buscar_data_otimizado(page):
    global ultima_rotacao_sucesso
    pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
    img_pil = Image.open(io.BytesIO(pix.tobytes("png")))

    outros_angulos = [0, 90, 180, 270]
    if ultima_rotacao_sucesso in outros_angulos:
        outros_angulos.remove(ultima_rotacao_sucesso)
    
    ordem_teste = [ultima_rotacao_sucesso] + outros_angulos
    
    for angulo in ordem_teste:
        img_temp = img_pil.rotate(angulo, expand=True)
        img_array = np.array(img_temp)
        resultados = reader.readtext(img_array, detail=0)
        texto = " ".join(resultados)
        datas = re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', texto)

        if datas:
            ultima_rotacao_sucesso = angulo
            return datas[0].replace('/', '-')
    return None

def salvar_unico(pasta, data, prefixo):
    data_str = data if data else "DATA_NAO_LIDA"
    nome_base = f"{prefixo}-{data_str}"
    caminho = os.path.join(pasta, f"{nome_base}.pdf")
    
    contador = 1
    while os.path.exists(caminho):
        caminho = os.path.join(pasta, f"{nome_base}_{contador}.pdf")
        contador += 1
    return caminho

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Organizador de Documentos PDF")
        self.geometry("500x400")

        # Interface
        self.label_arquivo = ctk.CTkLabel(self, text="Selecione o arquivo PDF:")
        self.label_arquivo.pack(pady=(20, 0))
        
        self.btn_arquivo = ctk.CTkButton(self, text="Escolher PDF", command=self.selecionar_pdf)
        self.btn_arquivo.pack(pady=10)

        self.label_destino = ctk.CTkLabel(self, text="Pasta de destino:")
        self.label_destino.pack(pady=(10, 0))
        
        self.btn_destino = ctk.CTkButton(self, text="Escolher Pasta", command=self.selecionar_pasta)
        self.btn_destino.pack(pady=10)

        self.label_prefixo = ctk.CTkLabel(self, text="Prefixo do arquivo (Ex: ARM#24):")
        self.label_prefixo.pack(pady=(10, 0))
        
        self.entry_prefixo = ctk.CTkEntry(self)
        self.entry_prefixo.insert(0, "")
        self.entry_prefixo.pack(pady=10)

        self.btn_processar = ctk.CTkButton(self, text="INICIAR PROCESSAMENTO", fg_color="green", command=self.iniciar_thread)
        self.btn_processar.pack(pady=30)

        self.pdf_path = ""
        self.dest_path = ""

    def selecionar_pdf(self):
        self.pdf_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if self.pdf_path: self.btn_arquivo.configure(text="Arquivo Selecionado ✔", fg_color="gray")

    def selecionar_pasta(self):
        self.dest_path = filedialog.askdirectory()
        if self.dest_path: self.btn_destino.configure(text="Pasta Selecionada ✔", fg_color="gray")

    def iniciar_thread(self):
        if not self.pdf_path or not self.dest_path:
            messagebox.showwarning("Erro", "Selecione o arquivo e o destino!")
            return
        threading.Thread(target=self.processar).start()

    def processar(self):
        self.btn_processar.configure(state="disabled", text="Processando...")
        try:
            doc = fitz.open(self.pdf_path)
            prefixo = self.entry_prefixo.get()
            
            for i in range(len(doc)):
                data = buscar_data_otimizado(doc[i])
                caminho = salvar_unico(self.dest_path, data, prefixo)
                
                novo_pdf = fitz.open()
                novo_pdf.insert_pdf(doc, from_page=i, to_page=i)
                novo_pdf.save(caminho)
                novo_pdf.close()
            
            doc.close()
            messagebox.showinfo("Sucesso", "Processamento concluído com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {str(e)}")
        finally:
            self.btn_processar.configure(state="normal", text="INICIAR PROCESSAMENTO")

if __name__ == "__main__":
    app = App()
    app.mainloop()