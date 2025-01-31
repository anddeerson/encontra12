import streamlit as st
import pandas as pd
import re
import matplotlib.pyplot as plt
from PyPDF2 import PdfReader
import pdfplumber
from pdfminer.high_level import extract_text
import unicodedata
from fpdf import FPDF
import time

def normalizar_texto(texto):
    """Remove acentos, converte para minúsculas e remove espaços extras."""
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return re.sub(r'\s+', ' ', texto.strip().lower())

def extrair_texto_pdf(pdf_file):
    """Extrai o texto do PDF utilizando múltiplas estratégias."""
    text = ""
    try:
        # Tentativa 1: PyPDF2
        pdf_reader = PdfReader(pdf_file)
        for page in pdf_reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
        if text.strip():
            return text
    except:
        pass
    
    try:
        # Tentativa 2: pdfplumber
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n" if page.extract_text() else ""
        if text.strip():
            return text
    except:
        pass
    
    try:
        # Tentativa 3: pdfminer
        text = extract_text(pdf_file)
        if text.strip():
            return text
    except:
        pass
    
    return ""  # Retorna string vazia se nenhuma abordagem funcionar

def extrair_nomes_pdf(pdf_file):
    """Extrai nomes completos do PDF, normalizando-os."""
    text = extrair_texto_pdf(pdf_file)
    if not text:
        return []  # Retorna lista vazia caso não consiga extrair texto
    
    # Expressão regular aprimorada para detectar nomes completos
    matches = re.findall(r'\b[A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)+\b', text)
    return sorted({normalizar_texto(name) for name in matches})

def gerar_pdf(resultados):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Relatorio de Alunos Aprovados", ln=True, align='C')
    pdf.ln(10)

    for idx, resultado in enumerate(resultados, start=1):
        pdf.cell(0, 10, f"{idx}. {resultado['Nome']} - {resultado['Arquivo PDF']}", ln=True)

    pdf_file = "alunos_aprovados.pdf"
    pdf.output(pdf_file)
    return pdf_file

def main():
    st.title("Encontra aluno(s) aprovado(s) - Versão Melhorada")
    st.write("Cole a lista de nomes dos alunos no campo abaixo e carregue um ou mais PDFs com as listas de aprovados.")

    nomes_texto = st.text_area("Cole aqui os nomes dos alunos, um por linha:")
    pdf_files = st.file_uploader("Carregar arquivos PDF", type=["pdf"], accept_multiple_files=True)

    if nomes_texto and pdf_files:
        nomes_lista = [normalizar_texto(nome) for nome in nomes_texto.split("\n") if nome.strip()]
        csv_names = set(nomes_lista)

        results = []
        failed_pdfs = []
        total_pdfs = len(pdf_files)
        progress_bar = st.progress(0)

        for i, pdf_file in enumerate(pdf_files, start=1):
            approved_names = extrair_nomes_pdf(pdf_file)
            if not approved_names:
                failed_pdfs.append(pdf_file.name)
                continue

            common_names = sorted(csv_names.intersection(approved_names))
            for idx, name in enumerate(common_names, start=1):
                results.append({"Ordem": idx, "Nome": name, "Arquivo PDF": pdf_file.name})

            progress_bar.progress(i / total_pdfs)

        if results:
            st.success("Alunos aprovados encontrados!")
            results_df = pd.DataFrame(results)
            st.dataframe(results_df)

            csv_download = results_df.to_csv(index=False).encode("utf-8")
            st.download_button("Baixar resultados como CSV", data=csv_download, file_name="alunos_aprovados.csv")

            pdf_download = gerar_pdf(results)
            with open(pdf_download, "rb") as pdf_file:
                st.download_button("Baixar resultados como PDF", data=pdf_file, file_name="alunos_aprovados.pdf",
                                   mime="application/pdf")
        else:
            st.warning("Nenhum aluno aprovado foi encontrado nos PDFs enviados.")

        if failed_pdfs:
            st.error(f"Falha ao extrair texto dos seguintes PDFs: {', '.join(failed_pdfs)}")

if __name__ == "__main__":
    main()
