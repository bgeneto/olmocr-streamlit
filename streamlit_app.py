import streamlit as st
import os
import time
from pathlib import Path
import pandas as pd
import base64

# Load environment variables
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", "./workspace")
INPUT_PDF_DIR = os.getenv("INPUT_PDF_DIR", f"{WORKSPACE_DIR}/input_pdfs")
OUTPUT_MARKDOWN_DIR = os.getenv("OUTPUT_MARKDOWN_DIR", f"{WORKSPACE_DIR}/markdown")

# Create directories if they don't exist
Path(INPUT_PDF_DIR).mkdir(parents=True, exist_ok=True)
Path(OUTPUT_MARKDOWN_DIR).mkdir(parents=True, exist_ok=True)


def get_pdf_files():
    """Get list of PDF files in the input directory"""
    return [f for f in os.listdir(INPUT_PDF_DIR) if f.lower().endswith(".pdf")]


def get_markdown_files():
    """Get list of markdown files in the output directory"""
    return [f for f in os.listdir(OUTPUT_MARKDOWN_DIR) if f.lower().endswith(".md")]


def display_pdf(file_path):
    """Display PDF in Streamlit"""
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="olmocr PDF Converter", layout="wide")
    st.title("olmocr PDF to Markdown Converter")

    # Sidebar for navigation
    page = st.sidebar.selectbox(
        "Navigation", ["Upload PDFs", "Processing Status", "View Results"]
    )

    if page == "Upload PDFs":
        st.header("Upload PDF Files")
        st.write(
            "Upload multiple PDF files for conversion to Markdown format using olmocr."
        )

        uploaded_files = st.file_uploader(
            "Choose PDF files", type=["pdf"], accept_multiple_files=True
        )

        if uploaded_files:
            st.subheader("Uploaded Files")
            for uploaded_file in uploaded_files:
                # Save the uploaded file to the input directory
                file_path = os.path.join(INPUT_PDF_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Display file info
                st.write(f"📄 {uploaded_file.name} ({uploaded_file.size // 1024} KB)")

                # Display PDF preview
                with st.expander("Preview PDF"):
                    display_pdf(file_path)

            if st.button("Start Conversion Process"):
                st.success(
                    "Files have been queued for processing. The olmocr worker will process them shortly."
                )
                st.info(
                    "Note: Processing time depends on document complexity and server load. Check the 'Processing Status' page for updates."
                )

    elif page == "Processing Status":
        st.header("Processing Status")

        # Get list of files being processed
        pdf_files = get_pdf_files()
        markdown_files = get_markdown_files()

        # Create a status table
        status_data = []
        for pdf_file in pdf_files:
            status = (
                "✅ Completed"
                if pdf_file.replace(".pdf", ".md") in markdown_files
                else "🔄 Processing"
            )
            status_data.append(
                {
                    "PDF File": pdf_file,
                    "Status": status,
                    "Last Modified": time.ctime(
                        os.path.getmtime(os.path.join(INPUT_PDF_DIR, pdf_file))
                    ),
                }
            )

        if status_data:
            df = pd.DataFrame(status_data)
            st.dataframe(df, use_container_width=True)

            # Show processing statistics
            completed = len([s for s in status_data if "Completed" in s["Status"]])
            processing = len([s for s in status_data if "Processing" in s["Status"]])

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Completed Files", completed)
            with col2:
                st.metric("Files in Progress", processing)

            if completed > 0:
                st.success(f"{completed} file(s) have been successfully converted!")
            if processing > 0:
                st.info(
                    f"{processing} file(s) are currently being processed. Results will appear in the 'View Results' section when ready."
                )
        else:
            st.info(
                "No PDF files have been uploaded yet. Go to the 'Upload PDFs' page to get started."
            )

        # Refresh button
        if st.button("Refresh Status"):
            st.experimental_rerun()

    elif page == "View Results":
        st.header("Converted Documents")

        markdown_files = get_markdown_files()

        if not markdown_files:
            st.info(
                "No converted documents available yet. Please upload PDFs and wait for processing to complete."
            )
            return

        # File selection
        selected_file = st.selectbox(
            "Select a converted document to view", markdown_files
        )

        if selected_file:
            # Get corresponding PDF file
            pdf_file = selected_file.replace(".md", ".pdf")

            # Create columns for side-by-side comparison
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Original PDF")
                if os.path.exists(os.path.join(INPUT_PDF_DIR, pdf_file)):
                    display_pdf(os.path.join(INPUT_PDF_DIR, pdf_file))
                else:
                    st.warning("Original PDF file not found.")

            with col2:
                st.subheader("Converted Markdown")
                md_path = os.path.join(OUTPUT_MARKDOWN_DIR, selected_file)
                with open(md_path, "r", encoding="utf-8") as f:
                    markdown_text = f.read()

                # Display as code for better formatting
                st.text_area("Markdown Content", markdown_text, height=800)

                # Download button
                st.download_button(
                    label="Download Markdown",
                    data=markdown_text,
                    file_name=selected_file,
                    mime="text/markdown",
                )

            # Show document stats
            st.subheader("Document Information")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File Name", selected_file)
            with col2:
                st.metric("File Size", f"{os.path.getsize(md_path) // 1024} KB")
            with col3:
                st.metric("Last Modified", time.ctime(os.path.getmtime(md_path)))


if __name__ == "__main__":
    main()
