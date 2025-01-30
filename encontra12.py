import streamlit as st
import pandas as pd
import re
import pdfplumber
import unicodedata
from fpdf import FPDF
from pdf2image import convert_from_bytes
import pytesseract
from io import BytesIO
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
    except Exception as e:
        st.error(f"Erro ao processar PDF: {e}")
        return ""

    # Se não encontrou texto, usa OCR
    if not texto.strip():
        st.warning("Nenhum texto detectado diretamente. Aplicando OCR...")
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

def gerar_pdf(resultados):
    """Gera um relatório PDF dos alunos aprovados encontrados e armazena em BytesIO."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Relatório de Alunos Aprovados", ln=True, align='C')
    pdf.ln(10)

    for idx, resultado in enumerate(resultados, start=1):
        pdf.cell(0, 10, f"{idx}. {resultado['Nome']} - {resultado['Arquivo PDF']}", ln=True)

    # Salvar PDF na memória (BytesIO) em vez de um arquivo físico
    pdf_output = BytesIO()
    pdf.output(pdf_output, 'F')
    pdf_output.seek(0)
    return pdf_output

def main():
    st.title("Encontra aluno(s) aprovado(s) versão 1.5 (Correções Finais)")
    st.write("Cole a lista de nomes dos alunos no campo abaixo e carregue um ou mais PDFs com as listas de aprovados.")

    nomes_texto = st.text_area("Cole aqui os nomes dos alunos, um por linha:")
    pdf_files = st.file_uploader("Carregar arquivos PDF", type=["pdf"], accept_multiple_files=True)

    if nomes_texto and pdf_files:
        nomes_lista = [normalizar_texto(nome) for nome in nomes_texto.split("\n") if nome.strip()]
        csv_names = set(nomes_lista)

        results = []
        total_pdfs = len(pdf_files)
        progress_bar = st.progress(0)

        for i, pdf_file in enumerate(pdf_files, start=1):
            texto_pdf = extrair_texto_pdf(pdf_file)
            approved_names = extrair_nomes(texto_pdf)
            common_names = []

            for nome in csv_names:
                nome_correto = encontrar_nomes_similares(nome, approved_names)
                if nome_correto:
                    common_names.append(nome_correto)

            for idx, name in enumerate(sorted(common_names), start=1):
                results.append({"Ordem": idx, "Nome": name, "Arquivo PDF": pdf_file.name})

            progress_bar.progress(i / total_pdfs)

        if results:
            st.success("Alunos aprovados encontrados!")
            results_df = pd.DataFrame(results)
            st.dataframe(results_df)

            csv_download = results_df.to_csv(index=False).encode("utf-8")
            st.download_button("Baixar resultados como CSV", data=csv_download, file_name="alunos_aprovados.csv")

            pdf_download = gerar_pdf(results)
            st.download_button("Baixar resultados como PDF", data=pdf_download, file_name="alunos_aprovados.pdf",
                               mime="application/pdf")
        else:
            st.warning("Nenhum aluno aprovado foi encontrado nos PDFs enviados.")

if __name__ == "__main__":
    main()
