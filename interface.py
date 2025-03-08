import streamlit as st
import requests
import base64

# Título da aplicação
st.title("Extrator de Dados de Documentos")

# Inicializar o estado da sessão
if "dados_extraidos" not in st.session_state:
    st.session_state.dados_extraidos = None
if "planilha_bytes" not in st.session_state:
    st.session_state.planilha_bytes = None
if "arquivo_anterior" not in st.session_state:
    st.session_state.arquivo_anterior = None

# Upload de arquivo
uploaded_file = st.file_uploader(
    "Faça o upload de um documento (PDF, JPEG, JPG, PNG)", type=["pdf", "jpeg", "jpg", "png"])

# Verificar se o arquivo foi removido
if st.session_state.arquivo_anterior is not None and uploaded_file is None:
    # O usuário removeu o arquivo, então resetamos o estado
    st.session_state.dados_extraidos = None
    st.session_state.planilha_bytes = None
    st.session_state.arquivo_anterior = None
    st.rerun()  # Recarrega a página para aplicar as mudanças

# Atualizar o arquivo anterior no estado da sessão
if uploaded_file is not None:
    st.session_state.arquivo_anterior = uploaded_file

# Campo para o tipo de documento
tipo_documento = st.text_input(
    "Informe o tipo de documento (ex: nota fiscal, fatura, contrato):")

if uploaded_file is not None and tipo_documento:
    st.write("Arquivo carregado com sucesso!")

    # Botão para extrair dados
    if st.button("Extrair Dados"):
        files = {"file": uploaded_file}
        data = {"tipo_documento": tipo_documento}
        response = requests.post(
            "http://127.0.0.1:5000/upload", files=files, data=data)

        if response.status_code == 200:
            dados = response.json()

            # Armazenar os dados extraídos no estado da sessão
            st.session_state.dados_extraidos = dados["campos_importantes"]
            st.session_state.planilha_bytes = base64.b64decode(
                dados["planilha"])

            st.success("Dados extraídos com sucesso!")
        else:
            st.error("Erro ao processar o arquivo.")

# Exibir campos importantes identificados pela LLM (se disponíveis)
if st.session_state.dados_extraidos:
    st.subheader("Campos Importantes:")
    st.text(st.session_state.dados_extraidos)

# Botão de download da planilha (se disponível)
if st.session_state.planilha_bytes:
    st.download_button(
        label="Baixar Planilha",
        data=st.session_state.planilha_bytes,
        file_name="dados_extraidos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
