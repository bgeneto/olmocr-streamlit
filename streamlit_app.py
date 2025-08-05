#!/usr/bin/env python3
"""
Streamlit web app for olmOCR PDF to Markdown conversion
"""

import streamlit as st
import tempfile
import os
import subprocess
import zipfile
from pathlib import Path
import json
import asyncio
from datetime import datetime
import shutil
import requests
import time
from lingua import Language

st.set_page_config(page_title="olmOCR PDF to Markdown Converter", layout="wide", page_icon="📄")

# Custom CSS for better styling
st.markdown(
    """
<style>
    .upload-section {
        border: 2px dashed #cccccc;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 5px;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 1rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


# New helper to get workspace directories
def get_workspace_dirs():
    """Return workspace root and subdirs for PDFs and outputs.
    WORKSPACE_DIR can be overridden via env var, defaults to '/workspace'.
    """
    workspace_root = os.environ.get("WORKSPACE_DIR", "/workspace")
    pdf_dir = os.path.join(workspace_root, "pdfs")
    outputs_dir = os.path.join(workspace_root, "outputs")
    # Ensure directories exist
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(outputs_dir, exist_ok=True)
    return workspace_root, pdf_dir, outputs_dir


def check_vllm_server_status(base_url: str) -> bool:
    """Check if vLLM server is accessible"""
    try:
        headers = {}
        # Add API key if available
        vllm_api_key = os.environ.get("VLLM_API_KEY")
        if vllm_api_key:
            headers["Authorization"] = f"Bearer {vllm_api_key}"

        response = requests.get(f"{base_url}/v1/models", headers=headers, timeout=5)
        return response.status_code == 200
    except:
        return False


def run_olmocr_conversion(pdf_files, workspace_dir: str, vllm_base_url: str, **kwargs):
    """Run olmOCR conversion on uploaded PDF files"""

    # Save uploaded files to workspace/pdf directory
    workspace_root, pdf_dir, outputs_dir = get_workspace_dirs()

    # Always clear previous results to ensure clean processing
    results_dir = os.path.join(workspace_dir, "results")
    markdown_dir = os.path.join(workspace_dir, "markdown")
    work_index_file = os.path.join(workspace_dir, "work_index_list.csv.zstd")

    # Clear work index file (this tracks which files have been processed)
    if os.path.exists(work_index_file):
        os.remove(work_index_file)
        st.info(f"🧹 Cleared work index file")

    # Clear PDF directory to prevent processing old files
    if os.path.exists(pdf_dir):
        existing_pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
        if existing_pdf_files:
            st.info(f"🧹 Clearing {len(existing_pdf_files)} previous PDF files")
        shutil.rmtree(pdf_dir)
        os.makedirs(pdf_dir, exist_ok=True)

    # Clear results directory
    if os.path.exists(results_dir):
        existing_files = [f for f in os.listdir(results_dir) if f.startswith("output_") and f.endswith(".jsonl")]
        if existing_files:
            st.info(f"🧹 Clearing {len(existing_files)} previous result files")
        shutil.rmtree(results_dir)

    # Clear markdown directory too for a fresh start
    if os.path.exists(markdown_dir):
        existing_md_files = []
        for root, dirs, files in os.walk(markdown_dir):
            for file in files:
                if file.endswith(".md"):
                    existing_md_files.append(file)
        if existing_md_files:
            st.info(f"🧹 Clearing {len(existing_md_files)} previous markdown files")
        shutil.rmtree(markdown_dir)

    pdf_paths = []

    # Instead of using session directories, use unique filenames to avoid conflicts
    import uuid
    import time

    session_timestamp = int(time.time())
    session_id = str(uuid.uuid4())[:8]

    for pdf_file in pdf_files:
        # Create a unique filename that combines timestamp, session ID, and original name
        unique_filename = f"{session_timestamp}_{session_id}_{pdf_file.name}"
        pdf_path = os.path.join(pdf_dir, unique_filename)

        with open(pdf_path, "wb") as f:
            f.write(pdf_file.getbuffer())
        pdf_paths.append(pdf_path)

    st.info(f"📁 Saving files to: {pdf_dir}")
    st.info(f"📄 Processing {len(pdf_paths)} PDF file(s): {[os.path.basename(p) for p in pdf_paths]}")

    # Build olmOCR command - workspace_dir used for run-specific temp artifacts
    cmd = [
        "python",
        "-m",
        "olmocr.pipeline",
        workspace_dir,
        "--markdown",
        "--pdfs",
        *pdf_paths,
    ]

    # Add vLLM server URL if provided
    if vllm_base_url:
        cmd.extend(["--vllm_base_url", vllm_base_url])

    # Add vLLM API key if available
    vllm_api_key = os.environ.get("VLLM_API_KEY")
    if vllm_api_key:
        cmd.extend(["--vllm_api_key", vllm_api_key])

    # Add additional parameters
    if kwargs.get("target_dim"):
        cmd.extend(["--target_longest_image_dim", str(kwargs["target_dim"])])
    if kwargs.get("apply_filter"):
        cmd.append("--apply_filter")
    if kwargs.get("guided_decoding"):
        cmd.append("--guided_decoding")
    if kwargs.get("workers"):
        cmd.extend(["--workers", str(kwargs["workers"])])
    # Add languages_to_keep argument if provided
    if kwargs.get("languages_to_keep"):
        # Convert Language enum to names (e.g. ENGLISH,PORTUGUESE)
        langs_arg = ",".join([l.name for l in kwargs["languages_to_keep"]])
        cmd.extend(["--languages_to_keep", langs_arg])
        st.info(f"🌐 Language filtering enabled. Allowed languages: {langs_arg}")
    else:
        st.info("🌐 No language filtering applied - all languages will be processed")

    # Add cleanup function for the uploaded files
    def cleanup_session_files():
        try:
            files_cleaned = 0
            for pdf_path in pdf_paths:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                    files_cleaned += 1
            if files_cleaned > 0:
                st.info(f"🧹 Cleaned up {files_cleaned} session file(s)")
        except Exception as e:
            st.warning(f"⚠️ Could not clean up session files: {e}")

    return cmd, pdf_paths, cleanup_session_files


def latex_replace(md):
    import re

    # Replace \[ ... \] with $$ ... $$
    md = re.sub(r"\\\[(.*?)\\\]", r"$$\1$$", md, flags=re.DOTALL)
    # Replace \( ... \) with $ ... $
    md = re.sub(r"\\\((.*?)\\\)", r"$\1$", md, flags=re.DOTALL)
    return md


def main():
    st.title("📄 PDF to Markdown Converter")
    st.markdown("Convert PDF documents to Markdown using visual language models.")

    # Language selection sidebar
    st.sidebar.subheader("Supported Languages")
    language_options = {
        "English": Language.ENGLISH,
        "Portuguese": Language.PORTUGUESE,
        "Spanish": Language.SPANISH,
        "French": Language.FRENCH,
        "German": Language.GERMAN,
        "Italian": Language.ITALIAN,
        "Dutch": Language.DUTCH,
        "Russian": Language.RUSSIAN,
        "Chinese": Language.CHINESE,
        "Japanese": Language.JAPANESE,
        # Add more as needed
    }
    default_langs = ["English", "Portuguese", "Spanish"]
    selected_langs = st.sidebar.multiselect(
        "Select allowed document languages:", options=list(language_options.keys()), default=default_langs, help="PDFs in other languages will be filtered out."
    )
    languages_to_keep = [language_options[l] for l in selected_langs]

    # Get vLLM server URL from environment variable
    vllm_base_url = os.environ.get("VLLM_BASE_URL", "http://vllm-server:30024")
    vllm_api_key = os.environ.get("VLLM_API_KEY")

    # Get workspace directory from environment variable or default to /workspace
    workspace_dir = os.environ.get("WORKSPACE_DIR", "/workspace")

    # Ensure workspace directory exists
    os.makedirs(workspace_dir, exist_ok=True)

    # Sidebar configuration
    st.sidebar.header("⚙️ Configuration")

    # Display workspace directory in sidebar
    st.sidebar.subheader("📁 Workspace")
    st.sidebar.info(f"Workspace: {workspace_dir}")
    st.sidebar.caption("All previous results are automatically cleared before each conversion.")

    # Server status in sidebar
    st.sidebar.subheader("Server Status")
    server_status = check_vllm_server_status(vllm_base_url)
    if server_status:
        st.sidebar.success("✅ vLLM Server: Online")
    else:
        st.sidebar.error("❌ vLLM Server: Offline")

    # API Key status
    if vllm_api_key:
        st.sidebar.success("🔑 API Key: Configured")
    else:
        st.sidebar.warning("🔑 API Key: Not set")
        st.sidebar.info("💡 Set VLLM_API_KEY environment variable if your server requires authentication")

    if st.sidebar.button("🔍 Refresh Server Status"):
        st.rerun()

    st.sidebar.markdown("---")

    # Advanced Settings
    st.sidebar.subheader("Advanced Settings")
    target_dim = st.sidebar.slider(
        "Target Image Dimension",
        800,
        2000,
        1288,
        help="Set the maximum dimension (in pixels) for images extracted from PDFs. Larger values may improve OCR accuracy but increase processing time and output size. See olmOCR docs for guidance.",
    )
    default_workers = int(os.environ.get("DEFAULT_WORKERS", 4))
    workers = st.sidebar.slider("Number of Workers", 1, 20, default_workers)
    apply_filter = st.sidebar.checkbox(
        "Apply PDF Filter",
        value=True,
        help="Apply advanced filtering to remove noisy or irrelevant PDF content before conversion. See olmOCR docs for details.",
    )
    guided_decoding = st.sidebar.checkbox(
        "Enable Guided Decoding",
        value=False,
        help="Use guided decoding to improve Markdown output quality by leveraging document structure hints. See olmOCR docs for more info.",
    )

    # Main interface
    st.header("📁 Upload PDF Files")

    st.info("💡 **Tip:** The workspace is automatically cleaned before each conversion to ensure fresh results.")

    # File uploader
    uploaded_files = st.file_uploader("Choose PDF files", type=["pdf"], accept_multiple_files=True, help="Upload one or more PDF files to convert to Markdown")

    if uploaded_files:
        st.write(f"📋 **{len(uploaded_files)} file(s) uploaded:**")
        for file in uploaded_files:
            file_size = len(file.getbuffer())
            st.write(f"• {file.name} ({file_size/1024/1024:.2f} MB)")

    # Conversion section
    if uploaded_files:
        st.header("🚀 Convert File(s)")

        if st.button("Start Conversion", type="primary", use_container_width=True):
            if not check_vllm_server_status(vllm_base_url):
                st.error("❌ vLLM server is not accessible. Please check the server status and ensure it's running.")
                return

            cleanup_session_files = None  # Initialize cleanup function
            try:
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()

                status_text.text("🔄 Preparing files...")
                progress_bar.progress(10)

                # Run conversion
                cmd, pdf_paths, cleanup_session_files = run_olmocr_conversion(
                    uploaded_files,
                    workspace_dir,
                    vllm_base_url,
                    target_dim=target_dim,
                    apply_filter=apply_filter,
                    guided_decoding=guided_decoding,
                    workers=workers,
                    languages_to_keep=languages_to_keep,
                )

                status_text.text("🚀 Running olmOCR conversion...")
                progress_bar.progress(30)

                # Execute conversion
                with st.expander("📋 Conversion Log", expanded=True):
                    log_text = st.empty()
                    # Set up logging to capture detailed output
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, universal_newlines=True)

                    log_lines = []
                    error_count = 0
                    connection_errors = 0

                    # Check if process started successfully
                    if process.stdout is None:
                        st.error("❌ Failed to start conversion process")
                        return

                    while True:
                        output = process.stdout.readline()
                        if output == "" and process.poll() is not None:
                            break
                        if output:
                            line = output.strip()
                            log_lines.append(line)
                            # Count different types of errors for better user feedback
                            if "ERROR" in line or "💥" in line or "❌" in line:
                                error_count += 1
                            if "CONNECTION ERROR" in line or "🔌" in line:
                                connection_errors += 1
                            # Show all log lines in a scrollable textarea
                            formatted_log = []
                            for log_line in log_lines:
                                if any(symbol in log_line for symbol in ["❌", "💥", "💀", "ERROR"]):
                                    formatted_log.append(f"🔥 {log_line}")
                                elif any(symbol in log_line for symbol in ["⚠️", "WARNING"]):
                                    formatted_log.append(f"⚠️ {log_line}")
                                elif any(symbol in log_line for symbol in ["✅", "SUCCESS"]):
                                    formatted_log.append(f"✅ {log_line}")
                                else:
                                    formatted_log.append(log_line)
                            log_text.text_area("Conversion Log (Verbose)", value="\n".join(formatted_log), height=400, disabled=True)
                return_code = process.poll()

                progress_bar.progress(80)
                status_text.text("📝 Processing results...")

                if return_code == 0:
                    # Check for generated markdown files
                    markdown_dir = os.path.join(workspace_dir, "markdown")
                    st.info(f"🔍 Looking for markdown files in: {markdown_dir}")

                    if os.path.exists(markdown_dir):
                        # Find all markdown files
                        markdown_files = []
                        for root, dirs, files in os.walk(markdown_dir):
                            for file in files:
                                if file.endswith(".md"):
                                    markdown_files.append(os.path.join(root, file))

                        st.info(f"📄 Found {len(markdown_files)} markdown files in {markdown_dir}")
                        progress_bar.progress(100)
                        status_text.text("✅ Conversion completed successfully!")

                        if markdown_files:
                            st.success(f"🎉 Successfully converted {len(markdown_files)} PDF file(s) to Markdown!")

                            # Results section
                            st.header("📥 Download Results")

                            if len(markdown_files) == 1:
                                # Single file - show download button first, then preview
                                md_file = markdown_files[0]
                                with open(md_file, "r", encoding="utf-8") as f:
                                    markdown_content = f.read()

                                markdown_content = latex_replace(markdown_content)

                                # Auto-download prompt with prominent download button
                                st.info("📥 **Your file is ready!** Click the button below to download:")

                                # Create a more prominent download button
                                download_col1, download_col2, download_col3 = st.columns([1, 2, 1])
                                with download_col2:
                                    st.download_button(
                                        label="⬇️ Download Markdown File",
                                        data=markdown_content,
                                        file_name=f"{os.path.splitext(uploaded_files[0].name)[0]}.md",
                                        mime="text/markdown",
                                        type="primary",
                                        use_container_width=True,
                                    )

                                # JavaScript to focus on the download button (best we can do for "auto-download")
                                st.markdown(
                                    """
                                <script>
                                // Auto-focus on download button and add visual emphasis
                                setTimeout(function() {
                                    const downloadBtn = document.querySelector('[data-testid="stDownloadButton"] button');
                                    if (downloadBtn) {
                                        downloadBtn.focus();
                                        downloadBtn.style.animation = 'pulse 2s infinite';
                                        downloadBtn.style.boxShadow = '0 0 20px rgba(255, 75, 75, 0.6)';
                                    }
                                }, 500);
                                </script>
                                <style>
                                @keyframes pulse {
                                    0% { transform: scale(1); }
                                    50% { transform: scale(1.05); }
                                    100% { transform: scale(1); }
                                }
                                </style>
                                """,
                                    unsafe_allow_html=True,
                                )

                                st.subheader("📄 Markdown Preview")
                                with st.expander("View Markdown Content", expanded=True):
                                    st.markdown(markdown_content, unsafe_allow_html=False)

                            else:
                                # Multiple files - create zip
                                st.subheader("📦 Multiple Files")

                                # Create zip file
                                zip_path = os.path.join(workspace_dir, "markdown_files.zip")
                                with zipfile.ZipFile(zip_path, "w") as zipf:
                                    for md_file in markdown_files:
                                        # Get relative path for zip
                                        rel_path = os.path.relpath(md_file, markdown_dir)
                                        zipf.write(md_file, rel_path)

                                # Read zip data
                                with open(zip_path, "rb") as f:
                                    zip_data = f.read()

                                # Auto-download prompt with prominent download button
                                st.info(f"📦 **Your {len(markdown_files)} files are ready!** Click the button below to download as ZIP:")

                                # Create a more prominent download button
                                download_col1, download_col2, download_col3 = st.columns([1, 2, 1])
                                with download_col2:
                                    st.download_button(
                                        label=f"📁 Download ZIP ({len(markdown_files)} files)",
                                        data=zip_data,
                                        file_name=f"olmocr_converted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                                        mime="application/zip",
                                        type="primary",
                                        use_container_width=True,
                                    )

                                # JavaScript to focus on the download button and add visual emphasis
                                st.markdown(
                                    """
                                <script>
                                // Auto-focus on download button and add visual emphasis
                                setTimeout(function() {
                                    const downloadBtn = document.querySelector('[data-testid="stDownloadButton"] button');
                                    if (downloadBtn) {
                                        downloadBtn.focus();
                                        downloadBtn.style.animation = 'pulse 2s infinite';
                                        downloadBtn.style.boxShadow = '0 0 20px rgba(255, 75, 75, 0.6)';
                                    }
                                }, 500);
                                </script>
                                <style>
                                @keyframes pulse {
                                    0% { transform: scale(1); }
                                    50% { transform: scale(1.05); }
                                    100% { transform: scale(1); }
                                }
                                </style>
                                """,
                                    unsafe_allow_html=True,
                                )

                                # Show file list
                                with st.expander("\U0001f4cb Converted Files", expanded=True):
                                    st.markdown(f"**{len(markdown_files)} Markdown files found.**")
                                    if len(markdown_files) < len(uploaded_files):
                                        st.warning(
                                            f"⚠️ Only {len(markdown_files)} Markdown files generated for {len(uploaded_files)} uploaded PDFs. Some conversions may have failed. Check the log above."
                                        )
                                    for md_file in markdown_files:
                                        filename = os.path.basename(md_file)
                                        file_size = os.path.getsize(md_file)
                                        st.write(f"• {filename} ({file_size/1024:.1f} KB)")

                                # Tabs for previewing up to 5 files
                                max_preview_files = 5
                                preview_files = markdown_files[:max_preview_files]
                                if preview_files:
                                    st.subheader(f"\U0001f4dd Preview (first {max_preview_files} files)")
                                    tab_labels = [os.path.basename(f) for f in preview_files]
                                    tabs = st.tabs(tab_labels)
                                    preview_char_limit = 5000  # Limit preview to first 5000 chars
                                    for i, md_file in enumerate(preview_files):
                                        with open(md_file, "r", encoding="utf-8") as f:
                                            markdown_content = f.read()

                                        markdown_content = latex_replace(markdown_content)
                                        preview_content = markdown_content[:preview_char_limit]
                                        with tabs[i]:
                                            st.markdown(f"**Preview limited to first {preview_char_limit} characters.**")
                                            st.markdown(preview_content, unsafe_allow_html=False)
                                            if len(markdown_content) > preview_char_limit:
                                                with st.expander("Show full content (may be slow)"):
                                                    st.markdown(markdown_content, unsafe_allow_html=False)
                        else:
                            st.warning("⚠️ Conversion completed but no markdown files were generated.")

                    else:
                        st.warning(f"⚠️ Conversion completed but no markdown directory was created at: {markdown_dir}")
                        # Let's also check if there are any .md files in the workspace root or other locations
                        st.info("🔍 Searching for markdown files in workspace...")
                        all_md_files = []
                        for root, dirs, files in os.walk(workspace_dir):
                            for file in files:
                                if file.endswith(".md"):
                                    all_md_files.append(os.path.join(root, file))

                        if all_md_files:
                            st.warning(f"❗ Found {len(all_md_files)} markdown files in unexpected locations:")
                            for md_file in all_md_files:
                                rel_path = os.path.relpath(md_file, workspace_dir)
                                st.write(f"• {rel_path}")
                        else:
                            st.error("❌ No markdown files found anywhere in the workspace")

                else:
                    progress_bar.progress(100)
                    status_text.text("❌ Conversion failed")
                    st.error(f"❌ Conversion failed with return code {return_code}")

            except Exception as e:
                st.error(f"❌ An error occurred during conversion: {str(e)}")
            finally:
                # Clean up session files regardless of success/failure/exception
                if cleanup_session_files is not None:
                    try:
                        cleanup_session_files()
                    except Exception as cleanup_error:
                        st.warning(f"⚠️ Failed to cleanup session files: {cleanup_error}")

    # Footer
    st.markdown("---")
    st.markdown(
        """
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>🔬 Powered by olmOCR • Built with Streamlit</p>
        <p>📖 For more information, visit the <a href='https://github.com/allenai/olmocr' target='_blank'>olmOCR GitHub repository</a></p>
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
