📄 Uchiha AI: Autonomous Multimodal Document Intelligence
The ultimate hybrid solution for document digitization, adaptive OCR routing, and contextual AI-driven summarization.

🌟 The "Aha!" Moment
Document processing usually falls into two traps: traditional OCR is fast but fails at complex layouts or handwriting, while AI Vision is powerful but expensive and slow for simple text. Uchiha AI eliminates this trade-off with an Intelligent Router that "looks" at your document and autonomously selects the most cost-effective and accurate engine.

✨ Key Features
🤖 Autonomous Routing (AI Gatekeeper): A lightweight GPT-4o-mini model analyzes document complexity and automatically chooses between Tesseract (Standard OCR) and GPT-4o/Llama Vision.

🛠️ Resilient Failover Architecture: Never face an API crash during a demo. If the primary model (GPT-4o) fails due to quota or rate limits, the system automatically falls back to Groq (Llama 3.3).

📁 Smart Categorization: The AI identifies the document type (e.g., Invoice, Legal, Medical) and dynamically names your exported PDF based on the detected category.

💬 Context-Aware Chatbot: Go beyond presets. Use the integrated chat input to ask specific questions about the document or request custom formatting like tables or bulleted lists.

🌍 Multi-Script Support: Seamlessly processes and summarizes documents in both English and Hindi, ensuring cross-lingual accessibility.

⚙️ Technical Architecture
Uchiha AI is built with a "Privacy-First, AI-Second" mindset:

Standard OCR: Powered by Pytesseract (Local execution).

Vision Intelligence: Powered by GPT-4o & Llama-3.2-11b-vision.

Summarization/Chat: Powered by Llama-3.3-70b-versatile (Groq) & GPT-4o.

Backend: Streamlit (Python-based interactive UI).

🚀 Getting Started
Prerequisites

Tesseract OCR installed on your system.

Poppler (for PDF rendering).

Valid API keys for OpenAI and Groq.

Installation

Bash
# Clone the repository
git clone https://github.com/your-username/UchihaAI.git

# Install dependencies
pip install streamlit openai pytesseract pdf2image pillow reportlab

# Set up environment variables
export OPENAI_API_KEY='your_openai_key'
export GROQ_API_KEY='your_groq_key'
Running the App

Bash
streamlit run app.py
🧠 Strategic Design Decisions (For Judges)
Cost Optimization: Why use a $0.01 Vision call for a clean PDF? Our router saves ~80% in token costs by utilizing local OCR whenever possible.

Latency vs. Accuracy: By utilizing Groq's Llama-3.3-70b, we provide near-instant failover responses, keeping the user experience fluid even when OpenAI is throttled.

Error Resilience: We implemented st.session_state and st.toast to ensure that even if a model fails, the user is notified of the "fallback" transition rather than seeing a crash.

📅 Roadmap (2026+)
[ ] Batch Processing: Ability to upload entire folders for mass categorization.

[ ] Vector Search (RAG): Integrate ChromaDB for chatting across multiple long-form documents.

[ ] Signature Detection: Visual AI model to verify the presence of wet signatures on legal forms.

🛡️ License

Distributed under the MIT License. See LICENSE for more information.

Built with ❤️ for the 2026 AI Innovation Hackathon.