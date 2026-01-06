import streamlit as st
import pytesseract
from PIL import Image
import tempfile
from pdf2image import convert_from_path, convert_from_bytes
from openai import OpenAI
import os
import base64
import io
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# ===== Config =====
# dev purposes
# pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"
# POPPLER_PATH = "/opt/homebrew/bin"

# Initialize clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# --- Session State Management ---
if "summary_result" not in st.session_state:
    st.session_state.summary_result = None
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = None
if "doc_category" not in st.session_state:
    st.session_state.doc_category = "Summary"

st.set_page_config(page_title="Uchiha AI", layout="wide")
st.title("📄 Uchiha AI – Document Digitisation & Summarisation")

# ===== Sidebar =====
st.sidebar.title("⚙️ AI Settings")

# 1. Manual Scan Selection (Used when Auto is OFF)
scanning_mode = st.sidebar.radio(
    "Manual Scanning Strategy",
    ["Standard OCR (Printed/Fast)", "AI Vision (Handwritten/Messy)"],
    index=0,
    help="Select only if Autonomous Routing is disabled."
)

# 2. Provider and Language
primary_provider = st.sidebar.selectbox("Primary Model", ["GPT-4o", "Groq"])
target_language = st.sidebar.radio("Summary Language", ["English", "Hindi"])

# 3. Autonomous Toggle (The "Brain" of the App)
use_auto = st.sidebar.checkbox("Autonomous Routing", value=True, help="AI automatically detects if the doc needs OCR or Vision scan.")

uploaded_file = st.file_uploader("Upload Document", type=["png", "jpg", "jpeg", "pdf"])

# --- Helper Functions ---
def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

def get_routing_decision(file):
    """AI Router: Analyzes visual complexity with automated GPT -> Groq fallback."""
    try:
        # Image Preparation
        if file.type == "application/pdf":
            images = convert_from_bytes(file.getvalue())
            img = images[0]
        else:
            img = Image.open(file)
        
        img.thumbnail((400, 400)) 
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        base64_img = encode_image(buf.getvalue())
        
        prompt = "Look at this document. Is it a clean printed form (OCR) or is it handwritten/complex/messy (VISION)? Reply with ONLY the word OCR or VISION."
        
        # --- PRIMARY: GPT-4o-mini ---
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                ]}],
                max_tokens=5
            )
            return response.choices[0].message.content.strip().upper()
        
        except Exception as e:
            # --- FALLBACK: Groq Llama Vision ---
            st.toast(f"⚠️ GPT failover: Switching to Groq", icon="🔄")
            response = groq_client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                ]}],
                max_tokens=5
            )
            return response.choices[0].message.content.strip().upper()
            
    except Exception:
        return "OCR"

def extract_text_standard(file):
    """Local Tesseract extraction (No API needed, but kept for structure)."""
    text = ""
    try:
        if file.type == "application/pdf":
            images = convert_from_bytes(file.getvalue())
            for img in images:
                text += pytesseract.image_to_string(img, lang="hin+eng") + "\n"
        else:
            image = Image.open(file)
            text = pytesseract.image_to_string(image, lang="hin+eng")
        return text
    except Exception as e:
        return f"OCR Error: {str(e)}"

def extract_text_vision(file, provider):
    """Image transcription with automated Provider -> Alternate fallback."""
    try:
        if file.type == "application/pdf":
            images = convert_from_bytes(file.getvalue())
            img = images[0]
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            img_bytes = buf.getvalue()
        else:
            img_bytes = file.getvalue()

        base64_img = encode_image(img_bytes)
        prompt = "Transcribe all text from this image perfectly. Match language script (Hindi/English). Fix handwriting errors."

        # Define sequence: [Primary, Fallback]
        if provider == "GPT-4o":
            sequence = [
                ("GPT-4o", openai_client, "gpt-4o"),
                ("Groq", groq_client, "meta-llama/llama-4-scout-17b-16e-instruct")
            ]
        else:
            sequence = [
                ("Groq", groq_client, "meta-llama/llama-4-scout-17b-16e-instruct"),
                ("GPT-4o", openai_client, "gpt-4o")
            ]

        # Loop through sequence until one works
        for name, client, model_id in sequence:
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                    ]}]
                )
                return response.choices[0].message.content
            except Exception as e:
                st.toast(f"🚨 {name} transcription failed. Trying fallback...", icon="🔄")
                continue # Move to next model in sequence
        
        return "❌ All transcription providers failed."
        
    except Exception as e:
        return f"Logic Error: {str(e)}"
    
def categorize_document(text, primary):
    """AI identifies document category for dynamic file naming."""
    prompt = f"Categorize this document (e.g., Invoice, Resume, Legal, Report). Return ONLY the 1-2 word name.\n\nText: {text[:1000]}"
    client = openai_client if primary == "GPT-4o" else groq_client
    model = "gpt-4o-mini" if primary == "GPT-4o" else "llama-3.1-8b-instant"
    try:
        response = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=10)
        return response.choices[0].message.content.strip().replace(" ", "_")
    except:
        return "Document"

if "failover_active" not in st.session_state:
    st.session_state.failover_active = False

def summarize_text(text, summary_type, primary, language):
    prompt_map = {
        "Short Summary": "Summarize briefly in 3-5 sentences.",
        "Detailed Summary": "Provide a comprehensive and detailed summary.",
        "Bullet Points": "Summarize using clear bullet points.",
    }
    instruction = prompt_map.get(summary_type, summary_type)
    prompt = f"Process this doc in {language}. Instruction: {instruction}\n\nContent: {text}"
    
    # Define sequence
    if primary == "GPT-4o":
        sequence = [
            ("GPT-4o", openai_client, "gpt-4o"),
            ("Groq", groq_client, "llama-3.3-70b-versatile")
        ]
    else:
        sequence = [
            ("Groq", groq_client, "llama-3.3-70b-versatile"),
            ("GPT-4o", openai_client, "gpt-4o")
        ]

    for i, (name, client, model_id) in enumerate(sequence):
        try:
            response = client.chat.completions.create(
                model=model_id, 
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception:
            # If the FIRST model fails, trigger the warning state
            if i == 0:
                st.session_state.failover_active = True
            continue 

    return "❌ All AI providers failed. Check API balance."

def generate_pdf(summary_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [Paragraph("<b>Uchiha AI – Intelligence Report</b>", styles["Title"]), Paragraph("<br/>", styles["Normal"])]
    for line in summary_text.split("\n"):
        if line.strip():
            clean_line = line.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
            story.append(Paragraph(clean_line, styles["Normal"]))
    doc.build(story)
    buffer.seek(0)
    return buffer

# ===== App Logic =====
if uploaded_file:
    if st.button("🚀 Process Document"):
        with st.spinner("Analyzing and Scanning..."):
            st.session_state.summary_result = None
            
            # --- The Automatic Logic Part ---
            if use_auto:
                decision = get_routing_decision(uploaded_file)
                st.toast(f"AI Router selected: {decision} mode", icon="🤖")
                if decision == "VISION":
                    st.session_state.extracted_text = extract_text_vision(uploaded_file, primary_provider)
                else:
                    st.session_state.extracted_text = extract_text_standard(uploaded_file)
            else:
                # Manual Fallback
                if "AI Vision" in scanning_mode:
                    st.session_state.extracted_text = extract_text_vision(uploaded_file, primary_provider)
                else:
                    st.session_state.extracted_text = extract_text_standard(uploaded_file)

            # Categorization logic
            if st.session_state.extracted_text:
                st.session_state.doc_category = categorize_document(st.session_state.extracted_text, primary_provider)
                st.toast(f"📂 Detected as: {st.session_state.doc_category}", icon="📁")
    
    if st.session_state.extracted_text:
        st.subheader(f"📜 Extracted Text ({st.session_state.doc_category})")
        st.code(st.session_state.extracted_text, language="text", wrap_lines=True, height=250)

        col1, col2 = st.columns([2, 1])
        with col1:
            options = ["Short Summary", "Detailed Summary", "Bullet Points", "✨ Customized Prompt (Chat)"]
            summary_type = st.selectbox("Select Output Style", options)
        
        with col2:
            if "Customized Prompt" not in summary_type:
                if st.button("✨ Summarize Now"):
                    st.session_state.failover_active = False
                    with st.spinner(f"Processing in {target_language}..."):
                        st.session_state.summary_result = summarize_text(st.session_state.extracted_text, summary_type, primary_provider, target_language)

        if "Customized Prompt" in summary_type:
            st.markdown("---")
            user_input = st.text_input("💬 Chat with Document:", placeholder="e.g. 'Extract key dates' or 'Make a table'")
            if st.button("🚀 Send Instructions"):
                if user_input:
                    st.session_state.failover_active = False
                    with st.spinner("AI is thinking..."):
                        st.session_state.summary_result = summarize_text(st.session_state.extracted_text, user_input, primary_provider, target_language)

        if st.session_state.failover_active:
            st.warning("⚠️ Primary Model failed. Switching to Failover Engine...", icon="🔄")

    if st.session_state.summary_result:
        st.subheader(f"🧠 AI Result ({target_language})")
        st.code(st.session_state.summary_result, language="text", wrap_lines=True)
        
        pdf = generate_pdf(st.session_state.summary_result)
        final_filename = f"{st.session_state.doc_category}_Summary.pdf"
        st.download_button("📥 Download PDF", data=pdf, file_name=final_filename, mime="application/pdf")