import streamlit as st
import streamlit.components.v1 as components
import requests
from bs4 import BeautifulSoup
import json
import os
import base64
from datetime import datetime

# Fetching Free Google Gemini API Key silently from background secrets
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# --- 0. AUTHENTICATION CREDENTIALS (10 UNIQUE ACCOUNTS) ---
USER_CREDENTIALS = {
    "newsdesk1": "JalNews#2026A",
    "newsdesk2": "JalNews#2026B",
    "editor_01": "EditRoom!981",
    "editor_02": "EditRoom!982",
    "producer1": "ProdStudio%1",
    "producer2": "ProdStudio%2",
    "reporter_a": "RepField@10",
    "reporter_b": "RepField@20",
    "admin_jal": "JalBagolaAdmin2026",
    "copydesk": "CopyEditor#2026"
}

# --- 1. SESSION STATE FOR SECURE ACCESS ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "breaking_story" not in st.session_state:
    st.session_state.breaking_story = ""
if "headline" not in st.session_state:
    st.session_state.headline = ""
if "package" not in st.session_state:
    st.session_state.package = ""
if "cgs" not in st.session_state:
    st.session_state.cgs = ""
if "active_model_version" not in st.session_state:
    st.session_state.active_model_version = ""
if "error" not in st.session_state:
    st.session_state.error = ""
if "archive" not in st.session_state:
    st.session_state.archive = []
if "last_input" not in st.session_state:
    st.session_state.last_input = ""

# --- 2. ENHANCED WEB SCRAPER ---
def scrape_article(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ur,en-US;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache'
        }
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code != 200:
            return f"Error: Webpage returned status code {response.status_code}"
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "form"]):
            element.decompose()
            
        article = soup.find('article') or soup.find('main') or soup.find('div', class_=lambda c: c and ('article' in c.lower() or 'content' in c.lower() or 'story' in c.lower()))
        
        if article:
            paragraphs = article.find_all(['p', 'h1', 'h2', 'h3'])
        else:
            paragraphs = soup.find_all('p')
            
        text_blocks = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 25]
        article_text = "\n\n".join(text_blocks)
        
        if len(article_text) < 100:
            body = soup.find('body')
            if body:
                raw_lines = [line.strip() for line in body.get_text().splitlines() if len(line.strip()) > 30]
                article_text = "\n\n".join(raw_lines)

        return article_text[:8000].strip()
    except Exception as e:
        return f"Scraping failed: {str(e)}"

# --- 3. GOOGLE GEMINI PROCESSOR ---
def process_with_gemini(text, api_key):
    clean_key = str(api_key).strip().replace('"', '').replace("'", "")
    
    system_prompt = (
        "آپ ایک سینئر اردو ٹی وی نیوز ایڈیٹر، کاپی ایڈیٹر اور نیوز پروڈیوسر ہیں جو پاکستانی ٹیلی ویژن نیوز چینل کے لیے کام کرتے ہیں۔\n"
        "آپ کا طریقہ تحریر پیشہ ورانہ اردو ٹی وی نیوز رومز کے ایڈیٹوریل معیار کے مطابق ہونا چاہیے۔ ہر جواب فوری نشر کرنے کے لیے موزوں ہو۔\n\n"

        "اہم ہدایت: صرف اور صرف صارف کے فراہم کردہ حالیہ ان پٹ متن پر کام کریں۔ پرامپٹ کی مثالوں کا مواد جواب میں مت دہرائیں۔\n\n"

        "جب صارف آپ کو کوئی مواد دالے تو آپ کو درج ذیل 4 چیزیں فراہم کرنی ہیں:\n\n"

        "1۔ بریکنگ اسٹوری (breaking_story):\n"
        "سب سے پہلے خبر کی بریکنگ اسٹوری بنائیں۔ بریکنگ اسٹوری جاندار، روان اور ٹی وی اینکر کے انداز میں ہونی چاہیے۔\n\n"

        "2۔ ہیڈ لائن (headline):\n"
        "اس بریکنگ کے بعد خبر کی ایک تفصیلی اور جامع ہیڈ لائن بنا کر دیں۔ ہیڈ لائن مختصر یا چھوٹی نہ ہو، بلکہ زیادہ سے زیادہ اہم تفصیلات ہیڈ لائن کا حصہ بنیں۔ کم از کم 4 سے 5 جملے ہوں، اگر متن زیادہ ہو تو 7، 8، 9 جملے یا خبر کی اہمیت کے مطابق 12 جملے بھی ہو سکتے ہیں۔ (اگر سورس ہی بہت کم ہو تو مختصر ہیڈ لائن بنائیں۔)\n"
        "ہیڈ لائن میں کوئی انگریزی ایلفابیٹ اور کوئی انگریزی/مغربی ہندسہ (1, 2, 3) نہ ہو، تمام اعداد اردو الفاظ میں لکھیں (مثلاً دس، پندرہ، چھبیس، تین سو ترانوے، پچہتر)۔\n\n"

        "3۔ پیکج (package):\n"
        "اس کے بعد اسی خبر کا ایک مکمل پیکج بنا کر دیں۔ پیکج کا فارمیٹ بالکُل اس ساخت پر ہو:\n"
        "اوسی\n"
        "[خبر کا اختصار اور جامعیت کے ساتھ اینکر انٹرو]\n\n"
        "---\n\n"
        "PKG\n\n"
        "MONTAGE\n"
        "[دو یا تین کھڑے جملے جو جملہ ناقص ہوں لیکن خبر کے اہم ترین حصوں کا احاطہ کریں]\n\n"
        "---\n\n"
        "وائس اور\n"
        "[تفصیلی اور روان وائس اوور اسکرپٹ]\n\n"
        "---\n\n"
        "TEMPS\n"
        "[وائس اوور میں شامل جملوں کے مختصر اور ناقص انداز میں لکھے گئے خلاصے]\n\n"

        "4۔ سی جی / لوئر تھرڈز / نیوز آئی ڈی (cgs):\n"
        "آخر میں خبر کی 3، 4 یا 5 کامل اور با معنی سی جی (لوئر تھرڈ) لائنز بنائیں۔ سی جی ناقص جملے نہ ہوں بلکہ کامل ہوں تاکہ اسکرین پر دیکھ کر پوری خبر سمجھ آ جائے۔ عام طور پر فی سی جی 6 سے 8 الفاظ رکھیں، ضرورت پڑنے پر 10، 12 یا 14-15 الفاظ تک جا سکتے ہیں۔\n\n"

        "سخت ایڈیٹوریل و املا کے قواعد:\n"
        "- لفظ 'امریکا' کا درست املا امریکا ہے، اسے کبھی 'امریکہ' مت لکھیں۔\n"
        "- الفاظ ملا کر نہ لکھیں: 'صورت حال' الگ لکھیں (صورتحال نہیں)، 'فٹ بال' الگ لکھیں (فٹبال نہیں)، 'کے لیے' الگ لکھیں (کیلئے یا کیلیے نہیں)۔\n"
        "- گالی یا نامناسب زبان کو اسٹیرک سے سنسر کریں (مثال: بے ******)۔\n"
        "- پاکستان مخالف، اسلام مخالف یا مشرقی روایات کے خلاف کوئی بات خبر کا حصہ نہ بنائیں۔\n"
        "- انگریزی اصطلاحات اور مخففات کو قدرتی اردو میں تبدیل کریں (مثلاً CTD -> سی ٹی ڈی، FIA -> ایف آئی اے، NASA -> ناسا، UAE -> یو اے ای، B-52 -> بی باون)۔\n"
        "- جواب کی زبان صرف اور صرف اردو رہے گی۔\n\n"

        "آپ کو اپنا جواب لازمی طور پر ایک JSON آبجیکٹ میں فراہم کرنا ہے جس کی 4 چابیاں یہ ہوں گی:\n"
        "{\n"
        "  \"breaking_story\": \"بریکنگ اسٹوری کا متن\",\n"
        "  \"headline\": \"تفصیلی اور جامع اردو ہیڈ لائن\",\n"
        "  \"package\": \"مکمل ٹی وی پیکیج (او سی، مونتاز، وائس اور، اور ٹیمپس کے ساتھ)\",\n"
        "  \"cgs\": \"3 سے 5 کامل سی جی / لوئر تھرڈز لسٹ یا متن\"\n"
        "}"
    )
    
    payload = {
        "contents": [{"parts": [{"text": f"صارف کی موصول شدہ خبر کا متن:\n\n{text}"}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"responseMimeType": "application/json"}
    }
    
    targets = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]
    last_err = ""
    
    for model_name in targets:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_key}"
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=25)
            if response.status_code == 200:
                result = response.json()
                content_str = result["candidates"][0]["content"]["parts"][0]["text"]
                parsed_json = json.loads(content_str)
                
                raw_model_version = result.get("modelVersion", model_name)
                parsed_json["_actual_model_version"] = raw_model_version
                return parsed_json
            else:
                last_err = f"{model_name} -> Status {response.status_code}: {response.text}"
        except Exception as e:
            last_err = str(e)
            
    return {"error": f"Gemini API Error: {last_err}"}

# --- 4. EXPORT ARCHIVE TO HTML ---
def generate_export_html(archive_list):
    html_content = """
    <!DOCTYPE html>
    <html lang="ur" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>جل بگولہ - ماسٹر آرکائیو رپورٹ</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaleeq+Urdu:wght@400;700&display=swap');
            body {
                font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaleeq Urdu', 'Segoe UI', Tahoma, sans-serif;
                background-color: #ffffff;
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
                font-size: 16px;
                margin-top: 10px;
                margin-bottom: 20px;
                text-align: right;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌪️ جل بگولہ - ماسٹر آرکائیو رپورٹ</h1>
            <p style="color: #64748b; margin: 5px 0 0 0;">Exported Archive Data</p>
        </div>
    """
    for item in archive_list:
        html_content += f"""
        <div class="archive-item">
            <div class="timestamp">🕒 تاریخ و وقت: {item['timestamp']}</div>
            <div class="section-label">1. بریکنگ اسٹوری:</div>
            <div class="content-text" style="white-space: pre-wrap;">{item['breaking_story']}</div>
            <div class="section-label">2. ہیڈ لائن:</div>
            <div class="content-text" style="white-space: pre-wrap;">{item['headline']}</div>
            <div class="section-label">3. ٹی وی پیکیج:</div>
            <div class="content-text" style="white-space: pre-wrap;">{item['package']}</div>
            <div class="section-label">4. سی جی / لوئر تھرڈز:</div>
            <div class="content-text" style="white-space: pre-wrap;">{item['cgs']}</div>
        </div>
        """
    html_content += "</body></html>"
    return html_content

# --- 5. THE JOURNALIST WEB INTERFACE ---
st.set_page_config(page_title="Jal Bagola", page_icon="🌪️", layout="wide")

# PURE GOOGLE-WHITE STYLING WITH STATIC NON-RESIZABLE INPUT BOXES
st.markdown("""
    <style>
        /* HIDE ALL STREAMLIT DECORATION / TOOLBARS / HEADER ARTIFACTS */
        header, [data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="manage-app-button"], footer {
            display: none !important;
            height: 0 !important;
            visibility: hidden !important;
        }
        
        /* STRICT PURE WHITE BACKGROUND */
        html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMainBlockContainer"], .main, section.main, .stApp {
            background-color: #ffffff !important;
            background: #ffffff !important;
            color: #202124 !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        }
        
        /* GOOGLE HOMEPAGE 18VH TOP OFFSET */
        .block-container {
            padding-top: 18vh !important;
            padding-bottom: 5rem !important;
            max-width: 1150px !important;
        }

        .wp-sidebar-wrapper {
            background-color: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px !important;
            padding: 20px !important;
        }

        /* STATIC NON-RESIZABLE INPUT TEXT AREA */
        div[data-testid="stTextArea"] textarea, div[data-testid="stTextInput"] input, textarea {
            background-color: #ffffff !important;
            color: #202124 !important;
            border: 1px solid #dfe1e5 !important;
            border-radius: 24px !important;
            padding: 14px 22px !important;
            font-size: 16px !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            box-shadow: 0 1px 6px rgba(32,33,36,0.08) !important;
            transition: all 0.2s ease !important;
            resize: none !important; /* PREVENT MOUSE DRAGGING / RESIZING */
        }
        
        div[data-testid="stTextArea"] textarea:focus, div[data-testid="stTextInput"] input:focus {
            box-shadow: 0 2px 10px rgba(32,33,36,0.18) !important;
            border-color: #1a73e8 !important;
            outline: none !important;
        }
        
        /* ACTION BUTTON */
        div.stButton > button {
            border-radius: 20px !important;
            background-color: #1a73e8 !important;
            color: #ffffff !important;
            border: 1px solid #1a73e8 !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            height: 52px !important;
            width: 100% !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
        }
        div.stButton > button:hover {
            background-color: #1557b0 !important;
            border-color: #1557b0 !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.15) !important;
        }
        
        .wp-sidebar-wrapper .stButton > button {
            text-align: right !important;
            direction: rtl !important;
            background-color: #ffffff !important;
            color: #3c4043 !important;
            border: none !important;
            border-bottom: 1px solid #f1f3f4 !important;
            border-radius: 0px !important;
            padding: 12px 8px !important;
            font-size: 13px !important;
            font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaleeq Urdu', serif !important;
            box-shadow: none !important;
            height: auto !important;
        }
        .wp-sidebar-wrapper .stButton > button:hover {
            color: #1a73e8 !important;
            background-color: #f8f9fa !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- 6. RENDER SECURE GATE (LOGIN PAGE) ---
if not st.session_state.logged_in:
    login_center_col1, login_center_col2, login_center_col3 = st.columns([1.5, 2.0, 1.5])
    
    with login_center_col2:
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png") if "__file__" in locals() else "logo.png"
        
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img_b64 = base64.b64encode(img_file.read()).decode()
            st.markdown(f'<div style="display: flex; justify-content: center; align-items: center; margin-bottom: 25px; width: 100%;"><img src="data:image/png;base64,{img_b64}" style="max-width: 300px; width: 100%;" /></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="display: flex; justify-content: center; align-items: center; margin-bottom: 25px; width: 100%;"><div style="text-align: center; color: #1a73e8;"><h1 style="margin: 0; font-family: Google Sans, Roboto, sans-serif; font-size: 2.8rem;">🌪️ جل بگولہ</h1></div></div>', unsafe_allow_html=True)
        
        st.markdown("<p style='text-align: center; color: #5f6368; font-size: 12px; font-weight: 600; margin-bottom: 20px; letter-spacing: 1px;'>EDITORIAL GATEWAY LOGIN</p>", unsafe_allow_html=True)
        username_input = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
        password_input = st.text_input("Password", placeholder="Password", type="password", label_visibility="collapsed")
        
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if st.button("LOG IN", type="primary"):
            u = username_input.strip()
            p = password_input.strip()
            if u in USER_CREDENTIALS and USER_CREDENTIALS[u] == p:
                st.session_state.logged_in = True
                st.session_state.error = ""
                st.rerun()
            else:
                st.error("Invalid Username or Password. Please try again.")

# --- 7. RENDER MAIN WORKSPACE (DYNAMIC ARCHIVE SIDEBAR) ---
else:
    if st.session_state.archive:
        archive_col, main_col = st.columns([2.4, 7.6], gap="large")
        with archive_col:
            st.markdown('<div class="wp-sidebar-wrapper">', unsafe_allow_html=True)
            st.markdown('<div style="border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 15px;"><h3 style="color: #202124; font-size: 16px; font-weight: 700; margin: 0;">📋 Recent Posts</h3></div>', unsafe_allow_html=True)
            
            for idx, item in enumerate(st.session_state.archive):
                display_label = f"📝 {item['headline'][:24]}...\n🕒 {item['timestamp']}"
                if st.button(display_label, key=f"arch_{idx}", use_container_width=True):
                    st.session_state.breaking_story = item["breaking_story"]
                    st.session_state.headline = item["headline"]
                    st.session_state.package = item["package"]
                    st.session_state.cgs = item["cgs"]
                    st.session_state.active_model_version = item.get("active_model_version", "")
                    st.session_state.last_input = item["input"]
                    st.rerun()
                    
            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
            export_html = generate_export_html(st.session_state.archive)
            st.download_button(label="📤 Export Archive", data=export_html, file_name="jal_bagola_master_archive.html", mime="text/html", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        main_col = st.container()

    with main_col:
        logo_path = os.path.join(os.path.dirname(__file__), "logo.png") if "__file__" in locals() else "logo.png"
        
        # CENTERED LOGO POSITIONED LOWER
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                img_b64 = base64.b64encode(img_file.read()).decode()
            st.markdown(f'<div style="display: flex; justify-content: center; align-items: center; margin-bottom: 30px; width: 100%;"><img src="data:image/png;base64,{img_b64}" style="max-width: 320px; width: 100%;" /></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="display: flex; justify-content: center; align-items: center; margin-bottom: 30px; width: 100%;"><div style="text-align: center; color: #1a73e8;"><h1 style="margin: 0; font-family: Google Sans, Roboto, sans-serif; font-size: 3rem;">🌪️ جل بگولہ</h1></div></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([8.8, 1.2], vertical_alignment="bottom")
        with col1:
            user_input = st.text_area("Input", placeholder="Paste a news website link or copy-paste summary of news here...", label_visibility="collapsed", height=60)
        with col2:
            go_pressed = st.button("Go", type="primary")

        if go_pressed:
            if not GEMINI_API_KEY:
                st.session_state.error = "سستم آف لائن ہے۔ برائے مہربانی بیک اینڈ پر 'GEMINI_API_KEY' محفوظ کریں۔"
            elif not user_input.strip():
                st.session_state.error = "مہربانی فرما کر پہلے کوئی لنک یا ٹیکسٹ درج کریں۔"
            else:
                st.session_state.error = ""
                
                if st.session_state.headline:
                    if not st.session_state.archive or st.session_state.archive[0]["headline"] != st.session_state.headline:
                        archive_item = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "input": st.session_state.last_input,
                            "breaking_story": st.session_state.breaking_story,
                            "headline": st.session_state.headline,
                            "package": st.session_state.package,
                            "cgs": st.session_state.cgs,
                            "active_model_version": st.session_state.active_model_version
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
                    
                    if len(content) < 80:
                        st.session_state.error = "⚠️ اس ویب سائٹ نے آٹو ریڈنگ بلاک کر دی ہے یا متن بہت کم ہے۔ برائے مہربانی خبر کا ٹیکسٹ کاپی کر کے ان پٹ باکس میں پیسٹ کریں۔"
                        st.stop()
                    
                    data = process_with_gemini(content, GEMINI_API_KEY)
                    
                    if "error" in data:
                        st.session_state.error = data["error"]
                    else:
                        st.session_state.breaking_story = str(data.get("breaking_story", "")).strip()
                        st.session_state.headline = str(data.get("headline", "")).strip()
                        st.session_state.package = str(data.get("package", "")).strip()
                        
                        cg_raw = data.get("cgs", "")
                        st.session_state.cgs = "\n".join(cg_raw) if isinstance(cg_raw, list) else str(cg_raw).strip()
                        
                        st.session_state.active_model_version = str(data.get("_actual_model_version", "Gemini API")).strip()
                        st.session_state.last_input = user_input.strip()

        if st.session_state.error:
            st.error(st.session_state.error)

        def render_copiable_box(label, text, height=160):
            safe_text = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace('"', '\\"')
            html_code = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin-bottom: 25px; background-color: #ffffff; text-align: right; direction: rtl; width: 100%;">
                <label style="font-weight: 700; color: #3c4043; display: block; margin-bottom: 6px; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;">{label}</label>
                <textarea id="{label}_text" style="width: 100%; height: {height}px; padding: 18px; border: 1px solid #dfe1e5; border-radius: 12px; font-size: 17px; box-sizing: border-box; background-color: #ffffff; color: #202124; font-family: 'Jameel Noori Nastaleeq', 'Noto Nastaleeq Urdu', Tahoma, sans-serif; line-height: 2.2; text-align: right; direction: rtl; resize: none; box-shadow: 0 1px 6px rgba(32,33,36,0.04);" readonly>{text}</textarea>
                <div style="text-align: right; margin-top: 8px;">
                    <button id="btn_{label}" onclick="copyText_{label}()" style="padding: 10px 24px; background-color: #1a73e8; border: 1px solid #1a73e8; border-radius: 18px; font-size: 12px; color: #ffffff; cursor: pointer; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Copy {label}</button>
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
                    btn.style.backgroundColor = "#188038";
                    btn.style.borderColor = "#188038";
                    setTimeout(function() {{
                        btn.innerHTML = "Copy {label}";
                        btn.style.backgroundColor = "#1a73e8";
                        btn.style.borderColor = "#1a73e8";
                    }}, 1500);
                }}
            </script>
            """
            components.html(html_code, height=height + 80)

        if st.session_state.breaking_story or st.session_state.headline or st.session_state.package:
            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
            
            if st.session_state.active_model_version:
                st.markdown(
                    f"""
                    <div style="background-color: #ffffff; border: 1px solid #e8eaed; border-radius: 12px; padding: 10px 18px; margin-bottom: 25px; display: flex; align-items: center; justify-content: space-between;">
                        <span style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 12px; font-weight: 600; color: #5f6368; text-transform: uppercase; letter-spacing: 1px;">
                            🤖 Executed AI Engine
                        </span>
                        <code style="background-color: #e8f0fe; color: #1a73e8; font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 6px; font-family: monospace;">
                            {st.session_state.active_model_version}
                        </code>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            render_copiable_box("Breaking Story (بریکنگ اسٹوری)", st.session_state.breaking_story, height=140)
            render_copiable_box("Headline (ہیڈ لائن)", st.session_state.headline, height=200)
            render_copiable_box("Package (پیکج)", st.session_state.package, height=360)
            render_copiable_box("CGs / Lower Thirds (سی جی / لوئر تھرڈز)", st.session_state.cgs, height=180)