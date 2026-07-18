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
if "box_headline_verify" not in st.session_state:
    st.session_state.box_headline_verify = ""
if "box_package" not in st.session_state:
    st.session_state.box_package = ""
if "box_oc_vo" not in st.session_state:
    st.session_state.box_oc_vo = ""
if "box_production_meta" not in st.session_state:
    st.session_state.box_production_meta = ""
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

# --- 3. GROQ NEWSROOM LLM PROCESSOR (Embedded Master Prompt V1.0) ---
def process_with_master_prompt(text, api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # MASTER PROMPT V1.0 DIRECT INTEGRATION
    system_prompt = (
        "MASTER PROMPT — PAKISTANI TV NEWSROOM AI (Version 1.0)\n\n"
        "ROLE:\n"
        "You are a Senior Pakistani Television Newsroom Editor, Assignment Editor, Bulletin Producer, News Researcher, Urdu Language Expert, Script Writer, Copy Editor and Editorial Gatekeeper.\n"
        "Your job is NOT to summarize news. Your job is to convert raw news into professional Pakistani television newsroom content exactly as it is produced in major Pakistani TV channels.\n"
        "Every output must sound as if it has been written by an experienced television news editor.\n\n"
        "OBJECTIVE:\n"
        "Convert the provided input (News Link, Urdu/English News, Press Release, Breaking News, Social Media Posts, Video Transcript, etc.) into complete broadcast-ready newsroom content.\n\n"
        "EDITORIAL POLICY & FILTERS:\n"
        "- Always write according to the editorial style of a mainstream Pakistani television newsroom. Professional, Neutral, Balanced, Broadcast Friendly, Fact-Based, Natural, Simple Urdu.\n"
        "- Never sound like an AI or Google Translate.\n"
        "- Do not generate material that promotes hatred, violence, or unlawful activity. No personal political opinions or ideological commentary.\n"
        "- Respect Pakistan's national context, Islamic values, and local cultural sensitivities in wording and presentation.\n"
        "- Never fabricate quotations, numbers, names, casualties, or official statements.\n\n"
        "NUMBER STYLE:\n"
        "- Never use Arabic numerals unless absolutely necessary. Always write numbers in Urdu words (e.g., 2 -> دو, 5 -> پانچ, 2026 -> دو ہزار چھبیس).\n"
        "- Avoid unnecessary English abbreviations (e.g., F-16 -> ایف سولہ لڑاکا طیارہ).\n"
        "- Translate foreign concepts or technical terms into clean, pure Urdu words. Absolutely NO Cyrillic text.\n\n"
        "OUTPUT FORMAT REQUIREMENTS:\n"
        "You MUST return your entire response strictly in a JSON object with the following keys:\n"
        "1. \"verification\": Classify the story as 'Confirmed', 'Likely', or 'Claim'. Mention if any important facts remain unverified. If it is a claim, properly attribute it (e.g., پولیس کے مطابق).\n"
        "2. \"headline\": One professional, chronological, broadcast-friendly television bulletin headline in Urdu. Dramatic but factual.\n"
        "3. \"oc\": Anchor Intro (On Camera) script in Urdu (Approx 30-45 seconds, 3 to 4 long sentences) that grabs attention and transitions smoothly.\n"
        "4. \"vo\": Voice Over script in Urdu (7 to 9 sentences) suitable for television visuals using short sentences.\n"
        "5. \"package\": Complete OC Package Script (Anchor Intro -> Package Script -> Strong Ending) formatted cleanly in Urdu.\n"
        "6. \"lower_thirds\": Three Lower Thirds (CG lines) in Urdu, maximum 6 to 8 words each, representing different angles without repeating the headline.\n"
        "7. \"tickers\": Fast, short, simple broadcast-ready television tickers in Urdu.\n"
        "8. \"background\": Brief background, timeline, context, strategic importance, or diplomatic impact in Urdu if relevant."
    )
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the raw input news material to convert:\n\n{text}"}
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
                border-bottom: 2px solid #1e1b4b;
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
                font-size: 17px;
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
            <div class="section-label">ہیڈ لائن اور تصدیق:</div>
            <div class="content-text">{item['headline_verify']}</div>
            <div class="section-label">تفصیلی نیوز پیکج:</div>
            <div class="content-text">{item['package']}</div>
            <div class="section-label">آن کیمرہ اور وائس اوور اسکرپٹ:</div>
            <div class="content-text" style="white-space: pre-wrap;">{item['oc_vo']}</div>
            <div class="section-label">سی جی، ٹکرز اور پس منظر:</div>
            <div class="content-text" style="white-space: pre-wrap;">{item['production_meta']}</div>
        </div>
        """
    html_content += "</body></html>"
    return html_content

# --- 5. THE JOURNALIST WEB INTERFACE ---
st.set_page_config(page_title="Jal Bagola", page_icon="🌪️", layout="wide")

st.markdown("""
    <style>
        /* 🔴 AGGRESSIVELY HIDE ALL STREAMLIT CLOUD BADGES, FORKS & MANAGE APP BUTTONS */
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
        
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            background-color: #fcfbf9 !important;
            color: #1e293b !important;
            font-family: 'Georgia', Times, serif !important;
        }
        [data-testid="stHeader"] {
            background-color: rgba(0,0,0,0) !important;
        }
        
        .block-container {
            padding-top: 6rem !important;
            padding-bottom: 3rem !important;
            max-width: 1250px !important;
        }
        
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

        .stTextArea textarea, div[data-testid="stTextInput"] input {
            border-radius: 6px !important;
            border: 1px solid #cbd5e1 !important;
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
            font-family: 'Georgia', serif !important;
        }
        div.stButton > button:hover {
            background-color: #312e81 !important;
            border-color: #312e81 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(30, 27, 75, 0.15) !important;
        }
        
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
            font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaleeq Urdu', serif !important;
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
        
        div.stButton > button[key="guest_login_btn"] {
            background-color: #ffffff !important;
            color: #1e1b4b !important;
            border: 1.5px solid #1e1b4b !important;
            box-shadow: none !important;
        }
        
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

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
            st.markdown(f'<div style="display: flex; justify-content: center; align-items: center; margin-bottom: 30px; width: 100%;"><img src="data:image/png;base64,{img_b64}" style="max-width: 250px; width: 100%; border-radius: 8px;" /></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="display: flex; justify-content: center; align-items: center; margin-bottom: 30px; width: 100%;"><div style="text-align: center; padding: 25px; border-radius: 12px; background: linear-gradient(135deg, #0f172a, #1e293b); color: #ffffff; max-width: 250px; width: 100%;"><h1 style="margin: 0; font-family: Georgia, serif; font-size: 2.2rem; color: #38bdf8;">🌪️ جل بگولہ</h1><p style="margin: 5px 0 0 0; font-size: 0.8rem; color: #94a3b8; text-transform: uppercase;">KHULASA NEWS SUMMARY</p></div></div>', unsafe_allow_html=True)
        
        st.markdown("<h4 style='text-align: center; color: #1e1b4b; font-family: Georgia, serif; font-size: 16px; font-weight: 700; margin-bottom: 25px;'>EDITORIAL GATEWAY</h4>", unsafe_allow_html=True)
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
                
        st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 11px; font-weight: 700; margin: 20px 0;'>OR</p>", unsafe_allow_html=True)
        if st.button("GUEST ACCESS", key="guest_login_btn"):
            st.session_state.logged_in = True
            st.session_state.error = ""
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --- 7. RENDER MAIN WORKSPACE (WHEN LOGGED IN) ---
else:
    archive_col, main_col = st.columns([2.8, 7.2], gap="large")

    # --- LEFT COLUMN: ARCHIVE SIDEBAR WIDGET ---
    with archive_col:
        st.markdown('<div class="wp-sidebar-wrapper">', unsafe_allow_html=True)
        st.markdown('<div style="border-bottom: 2px solid #1e1b4b; padding-bottom: 10px; margin-bottom: 20px;"><h3 style="color: #1e1b4b; font-family: Georgia, serif; font-size: 18px; font-weight: 700; margin: 0;">📋 Recent Posts</h3><p style="color: #64748b; font-size: 11px; margin: 4px 0 0 0;">Auto-saved summaries directory</p></div>', unsafe_allow_html=True)
        
        if st.session_state.archive:
            for idx, item in enumerate(st.session_state.archive):
                display_label = f"📝 {item['headline_verify'][:28]}...\n🕒 {item['timestamp']}"
                if st.button(display_label, key=f"arch_{idx}", use_container_width=True):
                    st.session_state.box_headline_verify = item["headline_verify"]
                    st.session_state.box_package = item["package"]
                    st.session_state.box_oc_vo = item["oc_vo"]
                    st.session_state.box_production_meta = item["production_meta"]
                    st.session_state.last_input = item["input"]
                    st.rerun()
                    
            st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
            export_html = generate_export_html(st.session_state.archive)
            st.download_button(label="📤 Export Archive", data=export_html, file_name="jal_bagola_master_archive.html", mime="text/html", use_container_width=True)
        else:
            st.markdown('<div style="text-align: center; padding: 40px 10px; border: 1px dashed #cbd5e1; border-radius: 8px;"><p style="color: #94a3b8; font-size: 12px; margin: 0;">No articles analyzed yet.</p></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- RIGHT COLUMN: MAIN WORKSPACE ---
    with main_col:
        st.markdown('<div class="wp-main-post-wrapper">', unsafe_allow_html=True)
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png") if "__file__" in locals() else "logo.png"
        
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img_b64 = base64.b64encode(img_file.read()).decode()
            st.markdown(f'<div style="display: flex; justify-content: center; align-items: center; margin-bottom: 30px; width: 100%;"><img src="data:image/png;base64,{img_b64}" style="max-width: 250px; width: 100%; border-radius: 12px;" /></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([8.6, 1.4], vertical_alignment="bottom")
        with col1:
            user_input = st.text_area("Input", placeholder="Paste a news website link or copy-paste summary of news here...", label_visibility="collapsed", height=54)
        with col2:
            go_pressed = st.button("Go", type="primary")

        if go_pressed:
            if not GROQ_API_KEY:
                st.session_state.error = "سستم آف لائن ہے۔ برائے مہربانی بیک اینڈ پر 'GROQ_API_KEY' محفوظ کریں۔"
            elif not user_input.strip():
                st.session_state.error = "مہربانی فرما کر پہلے کوئی لنک یا ٹیکسٹ درج کریں۔"
            else:
                st.session_state.error = ""
                
                # Auto-Archive logic
                if st.session_state.box_headline_verify:
                    if not st.session_state.archive or st.session_state.archive[0]["headline_verify"] != st.session_state.box_headline_verify:
                        archive_item = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "input": st.session_state.last_input,
                            "headline_verify": st.session_state.box_headline_verify,
                            "package": st.session_state.box_package,
                            "oc_vo": st.session_state.box_oc_vo,
                            "production_meta": st.session_state.box_production_meta
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
                    
                    data = process_with_master_prompt(content, GROQ_API_KEY)
                    
                    if "error" in data:
                        st.session_state.error = data["error"]
                    else:
                        # Map JSON data blocks cleanly into the 4 custom copiable card areas
                        verify_status = data.get("verification", "").strip()
                        hl_text = data.get("headline", "").strip()
                        st.session_state.box_headline_verify = f"خبر کی تصدیق:\n{verify_status}\n\nہیڈ لائن:\n{hl_text}"
                        
                        st.session_state.box_package = data.get("package", "").strip()
                        
                        oc_text = data.get("oc", "").strip()
                        vo_text = data.get("vo", "").strip()
                        st.session_state.box_oc_vo = f"او سی (ON-CAMERA):\n{oc_text}\n\n\nوی او (VOICE-OVER):\n{vo_text}"
                        
                        cg_data = data.get("lower_thirds", "")
                        cg_str = "\n".join(cg_data) if isinstance(cg_data, list) else str(cg_data)
                        ticker_text = data.get("tickers", "").strip()
                        bg_text = data.get("background", "").strip()
                        st.session_state.box_production_meta = f"تین سی جی (LOWER THIRDS):\n{cg_str}\n\n\nٹی وی ٹکر (TICKERS):\n{ticker_text}\n\n\nمختصر پس منظر (BACKGROUND):\n{bg_text}"
                        st.session_state.last_input = user_input.strip()

        if st.session_state.error:
            st.error(st.session_state.error)

        def render_copiable_box(label, text, height=120):
            safe_text = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace('"', '\\"')
            html_code = f"""
            <div style="font-family: 'Georgia', serif; margin-bottom: 25px; background-color: #ffffff; text-align: right; direction: rtl;">
                <label style="font-weight: 700; color: #1e1b4b; display: block; margin-bottom: 6px; font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px;">{label}</label>
                <textarea id="{label}_text" style="width: 100%; height: {height}px; padding: 14px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 16px; box-sizing: border-box; background-color: #ffffff; color: #0f172a; font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaleeq Urdu', Tahoma, sans-serif; line-height: 2.0; text-align: right; direction: rtl; resize: none; box-shadow: 0 1px 10px rgba(0,0,0,0.015);" readonly>{text}</textarea>
                <div style="text-align: right; margin-top: 8px;">
                    <button id="btn_{label}" onclick="copyText_{label}()" style="padding: 10px 24px; background-color: #1e1b4b; border: 1px solid #1e1b4b; border-radius: 6px; font-size: 11px; color: #ffffff; cursor: pointer; font-family: 'Georgia', serif; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">Copy {label}</button>
                </div>
            </div>
            <script>
                function copyText_{label}() {{
                    var copyText = document.getElementById("{label}_text");
                    copyText.select();
                    copyText.setSelectionRange(0, 99999);
                    try {{ navigator.clipboard.writeText(copyText.value); }} catch (err) {{ document.execCommand('copy'); }}
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

        if st.session_state.box_headline_verify or st.session_state.box_package or st.session_state.box_oc_vo:
            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
            render_copiable_box("Headline & Verification (ہیڈ لائن اور تصدیق)", st.session_state.box_headline_verify, height=100)
            render_copiable_box("Broadcast Package (تفصیلی نیوز پیکج)", st.session_state.box_package, height=150)
            render_copiable_box("OC & VO Script (آن کیمرہ اور وائس اوور اسکرپٹ)", st.session_state.box_oc_vo, height=220)
            render_copiable_box("Production CG, Tickers & Background (سی جی، ٹکرز اور پس منظر)", st.session_state.box_production_meta, height=220)
            
        st.markdown('</div>', unsafe_allow_html=True)