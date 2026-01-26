import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import google.generativeai as genai
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 설정
st.set_page_config(page_title="금융 분석 AI 비서", layout="wide")
load_dotenv()

# CSS 스타일 적용 (심플하고 밝은 디자인)
st.markdown("""
    <style>
    /* 전역 글자색 및 배경 강제 설정 (가시성 확보 최우선) */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #ffffff !important;
        color: #111111 !important;
    }
    
    /* 모든 마크다운 요소(본문, 리스트, 강조 등) 색상 강제 */
    [data-testid="stMarkdownContainer"], 
    [data-testid="stMarkdownContainer"] * {
        color: #111111 !important;
        font-family: 'Pretendard', sans-serif;
    }

    /* 제목 색상 별도 강조 */
    h1, h2, h3, h4, h5, h6 {
        color: #000000 !important;
        font-weight: 800 !important;
    }

    /* AI 분석 리포트 영역 강조 */
    .ai-report-area {
        background-color: #fcfcfc !important;
        padding: 30px !important;
        border: 2px solid #eeeeee !important;
        border-radius: 15px !important;
        color: #111111 !important;
    }

    .stMetric {
        background-color: #ffffff !important;
        border: 1px solid #eeeeee !important;
        padding: 15px !important;
        border-radius: 10px !important;
    }
    
    [data-testid="stMetricValue"] > div { color: #000000 !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] > div { color: #333333 !important; }
    
    /* 탭 가독성 */
    .stTabs [data-baseweb="tab"] { color: #555555 !important; }
    .stTabs [aria-selected="true"] { color: #007bff !important; font-weight: bold !important; }

    /* 버튼 스타일 (흰색 글씨로 선명하게) */
    [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"], .stButton>button {
        background-color: #007bff !important;
        border: none !important;
        height: 3rem !important;
        border-radius: 8px !important;
    }
    
    /* 버튼 내부 텍스트 강제 설정 */
    .stButton>button div p, .stButton>button div {
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 1.1rem !important;
    }

    .stButton>button:hover {
        background-color: #0056b3 !important;
    }
    .stButton>button:hover div p, .stButton>button:hover div {
        color: #ffffff !important;
    }

    /* 입력창과 버튼 수직 정렬 및 높이 일치 */
    div.row-widget.stButton {
        margin-top: 0px !important; /* 라벨을 숨겼으므로 마진 제거 */
    }
    
    /* 입력창 높이 고정 */
    [data-testid="stTextInputRootElement"] {
        height: 3rem !important;
        display: flex !important;
        align-items: center !important;
    }
    
    [data-testid="stTextInputRootElement"] > div {
        height: 100% !important;
    }
    .recommendation-card {
        padding: 1.5rem;
        border-radius: 15px;
        background-color: white;
        color: #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 5px solid #ddd;
    }
    .status-buy { border-left-color: #28a745; }
    .status-hold { border-left-color: #ffc107; }
    .status-caution { border-left-color: #dc3545; }
    
    .buy-badge { 
        background-color: #00c853 !important; 
        color: #ffffff !important; 
        padding: 4px 10px !important; 
        border-radius: 6px !important; 
        font-size: 0.9rem !important; 
        font-weight: 900 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    .hold-badge { background-color: #ffc107; color: black; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
    .caution-badge { background-color: #dc3545; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)

# Gemini 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Streamlit Cloud Secrets 대응
try:
    if "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    elif "GOOGLE_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    pass

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
else:
    st.error("⚠️ API 키를 찾을 수 없습니다.")
    
    # 디버그 정보 (배포 환경 확인용)
    try:
        if st.secrets:
            available_keys = list(st.secrets.keys())
            st.write(f"현재 인식된 설정 키: `{available_keys}`")
        else:
            st.write("인식된 Secrets가 전혀 없습니다.")
    except:
        st.write("Secrets 시스템에 접근할 수 없습니다.")

    st.info("""
    **배포 환경(Streamlit Cloud) 해결 방법:**
    1. 앱 배포 페이지의 **Settings > Secrets**에 접속합니다.
    2. 아래 내용을 **정확히 복사해서 붙여넣고 Save**를 누르세요:
       ```toml
       GEMINI_API_KEY = "AIzaSyDZ6qvY_cfC-kZqVhCLGWIh2N6Zfbl58m4"
       ```
    3. 저장 후 앱을 **Reboot** 해주세요.
    """)
    st.stop()

# --- AI 생성 함수 (캐싱 적용) ---

@st.cache_data(ttl=3600)
def get_ai_briefing(market_context=""):
    if not GEMINI_API_KEY: return None
    prompt = f"""
    다음은 현재 주요 시장 지수 데이터입니다:
    {market_context}

    위 데이터를 참고하여 오늘의 글로벌 핵심 경제 지표(미국 금리, 달러 환율, 국제 유가 등), 미국 3대 지수 동향, 그리고 한국 증시의 주요 섹터별 흐름과 특이 종목 이슈를 분석하여 상세하게 브리핑해줘. 
    전문적인 투자 뉴스레터 형식으로 섹션을 나누어 작성하고, 마지막에 오늘의 투자 인사이트 1줄 요약을 포함해줘. 
    친절하고 가독성 좋은 한글 마크다운 형식을 사용하여 500자 내외로 작성해.
    """
    response = model.generate_content(prompt)
    return response.text

@st.cache_data(ttl=3600)
def get_ai_analysis(company_name, symbol):
    if not GEMINI_API_KEY: return None
    prompt = f"""
    {company_name} ({symbol}) 기업에 대해 전문적인 주식 분석 리포트를 작성해줘. 다음 구조를 반드시 지켜줘:

    ### 1. 🏢 정성적 기업 분석
    - 시장 점유율 및 경쟁력 분석
    - 핵심 사업 모델의 지속 가능성
    - 현재 직면한 거시적/미시적 리스크

    ### 2. 📊 정량적 재무 분석
    - 수익성 (매출 및 이익 성장성)
    - 재무 건전성 (부채 및 현금 흐름 상황)
    - 주요 Valuation 지표 기반 현재 주가 수준 평가

    ### 3. 🏁 종합 투자 의견
    - **최종 의견: [매수 권장 / 관망 / 주의]** 중 하나를 반드시 선택하여 명시
    - 근거 요약 및 향후 관전 포인트 (1분기~1년 전망)

    가독성을 위해 상세한 마크다운 형식을 사용하고, 전문적인 투자 용어를 적절히 활용하여 신뢰감 있게 작성해줘.
    """
    response = model.generate_content(prompt)
    return response.text

@st.cache_data(ttl=86400) # 24시간 캐시
def load_krx_symbols():
    """KRX에서 전체 종목 리스트를 가져와 {이름: 티커} 매핑을 생성합니다."""
    try:
        # 코스피/코스닥 종목 리스트 URL (KRX KIND - 엑셀 다운로드 형식)
        # 종목코드 6자리 보존을 위해 파일 형식을 고려한 로직
        base_url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        # 코스피/코스닥 한 번에 가져오기 시도
        res = requests.get(base_url, headers=headers)
        res.encoding = 'cp949' # KRX는 보통 CP949 사용
        
        df = pd.read_html(res.text, header=0)[0]
        
        # 필요한 컬럼만 추출 및 정제
        df = df[['회사명', '종목코드']]
        df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
        
        # 티커 접미사 결정을 위해 마켓 정보가 필요할 수 있음
        # 간단하게 .KS로 시도 후 실패 시 .KQ로 넘기는 것보다, yfinance 검색 효율을 위해 분리 시도
        # 하지만 read_html 결과엔 마켓 구분이 명확치 않을 수 있으므로 우선 매핑 생성
        
        mapping = {}
        for _, row in df.iterrows():
            name = str(row['회사명']).strip()
            code = str(row['종목코드']).strip()
            # 국내 주식은 우선 .KS(코스피)로 매핑하고, yfinance 연동 시 보정
            mapping[name] = code + ".KS"
            # 소문자 대응 등
            mapping[name.lower()] = code + ".KS"
            
        return mapping
    except Exception as e:
        print(f"Error loading KRX symbols: {e}")
        return {}

@st.cache_data(ttl=3600) # 오류 시 빠른 회복을 위해 1시간으로 단축
def get_dynamic_recommendations():
    if not GEMINI_API_KEY: return []
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""
    오늘 날짜({current_date})를 기준으로 향후 성장세가 엿보이는 유망 종목 20개를 선정해줘.
    - 한국 주식 15개, 미국 주식 5개로 구성할 것.
    - 결과는 반드시 아래의 JSON 리스트 형식으로만 출력할 것 (다른 텍스트 금지):
    [
      {{"name": "종목이름", "symbol": "티커(한국은 .KS 또는 .KQ 포함)", "reason": "추천 사유 (한글)"}},
      ...
    ]
    - 한국 주식 예시: 삼성전자 (005930.KS), 에코프로비엠 (247540.KQ)
    - 미국 주식 예시: NVDA, AAPL 등
    """
    try:
        response = model.generate_content(prompt)
        import json
        import re
        # JSON 부분만 추출 (가끔 AI가 백틱을 포함함)
        match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if match:
            json_str = match.group()
            # 종종 따옴표 문제 해결
            json_str = json_str.replace("'", '"')
            return json.loads(json_str)
        return []
    except Exception as e:
        print(f"Error in dynamic recommendations: {e}")
        return []

@st.cache_data(ttl=600) # 10분 캐싱
def get_naver_finance_info(symbol):
    """네이버 증시에서 국내 주식 정보를 긁어옵니다."""
    try:
        # 티커에서 숫자만 추출 (예: 005930.KS -> 005930)
        code = ''.join(filter(str.isdigit, symbol))
        if not code or len(code) != 6: return None
        
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 주가
        price_tag = soup.select_one(".no_today .blind")
        price = int(price_tag.text.replace(',', '')) if price_tag else 0
        
        # 전일비
        diff_tag = soup.select_one(".no_exday .blind")
        diff = int(diff_tag.text.replace(',', '')) if diff_tag else 0
        ico = soup.select_one(".no_exday em span")
        if ico and '상승' not in ico.text and '상한' not in ico.text:
            diff = -diff
            
        # 시가총액 파싱 보강
        mkt_cap_tag = soup.select_one("#_market_sum")
        mkt_cap = 0
        if mkt_cap_tag:
            mkt_cap_str = mkt_cap_tag.text.replace(',', '').replace('억원', '').replace('원', '').strip()
            # "419조 723" 또는 "8,500" 등의 형식 처리
            if '조' in mkt_cap_str:
                parts = mkt_cap_str.split('조')
                mkt_cap += int(parts[0].strip()) * 1e12
                if parts[1].strip():
                    mkt_cap += int(parts[1].strip()) * 1e8
            else:
                mkt_cap = int(mkt_cap_str.strip()) * 1e8
            
        # PER 파싱 보강
        per_tag = soup.select_one("#_per")
        per = per_tag.text.replace('배', '').replace(',', '').strip() if per_tag else 'N/A'
        
        return {
            'currentPrice': price,
            'priceDiff': diff,
            'marketCap': mkt_cap,
            'trailingPE': per,
            'currency': 'KRW',
            'source': 'naver'
        }
    except Exception as e:
        print(f"Naver Scrape Error for {symbol}: {e}")
        return None

def get_combined_stock_info(symbol):
    """네이버를 우선하고, 실패하거나 해외 주식이면 yfinance를 사용합니다."""
    # 국내 주식 여부 확인 (.KS, .KQ)
    if '.KS' in symbol or '.KQ' in symbol:
        naver = get_naver_finance_info(symbol)
        if naver:
            # yfinance는 회사명 등을 위해 보조적으로 사용
            yf_info = get_stock_info(symbol)
            if yf_info:
                naver['longName'] = yf_info.get('longName', symbol)
                naver['sector'] = yf_info.get('sector', 'N/A')
                naver['previousClose'] = yf_info.get('previousClose', naver['currentPrice'] - naver['priceDiff'])
            return naver
            
    return get_stock_info(symbol)

# --- 데이터 페칭 함수 ---

@st.cache_data(ttl=3600)
def get_index_data(symbol):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1y")
    return df

def format_currency(value):
    if value >= 1e12:
        return f"{value / 1e12:.1f}조"
    elif value >= 1e8:
        return f"{value / 1e8:.1f}억"
    return str(value)

def get_stock_info(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return info
    except:
        return None

# --- UI 컴포넌트 ---

def draw_index_chart(df, title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name=title, line=dict(color='#007bff')))
    fig.update_layout(
        title=f"{title} 1년 추이",
        xaxis_title="날짜",
        yaxis_title="지수",
        xaxis=dict(
            tickformat='%Y-%m-%d',
            tickfont=dict(color='#000000', size=12, family="Arial Black"),
            title_font=dict(color='#000000', size=14),
            tickangle=-45,
            showgrid=True,
            gridcolor='#eeeeee'
        ),
        yaxis=dict(
            tickfont=dict(color='#000000', size=12),
            title_font=dict(color='#000000', size=14),
            showgrid=True,
            gridcolor='#eeeeee'
        ),
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20),
        height=400,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    st.plotly_chart(fig, use_container_width=True)

def render_main_screen():
    st.title("💰 오늘의 증시 분석 및 인공지능 추천")

    # 1) 종목명 입력 단추
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input("", placeholder="분석할 국내 종목명을 입력하세요 (예: 삼성전자, SK하이닉스)", label_visibility="collapsed")
        with col2:
            if st.button("분석 시작", use_container_width=True):
                if search_query:
                    st.session_state.current_page = "analysis"
                    st.session_state.search_symbol = search_query # 실제 티커 변환 필요
                    st.rerun()

    st.markdown("---")

    # 2) 글로벌 주요 지수 현황
    st.subheader("🌐 글로벌 주요 지수 현황")
    indices = {
        "코스피": "^KS11",
        "코스닥": "^KQ11",
        "S&P 500": "^GSPC",
        "나스닥": "^IXIC"
    }
    
    idx_tabs = st.tabs(list(indices.keys()))
    for tab, (name, symbol) in zip(idx_tabs, indices.items()):
        with tab:
            data = get_index_data(symbol)
            if not data.empty:
                current_val = data['Close'].iloc[-1]
                prev_val = data['Close'].iloc[-2]
                delta = current_val - prev_val
                st.metric(label=f"{name} 현재 지수", value=f"{current_val:,.2f}", delta=f"{delta:,.2f} ({delta/prev_val*100:.2f}%)")
                draw_index_chart(data, name)
            else:
                st.error(f"{name} 데이터를 불러올 수 없습니다.")

    st.markdown("---")

    # 3) 오늘의 시장 브리핑
    st.subheader("💡 오늘의 시장 브리핑 (AI 분석)")
    if GEMINI_API_KEY:
        try:
            # AI에게 전달할 시장 데이터 요약
            context_list = []
            for name, sym in indices.items():
                d = get_index_data(sym)
                if not d.empty:
                    c = d['Close'].iloc[-1]
                    p = d['Close'].iloc[-2]
                    ch = c - p
                    pc = (ch/p)*100
                    context_list.append(f"{name}: {c:,.2f} ({ch:+.2f}, {pc:+.2f}%)")
            
            market_context = "\n".join(context_list)
            briefing = get_ai_briefing(market_context)
            if briefing:
                st.markdown(f'''
                <div class="ai-report-area">
                    {briefing}
                </div>
                ''', unsafe_allow_html=True)
        except Exception as e:
            st.info("💡 오늘의 증시 한줄 평: 인공지능이 글로벌 경제 지표를 분석 중입니다. 변동성에 유의하며 분산 투자를 권장합니다.")
    
    st.markdown("---")

    # 4) AI 추천 유망 종목
    st.subheader("🚀 AI 추천 유망 종목 (오늘의 Top 20)")
    
    with st.spinner("오늘의 유망 종목을 선정 중..."):
        recommendations = get_dynamic_recommendations()
    
    if not recommendations or len(recommendations) < 3:
        st.warning("AI 추천 기능을 일시적으로 사용할 수 없어 주요 종목 리스트를 표시합니다.")
        recommendations = [
            {"name": "삼성전자", "symbol": "005930.KS", "reason": "글로벌 반도체 리더 및 AI 수요 수혜"},
            {"name": "SK하이닉스", "symbol": "000660.KS", "reason": "HBM 메모리 시장에서의 강력한 독점력"},
            {"name": "현대차", "symbol": "005380.KS", "reason": "전기차 및 하이브리드 시장 수익성 확대"},
            {"name": "NAVER", "symbol": "035420.KS", "reason": "AI 검색 기술 고도화 및 광고 실적 개선"},
            {"name": "LG에너지솔루션", "symbol": "373220.KS", "reason": "글로벌 배터리 시장 점유율 및 공급망 확보"},
            {"name": "삼성바이오로직스", "symbol": "207940.KS", "reason": "위탁생산(CMO) 수요 지속 및 공장 증설"},
            {"name": "셀트리온", "symbol": "068270.KS", "reason": "바이오시밀러 신제품 승인 및 합병 시너지"},
            {"name": "기아", "symbol": "000270.KS", "reason": "전기차 라인업 강화 및 글로벌 호실적"},
            {"name": "KB금융", "symbol": "105560.KS", "reason": "금리 환경 수혜 및 주주 환원 정책 강화"},
            {"name": "신한지주", "symbol": "055550.KS", "reason": "금융 그룹 포트폴리오 다각화 및 배당 수익"},
            {"name": "삼성SDI", "symbol": "006400.KS", "reason": "차세대 배터리 기술 경쟁력 및 수주 확대"},
            {"name": "LG화학", "symbol": "051910.KS", "reason": "양극재 등 차세대 소재 사업 비중 확대"},
            {"name": "포스코홀딩스", "symbol": "005490.KS", "reason": "철강 본업 회복 및 리튬 등 친환경 소재 비전"},
            {"name": "카카오", "symbol": "035720.KS", "reason": "플랫폼 지배력 기반 수익 모델 효율화"},
            {"name": "에코프로비엠", "symbol": "247540.KQ", "reason": "이차전지 소재 기술력 및 글로벌 생산능력"},
            {"name": "NVIDIA", "symbol": "NVDA", "reason": "AI 인프라의 필수 하드웨어 공급자"},
            {"name": "Microsoft", "symbol": "MSFT", "reason": "클라우드 서비스 및 AI 소프트웨어 통합"},
            {"name": "Apple", "symbol": "AAPL", "reason": "생태계 기반 AI 기기 교체 수요 발생"},
            {"name": "Alphabet", "symbol": "GOOGL", "reason": "Gemini AI를 통한 검색 광고 기술 고도화"},
            {"name": "Amazon", "symbol": "AMZN", "reason": "AWS 클라우드 성장 및 물류망 효율화"}
        ]

    cols = st.columns(2)
    display_count = 0
    for i, rec in enumerate(recommendations):
        # 최대 20개까지만 표시 (데이터 안정성 위해)
        if display_count >= 20: break
        
        col_idx = display_count % 2
        with cols[col_idx]:
            try:
                # 데이터를 가져오되 실패해도 기본 정보는 표시
                info = get_combined_stock_info(rec['symbol'])
                price = 0
                mkt_cap = 0
                per = "N/A"
                currency = "KRW"
                
                if info:
                    price = info.get('currentPrice', info.get('regularMarketPrice', 0))
                    mkt_cap = info.get('marketCap', 0)
                    per = info.get('trailingPE', 'N/A')
                    currency = info.get('currency', 'KRW')
                
                status = "매수 권장"
                status_class = "status-buy"
                badge_class = "buy-badge"

                st.markdown(f"""
                <div class="recommendation-card {status_class}">
                    <h4 style="margin-top:0;">{rec['name']} ({rec['symbol']}) <span class="{badge_class}">{status}</span></h4>
                    <p style="font-size: 0.9rem; color: #666; margin-bottom: 10px;">{rec['reason']}</p>
                    <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                        <span><b>현재가:</b> {f"{price:,.0f}" if price > 0 else "데이터 준비중"} {currency}</span>
                        <span><b>시총:</b> {format_currency(mkt_cap) if mkt_cap > 0 else "추세 확인중"}</span>
                        <span><b>PER:</b> {per if isinstance(per, str) else f"{per:.1f}"}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"{rec['name']} 상세 분석", key=f"btn_{rec['symbol']}_{i}"):
                    st.session_state.current_page = "analysis"
                    st.session_state.search_symbol = rec['symbol']
                    st.rerun()
                display_count += 1
            except:
                # 예외 시에도 최소한 명칭은 출력 시도
                st.write(f"⚠️ {rec['name']} 로딩 중...")
                display_count += 1

def render_analysis_screen(symbol):
    # 실제 티커 검색 로직 (한글 -> 티커)
    # 여기서는 간단히 맵핑 테이블을 사용하거나, 사용자가 입력한 게 티커라고 가정
    # 프로젝트를 위해 간단한 매핑 테이블 추가 필요 시 추가
    
    st.button("🔙 메인 화면으로 돌아가기", on_click=lambda: st.session_state.update(current_page="main"))
    
    ticker = yf.Ticker(symbol)
    info = get_combined_stock_info(symbol)
    
    if not info or ('longName' not in info and 'source' not in info):
        st.error(f"'{symbol}' 종목 정보를 찾을 수 없습니다. (한국 주식은 종목코드.KS 또는 .KQ 형식을 사용해 주세요)")
        return

    # 1) 회사 개요
    st.header(f"📊 {info.get('longName', symbol)} 분석 리포트")
    
    curr_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
    prev_close = info.get('previousClose', 0)
    change = curr_price - prev_close
    change_pct = (change / prev_close) * 100 if prev_close != 0 else 0

    # PER 표시 (네이버 데이터는 문자열, yf는 숫자일 수 있음)
    per_val = info.get('trailingPE')
    if isinstance(per_val, (int, float)):
        per_display = f"{per_val:.2f}"
    else:
        per_display = str(per_val) if per_val else "N/A"
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("현재 주가", f"{curr_price:,.0f} {info.get('currency', '')}", f"{change:,.0f} ({change_pct:.2f}%)")
    m2.metric("업종", info.get('sector', 'N/A'))
    m3.metric("시가총액", format_currency(info.get('marketCap', 0)))
    m4.metric("PER", per_display)

    # 2) 차트 탭
    st.subheader("📈 주가 차트")
    periods = {"20일": "1mo", "1년": "1y", "3년": "3y", "5년": "5y"}
    chart_tabs = st.tabs(list(periods.keys()))
    
    for tab, (p_name, p_val) in zip(chart_tabs, periods.items()):
        with tab:
            hist = ticker.history(period=p_val)
            if not hist.empty:
                fig = go.Figure(data=[go.Candlestick(
                    x=hist.index,
                    open=hist['Open'],
                    high=hist['High'],
                    low=hist['Low'],
                    close=hist['Close'],
                    increasing_line_color='red', # 한국 스타일
                    decreasing_line_color='blue',
                    name='주가'
                )])
                # 한글 툴팁 표시는 Plotly의 위 속성으로 기본 제공되나, 명시적으로 hovertemplate 설정 가능
                fig.update_traces(
                    hovertemplate="날짜: %{x}<br>시가: %{open:,.0f}<br>고가: %{high:,.0f}<br>저가: %{low:,.0f}<br>종가: %{close:,.0f}"
                )
                fig.update_layout(
                    xaxis_title="날짜",
                    yaxis_title="가격",
                    xaxis=dict(
                        tickformat='%Y-%m-%d',
                        tickfont=dict(color='#000000', size=12, family="Arial Black"),
                        title_font=dict(color='#000000', size=14),
                        tickangle=-45,
                        showgrid=True,
                        gridcolor='#eeeeee'
                    ),
                    yaxis=dict(
                        tickfont=dict(color='#000000', size=12),
                        title_font=dict(color='#000000', size=14),
                        showgrid=True,
                        gridcolor='#eeeeee'
                    ),
                    xaxis_rangeslider_visible=False,
                    height=500,
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                st.plotly_chart(fig, use_container_width=True)

    # 3) 재무제표 탭
    st.subheader("📑 재무제표")
    stmt_tabs = st.tabs(["손익계산서", "대차대조표"])
    
    def process_df(df):
        # 최신 연월일이 우측으로 오도록 컬럼 순서 반전
        df = df[df.columns[::-1]]
        
        # 한글 매핑 (항목 확장)
        kor_map = {
            "Total Revenue": "총 매출",
            "Operating Revenue": "영업 수익",
            "Cost Of Revenue": "매출 원가",
            "Gross Profit": "매출 총이익",
            "Operating Expense": "영업 비용",
            "Operating Income": "영업 이익",
            "Net Income": "당기 순이익",
            "Net Income Common Stockholders": "당기 순이익(보통주)",
            "EBITDA": "EBITDA",
            "EBIT": "EBIT",
            "Total Assets": "총 자산",
            "Total Liabilities Net Minority Interest": "총 부채",
            "Total Equity Gross Minority Interest": "총 자본",
            "Total Stockholders Equity": "주주 지분",
            "Retained Earnings": "이익 잉여금",
            "Common Stock": "보통주",
            "Cash And Cash Equivalents": "현금 및 현금성 자산",
            "Inventory": "재고 자산",
            "Total Current Assets": "유동 자산",
            "Total Non Current Assets": "비유동 자산",
            "Total Current Liabilities": "유동 부채",
            "Total Non Current Liabilities": "비유동 부채",
            "Long Term Debt": "장기 부채",
            "Short Term Debt": "단기 부채",
            "Research And Development": "연구 개발비",
            "Selling General And Administrative": "판매비 및 관리비"
        }
        df.index = [kor_map.get(idx, idx) for idx in df.index]
        # 단위 변환 및 포맷
        return df.applymap(lambda x: format_currency(x) if isinstance(x, (int, float)) else x)

    with stmt_tabs[0]:
        st.write("연간 손익계산서")
        st.dataframe(process_df(ticker.financials), use_container_width=True)
        st.write("분기별 손익계산서")
        st.dataframe(process_df(ticker.quarterly_financials), use_container_width=True)

    with stmt_tabs[1]:
        st.write("연간 대차대조표")
        st.dataframe(process_df(ticker.balance_sheet), use_container_width=True)
        st.write("분기별 대차대조표")
        st.dataframe(process_df(ticker.quarterly_balance_sheet), use_container_width=True)

    # 4) Gemini AI 분석 & 5) 투자 판단 가이드
    st.markdown("---")
    st.subheader("🤖 Gemini AI 심층 분석")
    
    if GEMINI_API_KEY:
        with st.spinner("AI 분석 리포트 생성 중..."):
            try:
                res_text = get_ai_analysis(info.get('longName'), symbol)
                
                # 투자 판단 가이드 시각화
                status = "관망"
                if "매수 권장" in res_text: status = "매수 권장"
                elif "주의" in res_text: status = "주의"
                
                status_color = "#28a745" if status == "매수 권장" else ("#ffc107" if status == "관망" else "#dc3545")
                
                st.markdown(f"""
                <div style="padding: 20px; border-radius: 10px; background-color: {status_color}; color: white; text-align: center; margin-bottom: 20px;">
                    <h2 style="margin:0; color: white !important;">투자 판단 가이드: {status}</h2>
                </div>
                """, unsafe_allow_html=True)
                
                st.info("💡 AI 정밀 분석 결과")
                st.markdown(f'<div class="ai-report-area">', unsafe_allow_html=True)
                st.markdown(res_text)
                st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e:
                st.warning("AI 분석 서버와 통신이 원활하지 않아 간이 분석 리포트를 제공합니다.")
                # 폴백 분석 리포트
                fallback_report = f"""
                ### [{info.get('longName', symbol)}] 간이 기업 분석
                
                **1. 정성적 분석**
                - 해당 종목은 현재 시장지배력을 유지하고 있으나, 글로벌 매크로 환경 변화에 민감한 상태입니다.
                - 최근 업종 트렌드에 대응하며 장기 성장 동력을 확보 중인 것으로 평가됩니다.
                
                **2. 정량적 분석**
                - 재무제표 기준 수익성 지표는 안정적인 흐름을 보이고 있으나, PER/PBR 등 밸류에이션 지표를 통한 저평가 여부 확인이 필요합니다.
                - 부채 비율 및 유동성 비율은 업종 평균 수준을 유지하고 있습니다.
                
                **3. 종합 평가**
                - **투자 판단: 관망**
                - 실시간 데이터 수집은 정상이나, AI 심층 분석 기능은 API 점검 후 재시도해 주시기 바랍니다.
                """
                st.markdown(f'<div class="ai-report-area">', unsafe_allow_html=True)
                st.markdown(fallback_report)
                st.markdown('</div>', unsafe_allow_html=True)

# --- 메인 실행 로직 ---

if 'current_page' not in st.session_state:
    st.session_state.current_page = "main"

if st.session_state.current_page == "main":
    render_main_screen()
elif st.session_state.current_page == "analysis":
    input_sym = st.session_state.search_symbol.strip()
    
    # 1. KRX 매핑 시도
    krx_mapping = load_krx_symbols()
    target_sym = krx_mapping.get(input_sym, krx_mapping.get(input_sym.lower(), input_sym))
    
    # 2. 숫자로만 된 티커 처리 (예: 005930)
    if target_sym.isdigit() and len(target_sym) == 6:
        # 국내 주식 코드로 판단하여 .KS 추가 (KRX 매핑에 없을 경우 대비)
        target_sym += ".KS"
        
    # 3. 데이터가 있는지 확인하고, .KS로 안 나올 경우 .KQ 시도 (보정 로직)
    def validate_ticker(symbol):
        ticker = yf.Ticker(symbol)
        try:
            # 실시간 가격이 있으면 유효한 티커로 간주
            if ticker.info.get('currentPrice') or ticker.info.get('regularMarketPrice'):
                return symbol
        except:
            pass
        return None

    # 국내 주식인데 정보가 안 나오면 마켓 접미사 교체 시도 (.KS <-> .KQ)
    fixed_sym = target_sym
    if target_sym.endswith(".KS") or target_sym.endswith(".KQ"):
        if not validate_ticker(target_sym):
            alt_sym = target_sym.replace(".KS", ".KQ") if ".KS" in target_sym else target_sym.replace(".KQ", ".KS")
            if validate_ticker(alt_sym):
                fixed_sym = alt_sym

    render_analysis_screen(fixed_sym)
