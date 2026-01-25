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
st.set_page_config(page_title="금융 데이터 분석 AI", layout="wide", initial_sidebar_state="expanded")

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
        height: 250px; /* 고정 높이 설정 */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
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
    # 데이터의 최소/최대값을 구하여 Y축 범위를 타이트하게 설정 (하단 빈 공간 제거)
    min_val = history_data['Close'].min()
    max_val = history_data['Close'].max()
    padding = (max_val - min_val) * 0.1
    
    fig.add_trace(go.Scatter(
        x=history_data.index,
        y=history_data['Close'],
        mode='lines',
        line=dict(color=color, width=2),
        # fill='tozeroy'를 제거하여 하단 여백 발생 방지
        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>지수: %{y:,.2f}<extra></extra>"
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=30), # 라벨 표시 공간 확보
        height=230, # 라벨 공간을 위해 전체 높이 소폭 상향
        showlegend=False,
        hovermode='x unified',
        xaxis=dict(
            visible=True,
            showticklabels=True,
            tickformat="%y-%m-%d", # 년월일(단축형)
            dtick="M3", # 3개월 단위로 표시하여 겹침 방지
            tickfont=dict(size=10, color="#888")
        ),
        yaxis=dict(
            visible=False,
            range=[min_val - padding, max_val + padding]
        ),
        paper_bgcolor='white',
        plot_bgcolor='white',
    )
    return fig

# Gemini AI Setup
st.sidebar.markdown("### 🔑 API 설정")
# key를 지정하여 세션 상태 유지 보장
user_api_key = st.sidebar.text_input("개인 Gemini API 키 입력", type="password", key="user_api_key_input", help="공용 할당량이 초과된 경우 자신의 API 키를 입력하면 즉시 해결됩니다.")
system_api_key = os.getenv("GOOGLE_API_KEY")
api_key = user_api_key if user_api_key else system_api_key

# 현재 활성화된 키 상태 표시
if user_api_key:
    masked_key = f"{user_api_key[:4]}...{user_api_key[-4:]}" if len(user_api_key) > 8 else "****"
    st.sidebar.success(f"✅ 개인 API 키 활성화됨 ({masked_key})")
elif system_api_key:
    st.sidebar.info("ℹ️ 공용 API 키 사용 중")
else:
    st.sidebar.error("⚠️ API 키가 없습니다.")

if api_key:
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        st.sidebar.error(f"API 키 설정 오류: {str(e)}")

st.sidebar.markdown(f"""
<div style="background-color: #fff3cd; padding: 10px; border-radius: 5px; border: 1px solid #ffeeba; color: #856404; font-size: 0.85em;">
    <b>💡 할당량 초과 해결 방법</b><br>
    <a href="https://aistudio.google.com/app/apikey" target="_blank">Google AI Studio</a>에서 <b>무료 API 키</b>를 발급받아 위 입력란에 넣으시면 즉시 정상 작동합니다.
</div>
""", unsafe_allow_html=True)

# Sidebar Utilities
with st.sidebar:
    st.title("🛠️ 설정 및 도구")
    
    # API Connection Test
    if st.button("🔍 API 연결 및 모델 진단"):
        if not api_key:
            st.error("진단할 API 키가 없습니다.")
        else:
            with st.spinner("진단 중..."):
                try:
                    genai.configure(api_key=api_key)
                    available_models = []
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            available_models.append(m.name)
                    st.success(f"연결 성공! 모델: {len(available_models)}개")
                    with st.expander("가용 모델 목록"):
                        st.write(available_models)
                except Exception as ex:
                    st.error(f"진단 실패: {str(ex)}")
    st.divider()
    
    if st.button("🔄 캐시 지우기 및 앱 초기화"):
        st.cache_data.clear()
        # 세션 상태 전체 초기화로 확실한 리셋 보장
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("앱이 초기화되었습니다!")
        st.rerun()
    st.divider()
    st.info("""
    **할당량 초과 문제 해결 안내:**
    1. '캐시 지우기' 버튼을 클릭해 보세요.
    2. Streamlit Cloud의 Dashboard -> Settings -> Secrets에 API 키가 정확히 입력되었는지 확인하세요.
    3. 무료 API 키는 분당 요청 제한이 엄격합니다.
    """)

def get_ai_analysis(ticker, info, current_api_key):
    if not current_api_key:
        return "⚠️ **API 키가 설정되지 않았습니다.**\n\n측면 바의 안내를 확인하여 Gemini API 키를 설정해주세요."

    # 호출 시점에 API 키 재설정 (병렬성 및 세션 독립성 보장)
    try:
        genai.configure(api_key=current_api_key)
    except: pass

    st.markdown("""
        <style>
        .ai-report h1, .ai-report h2 { font-size: 1.25rem !important; margin-top: 10px; margin-bottom: 5px; }
        .ai-report h3 { font-size: 1.1rem !important; }
        .ai-report p, .ai-report li { font-size: 0.95rem; line-height: 1.5; }
        </style>
    """, unsafe_allow_html=True)
    
    last_error = ""
    # 할당량이 가장 넉넉한 Lite 모델부터 순차적으로 시도
    for model_name in ['gemini-flash-lite-latest', 'gemini-flash-latest', 'gemini-2.0-flash', 'gemini-pro-latest']:
        try:
            model = genai.GenerativeModel(model_name)
            prompt = f"주식 분석 대상: {ticker} ({info.get('longName', ticker)})\n기업 요약: {info.get('longBusinessSummary', '정보 없음')}\n위 데이터를 바탕으로 한국어로 전문적인 투자 분석 보고서를 작성해줘:\n1. 정성적 분석 (시장 경쟁력, 주요 리스크)\n2. 정량적 분석 (수익성 지표, 재무 지표 기반 건전성)\n3. 종합 투자 의견: '매수 권장', '관망', '주의' 중 하나를 선택하고 명확한 근거 제시.\n※ 주의사항: 가독성을 위해 큰 제목(#) 대신 중간 제목(###)만 사용하여 내용을 구조화해줘."
            response = model.generate_content(prompt)
            return f'<div class="ai-report">{response.text}</div>'
        except Exception as e:
            last_error = str(e)
            if "429" in last_error:
                break # 할당량 초과는 바로 중단하여 계정 보호
            if "404" in last_error or "not found" in last_error.lower():
                continue # 모델이 없으면 다음 모델 시도
            break
    
    if "429" in last_error:
        return "⚠️ **AI 서비스 할당량이 일시적으로 초과되었습니다.** 무료 버전 제한(RPM)에 도달했습니다. 약 1분 후 다시 시도하시거나, 사이드바에 개인 API 키를 입력해 주세요."
    return f"AI 분석 생성 실패: {last_error}"

@st.cache_data(ttl=3600) # 1시간 동안 캐시 유지
def get_market_briefing_v2(index_info, current_api_key):
    if not current_api_key: return "지수 정보를 통해 분석할 AI 키가 없습니다."
    
    # 호출 시점에 API 키 재설정 (캐시 무효화 및 키 갱신 보장)
    try:
        genai.configure(api_key=current_api_key)
    except: pass

    if not index_info or index_info == "{}":
        return "현재 지수 데이터를 불러오는 데 실패하여 브리핑을 생성할 수 없습니다."
        
    last_error = ""
    for model_name in ['gemini-flash-lite-latest', 'gemini-flash-latest', 'gemini-2.0-flash', 'gemini-pro-latest']:
        try:
            model = genai.GenerativeModel(model_name)
            prompt = f"다음 글로벌 지수 데이터를 바탕으로 현재 시장 상황 및 전망을 3문장 이내의 아주 전문적인 한국어로 요약해줘: {index_info}"
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = str(e)
            if "429" in last_error:
                break
            if "404" in last_error or "not found" in last_error.lower():
                continue
            break
            
    if "429" in last_error:
        raise Exception(f"QUOTA_EXCEEDED: {last_error}")
    raise Exception(last_error or "사용 가능한 Gemini 모델을 찾을 수 없습니다.")

# Session State Initialization
if 'current_ticker' not in st.session_state:
    st.session_state['current_ticker'] = "삼성전자"
if 'ticker_history' not in st.session_state:
    st.session_state['ticker_history'] = []
if 'show_analysis' not in st.session_state:
    st.session_state['show_analysis'] = False
if 'last_briefing' not in st.session_state:
    st.session_state['last_briefing'] = None

# Main UI
st.title("🛡️ 실시간 AI 주식 분석기 v2.8")

# 사이드바 안내 (API 키가 없을 경우에만 표시)
if not api_key:
    st.warning("👈 **왼쪽 사이드바**가 보이지 않는다면 화면 좌측 상단의 **'>' 모양 화살표**를 클릭하여 **[개인 Gemini API 키]**를 입력해 주세요.")

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
                
                # 지수 데이터를 정수 및 소수점 1자리로 제한하여 캐시 효율성 증대 (너무 잦은 AI 호출 방지)
                index_summary_data[name] = f"{int(cv):,} ({dp:+.1f}%)"
            else:
                curr_p = t_obj.info.get('regularMarketPrice', 0)
                col.markdown(f'<div class="index-card">{name}<br><b>{curr_p:,.2f}</b><br><small>데이터 대기 중</small></div>', unsafe_allow_html=True)
        except: col.write(f"{name} 로딩 실패")

    # --- AI Briefing Section ---
    st.write("#### 📊 AI 시장 브리핑")
    
    if st.session_state['last_briefing'] is None:
        # 자동 호출 대신 버튼 클릭 시에만 호출하도록 변경 (할당량 보호)
        if st.button("🚀 AI 시장 브리핑 생성 (무료 API 이용)", use_container_width=True):
            with st.spinner("AI 시장 브리핑 생성 중..."):
                try:
                    # 최신 api_key를 인자로 전달하여 캐시 무효화 보장
                    briefing = get_market_briefing_v2(str(index_summary_data), api_key)
                    st.session_state['last_briefing'] = briefing
                    st.rerun()
                except Exception as e:
                    err_msg = str(e)
                    if "QUOTA_EXCEEDED" in err_msg:
                        # 실제로 개인 키를 사용 중인지 체크 (세션 상태와 비교)
                        is_using_personal = bool(st.session_state.get("user_api_key_input"))
                        if is_using_personal:
                            st.error(f"""
                            ⚠️ **입력하신 개인 API 키도 제한에 걸렸습니다.**
                            
                            **원인:** `{err_msg}`
                            
                            **조치 제안:**
                            1. **무료 키 제한**: 무료 API 키는 1분에 약 15번 정도만 호출이 가능합니다. 너무 빨리 클릭하지 마세요.
                            2. **잠시 대기**: 약 1~2분 정도만 아무 클릭 없이 기다리셨다가 다시 눌러보세요.
                            3. **키 유효성**: [Google AI Studio](https://aistudio.google.com/app/apikey)에서 방금 만드신 키가 제대로 활성화되었는지 확인해 주세요.
                            """)
                        else:
                            st.warning(f"""
                            ⚠️ **공용 AI 할당량이 모두 소진되었습니다.**
                            
                            **해결 방법:** 왼쪽 사이드바에 본인의 **[개인 Gemini API 키]**를 입력해 주세요. (가장 확실한 방법)
                            """)
                    else:
                        st.error(f"브리핑 생성 실패: {err_msg}")
        else:
            st.info("위 버튼을 클릭하면 AI가 현재 지수를 분석하여 브리핑을 생성합니다.")
    else:
        st.info(f"{st.session_state['last_briefing']}")
        if st.button("🔄 브리핑 새로고침", use_container_width=False):
            st.session_state['last_briefing'] = None
            st.rerun()
    
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
                
                # PER 데이터 다각도 취득 (K-주식은 필드가 제각각임)
                pe = inf.get('trailingPE') or inf.get('forwardPE')
                if not pe:
                    eps = inf.get('trailingEps')
                    if eps and eps > 0 and p > 0:
                        pe = p / eps
                
                div = inf.get('forwardDividendYield', 0)
                
                status = item.get('status', '관망')
                badge_class = 'badge-buy' if '매수' in status else 'badge-watch' if '주의' in status else 'badge-wait'

                updated_list.append({
                    **item, 
                    'price': f"{p:,.2f} {cur}" if cur != "KRW" else f"{p:,.0f}원", 
                    'change': f"{c:+.2f}%", 'color': '#e03131' if c >= 0 else '#1971c2',
                    'market_cap': format_market_cap(m_cap), 
                    'pe': f"{pe:.1f}배" if pe and pe > 0 else "N/A", 
                    'div_yield': f"{div*100:.1f}%" if div else "0.0%",
                    'badge_class': badge_class
                })
            except: updated_list.append({**item, 'change': '-', 'color': 'black', 'market_cap': "정보 없음", 'pe': "N/A", 'div_yield': "0.0%", 'badge_class': 'badge-wait', 'price': '-'})
        return updated_list

    kr_base = [
        {"name": "삼성전자", "code": "005930.KS", "reason": "AI 서버용 HBM3E 공급 본격화 및 파운드리 수익성 개선 기대, 업황 바닥 통과에 따른 실적 반등 가속화.", "status": "매수 권장"},
        {"name": "SK하이닉스", "code": "000660.KS", "reason": "HBM 시장 내 독보적 지위 유지 및 차세대 메모리 주도권 확보, 데이터센터 투자 확대에 따른 고부가 제품 판매 증가.", "status": "매수 권장"},
        {"name": "LG에너지솔루션", "code": "373220.KS", "reason": "4680 원통형 배터리 양산 및 북미 합작공장 가동을 통한 이익 확대, 글로벌 시장 점유율 1위 수성 전략 강화.", "status": "매수 권장"},
        {"name": "삼성바이오로직스", "code": "207940.KS", "reason": "4공장 풀가동 및 5공장 조기 증설을 통한 압도적 생산능력 확보, 대형 글로벌 제약사와의 장기 수주 계약 확대.", "status": "매수 권장"},
        {"name": "현대차", "code": "005380.KS", "reason": "전동화 전환 가속 및 하이브리드 비중 확대로 수익성 개선 성공, 주주환원 정책 강화(자사주 소각 등)로 기업 가치 제고.", "status": "매수 권장"},
        {"name": "NAVER", "code": "035420.KS", "reason": "생성형 AI '하이퍼클로바X' 기반 B2B 솔루션 매출 본격화, 치지직 등 커뮤니티 서비스 강화로 광고 수익 확대.", "status": "매수 권장"},
        {"name": "셀트리온", "code": "068270.KS", "reason": "짐펜트라 미국 직접 판매 채널 구축 및 신규 바이오시밀러 승인 기대, 합병 후 효율화된 비용 구조로 이익률 상승.", "status": "매수 권장"},
        {"name": "기아", "code": "000270.KS", "reason": "역대 최고 영업이익률 달성과 함께 공격적인 배당 정책 유지, 북미 및 유럽 내 고마진 모델 판매 비중 지속 확대.", "status": "매수 권장"},
        {"name": "삼성SDI", "code": "006400.KS", "reason": "전고체 배터리 시제품 공급 및 모빌리티용 원형 배터리 시장 점유율 확대, 기술 중심의 차별화된 고수익 성장 전략.", "status": "매수 권장"},
        {"name": "KB금융", "code": "105560.KS", "reason": "주주가치 제고를 위한 밸류업 프로그램 선도적 이행 및 자본 효율성 개선, 견고한 이익 체력을 바탕으로 배당 성향 확대.", "status": "매수 권장"},
        {"name": "신한지주", "code": "055550.KS", "reason": "속도감 있는 자사주 매입 및 소각 정책으로 주당 순이익 증가 유도, 금리 변동성에도 철저한 리스크 관리 탁월.", "status": "매수 권장"},
        {"name": "삼성물산", "code": "028260.KS", "reason": "바이오 부문 실적 호조 및 건설 부문 역대 최고 수주 잔고 유지, 자사주 순차적 소각 등 전향적 주주 환원 가시화.", "status": "매수 권장"},
        {"name": "현대모비스", "code": "012330.KS", "reason": "전동화 핵심 부품 공급 확대 및 AS 부문 고수익 구조 유지, 완성차 글로벌 가동률 상승에 따른 실적 개선 수혜.", "status": "매수 권장"},
        {"name": "LG화학", "code": "051910.KS", "reason": "배터리 양극재 캐파 증설 및 소재 수직 계열화 성공, 신성장 동력(신약, 필터 등) 비중 증대에 따른 재평가 기대.", "status": "매수 권장"},
        {"name": "카카오", "code": "035720.KS", "reason": "카카오톡 기반 광고 매출 안정화 및 AI 서비스 일상화 전략, 계열사 리스크 해소와 수익성 중심의 체질 개선 성공.", "status": "매수 권장"}
    ]
    us_base = [
        {"name": "NVIDIA", "code": "NVDA", "reason": "블랙웰 아키텍처 도입을 통한 압도적 기술 격차 유지, 데이터센터 매출의 지속적인 서프라이즈와 AI 가속기 시장 독점.", "status": "매수 권장"},
        {"name": "Microsoft", "code": "MSFT", "reason": "Azure 클라우드에 코파일럿 통합을 통한 AI 수익 모델 선점, 독보적인 현금 흐름과 장기 성장 가시성 확보.", "status": "매수 권장"},
        {"name": "Apple", "code": "AAPL", "reason": "자체 설계 AI '애플 인텔리전스' 기반의 아이폰 교체 주기 도래, 서비스 부문 비중 확대로 이익 고도화 지속.", "status": "매수 권장"},
        {"name": "Alphabet", "code": "GOOGL", "reason": "구글 클라우드의 AI 인프라 매출 급증 및 검색 광고 성공적 방어, 유튜브 쇼츠 수익화 가속 및 웨이모 성장 기대.", "status": "매수 권장"},
        {"name": "Amazon", "code": "AMZN", "reason": "AWS 인프라 효율화 및 AI 연계 서비스 성장 가시화, 물류 혁신을 통한 마진율 개선 및 광고 지배력 강화.", "status": "매수 권장"}
    ]

    with st.spinner("최신 추천주 데이터를 불러오는 중입니다..."):
        kr_recommends = get_recommendation_details_v4(kr_base)
        us_recommends = get_recommendation_details_v4(us_base)

    # 국내 주식을 우선 배치 (수직으로 나누어 국내 주식을 상단에 강조)
    st.write("#### 🇰🇷 국내 유망 종목 TOP 15")
    kr_cols = st.columns(3) # 3열로 나누어 15개를 효율적으로 배치
    for i, s_item in enumerate(kr_recommends):
        with kr_cols[i % 3]:
            with st.container():
                st.markdown(f"""
                <div class="recommend-box">
                    <div>
                        <div class="recommend-header">
                            <div class="recommend-name">
                                {s_item["name"]} <br><small style="color:#888; font-weight:normal;">{s_item["code"]}</small>
                                <span class="status-badge {s_item['badge_class']}">{s_item['status']}</span>
                            </div>
                        </div>
                        <div class="recommend-price" style="color:{s_item['color']}; font-size: 1.1em; margin: 5px 0;">
                            {s_item["price"]} <small>{s_item["change"]}</small>
                        </div>
                        <div style="font-size: 0.82em; color: #666;">
                            시총: {s_item["market_cap"]} | PER: {s_item["pe"]}
                        </div>
                        <div style="margin-top: 8px; font-size: 0.83em; color: #555; background-color: #f1f3f5; padding: 6px; border-radius: 4px; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;">
                            <b>💡 이유:</b> {s_item["reason"]}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"{s_item['name']} 분석", key=f"dtl_btn_{s_item['code']}", use_container_width=True):
                    st.session_state['current_ticker'] = s_item['code']
                    st.session_state['show_analysis'] = True
                    st.rerun()

    st.divider()
    st.write("#### 🇺🇸 미국 유망 종목 TOP 5")
    us_cols = st.columns(5) # 5개를 한 줄에 배치
    for i, s_item in enumerate(us_recommends):
        with us_cols[i]:
            with st.container():
                st.markdown(f"""
                <div class="recommend-box" style="padding: 10px; height: 160px; justify-content: flex-start;">
                    <div class="recommend-name" style="font-size: 1em;">{s_item["name"]}</div>
                    <div style="font-size: 0.8em; color: #888;">{s_item["code"]}</div>
                    <div class="recommend-price" style="color:{s_item['color']}; margin: 5px 0; font-size: 1em;">
                        {s_item["price"]} <br><small>{s_item["change"]}</small>
                    </div>
                    <div class="status-badge {s_item['badge_class']}" style="font-size: 0.75em; margin-left: 0; display: inline-block;">{s_item['status']}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("분석", key=f"us_dtl_{s_item['code']}", use_container_width=True):
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
        with st.spinner("AI 분석 중..."): 
            # 최신 api_key를 인자로 전달
            ai_text = get_ai_analysis(ticker, info, api_key)
        with a_col1: st.markdown(ai_text, unsafe_allow_html=True)
        with a_col2:
            st.write("### 🎯 투자 판단")
            if "매수 권장" in ai_text: st.markdown('<div class="status-card" style="background-color:#28a745;">매수 권장</div>', unsafe_allow_html=True)
            elif "주의" in ai_text: st.markdown('<div class="status-card" style="background-color:#dc3545;">주의</div>', unsafe_allow_html=True)
            else: st.markdown('<div class="status-card" style="background-color:#ffc107; color:black;">관망</div>', unsafe_allow_html=True)
            st.info("본 분석은 참고용이며 최종 투자는 본인의 판단하에 신중히 진행하시기 바랍니다.")
    else:
        st.error("종목 정보를 불러올 수 없습니다.")
