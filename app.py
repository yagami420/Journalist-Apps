import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# پس منظر میں خاموشی سے سیکرٹ کی تلاش کرنا
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

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

# --- 2. CLOUD GEMINI NEWSROOM ENGINE ---
def summarize_with_gemini(text, model_choice):
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(model_choice)
        
        combined_prompt = (
            "آپ ایک سینئر ٹی وی نیوز روم ایڈیٹر ہیں۔ دی گئی خبر کو پڑھیں اور اس کا مکمل، تفصیلی اور طویل اردو پیکیج تیار کریں۔\n\n"
            "سخت قوانین جن پر عمل کرنا فرض ہے:\n"
            "۱. آؤٹ پٹ میں کسی بھی قسم کے بریکٹس [ ] یا ڈیش کا استعمال بالکل نہ کریں۔\n"
            "۲. کوئی انگریزی لفظ یا گنتی کا نمبر (جیسے 15, 2026, 28) ہرگز نہ لکھیں‌۔ تمام نمبروں کو اردو الفاظ میں لکھیں (جیسے پندرہ جولائی، دو ہزار چھبیس، اٹھائیس)۔\n"
            "۳. او سی (OC) کی طوالت کو بڑھائیں۔ یہ کم از کم تین سے چار (3 to 4) تفصیلی، طویل اور جاندار جملوں پر مشتمل ہونا چاہیے جس میں خبر کا مکمل تعارف اور گہرائی موجود ہو۔\n"
            "۴. وی او (VO) کو بہت تفصیلی اور طویل بنائیں۔ یہ کم از کم ڈیڑھ سو سے دو سو (150 to 200) الفاظ یا سات سے نو (7 to 9) طویل اور مربوط جملوں پر مشتمل ہونا چاہیے، جس میں واقعے کا پس منظر، تمام کرداروں کے موقف، عدالت یا حکام کی ہدایات اور موجودہ صورتحال کی مکمل تفصیلات روانی کے ساتھ بیان کی گئی ہو۔\n"
            "۵. ہیڈ لائن (Headline) کو بھی طویل، جامع اور اثر انگیز بنائیں۔ یہ محض ایک مختصر فقرہ نہ ہو بلکہ ایک طویل اور مربوط جملہ ہو جو خبر کی تمام بڑی تفصیلات کو اپنے اندر سمیٹ لے۔\n"
            "۶. تین سی جی (CG) پٹیاں بنائیں اور ہر پٹی میں صرف ۶ سے ۸ الفاظ ہونے چاہئیں۔\n\n"
            "آؤٹ پٹ کا فارمیٹ بالکل اس مثال جیسا ہونا چاہیے:\n\n"
            "او سی (OC=on camera)\n"
            "گوجرانوالہ کی مقامی عدالت میں جمعیت علمائے اسلام کے سربراہ مولانا فضل الرحمان کے خلاف ایک اہم درخواست دائر کر دی گئی ہے۔ درخواست میں مولانا پر فوج کے خلاف متنازع تقریر کا الزام لگایا گیا ہے۔\n\n"
            "وی او (VO= Voice over)\n"
            "گوجرانوالہ میں ایڈووکیٹ قاسم بھٹی کی جانب سے دائر درخواست میں موقف اختیار کیا گیا ہے کہ مولانا فضل الرحمان نے متنازع بیانات دیے۔ ایڈیشنل سیشن جج فضا احمد نے ابتدائی سماعت کے بعد پولیس کو نوٹس جاری کر دیا۔ عدالت نے متعلقہ تھانے کو حکم دیا ہے کہ وہ اٹھائیس جولائی تک تفصیلی رپورٹ جمع کروائیں اور اس معاملے کی مکمل چھان بین کر کے حقائق سامنے لائیں۔\n\n"
            "ہیڈ لائن (Headline)\n"
            "فوج مخالف تقریر پر مولانا فضل الرحمان کے خلاف مقدمے کی درخواست دائر، عدالت نے پولیس سے اٹھائیس جولائی تک رپورٹ طلب کر لی۔\n\n"
            "تین سی جی (CG= Lower Third)\n"
            "- مولانا فضل الرحمان کے خلاف درخواست دائر\n"
            "- فوج مخالف تقریر پر مقدمے کی درخواست\n"
            "- عدالت کا پولیس کو اٹھائیس جولائی تک نوٹس\n\n"
            "-----------------------------------------\n"
            f"اب اس اصل خبر کا پیکیج اوپر دیے گئے طریقے کے مطابق بنائیں:\n\n{text}"
        )
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.0
        )
        
        response = model.generate_content(combined_prompt, generation_config=generation_config)
        return response.text
        
    except Exception as e:
        return f"Gemini API Error: {str(e)}"

# --- 3. THE JOURNALIST WEB INTERFACE ---
st.set_page_config(page_title="EditoFlow News Room App", page_icon="🌐", layout="centered")

st.title("🌐 EditoFlow جرنلسٹ نیوز روم ایپ")
st.write("یہ ایپ کلاؤڈ میں گوگل جیمنائ (Gemini Cloud Engine) پر چل رہی ہے۔")

# Clean Sidebar (No warning, no success boxes, completely clean)
st.sidebar.title("⚙️ ماڈل سیٹنگز")
selected_model = st.sidebar.selectbox(
    "اے آئی ماڈل منتخب کریں:",
    ("gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro")
)
st.sidebar.info("نوٹ: اگر پرو ماڈل ایرر دے، تو فلیش ماڈل استعمال کریں، وہ زیادہ مستحکم ہے۔")

option = st.radio("ان پٹ کا طریقہ منتخب کریں:", ("خبر کا لنک (URL)", "ٹیکسٹ یا ٹکرز پیسٹ کریں"))

if option == "خبر کا لنک (URL)":
    user_input = st.text_input("یہاں خبر کا لنک پیسٹ کریں:")
else:
    user_input = st.text_area("یہاں خبر کا ٹیکسٹ یا ٹکرز پیسٹ کریں:", height=200)

if st.button("پیکیج تیار کریں", type="primary"):
    if not GEMINI_API_KEY:
        st.error("سسٹم فی الحال آف لائن ہے یا کنکشن قائم نہیں ہو سکا۔ برائے مہربانی سیٹنگز چیک کریں۔")
    elif not user_input.strip():
        st.warning("مہربانی فرما کر پہلے کوئی لنک یا ٹیکسٹ لکھیں!")
    else:
        with st.spinner(f"گوگل {selected_model} پیکیج تیار کر رہا ہے..."):
            if option == "خبر کا لنک (URL)":
                content = scrape_article(user_input)
                if content.startswith("Error") or content.startswith("Scraping failed"):
                    st.error(content)
                    st.stop()
            else:
                content = user_input
            
            final_output = summarize_with_gemini(content, selected_model)
            
            st.success("نیوز پیکیج کلاؤڈ سے تیار ہو کر آ گیا ہے!")
            st.divider()
            st.subheader("📰 فائنل براڈکاسٹ ڈیٹا")
            st.text_area("کاپی کرنے کے لیے نیچے سلیکٹ کریں:", value=final_output, height=450)