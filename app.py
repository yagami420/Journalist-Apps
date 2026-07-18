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

# --- 1. SESSION STATE FOR SECURE ACCESS ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
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

# --- 2. THE WEB SCRAPER ---
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

# --- 3. GROQ NEWSROOM LLM PROCESSOR ---
def process_with_groq(text, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
        "You are a senior TV newsroom editor. Analyze the provided news text or scraped article and generate a complete, premium Urdu broadcast package.\n\n"
        "You MUST return your output strictly in JSON format with the following keys:\n"
        "1. \"headline\": A massive, highly detailed, and comprehensive Urdu headline that is at least TRIPLE the typical length (make it very long, descriptive, and impactful). No English words, Cyrillic characters, or western digits. Write numbers in Urdu words.\n"
        "2. \"package\": An exceptionally detailed and long Urdu package that is exactly DOUBLE the typical size (300 to 400 words, 14 to 18 sentences). Explain the background, deep perspectives, and current situation completely. No English/Cyrillic words or digits. Write numbers in Urdu words.\n"
        "3. \"oc\": A detailed On-Camera (OC) script in Urdu (3 to 4 sentences). This is the intro spoken by the anchor on camera. No English/Cyrillic words or digits.\n"
        "4. \"vo\": A short Voice-Over (VO) script in Urdu that is exactly HALF the normal length (around 3 to 4 sentences max) to play over video footages. Crisply explain only the core story details. No English/Cyrillic words or digits.\n\n"
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

# --- 4. EXPORT ARCHIVE TO BEAUTIFUL HTML / PDF PRINT-READY REPORT ---
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
                background-color: #faf9f5;
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
                color: #1e1b4b;
                margin: 0;
                font-size: 36px;
            }
            .archive-item {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
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
                color: #1e1b4b;
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
            <div class="content-text" style="white-space: pre-wrap;">{item['package']}</div>
            
            <div class="section-label">آن کیمرہ اور وائس اوور (OC & VO):</div>
            <div class="content-text" style="white-space: pre-wrap;">{item['oc_vo']}</div>
        </div>
        """
    html_content += """
    </body>
    </html>
    """
    return html_content

# --- 5. THE JOURNALIST WEB INTERFACE ---
st.set_page_config(page_title="Jal Bagola", page_icon="🌪️", layout="wide")

# Injecting Custom WordPress Editorial Premium Theme CSS (Highly Aggressive Hiders)
st.markdown("""
    <style>
        /* 🔴 AGGRESSIVELY FORCE HIDE FORK, DEPLOY, DECORATION, AND MANAGE APP OVERLAYS */
        .stDeployButton, .stAppDeployButton, [data-testid="stStatusWidget"], [data-testid="stDecoration"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            width: 0 !important;
            opacity: 0 !important;
        }
        .viewerBadge, [data-testid="manage-app-button"], .stViewerBadge, iframe[title="manage-app"], div[class*="viewerBadge"], button[class*="viewerBadge"], iframe[src*="manage-app"], div[class*="manage-app"], iframe[id*="manage-app"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            width: 0 !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        
        /* Globally clean warm WordPress background for premium magazine aesthetic */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            background-color: #fcfbf9 !important;
            color: #1e293b !important;
            font-family: 'Georgia', Times, serif !important;
        }
        [data-testid="stHeader"] {
            background-color: rgba(0,0,0,0) !important;
        }
        
        /* Frame the whole layout like a real Gutenberg WordPress Container Block */
        .block-container {
            padding-top: 6rem !important;
            padding-bottom: 3rem !important;
            max-width: 1250px !important;
        }
        
        /* High-End WordPress Style Top Navigation Header */
        .wp-nav-header {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 64px;
            background-color: #ffffff;
            border-bottom: 1px solid #e2e8f0;
            z-index: 999999;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 40px;
            box-shadow: 0 2px 15px rgba(0, 0, 0, 0.015);
        }
        
        .wp-nav-brand {
            font-family: 'Georgia', serif;
            font-size: 13px;
            font-weight: 800;
            color: #1e1b4b;
            text-transform: uppercase;
            letter-spacing: 2px;
        }
        
        /* WordPress HAFtech Badge styling */
        .haftech-badge {
            background-color: #ffffff;
            color: #4f46e5;
            border: 1px solid #e0dbff;
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 800;
            text-decoration: none;
            box-shadow: 0 2px 8px rgba(79, 70, 229, 0.05);
            transition: all 0.2s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
        }
        .haftech-badge:hover {
            border-color: #4f46e5;
            background-color: #f5f3ff;
            transform: translateY(-1px);
        }

        /* Isolated Card Wrapper for Sidebar and Main Canvas to bypass raw col backgrounds */
        .wp-sidebar-wrapper {
            background-color: #ffffff !important;
            border: 1px solid #e1dbcf !important;
            border-radius: 8px !important;
            padding: 24px !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.015) !important;
        }
        
        .wp-main-post-wrapper {
            background-color: #ffffff !important;
            border: 1px solid #e1dbcf !important;
            border-radius: 8px !important;
            padding: 40px !important;
            box-shadow: 0 8px 30px rgba(0,0,0,0.02) !important;
        }

        /* WordPress Styled Inputs */
        .stTextArea textarea, div[data-testid="stTextInput"] input {
            border-radius: 6px !important;
            border: 1px solid #cbd5e1 !important;
            box-shadow: inset 0 1px 2px rgba(0,0,0,0.01) !important;
            padding: 12px 18px !important;
            font-size: 14px !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
            background-color: #ffffff !important;
            color: #0f172a !important;
            transition: all 0.2s ease !important;
        }
        .stTextArea textarea:focus, div[data-testid="stTextInput"] input:focus {
            box-shadow: 0 0 0 3px rgba(30, 27, 75, 0.06) !important;
            border-color: #1e1b4b !important;
        }
        
        /* WordPress Premium Deep Indigo Buttons */
        div.stButton > button {
            border-radius: 6px !important;
            background-color: #1e1b4b !important;
            color: #ffffff !important;
            border: 1px solid #1e1b4b !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            height: 48px !important;
            width: 100% !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 2px 6px rgba(30, 27, 75, 0.1) !important;
            letter-spacing: 0.5px !important;
            font-family: 'Georgia', serif !important;
        }
        div.stButton > button:hover {
            background-color: #312e81 !important;
            border-color: #312e81 !important;
            color: #ffffff !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(30, 27, 75, 0.15) !important;
        }
        
        /* 🔴 WP SIDEBAR BUTTONS - TARGETING SIDEBAR CONTAINER SPECIFICALLY */
        .wp-sidebar-wrapper .stButton > button {
            text-align: right !important;
            direction: rtl !important;
            background-color: #ffffff !important;
            color: #334155 !important;
            border: none !important;
            border-bottom: 1px solid #f1ece1 !important;
            border-radius: 0px !important;
            padding: 14px 8px !important;
            font-size: 13px !important;
            font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaleeq Urdu', 'Urdu Typesetting', serif !important;
            transition: all 0.15s ease !important;
            box-shadow: none !important;
            line-height: 1.8 !important;
            white-space: normal !important;
            height: auto !important;
        }
        .wp-sidebar-wrapper .stButton > button:hover {
            color: #4f46e5 !important;
            background-color: #fcfbf9 !important;
            border-bottom: 1px solid #4f46e5 !important;
            padding-right: 12px !important;
        }
        
        /* Guest Access Button special formatting */
        div.stButton > button[key="guest_login_btn"] {
            background-color: #ffffff !important;
            color: #1e1b4b !important;
            border: 1.5px solid #1e1b4b !important;
            box-shadow: none !important;
        }
        div.stButton > button[key="guest_login_btn"]:hover {
            background-color: #f5f3ff !important;
        }
        
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Add WordPress Navigation Bar with Brand and Badge
st.markdown("""
    <div class="wp-nav-header">
        <a class="haftech-badge" href="#" onclick="return false;">⚡ Powered by HAFtech</a>
        <div class="wp-nav-brand">Jal Bagola Editorial Workspace</div>
    </div>
""", unsafe_allow_html=True)


# --- 6. RENDER SECURE GATE (LOGIN PAGE) ---
if not st.session_state.logged_in:
    st.markdown("<div style='margin-top: 5vh;'></div>", unsafe_allow_html=True)
    
    login_center_col1, login_center_col2, login_center_col3 = st.columns([1.6, 1.8, 1.6])
    
    with login_center_col2:
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png") if "__file__" in locals() else "logo.png"
        
        st.markdown("<div style='background-color: #ffffff; padding: 40px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 10px 30px rgba(0,0,0,0.02);'>", unsafe_allow_html=True)
        
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img_b64 = base64.b64encode(img_file.read()).decode()
            st.markdown(
                f"""
                <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 30px; width: 100%;">
                    <img src="data:image/png;base64,{img_b64}" style="max-width: 250px; width: 100%; border-radius: 8px;" />
                </div>
                """, 
                unsafe_allow_html=True
            )
        else:
            st.markdown("""
                <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 30px; width: 100%;">
                    <div style="text-align: center; padding: 25px; border-radius: 12px; background: linear-gradient(135deg, #0f172a, #1e293b); color: #ffffff; max-width: 250px; width: 100%;">
                        <h1 style="margin: 0; font-family: Georgia, serif; font-size: 2.2rem; letter-spacing: 1px; color: #38bdf8;">🌪️ جل بگولہ</h1>
                        <p style="margin: 5px 0 0 0; font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 3px; font-weight: 600;">KHULASA NEWS SUMMARY</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<h4 style='text-align: center; color: #1e1b4b; font-family: Georgia, serif; font-size: 16px; font-weight: 700; margin-bottom: 25px; letter-spacing: 1px;'>EDITORIAL GATEWAY</h4>", unsafe_allow_html=True)
        
        username_input = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
        password_input = st.text_input("Password", placeholder="Password", type="password", label_visibility="collapsed")
        
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        
        if st.button("LOG IN", type="primary"):
            if username_input.strip().lower() == "admin" and password_input == "jalbagola":
                st.session_state.logged_in = True
                st.session_state.error = ""
                st.rerun()
            else:
                st.error("Invalid Username or Password. Please try again.")
                
        st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 11px; font-weight: 700; letter-spacing: 1.5px; margin: 20px 0;'>OR</p>", unsafe_allow_html=True)
        
        if st.button("GUEST ACCESS", key="guest_login_btn"):
            st.session_state.logged_in = True
            st.session_state.error = ""
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)

# --- 7. RENDER MAIN WORKSPACE (WHEN LOGGED IN) ---
else:
    # --- SIDE-BY-SIDE TWO-COLUMN LAYOUT (Left Archive, Right Workspace) ---
    archive_col, main_col = st.columns([2.8, 7.2], gap="large")

    # --- LEFT COLUMN: ARCHIVE SIDEBAR WIDGET ---
    with archive_col:
        # Open secure sidebar card envelope
        st.markdown('<div class="wp-sidebar-wrapper">', unsafe_allow_html=True)
        
        st.markdown("""
            <div style="border-bottom: 2px solid #1e1b4b; padding-bottom: 10px; margin-bottom: 20px;">
                <h3 style="color: #1e1b4b; font-family: Georgia, serif; font-size: 18px; font-weight: 700; margin: 0;">📋 Recent Posts</h3>
                <p style="color: #64748b; font-size: 11px; font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 4px 0 0 0;">Auto-saved summaries directory</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.archive:
            for idx, item in enumerate(st.session_state.archive):
                display_label = f"📝 {item['headline'][:24]}...\n🕒 {item['timestamp']}"
                if st.button(display_label, key=f"arch_{idx}", use_container_width=True):
                    st.session_state.headline = item["headline"]
                    st.session_state.package = item["package"]
                    st.session_state.oc_vo = item["oc_vo"]
                    st.session_state.last_input = item["input"]
                    st.rerun()
                    
            st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
            
            export_html = generate_export_html(st.session_state.archive)
            
            st.markdown("<p style='color: #64748b; font-size: 11px; font-style: italic; text-align: center; margin-bottom: 8px; font-family: sans-serif;'>Press Ctrl+P on downloaded HTML file to generate a Nastaleeq PDF.</p>", unsafe_allow_html=True)
            st.download_button(
                label="📤 Export Archive",
                data=export_html,
                file_name="jal_bagola_archive_report.html",
                mime="text/html",
                use_container_width=True
            )
        else:
            st.markdown("""
                <div style="text-align: center; padding: 40px 10px; border: 1px dashed #cbd5e1; border-radius: 8px;">
                    <p style="color: #94a3b8; font-size: 12px; font-family: sans-serif; margin: 0;">No articles analyzed yet.</p>
                </div>
            """, unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

    # --- RIGHT COLUMN: MAIN WORKSPACE ---
    with main_col:
        # Open secure post container envelope
        st.markdown('<div class="wp-main-post-wrapper">', unsafe_allow_html=True)
        
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png") if "__file__" in locals() else "logo.png"
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img_b64 = base64.b64encode(img_file.read()).decode()
            st.markdown(
                f"""
                <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 30px; width: 100%;">
                    <img src="data:image/png;base64,{img_b64}" style="max-width: 250px; width: 100%; border-radius: 12px;" />
                </div>
                """, 
                unsafe_allow_html=True
            )
        else:
            st.markdown("""
                <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 30px; width: 100%;">
                    <div style="text-align: center; padding: 25px; border-radius: 12px; background: linear-gradient(135deg, #0f172a, #1e293b); color: #ffffff; max-width: 250px; width: 100%;">
                        <h1 style="margin: 0; font-family: Georgia, serif; font-size: 2.2rem; letter-spacing: 1px; color: #38bdf8;">🌪️ جل بگولہ</h1>
                        <p style="margin: 5px 0 0 0; font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 3px; font-weight: 600;">KHULASA NEWS SUMMARY</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        col1, col2 = st.columns([8.6, 1.4], vertical_alignment="bottom")
        with col1:
            user_input = st.text_area(
                "Input",
                placeholder="Paste a news website link or copy-paste summary of news here...",
                label_visibility="collapsed",
                height=54
            )
        with col2:
            go_pressed = st.button("Go", type="primary")

        if go_pressed:
            if not GROQ_API_KEY:
                st.session_state.error = "سستم آف لائن ہے۔ برائے مہربانی بیک اینڈ پر 'GROQ_API_KEY' محفوظ کریں۔"
            elif not user_input.strip():
                st.session_state.error = "مہربانی فرما کر پہلے کوئی لنک یا ٹیکسٹ درج کریں۔"
            else:
                st.session_state.error = ""
                
                if st.session_state.headline or st.session_state.package or st.session_state.oc_vo:
                    if not st.session_state.archive or st.session_state.archive[0]["headline"] != st.session_state.headline:
                        archive_item = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "input": st.session_state.last_input,
                            "headline": st.session_state.headline,
                            "package": st.session_state.package,
                            "oc_vo": st.session_state.oc_vo
                        }
                        st.session_state.archive.insert(0, archive_item)
                
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
                        
                        # Prepend "Package\nMontage\n" directly to the Package output window
                        raw_package = data.get("package", "").strip()
                        st.session_state.package = f"Package\nMontage\n{raw_package}"
                        
                        oc_text = data.get("oc", "").strip()
                        vo_text = data.get("vo", "").strip()
                        
                        # Format OC & VO with purely Urdu tags (No English metadata tags)
                        st.session_state.oc_vo = f"او سی:\n{oc_text}\n\n\nوی او:\n{vo_text}"
                        st.session_state.last_input = user_input.strip()

        if st.session_state.error:
            st.error(st.session_state.error)

        def render_copiable_box(label, text, height=120):
            safe_text = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace('"', '\\"')
            html_code = f"""
            <div style="font-family: 'Georgia', serif; margin-bottom: 25px; background-color: #ffffff; text-align: right; direction: rtl;">
                <label style="font-weight: 700; color: #1e1b4b; display: block; margin-bottom: 6px; font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px; text-align: right;">{label}</label>
                <textarea id="{label}_text" style="width: 100%; height: {height}px; padding: 14px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 16px; box-sizing: border-box; background-color: #ffffff; color: #0f172a; font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaleeq Urdu', 'Urdu Typesetting', Tahoma, sans-serif; line-height: 2.0; text-align: right; direction: rtl; resize: none; box-shadow: 0 1px 10px rgba(0,0,0,0.01); transition: all 0.2s ease;" readonly>{text}</textarea>
                <div style="text-align: right; margin-top: 8px; direction: rtl;">
                    <button id="btn_{label}" onclick="copyText_{label}()" style="padding: 10px 24px; background-color: #1e1b4b; border: 1px solid #1e1b4b; border-radius: 6px; font-size: 11px; color: #ffffff; cursor: pointer; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 700; transition: all 0.2s ease; box-shadow: 0 2px 6px rgba(30, 27, 75, 0.12); text-transform: uppercase; letter-spacing: 1px;">Copy {label}</button>
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
                    btn.style.backgroundColor = "#10b981";
                    btn.style.borderColor = "#10b981";
                    
                    setTimeout(function() {{
                        btn.innerHTML = "Copy {label}";
                        btn.style.backgroundColor = "#1e1b4b";
                        btn.style.borderColor = "#1e1b4b";
                    }}, 1500);
                }}
            </script>
            """
            components.html(html_code, height=height + 80)

        if st.session_state.headline or st.session_state.package or st.session_state.oc_vo:
            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
            
            # Adjusted heights proportionally to compensate for triple length headlines and double length packages
            render_copiable_box("Headline", st.session_state.headline, height=120)
            render_copiable_box("Package", st.session_state.package, height=280)
            render_copiable_box("OC & VO", st.session_state.oc_vo, height=200)
            
        st.markdown('</div>', unsafe_allow_html=True)