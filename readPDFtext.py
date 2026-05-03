import fitz  # PyMuPDF
import easyocr
import re
import os
import io
import numpy as np
from PIL import Image

# Inicializa o leitor (pt = português)
reader = easyocr.Reader(['pt'], gpu=False) 

# Variável global para memorizar a última rotação bem-sucedida
ultima_rotacao_sucesso = 0

def buscar_data_com_ocr_otimizado(page):
    """
    Tenta encontrar uma data testando primeiro a última rotação que funcionou.
    """
    global ultima_rotacao_sucesso
    
    # Renderiza a página em alta definição
    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
    img_pil = Image.open(io.BytesIO(pix.tobytes("png")))

    # Define a ordem de teste: primeiro a última que funcionou, depois as outras
    outros_angulos = [0,270, 180, 90]
    if ultima_rotacao_sucesso in outros_angulos:
        outros_angulos.remove(ultima_rotacao_sucesso)
    
    ordem_teste = [ultima_rotacao_sucesso] + outros_angulos
    
    for angulo in ordem_teste:
        # Rotaciona e converte para array
        img_temp = img_pil.rotate(angulo, expand=True)
        img_array = np.array(img_temp)

        # Executa o OCR[cite: 1]
        resultados = reader.readtext(img_array, detail=0)
        texto_completo = " ".join(resultados)

        # Regex para DD/MM/AAAA ou D/M/AA[cite: 1]
        datas = re.findall(r'(\d{1,2}/\d{1,2}/\d{2,4})', texto_completo)

        if datas:
            ultima_rotacao_sucesso = angulo  # Memoriza para a próxima página[cite: 1]
            return datas[0].replace('/', '-')

    return None

def salvar_com_nome_unico(pasta, data, prefixo=""):
    """
    Gera um nome de arquivo único adicionando sufixos se a data for duplicada[cite: 1].
    """
    data_str = data if data else "DATA_NAO_LIDA"
    nome_base = f"{prefixo}-{data_str}"
    extensao = ".pdf"
    
    caminho_final = os.path.join(pasta, f"{nome_base}{extensao}")
    
    # Se o arquivo já existir, adiciona _1, _2, etc.[cite: 1]
    contador = 1
    while os.path.exists(caminho_final):
        caminho_final = os.path.join(pasta, f"{nome_base}_{contador}{extensao}")
        contador += 1
        
    return caminho_final

def processar_pdf(arquivo_entrada, pasta_saida):
    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)

    doc = fitz.open(arquivo_entrada)
    print(f"Processando {len(doc)} páginas de {arquivo_entrada}...")

    for i in range(len(doc)):
        print(f"Página {i+1}:")
        
        # Busca a data com a otimização de rotação[cite: 1]
        data_encontrada = buscar_data_com_ocr_otimizado(doc[i])
        
        # Define o caminho único para evitar duplicatas[cite: 1]
        caminho_destino = salvar_com_nome_unico(pasta_saida, data_encontrada)

        # Extrai e salva a página[cite: 1]
        novo_pdf = fitz.open()
        novo_pdf.insert_pdf(doc, from_page=i, to_page=i)
        novo_pdf.save(caminho_destino)
        novo_pdf.close()
        
        print(f"  -> Salvo: {os.path.basename(caminho_destino)}")

    doc.close()
    print("\n--- Concluído ---")

if __name__ == "__main__":
    # Teste com o seu arquivo[cite: 1]
    processar_pdf('Teste_merged.pdf', 'Documentos_Processados')