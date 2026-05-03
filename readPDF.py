import fitz  # PyMuPDF
import easyocr
import re
import os
import io
import numpy as np
from PIL import Image

# Inicializa o leitor do EasyOCR. 
# 'pt' para português e 'en' para inglês. 
# Na primeira vez, ele baixará os modelos (cerca de 100MB) automaticamente.
reader = easyocr.Reader(['pt', 'en'], gpu=False) 

def buscar_data_com_easyocr(page):
    """
    Renderiza a página e utiliza o EasyOCR para encontrar a data.
    """
    # 1. Renderiza a página em alta definição (Zoom 3x)
    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
    
    # 2. Converte para um formato que o EasyOCR aceita (Numpy array via Pillow)
    img_pil = Image.open(io.BytesIO(pix.tobytes("png")))
    img_array = np.array(img_pil)

    # 3. Executa a leitura
    # detail=0 retorna apenas o texto, facilitando a busca
    resultados = reader.readtext(img_array, detail=0)
    
    # Junta tudo em uma string para aplicar o Regex
    texto_completo = " ".join(resultados)
    
    # Busca o padrão de data (DD/MM/AAAA)
    datas = re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', texto_completo)
    
    # Retorna a primeira data encontrada com hífen para o nome do arquivo
    return datas[0].replace('/', '-') if datas else None

def processar_pdf(arquivo_entrada, pasta_saida):
    """
    Lê o PDF, identifica datas e separa as páginas.
    """
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)

    doc = fitz.open(arquivo_entrada)
    print(f"Documento aberto: {len(doc)} páginas.")

    for i in range(len(doc)):
        print(f"Analisando página {i+1}...")
        
        # Tenta extrair a data
        data_arquivo = buscar_data_com_easyocr(doc[i])
        
        prefixo = data_arquivo if data_arquivo else "DATA_DESCONHECIDA"
        nome_final = f"{prefixo}_pag_{i+1}.pdf"
        caminho_final = os.path.join(pasta_saida, nome_final)

        # Cria um novo PDF com a página atual
        novo_pdf = fitz.open()
        novo_pdf.insert_pdf(doc, from_page=i, to_page=i)
        novo_pdf.save(caminho_final)
        novo_pdf.close()
        
        print(f"  -> Sucesso: {nome_final}")

    doc.close()
    print("\n--- Processo concluído! ---")

if __name__ == "__main__":
    # Certifique-se de que o 'Teste.pdf' está na mesma pasta do script
    processar_pdf('Teste.pdf', 'Documentos_EasyOCR')