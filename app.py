import streamlit as st
import streamlit.components.v1 as components
import requests
from bs4 import BeautifulSoup
import json

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
        "1. \"headline\": A long, impactful, and comprehensive Urdu headline. No English words or digits. Write numbers in Urdu words.\n"
        "2. \"package\": A highly detailed and long Urdu package (150 to 200 words, 7 to 9 sentences). Explain the background, perspectives, and current situation in depth. No English words or digits. Write numbers in Urdu words.\n"
        "3. \"oc_vo\": A detailed On-Camera and Voice-Over script. Combine detailed On-Camera text (3 to 4 sentences) and Voice-Over text (7 to 9 sentences) in Urdu. Clean formatting with clear transitions. Do not use asterisks (*).\n"
        "4. \"ticker\": Three Urdu tickers/CG lines, each exactly 6 to 8 words. No English words or digits. Do not use asterisks (*).\n\n"
        "Strict Editorial Rules:\n"
        "- Absolutely NO brackets [ ] or dashes inside any of the generated Urdu text.\n"
        "- NO English words or western digits (e.g., 15, 2026, 28) anywhere in the Urdu text. All numbers must be written as Urdu words (e.g., اٹھائیس, دو ہزار چھبیس).\n"
        "- Do not use asterisks (*) for formatting or bullet points. Use standard clean text layout.\n"
        "- Keep the Urdu highly fluent, professional, dramatic, and grammatically precise."
    )
    
    # Using 'llama-3.3-70b-versatile' which fully supports stable JSON mode & high-speed tokenization
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
                # Try to extract exact API response error message for debugging
                error_data = response.json()
                err_msg = error_data.get("error", {}).get("message", "Unknown Error")
                return {"error": f"Groq API Error: {err_msg} (Status {response.status_code})"}
            except:
                return {"error": f"Groq API Error: Status {response.status_code}"}
    except Exception as e:
        return {"error": f"Processing failed: {str(e)}"}

# --- 3. THE JOURNALIST WEB INTERFACE ---
st.set_page_config(page_title="Jal Bagola", page_icon="🌐", layout="centered")

# Force Light Minimalist Google Theme
st.markdown("""
    <style>
        /* Force Clean White Background globally */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            background-color: #ffffff !important;
            color: #202124 !important;
            font-family: Arial, sans-serif !important;
        }
        [data-testid="stHeader"] {
            background-color: rgba(0,0,0,0) !important;
        }
        .block-container {
            padding-top: 5rem !important;
            padding-bottom: 2rem !important;
            max-width: 800px !important;
        }
        /* Style Search/Input Textarea to look like Google Search box */
        .stTextArea textarea {
            border-radius: 24px !important;
            border: 1px solid #dfe1e5 !important;
            box-shadow: none !important;
            padding: 14px 24px !important;
            font-size: 16px !important;
            background-color: #ffffff !important;
            color: #202124 !important;
            line-height: 1.5 !important;
            min-height: 52px !important;
        }
        .stTextArea textarea:focus {
            box-shadow: 0 1px 6px rgba(32,33,36,0.28) !important;
            border-color: rgba(223,225,229,0) !important;
        }
        /* Style Go Button adjacent to input tab */
        div.stButton > button {
            border-radius: 24px !important;
            background-color: #f8f9fa !important;
            color: #3c4043 !important;
            border: 1px solid #dadce0 !important;
            font-size: 15px !important;
            padding: 10px 24px !important;
            height: 52px !important;
            width: 100% !important;
            font-weight: 500 !important;
            transition: all 0.15s ease !important;
            box-shadow: 0 1px 1px rgba(0,0,0,0.05) !important;
        }
        div.stButton > button:hover {
            border: 1px solid #c6c6c6 !important;
            color: #202124 !important;
            background-color: #f8f9fa !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
        }
        div.stButton > button:active {
            background-color: #f1f3f4 !important;
        }
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Google Styled centered "Jal Bagola" Logo
logo_html = """
<div style="text-align: center; margin-top: 20px; margin-bottom: 25px; user-select: none; cursor: default;">
    <span style="font-family: 'Product Sans', Arial, sans-serif; font-size: 5rem; font-weight: bold; letter-spacing: -2px;">
        <span style="color: #4285F4;">J</span>
        <span style="color: #EA4335;">a</span>
        <span style="color: #FBBC05;">l</span>
        <span style="color: #4285F4;">B</span>
        <span style="color: #34A853;">a</span>
        <span style="color: #EA4335;">g</span>
        <span style="color: #FBBC05;">o</span>
        <span style="color: #34A853;">l</span>
        <span style="color: #EA4335;">a</span>
    </span>
</div>
"""
st.markdown(logo_html, unsafe_allow_html=True)

# Session States for persistent outputs across runs
if "headline" not in st.session_state:
    st.session_state.headline = ""
if "package" not in st.session_state:
    st.session_state.package = ""
if "oc_vo" not in st.session_state:
    st.session_state.oc_vo = ""
if "ticker" not in st.session_state:
    st.session_state.ticker = ""
if "error" not in st.session_state:
    st.session_state.error = ""

# Single Tab Search Engine Bar adjacent to Go Button
col1, col2 = st.columns([8.5, 1.5], vertical_alignment="bottom")
with col1:
    user_input = st.text_area(
        "Input",
        placeholder="Paste a news website link or copy-paste summary of news here...",
        label_visibility="collapsed",
        height=52
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
        with st.spinner("پروسیسنگ جاری ہے..."):
            # Check if input is a Link
            if user_input.strip().startswith("http://") or user_input.strip().startswith("https://"):
                content = scrape_article(user_input.strip())
                if content.startswith("Error") or content.startswith("Scraping failed"):
                    st.session_state.error = f"سکریپنگ ناکام ہوئی: {content}"
                    st.stop()
            else:
                content = user_input.strip()
            
            # Send to Groq
            data = process_with_groq(content, GROQ_API_KEY)
            
            if "error" in data:
                st.session_state.error = data["error"]
            else:
                st.session_state.headline = data.get("headline", "")
                st.session_state.package = data.get("package", "")
                st.session_state.oc_vo = data.get("oc_vo", "")
                st.session_state.ticker = data.get("ticker", "")

# Display background system error if any
if st.session_state.error:
    st.error(st.session_state.error)

# Render premium output text areas with Dual-Fallback Copy engine (execCommand + ClipboardAPI)
def render_copiable_box(label, text, height=120):
    # Safe javascript string parsing to avoid crash on single quotes or newlines
    safe_text = text.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace('"', '\\"')
    html_code = f"""
    <div style="font-family: Arial, sans-serif; margin-bottom: 20px; background-color: #ffffff;">
        <label style="font-weight: bold; color: #202124; display: block; margin-bottom: 8px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">{label}</label>
        <textarea id="{label}_text" style="width: 100%; height: {height}px; padding: 14px; border: 1px solid #dadce0; border-radius: 8px; font-size: 15px; box-sizing: border-box; background-color: #f8f9fa; color: #202124; font-family: 'Segoe UI', Tahoma, Geneva, sans-serif; line-height: 1.6; text-align: right; direction: rtl; resize: none;" readonly>{text}</textarea>
        <div style="text-align: right; margin-top: 6px;">
            <button id="btn_{label}" onclick="copyText_{label}()" style="padding: 8px 20px; background-color: #f8f9fa; border: 1px solid #dadce0; border-radius: 20px; font-size: 13px; color: #3c4043; cursor: pointer; font-family: inherit; font-weight: 500; transition: all 0.15s ease; box-shadow: 0 1px 1px rgba(0,0,0,0.05);">Copy {label}</button>
        </div>
    </div>
    <script>
        function copyText_{label}() {{
            var copyText = document.getElementById("{label}_text");
            copyText.select();
            copyText.setSelectionRange(0, 99999);
            
            // Dual copy action to bypass Iframe security restrictions
            try {{
                navigator.clipboard.writeText(copyText.value);
            }} catch (err) {{
                document.execCommand('copy');
            }}
            
            var btn = document.getElementById("btn_{label}");
            btn.innerHTML = "✓ Copied!";
            btn.style.backgroundColor = "#e8f0fe";
            btn.style.borderColor = "#1a73e8";
            btn.style.color = "#1a73e8";
            
            setTimeout(function() {{
                btn.innerHTML = "Copy {label}";
                btn.style.backgroundColor = "#f8f9fa";
                btn.style.borderColor = "#dadce0";
                btn.style.color = "#3c4043";
            }}, 1500);
        }}
    </script>
    """
    components.html(html_code, height=height + 80)

# Render Output Cards below search engine bar
if st.session_state.headline or st.session_state.package or st.session_state.oc_vo or st.session_state.ticker:
    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    
    render_copiable_box("Headline", st.session_state.headline, height=90)
    render_copiable_box("Package", st.session_state.package, height=180)
    render_copiable_box("OC & VO", st.session_state.oc_vo, height=220)
    render_copiable_box("Ticker", st.session_state.ticker, height=100)