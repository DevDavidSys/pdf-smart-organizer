# 🗂️ PDF Smart Organizer — OCR de Alta Performance

> Desenvolvido durante estágio na **CSN (GDOP)** para automatizar a organização de milhares de documentos escaneados.

---

## 🚨 O Problema Real

Quatro estagiários. Seis horas de trabalho. **4.000 folhas** para renomear manualmente com a data de cada documento.

O processo era simples, porém brutal: abrir o arquivo, ler a data, digitar o nome, salvar. Repetir 4.000 vezes.

> **24 horas de esforço humano combinado** — e ainda estávamos longe de concluir.

Este projeto nasceu da recusa em aceitar esse desperdício.

---

## 💡 A Solução

Um programa Python com uma **heurística de decisão em cascata**, que prioriza velocidade sem sacrificar precisão.

Em vez de tratar todos os documentos da mesma forma, o algoritmo escolhe o caminho mais rápido disponível para cada página:

```
┌─────────────────────────────────────────────────┐
│           FLUXO DE DECISÃO EM CASCATA            │
├──────────────────────────────────────────────────┤
│  1. 📄 Texto Nativo?  ──► SIM → Extração (0ms)  │
│            │                                      │
│           NÃO                                     │
│            ▼                                      │
│  2. 🔄 OCR com última rotação conhecida          │
│     (Grayscale + Matrix 1.5x)                    │
│            │                                      │
│    Data encontrada? ──► SIM → Salvar             │
│            │                                      │
│           NÃO                                     │
│            ▼                                      │
│  3. 🔁 Testar demais rotações (0°, 90°, 180°, 270°)│
└──────────────────────────────────────────────────┘
```

### As 4 Otimizações-Chave

| # | Técnica | Impacto |
|---|---------|---------|
| ⚡ | **Fast Track Nativo** — verifica texto digital antes do OCR | Extração instantânea (ms) quando possível |
| 📉 | **Downscaling Estratégico** — Matrix `3.0` → `1.5` | ~4x menos dados para processar |
| 🎨 | **Pré-processamento Grayscale** — converte para tons de cinza | Reduz canais de cor de 3 para 1 |
| 🧠 | **Memória de Rotação** — aprende com a página anterior | Evita tentativas desnecessárias |

---

## 📊 Benchmark de Performance

Testes realizados em amostra de **5 páginas** de documento real:

| Métrica | Algoritmo Original | Algoritmo Otimizado |
|---------|:-----------------:|:-------------------:|
| Tempo total | `273.68s` | `63.18s` |
| Média por folha | `~54s` | `~12s` |
| **Ganho de performance** | — | **🚀 76.9% mais rápido** |

### Impacto nas 4.000 folhas

```
Trabalho manual:   4 pessoas × 6h = 24h (incompleto)
Método original:   4.000 × 54s   ≈ 60 horas
Método otimizado:  4.000 × 12s   ≈ 13 horas  ✅
```

---

## 🛠️ Tecnologias

- **Python 3.x**
- **[PyMuPDF (fitz)](https://pymupdf.readthedocs.io/)** — manipulação e renderização de PDFs
- **[EasyOCR](https://github.com/JaidedAI/EasyOCR)** — reconhecimento óptico de caracteres (suporte a GPU)
- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** — interface gráfica moderna
- **[Pillow](https://python-pillow.org/) & [NumPy](https://numpy.org/)** — processamento de imagem

---

## 💻 Como Instalar e Usar

**1. Clone o repositório**
```bash
git clone https://github.com/seu-usuario/pdf-smart-organizer.git
cd pdf-smart-organizer
```

**2. Instale as dependências**
```bash
pip install -r requirements.txt
```

**3. Execute o aplicativo**
```bash
python app_optimized.py
```

### Usando a Interface

1. Clique em **"Selecionar PDF de Origem"** e escolha seu arquivo
2. Clique em **"Selecionar Pasta de Destino"**
3. (Opcional) Digite um **prefixo** para os arquivos gerados (ex: `NF`, `ARM#24`)
4. Clique em **"INICIAR PROCESSAMENTO"**

O programa irá separar cada página em um arquivo individual, nomeado com a data encontrada no documento.

---

## 📁 Estrutura do Projeto

```
pdf-smart-organizer/
├── app_optimized.py    # Aplicativo principal com interface gráfica
├── app.py              # Versão inicial (sem otimizações)
├── benchmark.py        # Script de comparação de performance
├── readPDF.py          # Módulo de leitura OCR base
├── readPDFtext.py      # Módulo com otimização de rotação
├── requirements.txt
└── README.md
```

---

## 🔧 requirements.txt

```
pymupdf
easyocr
customtkinter
Pillow
numpy
```

---

## 🎯 Aprendizados

Este projeto demonstra que **otimização algorítmica importa tanto quanto a solução em si**. A diferença entre o método original e o otimizado não está na lógica central — ambos fazem OCR — mas em como os dados são preparados e em quais atalhos podem ser tomados com segurança.

> *Uma solução computacional bem pensada pode transformar dias de trabalho mecânico em horas de processamento automatizado, liberando pessoas para tarefas que realmente exigem julgamento humano.*

---

## 📄 Licença

MIT License — sinta-se livre para usar, modificar e distribuir.
