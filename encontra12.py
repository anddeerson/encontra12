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
from pdf2image import convert_from_path
import pytesseract

def normalizar_texto(texto):
    """Remove acentos, converte para minúsculas e remove espaços extras."""
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return re.sub(r'\s+', ' ', texto.strip().lower())

def extrair_texto_pdf(pdf_file):
    """Extrai o texto do PDF utilizando múltiplas estratégias, incluindo OCR para PDFs baseados em imagem."""
    text = ""
    is_image_only = True  # Flag para detectar se o PDF é baseado em imagem
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                if page.extract_text():
                    text += page.extract_text() + "\n"
                    is_image_only = False
        if text.strip():
            return text, is_image_only
    except:
        pass
    
    try:
        pdf_reader = PdfReader(pdf_file)
        for page in pdf_reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
                is_image_only = False
        if text.strip():
            return text, is_image_only
    except:
        pass
    
    try:
        text = extract_text(pdf_file)
        if text.strip():
            return text, is_image_only
    except:
        pass
    
    try:
        images = convert_from_path(pdf_file)
        for image in images:
            text += pytesseract.image_to_string(image, lang='por') + "\n"
        if text.strip():
            return text, True  # Se só OCR funcionou, consideramos que é imagem
    except:
        pass
    
    return "", is_image_only  # Retorna string vazia e flag indicando se é imagem

def extrair_nomes_pdf(pdf_file):
    """Extrai nomes completos do PDF, normalizando-os."""
    text, is_image_only = extrair_texto_pdf(pdf_file)
    
    if not text:
        return [], is_image_only
    
    matches = re.findall(r'\b[A-ZÀ-Ú][a-zà-ú]+(?: [A-ZÀ-Ú][a-zà-ú]+)+\b', text)
    return sorted({normalizar_texto(name) for name in matches}), is_image_only

def main():
    st.title("Encontra aluno(s) aprovado(s) - 1.2 Versão Melhorada Para OCR")
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
        
        found_names = {}
        image_only_pdfs = []
        
        for i, pdf_file in enumerate(pdf_files, start=1):
            approved_names, is_image_only = extrair_nomes_pdf(pdf_file)
            if not approved_names:
                failed_pdfs.append(pdf_file.name)
                continue
            
            if is_image_only:
                image_only_pdfs.append(pdf_file.name)
            
            for name in csv_names.intersection(approved_names):
                if name not in found_names:
                    found_names[name] = []
                found_names[name].append(pdf_file.name)
            
            progress_bar.progress(i / total_pdfs)
        
        if found_names:
            st.success("Alunos aprovados encontrados!")
            results_df = pd.DataFrame([{"Nome": name, "Arquivos PDF": ", ".join(files)} for name, files in found_names.items()])
            st.dataframe(results_df)
        else:
            st.warning("Nenhum aluno aprovado foi encontrado nos PDFs enviados.")
        
        if failed_pdfs:
            st.error(f"Falha ao extrair texto dos seguintes PDFs: {', '.join(failed_pdfs)}")
        
        if image_only_pdfs:
            st.warning(f"Os seguintes PDFs são imagens e foram processados com OCR: {', '.join(image_only_pdfs)}")

if __name__ == "__main__":
    main()
