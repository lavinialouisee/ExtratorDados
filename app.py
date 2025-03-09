"""
Módulo principal da API Flask para extração de dados de documentos.
"""

import base64
import logging
import os
import re
from io import BytesIO


import camelot
import pandas as pd
import pytesseract
from flask import after_this_request, Flask, jsonify, request
from openai import OpenAI
from pdf2image import convert_from_path


# Configuração do Tesseract (ajuste o caminho conforme necessário)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Configuração da OpenAI
organization = os.environ.get('ORG_ID')
project = os.environ.get('PROJECT_ID')
api_key = os.environ.get('OPENAI_API_KEY')

client = OpenAI(
    organization=organization,
    project=project,
    api_key=api_key
)

app = Flask(__name__)

# Configuração de logs
logging.basicConfig(level=logging.INFO)


def extrair_tabelas_do_texto(texto):
    """
    Extrai tabelas de um texto usando regex.

    Args:
        texto (str): Texto bruto extraído do documento.

    Returns:
        list: Lista de tabelas extraídas, onde cada tabela é uma lista de linhas.
    """
    tabelas = []
    # Regex para identificar linhas com 3 colunas
    padrao = r"(\S+)\s+(\S+)\s+(\S+)"
    matches = re.findall(padrao, texto)

    if matches:
        tabelas.append(matches)

    return tabelas


def extrair_tabelas(file_path, texto_extraido):
    """
    Extrai tabelas de um arquivo (PDF ou imagem) usando Camelot para PDFs e regex para texto/imagens.

    Args:
        file_path (str): Caminho do arquivo a ser processado.
        texto_extraido (str): Texto extraído do arquivo (usado para arquivos de imagem).

    Returns:
        list: Lista de tabelas extraídas. Para PDFs, são objetos Camelot; para imagens, são listas de linhas.
    """
    tabelas = []

    if file_path.lower().endswith('.pdf'):
        # Extrair tabelas de PDFs usando Camelot
        tabelas_lattice = camelot.read_pdf(
            file_path, flavor='lattice', pages='all', line_scale=40)
        tabelas_stream = camelot.read_pdf(
            file_path, flavor='stream', pages='all', row_tol=10)

        # Adicionar tabelas extraídas à lista
        tabelas.extend(tabelas_lattice)
        tabelas.extend(tabelas_stream)

        logging.info(f"Número de tabelas extraídas do PDF: {len(tabelas)}")
    else:
        # Extrair tabelas de texto ou imagens usando regex
        tabelas = extrair_tabelas_do_texto(texto_extraido)
        logging.info(
            f"Número de tabelas extraídas do texto/imagem: {len(tabelas)}")

    return tabelas


def processar_com_llm(texto_bruto, tabelas, tipo_documento):
    """
    Processa o texto e as tabelas com um modelo de linguagem (LLM) para extrair campos importantes.

    Args:
        texto_bruto (str): Texto bruto extraído do documento.
        tabelas (list): Lista de tabelas extraídas.
        tipo_documento (str): Tipo do documento (ex: nota fiscal, fatura).

    Returns:
        str: Resposta da LLM com os campos importantes.
    """
    tabelas_str = ""
    for tabela in tabelas:
        if isinstance(tabela, list):  # Tabelas extraídas com regex
            tabelas_str += "\n".join(["\t".join(linha)
                                     for linha in tabela]) + "\n\n"
        else:  # Tabelas extraídas com Camelot
            tabelas_str += tabela.df.to_string() + "\n\n"

    texto_completo = f"Texto bruto:\n{texto_bruto}\n\nTabelas:\n{tabelas_str}"

    prompt = f"""
    Você é um assistente especializado em extrair informações importantes de documentos.
    O usuário enviou um documento do tipo: {tipo_documento}.
    Abaixo está o texto bruto e as tabelas extraídas do documento:

    {texto_completo}

    Identifique e retorne os campos mais importantes para um documento do tipo {tipo_documento}. 
    Sua resposta deve seguir o padrão de um campo por linha,
    com a cada linha contendo o nome do campo ou item seguido por um "=" e o valor do campo ou item
    """

    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=5000
    )

    return resposta.choices[0].message.content


def gerar_planilha(campos_importantes):
    """
    Converte a saída da LLM em um DataFrame e gera um arquivo Excel.

    Args:
        campos_importantes (str): Resposta da LLM com os campos importantes.

    Returns:
        BytesIO: Arquivo Excel em memória.
    """
    # Lista para armazenar os dados
    dados = []

    # Dicionário temporário para armazenar um conjunto de campo=valor
    item_atual = {}

    # Processar cada linha da saída da LLM
    for linha in campos_importantes.split("\n"):
        linha = linha.strip()
        if not linha:
            if item_atual:  # Se houver um item atual, adicioná-lo à lista
                dados.append(item_atual)
                item_atual = {}  # Reiniciar o item atual
            continue

        # Verificar se a linha contém um par campo=valor
        if "=" in linha:
            campo, valor = linha.split("=", 1)
            campo = campo.strip()
            valor = valor.strip()
            item_atual[campo] = valor
        else:
            # Se a linha não contiver '=', tratar como um campo sem valor ou um comentário
            item_atual[linha] = ""

    # Adicionar o último item, se houver
    if item_atual:
        dados.append(item_atual)

    # Criar DataFrame a partir da lista de dicionários
    df = pd.DataFrame(dados)

    # Salvar DataFrame em um arquivo Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    return output


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Endpoint para upload de arquivos e processamento de documentos.
    """
    logging.info("Requisição recebida.")
    if 'file' not in request.files:
        logging.error("Nenhum arquivo enviado.")
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files['file']
    if file.filename == '':
        logging.error("Nome de arquivo inválido.")
        return jsonify({"error": "Nome de arquivo inválido"}), 400

    tipo_documento = request.form.get('tipo_documento', '')
    if not tipo_documento:
        logging.error("Tipo de documento não informado.")
        return jsonify({"error": "Tipo de documento não informado"}), 400

    # Salvar o arquivo temporariamente
    uploads_dir = "uploads"
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
    file_path = os.path.join(uploads_dir, file.filename)
    file.save(file_path)
    logging.info(f"Arquivo salvo em: {file_path}")

    # Função para limpar o arquivo após a resposta
    @after_this_request
    def cleanup(response):
        try:
            os.remove(file_path)
            logging.info(f"Arquivo removido: {file_path}")
        except Exception as e:
            logging.error(f"Erro ao remover arquivo: {e}")
        return response

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
    tabelas = extrair_tabelas(file_path, texto_extraido)

    # Processar texto e tabelas com a LLM
    campos_importantes = processar_com_llm(
        texto_extraido, tabelas, tipo_documento)

    logging.info(campos_importantes)

    # Gerar planilha
    planilha = gerar_planilha(campos_importantes)
    planilha_base64 = base64.b64encode(planilha.getvalue()).decode("utf-8")

    return jsonify({
        "campos_importantes": campos_importantes,
        "planilha": planilha_base64
    })


if __name__ == '__main__':
    logging.info("API iniciada.")
    app.run(debug=True)
