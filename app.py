
import os
import shutil
import subprocess
import tempfile

import pandas as pd
import pymupdf
import streamlit as st

st.set_page_config(page_title="IU PDF Accessibility Helper", layout="wide")

st.title("IU PDF Accessibility Helper")
st.caption(
    "Free first-pass PDF accessibility helper for OCR, image-page detection, and alt-text worksheets."
)

with st.expander("What this tool does / does not do", expanded=False):
    st.markdown("""
**What it does**
- Accepts multiple PDF uploads
- Attempts OCR with OCRmyPDF when available
- Detects pages that likely contain images
- Creates a processing report
- Creates an alt-text worksheet for faculty/staff

**What it does not do**
- It does **not** automatically add alt text into the PDF
- It does **not** perform full PDF/UA or WCAG validation
- It does **not** fix reading order, heading structure, tables, or forms
    """)

uploaded_files = st.file_uploader(
    "Upload one or more PDF files",
    type=["pdf"],
    accept_multiple_files=True,
)

ocr_enabled = st.checkbox("Attempt OCR with OCRmyPDF when available", value=True)

def command_exists(cmd_name: str) -> bool:
    return shutil.which(cmd_name) is not None

def run_ocr(input_path: str, output_path: str):
    if not command_exists("ocrmypdf"):
        return False, "OCRmyPDF not available in this hosted version."
    try:
        result = subprocess.run(
            ["ocrmypdf", "--skip-text", "--force-ocr", input_path, output_path],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return True, "OCR completed successfully."
        return False, (result.stderr or result.stdout or "OCR failed.").strip()
    except Exception as e:
        return False, f"OCR failed: {e}"

def analyze_pdf(pdf_path: str):
    report_rows = []
    worksheet_rows = []

    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    total_images = 0

    for page_index in range(total_pages):
        page = doc.load_page(page_index)
        images = page.get_images(full=True)
        text = page.get_text("text").strip()
        image_count = len(images)
        total_images += image_count

        report_rows.append({
            "page": page_index + 1,
            "has_text": bool(text),
            "image_count": image_count,
            "likely_needs_alt_text_review": "Yes" if image_count > 0 else "No",
        })

        if image_count > 0:
            for image_num, image in enumerate(images, start=1):
                xref = image[0]
                try:
                    img_info = doc.extract_image(xref)
                    width = img_info.get("width")
                    height = img_info.get("height")
                except Exception:
                    width, height = None, None

                worksheet_rows.append({
                    "page": page_index + 1,
                    "image_number_on_page": image_num,
                    "image_width_px": width,
                    "image_height_px": height,
                    "suggested_alt_text": "",
                    "decorative_image": "",
                    "review_status": "Needs review",
                    "notes": "",
                })

    doc.close()

    summary = {
        "total_pages": total_pages,
        "total_images": total_images,
        "pages_with_images": sum(1 for r in report_rows if r["image_count"] > 0),
        "pages_without_extractable_text": sum(1 for r in report_rows if not r["has_text"]),
    }
    return summary, report_rows, worksheet_rows

if uploaded_files:
    all_summary_rows = []
    all_page_report_rows = []
    all_worksheet_rows = []

    for uploaded_file in uploaded_files:
        with tempfile.TemporaryDirectory() as tmpdir:
            original_path = os.path.join(tmpdir, uploaded_file.name)
            with open(original_path, "wb") as f:
                f.write(uploaded_file.read())

            working_path = original_path
            ocr_status = "OCR not attempted."

            if ocr_enabled:
                ocr_output_path = os.path.join(tmpdir, f"ocr_{uploaded_file.name}")
                ocr_ok, ocr_status = run_ocr(original_path, ocr_output_path)
                if ocr_ok and os.path.exists(ocr_output_path):
                    working_path = ocr_output_path

            try:
                summary, page_rows, worksheet_rows = analyze_pdf(working_path)
                all_summary_rows.append({
                    "file_name": uploaded_file.name,
                    "ocr_status": ocr_status,
                    **summary,
                })

                for row in page_rows:
                    row["file_name"] = uploaded_file.name
                    all_page_report_rows.append(row)

                for row in worksheet_rows:
                    row["file_name"] = uploaded_file.name
                    all_worksheet_rows.append(row)

                with open(working_path, "rb") as f:
                    st.download_button(
                        label=f"Download processed PDF: {uploaded_file.name}",
                        data=f.read(),
                        file_name=f"processed_{uploaded_file.name}",
                        mime="application/pdf",
                    )
            except Exception as e:
                all_summary_rows.append({
                    "file_name": uploaded_file.name,
                    "ocr_status": ocr_status,
                    "total_pages": "",
                    "total_images": "",
                    "pages_with_images": "",
                    "pages_without_extractable_text": "",
                    "error": str(e),
                })

    st.subheader("Processing summary")
    summary_df = pd.DataFrame(all_summary_rows)
    st.dataframe(summary_df, use_container_width=True)

    st.subheader("Page-by-page report")
    page_report_df = pd.DataFrame(all_page_report_rows)
    if not page_report_df.empty:
        st.dataframe(page_report_df, use_container_width=True)
    else:
        st.info("No page-level image data found.")

    st.subheader("Alt-text worksheet")
    worksheet_df = pd.DataFrame(all_worksheet_rows)
    if not worksheet_df.empty:
        st.dataframe(worksheet_df, use_container_width=True)
    else:
        st.info("No images were detected in the uploaded PDFs.")

    st.download_button(
        "Download processing summary (CSV)",
        data=summary_df.to_csv(index=False).encode("utf-8"),
        file_name="pdf_processing_summary.csv",
        mime="text/csv",
    )

    if not page_report_df.empty:
        st.download_button(
            "Download page-by-page report (CSV)",
            data=page_report_df.to_csv(index=False).encode("utf-8"),
            file_name="pdf_page_report.csv",
            mime="text/csv",
        )

    if not worksheet_df.empty:
        st.download_button(
            "Download alt-text worksheet (CSV)",
            data=worksheet_df.to_csv(index=False).encode("utf-8"),
            file_name="pdf_alt_text_worksheet.csv",
            mime="text/csv",
        )
else:
    st.info("Upload one or more PDFs to begin.")
