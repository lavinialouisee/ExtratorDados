from flask import Flask, request, jsonify
import os
import pytesseract
from pdf2image import convert_from_path
import camelot
import re
import logging

# Configuração do Tesseract (ajuste o caminho conforme necessário)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__)

# Configuração de logs
logging.basicConfig(level=logging.INFO)

def extrair_tabelas_do_texto(texto):
    """
    Extrai tabelas de um texto usando regex.
    Esta função assume que as tabelas são delimitadas por linhas com valores separados por espaços ou tabulações.
    """
    tabelas = []
    padrao = r"(\S+)\s+(\S+)\s+(\S+)"  # Regex para identificar linhas com 3 colunas
    matches = re.findall(padrao, texto)
    
    if matches:
        tabelas.append(matches)  # Adiciona as linhas encontradas como uma tabela
    
    return tabelas

@app.route('/upload', methods=['POST'])
def upload_file():
    logging.info("Requisição recebida.")
    if 'file' not in request.files:
        logging.error("Nenhum arquivo enviado.")
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files['file']
    if file.filename == '':
        logging.error("Nome de arquivo inválido.")
        return jsonify({"error": "Nome de arquivo inválido"}), 400

    # Salvar o arquivo temporariamente
    uploads_dir = "uploads"
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
    file_path = os.path.join(uploads_dir, file.filename)
    file.save(file_path)
    logging.info(f"Arquivo salvo em: {file_path}")

    # Extrair texto com OCR
    texto_extraido = ""
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        texto_extraido = pytesseract.image_to_string(file_path)
    elif file_path.lower().endswith('.pdf'):
        imagens = convert_from_path(file_path)
        for imagem in imagens:
            texto_extraido += pytesseract.image_to_string(imagem)
    logging.info(f"Texto extraído: {texto_extraido}")

    # Extrair tabelas
    tabelas = []
    if file_path.lower().endswith('.pdf'):
        # Extrair tabelas de PDFs usando Camelot
        tabelas_lattice = camelot.read_pdf(file_path, flavor='lattice', pages='all', line_scale=40)
        tabelas_stream = camelot.read_pdf(file_path, flavor='stream', pages='all', row_tol=10)
        
        # Adicionar tabelas extraídas à lista
        tabelas.extend(tabelas_lattice)
        tabelas.extend(tabelas_stream)
        
        logging.info(f"Número de tabelas extraídas do PDF: {len(tabelas)}")
    else:
        # Extrair tabelas de texto ou imagens usando regex
        tabelas = extrair_tabelas_do_texto(texto_extraido)
        logging.info(f"Número de tabelas extraídas do texto/imagem: {len(tabelas)}")

    # Converter tabelas para JSON
    tabelas_json = []
    for tabela in tabelas:
        if isinstance(tabela, list):  # Tabelas extraídas com regex
            tabelas_json.append({"dados": tabela})
        else:  # Tabelas extraídas com Camelot
            tabelas_json.append(tabela.df.to_dict())

    # Retornar resultados
    return jsonify({
        "texto_extraido": texto_extraido,
        "tabelas": tabelas_json
    })

if __name__ == '__main__':
    logging.info("API iniciada.")
    app.run(debug=True)