
import streamlit as st
import tempfile
import subprocess
import os

st.set_page_config(page_title="IU PDF Accessibility Fixer", layout="wide")

st.title("IU PDF Accessibility Fixer (MVP)")
st.write("Upload PDFs. The tool attempts OCR and runs machine validation (veraPDF). "
         "Some accessibility issues still require manual review.")

uploaded_files = st.file_uploader(
    "Upload PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

def run_ocr(input_path, output_path):
    try:
        subprocess.run(["ocrmypdf", input_path, output_path], check=True)
        return True
    except Exception:
        return False

def run_verapdf(file_path):
    try:
        result = subprocess.run(["verapdf", "--format", "text", file_path], capture_output=True, text=True)
        return result.stdout
    except Exception:
        return "veraPDF not available."

if uploaded_files:
    for file in uploaded_files:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = os.path.join(tmp, file.name)
            with open(input_path, "wb") as f:
                f.write(file.read())

            output_path = os.path.join(tmp, "remediated_" + file.name)

            st.write(f"Processing {file.name}...")

            success = run_ocr(input_path, output_path)
            if not success:
                output_path = input_path

            report = run_verapdf(output_path)

            with open(output_path, "rb") as f:
                st.download_button(
                    label=f"Download remediated {file.name}",
                    data=f,
                    file_name="remediated_" + file.name
                )

            st.text_area("Validation report", report, height=200)
