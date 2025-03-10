# __Extrator de Dados de Documentos com LLM__

Este projeto tem como objetivo a extração de dados de documentos (PDF, JPEG, JPG, PNG). A abordagem escolhida foi primeiro a utilização do Tesseract OCR para extrair o texto presente no documento e o depois o texto extraído é enviado para um requisição de uma LLM (no caso, a Openai) para a seleção de dados relevantes, e depois os dados retorna a aplicação e também pode ser acessados por uma planilha.

##  __Integrantes da Equipe__

- **Lanna Luara Novaes Silva** ([Perfil no Github](github.com/lannalua))
- **Lavínia Louise Rosa Santos** ([Perfil no Github](github.com/lavinialouisee))

##  __Pontos Importantes__

O projeto apresentado utiliza algumas tecnologias:
- Tesseract OCR para extrair texto em imagens
- camelot-py para extrair tabelas de arquivos PDF
- pdf2image para converter páginas de PDF em imagens (para o aplicar o OCR depois)
- pandas para manipulação e nálise de dados estruturados
- flask para criar uma API web no Python
- openai para integrar com LLM para análise do texto extraído


##  __Instalação e Configuração__

A seguir será apresentada a instalação das extensões necessárias. Também há o arquivo `requirements.txt` com as extensões utilizadas. 

### Instalação e Configuração

1. Clone o repositório e instale as dependências necessárias:

    Para o arquivo `app.py`,
    ```sh
    pip install camelot-py pandas pytesseract Flask openai pdf2image
    ```
    Para o arquivo `interface.py`
    ```sh
    pip install streamlit
    ```

2. Tesseract OCR e Poppler

    O Tesseract OCR precisa estar instalado no sistema
    No Ubuntu,
    ```sh
    sudo apt install tesseract-ocr
    ```
    No Windows, a instalação está disponível no [Link Instalação Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)

    O Poppler faz parte do pdf2image e também precisa estar instalado no sistema
    No Ubuntu,
    ```sh
    sudo apt install poppler-utils
    ```
    No Windows, a instalação está disponível no [Link Instalação Poppler](https://github.com/oschwartz10612/poppler-windows/releases) e precisa ser adicionado ao PATH do sistema.


3. Execução:
    Execute primeiro o `app.py` para iniciar a aplicação
    ```sh
    python app.py
    ```
    Após isso, execute o seguinte comando para a `interface.py` 
    ```sh
    streamlit run interface.py
    ```
    Será aberta uma página no browser para a aplicação. 
