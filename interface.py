"""
Módulo da interface Streamlit para interação com a API de extração de dados.
"""

import streamlit as st
import requests
import base64

# Título da aplicação
st.title("📄 Extrator de Dados de Documentos")

# Inicializar o estado da sessão
if "dados_extraidos" not in st.session_state:
    st.session_state.dados_extraidos = None
if "planilha_bytes" not in st.session_state:
    st.session_state.planilha_bytes = None
if "arquivo_anterior" not in st.session_state:
    st.session_state.arquivo_anterior = None


def limpar_estado():
    """Limpa o estado da sessão quando o arquivo é removido."""
    st.session_state.dados_extraidos = None
    st.session_state.planilha_bytes = None
    st.session_state.arquivo_anterior = None
    st.rerun()


def processar_arquivo(uploaded_file, tipo_documento):
    """
    Envia o arquivo para a API e processa a resposta.

    Args:
        uploaded_file (UploadedFile): Arquivo carregado pelo usuário.
        tipo_documento (str): Tipo do documento informado pelo usuário.
    """
    with st.spinner("Processando arquivo..."):
        try:
            files = {"file": uploaded_file}
            data = {"tipo_documento": tipo_documento}
            response = requests.post(
                "http://127.0.0.1:5000/upload", files=files, data=data)
            response.raise_for_status()

            dados = response.json()
            st.session_state.dados_extraidos = dados["campos_importantes"]
            st.session_state.planilha_bytes = base64.b64decode(
                dados["planilha"])
            st.success("✅ Dados extraídos com sucesso!")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Erro ao processar o arquivo: {e}")


# Upload de arquivo
uploaded_file = st.file_uploader(
    "Faça o upload de um documento (PDF, JPEG, JPG, PNG)", type=["pdf", "jpeg", "jpg", "png"])

# Verificar se o arquivo foi removido
if st.session_state.arquivo_anterior is not None and uploaded_file is None:
    limpar_estado()

# Atualizar o arquivo anterior no estado da sessão
if uploaded_file is not None:
    st.session_state.arquivo_anterior = uploaded_file

# Campo para o tipo de documento
tipo_documento = st.text_input(
    "Informe o tipo de documento (ex: nota fiscal, fatura, contrato):")

if uploaded_file is not None and tipo_documento:
    st.write("✅ Arquivo carregado com sucesso!")

    # Botão para extrair dados
    if st.button("Extrair Dados"):
        processar_arquivo(uploaded_file, tipo_documento)

# Exibir campos importantes
if st.session_state.dados_extraidos:
    st.subheader("📋 Campos Importantes:")
    st.write(st.session_state.dados_extraidos)

# Botão de download da planilha
if st.session_state.planilha_bytes:
    st.download_button(
        label="📥 Baixar Planilha",
        data=st.session_state.planilha_bytes,
        file_name="dados_extraidos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Clique para baixar a planilha com os dados extraídos."
    )
