import fitz
import easyocr
import re
import os
import io
import time
import numpy as np
from PIL import Image

# Configuração do Leitor
reader = easyocr.Reader(['pt'], gpu=False)

# --- FUNÇÃO ORIGINAL (COMO ESTÁ NO SEU POST) ---
def buscar_data_ORIGINAL(page):
    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3)) # Alta resolução original
    img_pil = Image.open(io.BytesIO(pix.tobytes("png")))
    
    # Simulando apenas uma rotação para o teste ser justo na comparação
    img_array = np.array(img_pil)
    resultados = reader.readtext(img_array, detail=0)
    texto = " ".join(resultados)
    return re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', texto)

# --- FUNÇÃO OTIMIZADA (COM AS MELHORIAS) ---
def buscar_data_OTIMIZADA(page):
    # 1. Tentativa Instantânea (Texto Nativo)
    texto_nativo = page.get_text()
    datas = re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', texto_nativo)
    if datas: return datas, "Nativo"

    # 2. OCR Otimizado (Redução de Matrix de 3 para 1.5 e Grayscale)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)) 
    img_pil = Image.open(io.BytesIO(pix.tobytes("png"))).convert('L') # GrayScale
    
    img_array = np.array(img_pil)
    resultados = reader.readtext(img_array, detail=0)
    texto = " ".join(resultados)
    return re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', texto), "OCR Otimizado"

def rodar_benchmarks(caminho_pdf):
    doc = fitz.open(caminho_pdf)
    num_paginas = min(len(doc), 5) # Testar as primeiras 5 páginas para não demorar
    
    print(f"--- Iniciando Teste em {num_paginas} páginas ---")

    # Teste Original
    start_time = time.time()
    for i in range(num_paginas):
        buscar_data_ORIGINAL(doc[i])
    tempo_original = time.time() - start_time
    print(f"Tempo MÉTODO ORIGINAL: {tempo_original:.2f} segundos")

    # Teste Otimizado
    start_time = time.time()
    for i in range(num_paginas):
        buscar_data_OTIMIZADA(doc[i])
    tempo_otimizado = time.time() - start_time
    print(f"Tempo MÉTODO OTIMIZADO: {tempo_otimizado:.2f} segundos")
    
    # Resultado
    melhoria = ((tempo_original - tempo_otimizado) / tempo_original) * 100
    print(f"\nGanho de performance: {melhoria:.1f}% mais rápido")
    
    doc.close()

if __name__ == "__main__":
    # Certifique-se que o arquivo existe antes de rodar
    arquivo = r'C:\Users\IceCube\Documents\Projects\AnalysisData\PowerEfficence\scripts\Teste_merged.pdf'
    if os.path.exists(arquivo):
        rodar_benchmarks(arquivo)
    else:
        print(f"Arquivo {arquivo} não encontrado para teste.")