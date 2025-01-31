import streamlit as st
import pandas as pd
import re
import pdfplumber
import unicodedata
from pdf2image import convert_from_bytes
import pytesseract
from difflib import get_close_matches

def normalizar_texto(texto):
    """Remove acentos, espaços extras e converte para minúsculas."""
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return texto.lower().strip()

def extrair_texto_pdf(pdf_file):
    """Tenta extrair texto diretamente do PDF. Se falhar, usa OCR."""
    texto = ""

    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    texto += page_text + "\n"
    except Exception:
        return ""

    # Se não encontrou texto, usa OCR
    if not texto.strip():
        texto = extrair_texto_ocr(pdf_file)

    return texto

def extrair_texto_ocr(pdf_file):
    """Extrai texto de PDFs digitalizados convertendo em imagem e aplicando OCR."""
    texto = ""
    images = convert_from_bytes(pdf_file.read())

    for img in images:
        texto += pytesseract.image_to_string(img, lang="por") + "\n"

    return texto

def extrair_nomes(texto):
    """Extrai nomes completos do texto do PDF usando regex aprimorada."""
    
    # Expressão regular para capturar nomes completos
    matches = re.findall(r'\b[A-ZÁÉÍÓÚ][a-záéíóú]+\s[A-ZÁÉÍÓÚ][a-záéíóú]+(?:\s[A-ZÁÉÍÓÚ][a-záéíóú]+)*\b', texto)

    # Filtra apenas nomes reais e evita palavras comuns em editais
    palavras_excluidas = ["MINISTÉRIO", "EDITAL", "CLASSIFICAÇÃO", "CONCORRÊNCIA", "INSCRIÇÃO"]
    nomes_filtrados = [nome for nome in matches if len(nome.split()) >= 2 and not any(palavra in nome for palavra in palavras_excluidas)]

    nomes_extraidos = sorted({normalizar_texto(name) for name in nomes_filtrados})

    return nomes_extraidos

def encontrar_nomes_similares(nome_digitado, lista_nomes_extraidos):
    """Tenta encontrar nomes semelhantes para corrigir pequenos erros de OCR, com maior precisão."""
    match = get_close_matches(nome_digitado, lista_nomes_extraidos, n=1, cutoff=0.95)  # Maior precisão para evitar falsos positivos
    return match[0] if match else None

def main():
    st.title("Encontra aluno(s) aprovado(s)")
    st.write("Cole a lista de nomes dos alunos no campo abaixo e carregue um ou mais PDFs com as listas de aprovados.")

    # Campo para colar os nomes dos alunos
    nomes_texto = st.text_area("Cole aqui os nomes dos alunos, um por linha:")

    # Upload de arquivos PDF
    pdf_files = st.file_uploader("Carregar arquivos PDF", type=["pdf"], accept_multiple_files=True)

    if nomes_texto and pdf_files:
        # Normaliza a lista de nomes fornecida pelo usuário
        nomes_lista = [normalizar_texto(nome) for nome in nomes_texto.split("\n") if nome.strip()]
        csv_names = set(nomes_lista)

        results = []

        # Processa cada PDF carregado
        for pdf_file in pdf_files:
            texto_pdf = extrair_texto_pdf(pdf_file)
            approved_names = extrair_nomes(texto_pdf)

            # Verifica se os nomes fornecidos estão na lista de aprovados
            for nome in csv_names:
                nome_correto = encontrar_nomes_similares(nome, approved_names)
                if nome_correto:
                    results.append({"Nome": nome_correto, "Arquivo PDF": pdf_file.name})

        # Se houver resultados, exibe os nomes encontrados e o botão de download
        if results:
            st.write("### Alunos Aprovados Encontrados:")
            for resultado in results:
                st.write(f"- {resultado['Nome']} (Arquivo: {resultado['Arquivo PDF']})")

            # Cria um DataFrame para o CSV
            results_df = pd.DataFrame(results)

            # Botão para baixar CSV
            csv_download = results_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Baixar resultados como CSV",
                data=csv_download,
                file_name="alunos_aprovados.csv",
                mime="text/csv"
            )
        else:
            st.warning("Nenhum aluno aprovado foi encontrado nos PDFs enviados.")

if __name__ == "__main__":
    main()
