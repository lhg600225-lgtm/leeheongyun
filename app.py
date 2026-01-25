import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import google.generativeai as genai
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Page setting
st.set_page_config(page_title="금융 데이터 분석 AI", layout="wide", initial_sidebar_state="collapsed")

# Simple & Bright Style
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff !important;
        border: 1px solid #dee2e6;
        padding: 10px;
        border-radius: 8px;
    }
    [data-testid="stMetricValue"] {
        color: #000000 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #333333 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .status-card {
        padding: 20px;
        border-radius: 10px;
        color: white;
        font-weight: bold;
        text-align: center;
        margin-bottom: 20px;
    }
    .recommend-box {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin-bottom: 10px;
        color: #333;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .metric-row {
        display: flex;
        justify-content: space-between;
        font-size: 0.85em;
        margin-top: 6px;
        color: #666;
    }
    .recommend-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 5px;
    }
    .recommend-name {
        font-size: 1.1em;
        font-weight: bold;
        color: #1f1f1f;
    }
    .recommend-price {
        font-size: 1.05em;
        font-weight: 700;
        text-align: right;
    }
    .status-badge {
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: 600;
        color: white;
        margin-left: 8px;
    }
    .badge-buy { background-color: #28a745; }
    .badge-wait { background-color: #ffc107; color: black; }
    .badge-watch { background-color: #dc3545; }

    /* Index Card Enhancement */
    .index-card {
        padding: 5px 10px;
        text-align: center;
        background-color: transparent;
        border: none;
    }
    .index-up {
        background-color: #fff5f5;
        border-left: 5px solid #e03131;
    }
    .index-down {
        background-color: #f3f8ff;
        border-left: 5px solid #1971c2;
    }
    .index-name {
        font-size: 1.25em;
        font-weight: 800;
        color: #212529;
        margin-bottom: 5px;
    }
    .index-value {
        font-size: 1.5em;
        font-weight: 800;
        margin-bottom: 2px;
    }
    .index-delta-up {
        color: #e03131;
        font-weight: 600;
        font-size: 1em;
    }
    .index-delta-down {
        color: #1971c2;
        font-weight: 600;
        font-size: 1em;
    }
    .sparkline-container {
        margin-top: 10px;
        height: 100px;
    }
    </style>
    """, unsafe_allow_html=True)

# Helper Functions
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return stock, info
    except Exception as e:
        return None, None

def format_ticker(query):
    query = query.strip().upper()
    common_mapping = {
        "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "카카오": "035720.KS",
        "NAVER": "035420.KS", "네이버": "035420.KS", "현대차": "005380.KS",
        "LG에너지솔루션": "373220.KS", "엔비디아": "NVDA", "애플": "AAPL",
        "테슬라": "TSLA", "마이크로소프트": "MSFT", "구글": "GOOGL"
    }
    if query in common_mapping:
        return common_mapping[query]
    if query.isdigit() and len(query) == 6:
        return query + ".KS"
    if "." in query and any(query.endswith(ext) for ext in [".KS", ".KQ"]):
        return query
    try:
        search = yf.Search(query, max_results=5)
        if hasattr(search, 'quotes') and search.quotes:
            for quote in search.quotes:
                symbol = quote.get('symbol', '')
                if symbol.endswith(".KS") or symbol.endswith(".KQ"):
                    return symbol
            return search.quotes[0].get('symbol', query)
    except:
        pass
    return query

def format_market_cap(val):
    if not val or not isinstance(val, (int, float)):
        return "정보 없음"
    if val >= 1e12: return f"{val / 1e12:,.1f}조"
    elif val >= 1e8: return f"{val / 1e8:,.0f}억"
    return f"{val:,.0f}"

def create_sparkline(history_data, color):
    """Creates a small sparkline chart using Plotly."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=history_data.index,
        y=history_data['Close'],
        mode='lines',
        line=dict(color=color, width=2),
        fill='tozeroy',
        fillcolor=f"rgba({224 if color=='#e03131' else 25}, {49 if color=='#e03131' else 113}, {49 if color=='#e03131' else 194}, 0.1)",
        hoverinfo='none'
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=100,
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        paper_bgcolor='white',
        plot_bgcolor='white',
    )
    return fig

# Gemini AI Setup
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.sidebar.warning("Gemini API 키가 설정되지 않았습니다. Streamlit Cloud의 Secrets나 .env 파일에 GOOGLE_API_KEY를 등록해주세요.")

# Sidebar Utilities
with st.sidebar:
    st.title("🛠️ 설정 및 도구")
    if st.button("🔄 캐시 지우기 및 새로고침"):
        st.cache_data.clear()
        st.success("캐시가 삭제되었습니다!")
        st.rerun()
    st.divider()
    st.info("""
    **할당량 초과 문제 해결 안내:**
    1. '캐시 지우기' 버튼을 클릭해 보세요.
    2. Streamlit Cloud의 Dashboard -> Settings -> Secrets에 API 키가 정확히 입력되었는지 확인하세요.
    3. 무료 API 키는 분당 요청 제한이 엄격합니다.
    """)

def get_ai_analysis(ticker, info):
    if not api_key:
        return "⚠️ **API 키가 설정되지 않았습니다.**\n\n측면 바의 안내를 확인하여 Gemini API 키를 설정해주세요."

    st.markdown("""
        <style>
        .ai-report h1, .ai-report h2 { font-size: 1.25rem !important; margin-top: 10px; margin-bottom: 5px; }
        .ai-report h3 { font-size: 1.1rem !important; }
        .ai-report p, .ai-report li { font-size: 0.95rem; line-height: 1.5; }
        </style>
    """, unsafe_allow_html=True)
    
    last_error = ""
    for model_name in ['gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro']:
        try:
            model = genai.GenerativeModel(model_name)
            prompt = f"주식 분석 대상: {ticker} ({info.get('longName', ticker)})\n기업 요약: {info.get('longBusinessSummary', '정보 없음')}\n위 데이터를 바탕으로 한국어로 전문적인 투자 분석 보고서를 작성해줘:\n1. 정성적 분석 (시장 경쟁력, 주요 리스크)\n2. 정량적 분석 (수익성 지표, 재무 지표 기반 건전성)\n3. 종합 투자 의견: '매수 권장', '관망', '주의' 중 하나를 선택하고 명확한 근거 제시.\n※ 주의사항: 가독성을 위해 큰 제목(#) 대신 중간 제목(###)만 사용하여 내용을 구조화해줘."
            response = model.generate_content(prompt)
            return f'<div class="ai-report">{response.text}</div>'
        except Exception as e:
            last_error = str(e)
            if "429" in last_error:
                continue # 다음 모델 시도
            elif "404" in last_error:
                continue # 모델이 없는 경우 다음 모델 시도
            break # 다른 심각한 에러는 중단
    
    if "429" in last_error:
        return "⚠️ **AI 서비스 할당량이 일시적으로 초과되었습니다.** 무료 버전 제한으로 인해 빈번한 요청이 거부될 수 있습니다. 잠시 후 다시 시도하거나 API 키 설정을 확인해 주세요."
    return f"AI 분석 생성 실패: {last_error}"

@st.cache_data(ttl=600)
def get_market_briefing_v2(index_info):
    if not api_key: return "지수 정보를 통해 분석할 AI 키가 없습니다."
    if "{} " in index_info or index_info == "{}":
        return "현재 지수 데이터를 불러오는 데 실패하여 브리핑을 생성할 수 없습니다."
        
    last_error = ""
    for model_name in ['gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro']:
        try:
            model = genai.GenerativeModel(model_name)
            prompt = f"다음 글로벌 지수 데이터를 바탕으로 현재 시장 상황 및 전망을 3문장 이내의 아주 전문적인 한국어로 요약해줘: {index_info}"
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = str(e)
            if "429" in last_error:
                continue
            if "404" in last_error:
                continue
            break
            
    if "429" in last_error:
        raise Exception("AI 서비스 할당량 초과")
    raise Exception(last_error or "사용 가능한 Gemini 모델을 찾을 수 없습니다.")

# Session State Initialization
if 'current_ticker' not in st.session_state:
    st.session_state['current_ticker'] = "삼성전자"
if 'ticker_history' not in st.session_state:
    st.session_state['ticker_history'] = []
if 'show_analysis' not in st.session_state:
    st.session_state['show_analysis'] = False

# Main UI
st.title("🛡️ 실시간 AI 주식 분석기 v2.8")

# Search Bar Area
col_search1, col_search2, col_search3 = st.columns([3, 1, 1])
with col_search1:
    user_input = st.text_input("종목명 또는 티커(코드) 입력 (예: 삼성전자, AAPL, 005930)", value=st.session_state['current_ticker'] if st.session_state['show_analysis'] else "", key="main_search")

with col_search2:
    if st.button("분석하기", use_container_width=True):
        input_val = st.session_state.main_search.strip()
        if input_val:
            if st.session_state['show_analysis'] and input_val != st.session_state['current_ticker']:
                st.session_state['ticker_history'].append(st.session_state['current_ticker'])
            st.session_state['current_ticker'] = input_val
            st.session_state['show_analysis'] = True
            st.rerun()

with col_search3:
    if st.button("⬅️ 되돌리기", use_container_width=True):
        if len(st.session_state['ticker_history']) > 0:
            prev = st.session_state['ticker_history'].pop()
            st.session_state['current_ticker'] = prev
            st.session_state['show_analysis'] = True
        else:
            st.session_state['show_analysis'] = False
        st.rerun()

st.divider()

# --- Conditional Rendering ---
if not st.session_state['show_analysis']:
    # --- Home Screen ---
    st.write("### 🌍 글로벌 주요 지수 현황 (최근 1년 추이)")
    indices = {"코스피": "^KS11", "코스닥": "^KQ11", "S&P 500": "^GSPC", "나스닥": "^IXIC"}
    idx_cols = st.columns(4)
    index_summary_data = {}

    for (name, symbol), col in zip(indices.items(), idx_cols):
        try:
            t_obj = yf.Ticker(symbol)
            # Fetch 1 year for the chart and 2 days for the change percent
            idx_hist_1y = t_obj.history(period="1y")
            if not idx_hist_1y.empty and len(idx_hist_1y) >= 2:
                cv = idx_hist_1y['Close'].iloc[-1]
                pv = idx_hist_1y['Close'].iloc[-2]
                dv = cv - pv
                dp = (dv / pv) * 100
                
                card_class = "index-up" if dv >= 0 else "index-down"
                delta_class = "index-delta-up" if dv >= 0 else "index-delta-down"
                arrow = "▲" if dv >= 0 else "▼"
                color = "#e03131" if dv >= 0 else "#1971c2"
                
                with col:
                    # 하나의 테두리 박스 안에 수치와 차트를 통합
                    with st.container(border=True):
                        # 배경색을 흰색으로 통일
                        bg_color = "#ffffff"
                        st.markdown(f"""
                        <div class="index-card" style="background-color: {bg_color}; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid {color};">
                            <div class="index-name">{name}</div>
                            <div class="index-value" style="color: #212529;">{cv:,.2f}</div>
                            <div class="{delta_class}">{arrow} {abs(dv):,.2f} ({dp:+.2f}%)</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        spark_fig = create_sparkline(idx_hist_1y, color)
                        st.plotly_chart(spark_fig, use_container_width=True, config={'displayModeBar': False})
                
                index_summary_data[name] = f"{cv:,.2f} ({dp:+.2f}%)"
            else:
                curr_p = t_obj.info.get('regularMarketPrice', 0)
                col.markdown(f'<div class="index-card">{name}<br><b>{curr_p:,.2f}</b><br><small>데이터 대기 중</small></div>', unsafe_allow_html=True)
        except: col.write(f"{name} 로딩 실패")

    with st.spinner("AI 시장 브리핑 생성 중..."):
        try:
            briefing = get_market_briefing_v2(str(index_summary_data))
            st.info(f"📊 **AI 시장 브리핑:** {briefing}")
        except Exception as e:
            if "할당량 초과" in str(e):
                st.warning("📊 **AI 시장 브리핑:** ⚠️ AI 서비스 할당량이 일시적으로 초과되었습니다. 무료 버전 제한으로 인해 잠시 후 다시 시도해 주세요.")
            else:
                st.error(f"📊 **AI 시장 브리핑:** 브리핑을 생성할 수 없습니다. ({str(e)})")
    st.divider()

    @st.cache_data(ttl=3600)
    def get_recommendation_details_v4(stock_list):
        updated_list = []
        for item in stock_list:
            try:
                s_obj = yf.Ticker(item['code'])
                inf = s_obj.info
                p = inf.get('currentPrice', inf.get('regularMarketPreviousClose', 0))
                c = inf.get('regularMarketChangePercent', 0)
                cur = inf.get('currency', '')
                m_cap = inf.get('marketCap', 0)
                pe = inf.get('trailingPE', 0)
                div = inf.get('forwardDividendYield', 0)
                
                status = item.get('status', '관망')
                badge_class = 'badge-buy' if '매수' in status else 'badge-watch' if '주의' in status else 'badge-wait'

                updated_list.append({
                    **item, 
                    'price': f"{p:,.2f} {cur}" if cur != "KRW" else f"{p:,.0f}원", 
                    'change': f"{c:+.2f}%", 'color': '#e03131' if c >= 0 else '#1971c2',
                    'market_cap': format_market_cap(m_cap), 'pe': f"{pe:.1f}" if pe else "N/A", 'div_yield': f"{div*100:.1f}%" if div else "0.0%",
                    'badge_class': badge_class
                })
            except: updated_list.append({**item, 'change': '-', 'color': 'black', 'market_cap': "정보 없음", 'pe': "N/A", 'div_yield': "0.0%", 'badge_class': 'badge-wait', 'price': '-'})
        return updated_list

    kr_base = [
        {"name": "삼성전자", "code": "005930.KS", "reason": "AI 반도체 수요 및 HBM 공급 가시화", "status": "매수 권장"},
        {"name": "SK하이닉스", "code": "000660.KS", "reason": "D램 가격 상승 및 메모리 리더십 유지", "status": "매수 권장"},
        {"name": "LG에너지솔루션", "code": "373220.KS", "reason": "IRA 보조금 혜택 및 전기차 시장 회복", "status": "관망"},
        {"name": "삼성바이오로직스", "code": "207940.KS", "reason": "안정적 수주 확보 및 CMO 지배력", "status": "매수 권장"},
        {"name": "현대차", "code": "005380.KS", "reason": "하이브리드 판매 호조 및 주주환원 강화", "status": "매수 권장"},
        {"name": "NAVER", "code": "035420.KS", "reason": "생성형 AI '하이퍼클로바X' 성과 본격화", "status": "관망"},
        {"name": "셀트리온", "code": "068270.KS", "reason": "합병 시너지 및 미국 매출 확대 기대", "status": "관망"},
        {"name": "기아", "code": "000270.KS", "reason": "역대급 실적 기반 고배당 매력 상승", "status": "매수 권장"},
        {"name": "POSCO홀딩스", "code": "005490.KS", "reason": "이차전지 소재 사업 장기 성장 동력", "status": "주의"},
        {"name": "KB금융", "code": "105560.KS", "reason": "밸류업 프로그램 수혜 및 이익 방어력", "status": "매수 권장"}
    ]
    us_base = [
        {"name": "NVIDIA", "code": "NVDA", "reason": "AI 칩 시장 독점 및 높은 수익성 유지", "status": "매수 권장"},
        {"name": "Microsoft", "code": "MSFT", "reason": "Cloud와 AI 결합 시너지 지속", "status": "매수 권장"},
        {"name": "Apple", "code": "AAPL", "reason": "강력한 현금흐름 및 AI 아이폰 기대", "status": "매수 권장"},
        {"name": "Alphabet", "code": "GOOGL", "reason": "클라우드 성장 가속 및 광고 지배력", "status": "관망"},
        {"name": "Amazon", "code": "AMZN", "reason": "AWS 성과 회복 및 물류 효율화", "status": "매수 권장"},
        {"name": "Meta", "code": "META", "reason": "AI 기반 콘텐츠 추천 및 광고 효율 증가", "status": "매수 권장"},
        {"name": "Tesla", "code": "TSLA", "reason": "자율주행 기술 진보 및 에너지 사업 성장", "status": "주의"},
        {"name": "Eli Lilly", "code": "LLY", "reason": "비만 치료제 시장 폭발적 수요 지배", "status": "매수 권장"},
        {"name": "Broadcom", "code": "AVGO", "reason": "AI 네트워킹 수요 및 VMWare 시너지", "status": "매수 권장"},
        {"name": "Costco", "code": "COST", "reason": "강력한 고객 충성도 기반 방어주 매력", "status": "매수 권장"}
    ]

    with st.spinner("최신 추천주 데이터를 불러오는 중입니다..."):
        kr_recommends = get_recommendation_details_v4(kr_base)
        us_recommends = get_recommendation_details_v4(us_base)

    rec_col1, rec_col2 = st.columns(2)
    for title, recoms, col in [("#### 🇰🇷 국내 유망 종목 TOP 10", kr_recommends, rec_col1), ("#### 🇺🇸 미국 유망 종목 TOP 10", us_recommends, rec_col2)]:
        with col:
            st.write(title)
            for s_item in recoms:
                with st.container():
                    st.markdown(f"""
                    <div class="recommend-box">
                        <div class="recommend-header">
                            <div class="recommend-name">
                                {s_item["name"]} <small style="color:#888; font-weight:normal;">{s_item["code"]}</small>
                                <span class="status-badge {s_item['badge_class']}">{s_item['status']}</span>
                            </div>
                            <div class="recommend-price" style="color:{s_item['color']};">
                                {s_item["price"]} <small>{s_item["change"]}</small>
                            </div>
                        </div>
                        <div class="metric-row">
                            <span>시가총액: {s_item["market_cap"]}</span>
                            <span>PER: {s_item["pe"]}배</span>
                            <span>배당수익률: {s_item["div_yield"]}</span>
                        </div>
                        <div style="margin-top: 10px; font-size: 0.88em; color: #555; background-color: #f8f9fa; padding: 8px; border-radius: 6px;">
                            <b>💡 추천 이유:</b> {s_item["reason"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"{s_item['name']} 분석 상세 보기", key=f"dtl_btn_{s_item['code']}", use_container_width=True):
                        st.session_state['current_ticker'] = s_item['code']
                        st.session_state['show_analysis'] = True
                        st.rerun()

else:
    # --- Analysis Screen ---
    ticker = format_ticker(st.session_state['current_ticker'])
    with st.spinner(f"'{st.session_state['current_ticker']}' 분석 중..."):
        stock_obj, info = get_stock_data(ticker)

    if info and 'symbol' in info:
        st.subheader(f"🏢 {info.get('longName', info.get('shortName', ticker))}")
        with st.expander("데이터 진단 정보"): st.json(info)
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            prc = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('regularMarketPreviousClose', 0)
            curr = info.get('currency', 'KRW')
            st.metric("현재가", f"{prc:,.0f} {curr}" if curr == "KRW" else f"{prc:,.2f} {curr}")
        with m_col2: st.metric("산업 분야", info.get('sector', info.get('industry', '정보 없음')))
        with m_col3: st.metric("시가총액(규모)", format_market_cap(info.get('marketCap')))
        with m_col4:
            chg = info.get('regularMarketChangePercent', 0)
            st.metric("전일대비", f"{chg:+.2f}%", delta=f"{chg:+.2f}%" if chg else None)

        st.subheader("📊 주가 분석 차트")
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["20일", "1년", "3년", "5년", "인터랙티브"])
        for tab, (p_name, p_val) in zip([tab1, tab2, tab3, tab4, tab5], {"20일": "1mo", "1년": "1y", "3년": "3y", "5년": "5y", "인터랙티브": "max"}.items()):
            with tab:
                hist = stock_obj.history(period=p_val)
                if not hist.empty:
                    fig = go.Figure(data=[go.Candlestick(
                        x=hist.index,
                        open=hist['Open'], high=hist['High'],
                        low=hist['Low'], close=hist['Close'],
                        name="주가 정보",
                        increasing_line_color='#e03131', # 상승: 빨간색
                        decreasing_line_color='#1971c2', # 하락: 파란색
                        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>시가: %{open:,.0f}원<br>고가: %{high:,.0f}원<br>저가: %{low:,.0f}원<br>종가: %{close:,.0f}원<br><extra></extra>" if curr == "KRW" else "<b>%{x|%Y-%m-%d}</b><br>시가: %{open:,.2f}<br>고가: %{high:,.2f}<br>저가: %{low:,.2f}<br>종가: %{close:,.2f}<br><extra></extra>"
                    )])
                    fig.update_layout(xaxis_rangeslider_visible=False, height=500, yaxis=dict(tickformat=",.0f" if curr == "KRW" else ",.2f", ticksuffix="원" if curr == "KRW" else ""))
                    st.plotly_chart(fig, use_container_width=True)
                else: st.write("데이터가 없습니다.")

        # Financials
        st.subheader("🧾 재무제표 (단위: 한글)")
        FIN_MAP = {
            # 손익계산서 (Income Statement)
            "Total Revenue": "매출액",
            "Cost Of Revenue": "매출원가",
            "Gross Profit": "매출총이익",
            "Operating Expense": "영업비용",
            "Operating Income": "영업이익",
            "Net Non Operating Interest Income Expense": "영업외손익(이자)",
            "Other Income Expense": "기타영업외손익",
            "Pretax Income": "법인세차감전순이익",
            "Tax Provision": "법인세비용",
            "Net Income Common Stockholders": "당기순이익(보통주)",
            "Net Income": "당기순이익",
            "Basic EPS": "기본주당순이익(EPS)",
            "Diluted EPS": "희석주당순이익(EPS)",
            "EBITDA": "EBITDA",
            "EBIT": "EBIT",
            
            # 대차대조표 (Balance Sheet)
            "Total Assets": "자산총계",
            "Current Assets": "유동자산",
            "Cash And Cash Equivalents": "현금및현금성자산",
            "Receivables": "매출채권",
            "Inventory": "재고자산",
            "Prepaid Assets": "선급비용",
            "Other Current Assets": "기타유동자산",
            "Total Non Current Assets": "비유동자산총계",
            "Net PPE": "유형자산",
            "Goodwill And Other Intangible Assets": "무형자산및영업권",
            "Total Liabilities Net Minority Interest": "부채총계",
            "Current Liabilities": "유동부채",
            "Payables": "매입채무",
            "Current Debt": "단기차입금",
            "Total Non Current Liabilities Net Minority Interest": "비유동부채총계",
            "Long Term Debt": "장기차입금",
            "Total Equity Gross Minority Interest": "자본총계",
            "Stockholders Equity": "자본총계(지배)",
            "Common Stock": "자본금",
            "Retained Earnings": "이익잉여금",
            "Working Capital": "운전자본"
        }
        
        def format_won_korean(val):
            """숫자를 조, 억 단위 한글로 변환"""
            if pd.isna(val) or val == 0: return "-"
            abs_val = abs(val)
            res = ""
            if abs_val >= 1e12:
                res += f"{int(abs_val // 1e12)}조 "
                abs_val %= 1e12
            if abs_val >= 1e8:
                res += f"{int(abs_val // 1e8)}억"
            
            if not res: return f"{val:,.0f}"
            return ("-" if val < 0 else "") + res.strip()

        def proc_fin(df):
            if df is None or df.empty: return df
            # 인덱스 한글화
            df.index = [FIN_MAP.get(i, i) for i in df.index]
            # 컬럼 순서 반전 (최신 데이터를 우측으로 배치)
            df = df.iloc[:, ::-1]
            # 모든 셀에 한글 단위 적용
            return df.applymap(format_won_korean)

        fin_period = st.radio("보고서 주기 선택", ["연간 (Annual)", "분기별 (Quarterly)"], horizontal=True)
        f_t1, f_t2 = st.tabs(["손익계산서", "대차대조표"])
        if "연간" in fin_period:
            with f_t1: st.table(proc_fin(stock_obj.income_stmt))
            with f_t2: st.table(proc_fin(stock_obj.balance_sheet))
        else:
            with f_t1: st.table(proc_fin(stock_obj.quarterly_income_stmt))
            with f_t2: st.table(proc_fin(stock_obj.quarterly_balance_sheet))

        st.subheader("🤖 AI 투자 분석 리포트")
        a_col1, a_col2 = st.columns([2, 1])
        with st.spinner("AI 분석 중..."): ai_text = get_ai_analysis(ticker, info)
        with a_col1: st.markdown(ai_text, unsafe_allow_html=True)
        with a_col2:
            st.write("### 🎯 투자 판단")
            if "매수 권장" in ai_text: st.markdown('<div class="status-card" style="background-color:#28a745;">매수 권장</div>', unsafe_allow_html=True)
            elif "주의" in ai_text: st.markdown('<div class="status-card" style="background-color:#dc3545;">주의</div>', unsafe_allow_html=True)
            else: st.markdown('<div class="status-card" style="background-color:#ffc107; color:black;">관망</div>', unsafe_allow_html=True)
            st.info("본 분석은 참고용이며 최종 투자는 본인의 판단하에 신중히 진행하시기 바랍니다.")
    else:
        st.error("종목 정보를 불러올 수 없습니다.")
