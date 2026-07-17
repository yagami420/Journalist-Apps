import streamlit as st
import streamlit.components.v1 as components
import requests
from bs4 import BeautifulSoup
import json
import os
import base64
from datetime import datetime

# Fetching Groq Key silently from background secrets
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

# --- 1. THE WEB SCRAPER ---
def scrape_article(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return f"Error: Webpage returned status code {response.status_code}"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        paragraphs = soup.find_all('p')
        article_text = "\n".join([p.get_text() for p in paragraphs])
        return article_text[:8000].strip()
    except Exception as e:
        return f"Scraping failed: {str(e)}"

# --- 2. GROQ NEWSROOM LLM PROCESSOR ---
def process_with_groq(text, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
        "You are a senior TV newsroom editor. Analyze the provided news text or scraped article and generate a complete, premium Urdu broadcast package.\n\n"
        "You MUST return your output strictly in JSON format with the following keys:\n"
        "1. \"headline\": A long, impactful, and comprehensive Urdu headline. No English words, Cyrillic characters, or western digits. Write numbers in Urdu words.\n"
        "2. \"package\": A highly detailed and long Urdu package (150 to 200 words, 7 to 9 sentences). Explain the background, perspectives, and current situation in depth. No English/Cyrillic words or digits. Write numbers in Urdu words.\n"
        "3. \"oc\": A detailed On-Camera (OC) script in Urdu (3 to 4 sentences). This is the intro spoken by the anchor on camera. No English/Cyrillic words or digits.\n"
        "4. \"vo\": A detailed Voice-Over (VO) script in Urdu (7 to 9 sentences) to play over video footages. Explain the main story details. No English/Cyrillic words or digits.\n\n"
        "Strict Editorial Rules:\n"
        "- Absolutely NO brackets [ ] or dashes inside any of the generated Urdu text.\n"
        "- Absolutely NO Cyrillic text or non-Urdu scripts. Translate all foreign concepts into clean, pure Urdu words.\n"
        "- NO English words or western digits anywhere in the Urdu text. All numbers must be written as Urdu words.\n"
        "- Do not use asterisks (*) for formatting or bullet points.\n"
        "- Keep the Urdu highly fluent, professional, dramatic, and grammatically precise."
    )
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the news text to process:\n\n{text}"}
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            result = response.json()
            content_str = result["choices"][0]["message"]["content"]
            return json.loads(content_str)
        else:
            try:
                error_data = response.json()
                err_msg = error_data.get("error", {}).get("message", "Unknown Error")
                return {"error": f"Groq API Error: {err_msg} (Status {response.status_code})"}
            except:
                return {"error": f"Groq API Error: Status {response.status_code}"}
    except Exception as e:
        return {"error": f"Processing failed: {str(e)}"}

# --- 3. EXPORT ARCHIVE TO BEAUTIFUL HTML / PDF PRINT-READY REPORT ---
def generate_export_html(archive_list):
    html_content = """
    <!DOCTYPE html>
    <html lang="ur" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>جل بگولہ - آرکائیو رپورٹ</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaleeq+Urdu:wght@400;700&display=swap');
            body {
                font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaleeq Urdu', 'Segoe UI', Tahoma, sans-serif;
                background-color: #fafbfc;
                color: #0f172a;
                padding: 40px;
                line-height: 2.2;
            }
            .header {
                text-align: center;
                margin-bottom: 50px;
                border-bottom: 2px solid #e2e8f0;
                padding-bottom: 25px;
            }
            .header h1 {
                color: #4f46e5;
                margin: 0;
                font-size: 36px;
            }
            .archive-item {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 16px;
                padding: 30px;
                margin-bottom: 40px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.02);
            }
            .timestamp {
                font-size: 13px;
                color: #64748b;
                font-weight: bold;
                margin-bottom: 15px;
                border-bottom: 1px dashed #e2e8f0;
                padding-bottom: 8px;
            }
            .section-label {
                font-weight: bold;
                color: #4f46e5;
                margin-top: 20px;
                font-size: 14px;
                text-transform: uppercase;
                border-bottom: 1px solid #f1f5f9;
                padding-bottom: 5px;
            }
            .content-text {
                font-size: 18px;
                margin-top: 10px;
                margin-bottom: 20px;
                text-align: right;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌪️ جل بگولہ - آرکائیو رپورٹ</h1>
            <p style="color: #64748b; margin: 5px 0 0 0;">Powered by HAFtech | Exported Archive Data</p>
        </div>
    """
    for item in archive_list:
        html_content += f"""
        <div class="archive-item">
            <div class="timestamp">🕒 تاریخ و وقت: {item['timestamp']}</div>
            
            <div class="section-label" style="direction: ltr; text-align: left;">INPUT SOURCE:</div>
            <div class="content-text" style="font-size: 14px; color: #475569; font-family: monospace; direction: ltr; text-align: left;">{item['input']}</div>
            
            <div class="section-label">ہیڈ لائن (Headline):</div>
            <div class="content-text" style="font-weight: bold; color: #0f172a;">{item['headline']}</div>
            
            <div class="section-label">تفصیلی پیکیج (Package):</div>
            <div class="content-text">{item['package']}</div>
            
            <div class="section-label">آن کیمرہ اور وائس اوور (OC & VO):</div>
            <div class="content-text" style="white-space: pre-wrap;">{item['oc_vo']}</div>
        </div>
        """
    html_content += """
    </body>
    </html>
    """
    return html_content

# --- 4. THE JOURNALIST WEB INTERFACE ---
st.set_page_config(page_title="Jal Bagola", page_icon="🌪️", layout="wide")

# Force Premium Minimalist Google-Class Theme
st.markdown("""
    <style>
        /* Globally clean white, high-end editorial canvas background */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            background-color: #fafbfc !important;
            color: #1e293b !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        }
        [data-testid="stHeader"] {
            background-color: rgba(0,0,0,0) !important;
        }
        .block-container {
            padding-top: 3.5rem !important;
            padding-bottom: 2rem !important;
        }
        
        /* Floating "Powered by HAFtech" badge on top left corner - High-end Glassmorphism */
        .haftech-badge {
            position: fixed;
            top: 24px;
            left: 24px;
            background-color: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            color: #4f46e5;
            border: 2px solid #4f46e5;
            padding: 8px 18px;
            border-radius: 40px;
            font-size: 11px;
            font-weight: 800;
            text-decoration: none;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.1);
            z-index: 999999;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .haftech-badge:hover {
            background-color: #4f46e5;
            color: #ffffff;
            box-shadow: 0 6px 20px rgba(79, 70, 229, 0.2);
            transform: translateY(-1px);
        }

        /* Style Search Input Box - Sleek Editorial Search Bar with Premium Indigo Border */
        .stTextArea textarea {
            border-radius: 16px !important;
            border: 2px solid #4f46e5 !important;
            box-shadow: 0 4px 18px rgba(79, 70, 229, 0.05) !important;
            padding: 16px 24px !important;
            font-size: 15px !important;
            font-weight: 500 !important;
            background-color: #ffffff !important;
            color: #0f172a !important;
            line-height: 1.6 !important;
            min-height: 54px !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        .stTextArea textarea:focus {
            box-shadow: 0 6px 24px rgba(79, 70, 229, 0.12) !important;
            border-color: #4f46e5 !important;
        }
        
        /* Style Go Button adjacent to input - Premium Dark Slate Solid Style */
        div.stButton > button {
            border-radius: 16px !important;
            background-color: #ffffff !important;
            color: #4f46e5 !important;
            border: 2px solid #4f46e5 !important;
            font-size: 16px !important;
            font-weight: 800 !important;
            height: 54px !important;
            width: 100% !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 4px 14px rgba(79, 70, 229, 0.08) !important;
            letter-spacing: 0.5px !important;
        }
        div.stButton > button:hover {
            background-color: #4f46e5 !important;
            color: #ffffff !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 8px 22px rgba(79, 70, 229, 0.2) !important;
        }
        div.stButton > button:active {
            transform: translateY(1px) !important;
            box-shadow: 0 2px 8px rgba(79, 70, 229, 0.08) !important;
        }
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Add "Powered by HAFtech" top left button
st.markdown('<a class="haftech-badge" href="#" onclick="return false;">⚡ Powered by HAFtech</a>', unsafe_allow_html=True)

# Session States for persistent outputs across runs
if "headline" not in st.session_state:
    st.session_state.headline = ""
if "package" not in st.session_state:
    st.session_state.package = ""
if "oc_vo" not in st.session_state:
    st.session_state.oc_vo = ""
if "error" not in st.session_state:
    st.session_state.error = ""
if "archive" not in st.session_state:
    st.session_state.archive = []
if "last_input" not in st.session_state:
    st.session_state.last_input = ""

# --- 5. SIDE-BY-SIDE TWO-COLUMN LAYOUT ---
# 7.2 Units for main workspace (Left), 2.8 Units for Archive Panel (Right)
main_col, archive_col = st.columns([7.2, 2.8], gap="large")

with main_col:
    # Centered Logo Image Section within main column - Perfect Symmetry
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png") if "__file__" in locals() else "logo.png"
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 25px; width: 100%;">
                <img src="data:image/png;base64,{img_b64}" style="max-width: 320px; width: 100%; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.03);" />
            </div>
            """, 
            unsafe_allow_html=True
        )
    else:
        st.markdown("""
            <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 25px; width: 100%;">
                <div style="text-align: center; padding: 25px; border-radius: 20px; background: linear-gradient(135deg, #0f172a, #1e293b); color: #ffffff; box-shadow: 0 15px 35px rgba(0,0,0,0.15); max-width: 320px; width: 100%;">
                    <h1 style="margin: 0; font-family: Arial, sans-serif; font-size: 2.2rem; letter-spacing: 1px; color: #38bdf8;">🌪️ جل بگولہ</h1>
                    <p style="margin: 5px 0 0 0; font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 3px; font-weight: 600;">KHULASA NEWS SUMMARY</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # Single Tab Search Engine Bar adjacent to Go Button
    col1, col2 = st.columns([8.5, 1.5], vertical_alignment="bottom")
    with col1:
        user_input = st.text_area(
            "Input",
            placeholder="Paste a news website link or copy-paste summary of news here...",
            label_visibility="collapsed",
            height=54
        )
    with col2:
        go_pressed = st.button("Go", type="primary")

    # Run Logic when Go is clicked
    if go_pressed:
        if not GROQ_API_KEY:
            st.session_state.error = "سسٹم آف لائن ہے۔ برائے مہربانی بیک اینڈ پر 'GROQ_API_KEY' محفوظ کریں۔"
        elif not user_input.strip():
            st.session_state.error = "مہربانی فرما کر پہلے کوئی لنک یا ٹیکسٹ درج کریں۔"
        else:
            st.session_state.error = ""
            
            # 🔴 AUTO-ARCHIVE ENGINE: Push current active results to archive BEFORE overwriting
            if st.session_state.headline or st.session_state.package or st.session_state.oc_vo:
                # Avoid archiving duplicate consecutive requests
                if not st.session_state.archive or st.session_state.archive[0]["headline"] != st.session_state.headline:
                    archive_item = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "input": st.session_state.last_input,
                        "headline": st.session_state.headline,
                        "package": st.session_state.package,
                        "oc_vo": st.session_state.oc_vo
                    }
                    st.session_state.archive.insert(0, archive_item)
            
            # Fetch new values
            with st.spinner("پروسیسنگ جاری ہے..."):
                if user_input.strip().startswith("http://") or user_input.strip().startswith("https://"):
                    content = scrape_article(user_input.strip())
                    if content.startswith("Error") or content.startswith("Scraping failed"):
                        st.session_state.error = f"سکریپنگ ناکام ہوئی: {content}"
                        st.stop()
                else:
                    content = user_input.strip()
                
                data = process_with_groq(content, GROQ_API_KEY)
                
                if "error" in data:
                    st.session_state.error = data["error"]
                else:
                    st.session_state.headline = data.get("headline", "")
                    st.session_state.package = data.get("package", "")
                    
                    # Combine OC and VO with beautiful spacing and bold, clean separation headers
                    oc_text = data.get("oc", "").strip()
                    vo_text = data.get("vo", "").strip()
                    st.session_state.oc_vo = f"او سی (ON-CAMERA):\n{oc_text}\n\n\nوی او (VOICE-OVER):\n{vo_text}"
                    st.session_state.last_input = user_input.strip()

    # Display background system error if any
    if st.session_state.error:
        st.error(st.session_state.error)

    # Render premium output text areas with clean outlines, shadows, unified button aesthetics, and reduced font size
    def render_copiable_box(label, text, height=120):
        safe_text = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace('"', '\\"')
        html_code = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin-bottom: 20px; background-color: #fafbfc; text-align: right; direction: rtl;">
            <label style="font-weight: 700; color: #4f46e5; display: block; margin-bottom: 8px; font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px; text-align: right;">{label}</label>
            <textarea id="{label}_text" style="width: 100%; height: {height}px; padding: 14px; border: 2px solid #4f46e5; border-radius: 12px; font-size: 17px; box-sizing: border-box; background-color: #ffffff; color: #0f172a; font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaleeq Urdu', 'Urdu Typesetting', Tahoma, sans-serif; line-height: 2.0; text-align: right; direction: rtl; resize: none; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.04); transition: all 0.2s ease;" readonly>{text}</textarea>
            <div style="text-align: right; margin-top: 8px; direction: rtl;">
                <button id="btn_{label}" onclick="copyText_{label}()" style="padding: 10px 24px; background-color: #ffffff; border: 2px solid #4f46e5; border-radius: 12px; font-size: 12px; color: #4f46e5; cursor: pointer; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 800; transition: all 0.2s ease; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.08); text-transform: uppercase;">Copy {label}</button>
            </div>
        </div>
        <script>
            function copyText_{label}() {{
                var copyText = document.getElementById("{label}_text");
                copyText.select();
                copyText.setSelectionRange(0, 99999);
                
                try {{
                    navigator.clipboard.writeText(copyText.value);
                }} catch (err) {{
                    document.execCommand('copy');
                }}
                
                var btn = document.getElementById("btn_{label}");
                btn.innerHTML = "✓ Copied!";
                btn.style.backgroundColor = "#4f46e5";
                btn.style.borderColor = "#4f46e5";
                btn.style.color = "#ffffff";
                btn.style.boxShadow = "0 4px 12px rgba(79, 70, 229, 0.2)";
                
                setTimeout(function() {{
                    btn.innerHTML = "Copy {label}";
                    btn.style.backgroundColor = "#ffffff";
                    btn.style.borderColor = "#4f46e5";
                    btn.style.color = "#4f46e5";
                    btn.style.boxShadow = "0 4px 12px rgba(79, 70, 229, 0.08)";
                }}, 1500);
            }}
        </script>
        """
        components.html(html_code, height=height + 80)

    # Render Output Cards below search engine bar - Tightened heights for maximum visibility
    if st.session_state.headline or st.session_state.package or st.session_state.oc_vo:
        st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
        
        render_copiable_box("Headline", st.session_state.headline, height=75)
        render_copiable_box("Package", st.session_state.package, height=150)
        render_copiable_box("OC & VO", st.session_state.oc_vo, height=230)

# --- 6. ARCHIVE SIDEBAR PANEL ---
with archive_col:
    # Stylized vertical divider and section header
    st.markdown("""
        <div style="border-left: 2px solid #f1f5f9; padding-left: 15px; margin-bottom: 20px;">
            <h3 style="color: #4f46e5; font-size: 16px; font-weight: 800; letter-spacing: 1.5px; margin: 0; text-transform: uppercase;">🌪️ ARCHIVE HISTORY</h3>
            <p style="color: #64748b; font-size: 11px; margin: 3px 0 0 0;">Auto-saves previous summaries instantly.</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Custom CSS to style archive buttons like elegant, clean single-line text hyperlinks
    st.markdown("""
        <style>
            div[data-testid="stVerticalBlock"] > div {
                border: none !important;
            }
            /* Styling buttons inside archive to look like smooth clickable hyperlinks */
            .stButton > button[key^="arch_"] {
                text-align: left !important;
                background-color: #ffffff !important;
                color: #0f172a !important;
                border: 1px solid #e2e8f0 !important;
                border-radius: 10px !important;
                padding: 10px 14px !important;
                font-size: 12px !important;
                font-weight: 600 !important;
                box-shadow: 0 2px 6px rgba(0,0,0,0.02) !important;
                height: auto !important;
                transition: all 0.15s ease !important;
                margin-bottom: 8px !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                display: block !important;
            }
            .stButton > button[key^="arch_"]:hover {
                border-color: #4f46e5 !important;
                color: #4f46e5 !important;
                background-color: #f5f3ff !important;
                transform: translateY(-1px) !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    if st.session_state.archive:
        # Loop to show previous runs as a list of minimalist links
        for idx, item in enumerate(st.session_state.archive):
            # Create button with timestamp and short slice of headline
            display_label = f"🕒 {item['timestamp']} | {item['headline'][:25]}..."
            if st.button(display_label, key=f"arch_{idx}", use_container_width=True):
                # Swap active panel variables with selected archived values
                st.session_state.headline = item["headline"]
                st.session_state.package = item["package"]
                st.session_state.oc_vo = item["oc_vo"]
                st.session_state.last_input = item["input"]
                st.rerun()
                
        # Space divider at bottom of list
        st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
        
        # EXPORT SYSTEM: Renders a beautiful HTML file for perfect Nastaleeq PDF Print Engine
        export_html = generate_export_html(st.session_state.archive)
        
        st.markdown("<p style='color: #64748b; font-size: 11px; font-style: italic; text-align: center; margin-bottom: 5px;'>Open downloaded report and press Ctrl+P to Save as PDF with perfect Nastaleeq formatting.</p>", unsafe_allow_html=True)
        st.download_button(
            label="📤 EXPORT ALL TO PDF",
            data=export_html,
            file_name="jal_bagola_archive_report.html",
            mime="text/html",
            use_container_width=True
        )
    else:
        st.markdown("""
            <div style="text-align: center; padding: 40px 10px; border: 1px dashed #e2e8f0; border-radius: 12px; background-color: #ffffff;">
                <p style="color: #94a3b8; font-size: 13px; margin: 0;">No items archived yet.</p>
            </div>
        """, unsafe_allow_html=True)