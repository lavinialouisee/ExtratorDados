from flask import Flask, request, jsonify, send_file
import os
import pytesseract
from pdf2image import convert_from_path
import camelot
import re
import logging
from openai import OpenAI
import pandas as pd
from io import BytesIO
import base64

# Configuração do Tesseract (ajuste o caminho conforme necessário)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

organization = os.environ.get('ORG_ID')
project = os.environ.get('PROJECT_ID')
api_key = os.environ.get('OPENAI_API_KEY')

# Configuração da OpenAI
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
    Esta função assume que as tabelas são delimitadas por linhas com valores separados por espaços ou tabulações.
    """
    tabelas = []
    # Regex para identificar linhas com 3 colunas
    padrao = r"(\S+)\s+(\S+)\s+(\S+)"
    matches = re.findall(padrao, texto)

    if matches:
        # Adiciona as linhas encontradas como uma tabela
        tabelas.append(matches)

    return tabelas


def processar_com_llm(texto_bruto, tabelas, tipo_documento):
    # Converter tabelas para string
    tabelas_str = ""
    for tabela in tabelas:
        if isinstance(tabela, list):  # Tabelas extraídas com regex
            tabelas_str += "\n".join(["\t".join(linha)
                                     for linha in tabela]) + "\n\n"
        else:  # Tabelas extraídas com Camelot
            tabelas_str += tabela.df.to_string() + "\n\n"

    # Combinar texto bruto e tabelas
    texto_completo = f"Texto bruto:\n{texto_bruto}\n\nTabelas:\n{tabelas_str}"

    # Prompt para a LLM
    prompt = f"""
    Você é um assistente especializado em extrair informações importantes de documentos.
    O usuário enviou um documento do tipo: {tipo_documento}. Em documentos com destinatário e remetente é importante
    citar essas duas entidades que podem ser por exemplo, nome da empresa e nome do cliente respectivamente.
    Abaixo está o texto bruto e as tabelas extraídas do documento:

    {texto_completo}

    Identifique e retorne os campos mais importantes para um documento do tipo {tipo_documento}. 
    Sua resposta deve seguir o padrão de um campo por linha,
    com a cada linha contendo o nome do campo ou item seguido por um "=" e o valor do campo ou item
    """

    # Chamar a API da OpenAI (nova interface)
    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt}
        ],
        max_tokens=5000
    )

    # Retornar a resposta da LLM
    return resposta.choices[0].message.content


def gerar_planilha(campos_importantes):
    """
    Converte a saída da LLM em um DataFrame e gera um arquivo Excel.
    """
    # Extrair campos e valores
    dados = {}
    for linha in campos_importantes.split("\n"):
        if "=" in linha:
            campo, valor = linha.split("=", 1)
            dados[campo.strip()] = valor.strip()

    # Criar DataFrame
    df = pd.DataFrame(list(dados.items()), columns=["Campo", "Valor"])

    # Salvar DataFrame em um arquivo Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    return output


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

    # Obter o tipo de documento do formulário
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

    # Processar texto e tabelas com a LLM
    campos_importantes = processar_com_llm(
        texto_extraido, tabelas, tipo_documento)

    # Gerar planilha
    planilha = gerar_planilha(campos_importantes)

    # Codificar a planilha em base64
    planilha_base64 = base64.b64encode(planilha.getvalue()).decode("utf-8")

    # Retornar resultados
    return jsonify({
        "campos_importantes": campos_importantes,
        "planilha": planilha_base64  # Planilha codificada em base64
    })


if __name__ == '__main__':
    logging.info("API iniciada.")
    app.run(debug=True)
