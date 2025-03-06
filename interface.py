import streamlit as st
import requests

# Título da aplicação
st.title("Extrator de Dados de Documentos")

# Upload de arquivo
uploaded_file = st.file_uploader(
    "Faça o upload de um documento (PDF, JPEG, JPG, PNG)", type=["pdf", "jpeg", "jpg", "png"])

if uploaded_file is not None:
    st.write("Arquivo carregado com sucesso!")

    # Botão para extrair dados
    if st.button("Extrair Dados"):
        files = {"file": uploaded_file}
        response = requests.post("http://127.0.0.1:5000/upload", files=files)

        if response.status_code == 200:
            dados = response.json()

            # Exibir texto extraído
            st.subheader("Texto Extraído (OCR):")
            st.text(dados["texto_extraido"])

            # Exibir tabelas extraídas
            st.subheader("Tabelas Extraídas:")
            for tabela in dados["tabelas"]:
                st.write(tabela)
        else:
            st.error("Erro ao processar o arquivo.")
