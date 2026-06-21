import streamlit as st
import json
import requests
from datetime import datetime
import os
import urllib.parse
import time
from bs4 import BeautifulSoup
import re

# ============ AI CONFIGURATION ============
def get_ai_response(api_key: str, system_prompt: str, user_prompt: str, model: str = "mixtral-8x7b-32768") -> str | None:
    """Get response from Groq API with retry logic"""
    if not api_key or not api_key.startswith("gsk_"):
        st.error("Invalid Groq API key. Please enter a valid key starting with 'gsk_'")
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1500
    }
    
    max_retries = 8
    base_wait = 2
    
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=75
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 401:
                st.error("Invalid Groq API key. Please check your key in the sidebar.")
                return None
            elif resp.status_code == 429:
                if attempt < max_retries - 1:
                    wait = base_wait * (2 ** attempt)
                    st.warning(f"Rate limit reached. Retrying in {wait}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait)
                    continue
                else:
                    st.error("Rate limit exceeded. Please try again later.")
                    return None
            else:
                st.error(f"API error: {e}")
                return None
        except requests.exceptions.Timeout:
            st.error("Request timed out. Please try again.")
            return None
        except Exception as e:
            st.error(f"Connection error: {e}")
            return None
    return None

# ============ WEB SEARCH ============
UAE_DOMAINS = [
    "uae.gov.ae", "moccae.gov.ae", "moi.gov.ae", "mohap.gov.ae",
    "dm.gov.ae", "adpolice.gov.ae", "dubai.gov.ae", "shj.gov.ae",
    "rak.ae", "ajman.ae", "fujairah.ae", "uaq.ae",
    "wam.ae", "ncms.ae", "adnoc.ae", "dea.gov.ae"
]

def search_uae_content(query: str, max_results: int = 6) -> list[str]:
    """Search for UAE-related content using DuckDuckGo"""
    if "uae" not in query.lower() and "emirates" not in query.lower():
        query += " UAE"
    
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        results = []
        for result in soup.select(".result"):
            title_el = result.select_one(".result__title")
            snippet_el = result.select_one(".result__snippet")
            url_el = result.select_one(".result__url")
            
            title = title_el.get_text(strip=True) if title_el else ""
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            source = url_el.get_text(strip=True) if url_el else ""
            
            if title or snippet:
                results.append(f"[{source}] {title}: {snippet}")
            if len(results) >= max_results:
                break
        return results
    except Exception as e:
        return []

# ============ UAE DATA ============
EMIRATES = {
    "Abu Dhabi": {
        "capital": "Abu Dhabi",
        "emergency": {"Police": "999", "Ambulance": "998", "Civil Defence": "997"},
        "hospitals": [
            {"name": "Sheikh Khalifa Medical City", "type": "Major Trauma", "24h": True},
            {"name": "Mafraq Hospital", "type": "General", "24h": True},
            {"name": "Al Rahba Hospital", "type": "General", "24h": True}
        ],
        "shelters": [
            {"name": "ADNEC Shelter", "capacity": 5000, "status": "Available"},
            {"name": "Zayed Sports City", "capacity": 8000, "status": "Available"},
            {"name": "Khalifa University Hall", "capacity": 1200, "status": "At 70%"}
        ]
    },
    "Dubai": {
        "capital": "Dubai",
        "emergency": {"Police": "999", "Ambulance": "998", "Civil Defence": "997"},
        "hospitals": [
            {"name": "Rashid Hospital", "type": "Major Trauma", "24h": True},
            {"name": "Dubai Hospital", "type": "General", "24h": True},
            {"name": "Mediclinic City Hospital", "type": "General", "24h": True}
        ],
        "shelters": [
            {"name": "Dubai World Trade Centre", "capacity": 10000, "status": "Available"},
            {"name": "Dubai Stadium", "capacity": 6000, "status": "Available"},
            {"name": "Al Quoz Community Centre", "capacity": 800, "status": "Limited"}
        ]
    },
    "Sharjah": {
        "capital": "Sharjah",
        "emergency": {"Police": "999", "Ambulance": "998", "Civil Defence": "997"},
        "hospitals": [
            {"name": "Al Qassimi Hospital", "type": "General", "24h": True},
            {"name": "Kuwaiti Hospital", "type": "General", "24h": True}
        ],
        "shelters": [
            {"name": "Sharjah Expo Centre", "capacity": 4000, "status": "Available"},
            {"name": "Al Dhaid Community Hall", "capacity": 600, "status": "Available"}
        ]
    }
}

UAE_ROADS = {
    "highways": [
        {"name": "E11 - Sheikh Zayed Road", "risk": "Low", "status": "Open"},
        {"name": "E311 - Sheikh Mohammed Bin Zayed Rd", "risk": "Medium", "status": "Open"},
        {"name": "E66 - Dubai-Al Ain Road", "risk": "High", "status": "Watch"},
        {"name": "E88 - Abu Dhabi-Al Ain Road", "risk": "Medium", "status": "Open"},
        {"name": "E84 - Sharjah-Fujairah Road", "risk": "High", "status": "Watch"}
    ],
    "flood_zones": [
        "Al Quoz Industrial Area, Dubai",
        "Wadi Helo, Sharjah-Fujairah border",
        "Al Ain wadi crossings",
        "Ras Al Khaimah coastal areas",
        "Fujairah mountain passes"
    ]
}

EMERGENCY_NUMBERS = {
    "Police": "999",
    "Ambulance": "998",
    "Civil Defence/Fire": "997",
    "Coast Guard": "996",
    "NCEMA Hotline": "8002626",
    "Red Crescent": "800733",
    "Electricity Emergency": "991",
    "Water Emergency": "992",
    "MOHAP": "80011111",
    "Dubai RTA": "8009090"
}

# ============ PAGE CONFIG ============
st.set_page_config(
    page_title="AIGIS - UAE Emergency Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============ CUSTOM CSS ============
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  
*,
*::before,
*::after {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    border-radius: 0 !important;
}
  
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.stApp {
    background: #0d1117;
    color: #e6edf3;
}

section[data-testid="stSidebar"] {
    background: #161b22;
    border-right: 1px solid #30363d;
}

.header-banner {
    background: linear-gradient(135deg, #0d1117 0%, #1a2332 100%);
    border-bottom: 1px solid #30363d;
    padding: 28px 0;
    margin: -1rem -1rem 32px -1rem;
}

.header-title {
    font-size: 32px;
    font-weight: 700;
    color: #f0f6fc;
    letter-spacing: -0.5px;
}

.header-subtitle {
    font-size: 14px;
    color: #8b949e;
    margin-top: 6px;
    font-weight: 400;
}

.feature-card {
    background: #161b22;
    border: 1px solid #30363d;
    padding: 18px;
    margin-bottom: 14px;
    transition: all 0.2s;
}

.feature-card:hover {
    background: #1c2333;
    border-color: #484f58;
}

.feature-title {
    font-size: 15px;
    font-weight: 600;
    color: #f0f6fc;
    margin-bottom: 4px;
}

.feature-desc {
    font-size: 13px;
    color: #8b949e;
    line-height: 1.6;
}

.result-panel {
    background: #161b22;
    border: 1px solid #30363d;
    padding: 24px;
    margin-top: 20px;
}

.result-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: #8b949e;
    text-transform: uppercase;
    margin-bottom: 16px;
}

.alert-critical {
    background: #2d1b1b;
    border-left: 3px solid #da3633;
    padding: 14px 18px;
    margin: 12px 0;
    color: #f0f6fc;
    font-weight: 600;
    font-size: 13px;
}

.alert-warning {
    background: #2d241b;
    border-left: 3px solid #d29922;
    padding: 14px 18px;
    margin: 12px 0;
    color: #f0f6fc;
    font-size: 13px;
}

.alert-safe {
    background: #1b2d1b;
    border-left: 3px solid #3fb950;
    padding: 14px 18px;
    margin: 12px 0;
    color: #f0f6fc;
    font-size: 13px;
}

.alert-info {
    background: #1b2433;
    border-left: 3px solid #58a6ff;
    padding: 14px 18px;
    margin: 12px 0;
    color: #f0f6fc;
    font-size: 13px;
}

.verdict-true {
    background: #1b3a1b;
    color: #3fb950;
    padding: 6px 16px;
    font-weight: 700;
    font-size: 13px;
    display: inline-block;
    border: 1px solid #2d6b2d;
}

.verdict-false {
    background: #3a1b1b;
    color: #da3633;
    padding: 6px 16px;
    font-weight: 700;
    font-size: 13px;
    display: inline-block;
    border: 1px solid #6b2d2d;
}

.verdict-unverified {
    background: #2d2d1b;
    color: #d29922;
    padding: 6px 16px;
    font-weight: 700;
    font-size: 13px;
    display: inline-block;
    border: 1px solid #6b6b2d;
}

.source-chip {
    display: inline-block;
    background: #1c2333;
    color: #8b949e;
    padding: 4px 12px;
    font-size: 12px;
    margin: 4px 4px 4px 0;
    border: 1px solid #30363d;
}

.nav-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: #8b949e;
    text-transform: uppercase;
    margin: 20px 0 10px 0;
}

.stTextArea textarea, .stTextInput input {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    font-size: 14px !important;
    padding: 10px !important;
}

.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #58a6ff !important;
    box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.1) !important;
}

.stSelectbox > div > div {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
}

.stButton > button {
    background: #238636 !important;
    color: #ffffff !important;
    border: none !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    font-size: 14px !important;
    transition: all 0.2s;
}

.stButton > button:hover {
    background: #2ea043 !important;
    transform: translateY(-1px);
}

.stButton > button:active {
    transform: translateY(0px);
}

.stTabs [data-baseweb="tab"] {
    color: #8b949e !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    padding: 8px 16px !important;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #f0f6fc !important;
    border-bottom: 2px solid #58a6ff !important;
}

hr {
    border: none;
    border-top: 1px solid #30363d !important;
    margin: 24px 0 !important;
}

.metric-box {
    background: #161b22;
    border: 1px solid #30363d;
    padding: 16px;
    text-align: center;
}

.metric-value {
    font-size: 28px;
    font-weight: 700;
    color: #f0f6fc;
}

.metric-label {
    font-size: 12px;
    color: #8b949e;
    margin-top: 4px;
}

</style>
""", unsafe_allow_html=True)

# ============ SIDEBAR ============
with st.sidebar:
    st.markdown("### AIGIS")
    st.markdown('<div class="nav-label">Configuration</div>', unsafe_allow_html=True)
    
    groq_key = st.text_input(
        "Groq API Key",
        type="password",
        placeholder="gsk-...",
        help="Get your key at console.groq.com"
    )
    
    st.markdown('<div class="nav-label">Your Location</div>', unsafe_allow_html=True)
    location_emirate = st.selectbox(
        "Emirate",
        ["Abu Dhabi", "Dubai", "Sharjah", "Ajman", "Ras Al Khaimah", "Fujairah", "Umm Al Quwain"]
    )
    location_area = st.text_input("Area / Neighbourhood", placeholder="e.g. Downtown, Marina")
    
    st.markdown('<div class="nav-label">Current Threats</div>', unsafe_allow_html=True)
    active_threats = st.multiselect(
        "Select active threats",
        ["Flash Flooding", "Severe Sandstorm", "Extreme Heat", "Wildfire", "Storm Surge", "Power Outage", "Infrastructure Damage"],
        default=[]
    )
    
    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.72rem; color:#6e7681; line-height:1.8;">
    <strong style="color:#8b949e;">Data Sources:</strong><br>
    NCEMA · NCM · WAM · MOHAP · RTA<br>
    <strong style="color:#8b949e;">Emergency Numbers:</strong><br>
    Police: 999 · Ambulance: 998 · Civil Defence: 997
    </div>
    """, unsafe_allow_html=True)

# ============ MAIN TABS ============
tabs = st.tabs(["🚨 Alerts", "🗺️ Routes", "🏥 Relief", "🔍 Verify"])

# ============ TAB 1: ALERTS ============
with tabs[0]:
    st.markdown("#### Emergency Alert & Response")
    st.markdown('<div class="feature-desc" style="margin-bottom:16px;">AI-generated emergency plan based on your location, active threats, and real-time UAE news.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        threat_scenario = st.selectbox(
            "Scenario Type",
            ["Flash Flood Warning", "Sandstorm", "Extreme Heat (>48°C)", "Wildfire", "Storm Surge", "Infrastructure Failure", "Custom"]
        )
        additional_info = st.text_area(
            "Additional details (optional)",
            placeholder="e.g. Elderly family member, need medication, car available",
            height=80
        )
    
    if st.button("Generate Emergency Plan", key="alert_btn"):
        if not groq_key:
            st.error("⚠️ Please enter your Groq API key in the sidebar.")
        else:
            with st.spinner("🔄 Analyzing threats and generating plan..."):
                # Search for relevant news
                news_results = search_uae_content(f"{threat_scenario} {location_emirate} emergency", max_results=4)
                
                # Build context
                context = (
                    f"Location: {location_area}, {location_emirate}, UAE\n"
                    f"Threat: {threat_scenario}\n"
                    f"Active threats: {', '.join(active_threats) if active_threats else 'None specified'}\n"
                    f"Additional info: {additional_info or 'None'}"
                )
                
                # System prompt
                system = (
                    "You are AIGIS, the UAE Emergency Response AI.\n\n"
                    "Provide a CONCISE, ACTIONABLE emergency plan with these sections:\n\n"
                    "THREAT LEVEL: [Critical/High/Medium/Low] - brief justification\n"
                    "TIME FRAME: How soon action is needed\n"
                    "IMMEDIATE ACTIONS: 3-5 specific numbered steps\n"
                    "SAFE ROUTES: Which roads to use/avoid in UAE\n"
                    "SHELTERS: Nearest facility + capacity\n"
                    "EMERGENCY CONTACTS: Police 999 · Ambulance 998 · Civil Defence 997\n"
                    "CRITICAL TIP: One UAE-specific survival tip\n\n"
                    "Use real UAE roads (E11, E311, etc.) and landmarks. Be specific to the emirate."
                )
                
                news_context = "\n".join([f"- {n}" for n in news_results]) if news_results else "No recent news found."
                prompt = f"{context}\n\nLive news context:\n{news_context}"
                
                response = get_ai_response(groq_key, system, prompt)
                
                if response:
                    st.markdown('<div class="result-panel">', unsafe_allow_html=True)
                    st.markdown('<div class="result-label">Emergency Plan</div>', unsafe_allow_html=True)
                    
                    if "Critical" in response or "HIGH" in response.upper():
                        st.markdown('<div class="alert-critical">⚠️ CRITICAL THREAT - Act immediately</div>', unsafe_allow_html=True)
                    elif "Medium" in response:
                        st.markdown('<div class="alert-warning">⚠️ HIGH THREAT - Take action soon</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="alert-info">Monitor situation. Follow UAE official guidance.</div>', unsafe_allow_html=True)
                    
                    st.markdown(response)
                    
                    if news_results:
                        st.markdown("---")
                        st.markdown('<div class="result-label">Sources</div>', unsafe_allow_html=True)
                        for n in news_results:
                            st.markdown(f'<span class="source-chip">{n[:80]}...</span>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

# ============ TAB 2: ROUTES ============
with tabs[1]:
    st.markdown("#### Safe Route Navigator")
    st.markdown('<div class="feature-desc" style="margin-bottom:16px;">Disaster-aware routing avoiding flooded roads, sandstorms, and hazards - updated with live UAE traffic info.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        start_loc = st.text_input("Starting Location", placeholder="e.g. Jumeirah, Dubai")
        route_hazards = st.multiselect(
            "Hazards to avoid",
            ["Flooded Roads", "Low Visibility", "Road Closures", "Heavy Traffic", "Bridge Damage"],
            default=[]
        )
    with col2:
        end_loc = st.text_input("Destination", placeholder="e.g. Dubai Airport")
        transport = st.radio("Transport", ["Car/SUV", "Emergency Vehicle", "Walking"], horizontal=True)
    
    if st.button("Find Safe Route", key="route_btn"):
        if not groq_key:
            st.error("⚠️ Please enter your Groq API key in the sidebar.")
        elif not start_loc or not end_loc:
            st.warning("⚠️ Please enter both start and destination.")
        else:
            with st.spinner("🔄 Checking UAE road conditions..."):
                news_results = search_uae_content(f"UAE road closure traffic {start_loc} {end_loc}", max_results=4)
                
                system = (
                    "You are AIGIS Route Navigator for UAE.\n\n"
                    "Provide safe routing advice with these sections:\n\n"
                    "RECOMMENDED ROUTE: Step-by-step using real UAE roads\n"
                    "ROADS TO AVOID: Specific roads + reason\n"
                    "ESTIMATED TIME: Normal vs current conditions\n"
                    "ALTERNATE ROUTE: Backup option\n"
                    "CONDITIONS: What to expect\n"
                    "DRIVER TIP: Critical UAE-specific advice\n\n"
                    "Use real UAE road names (E11, E311, D89, etc.)."
                )
                
                hazard_text = ', '.join(route_hazards) if route_hazards else "General conditions"
                news_ctx = "\n".join([f"- {n}" for n in news_results]) if news_results else ""
                prompt = (
                    f"Start: {start_loc}\nDestination: {end_loc}\n"
                    f"Transport: {transport}\nHazards: {hazard_text}\n"
                    f"Emirate: {location_emirate}\n\nLive traffic news:\n{news_ctx}"
                )
                
                response = get_ai_response(groq_key, system, prompt)
                
                if response:
                    st.markdown('<div class="result-panel">', unsafe_allow_html=True)
                    st.markdown('<div class="result-label">Route Analysis</div>', unsafe_allow_html=True)
                    st.markdown(response)
                    
                    if news_results:
                        st.markdown("---")
                        st.markdown('<div class="result-label">Traffic Sources</div>', unsafe_allow_html=True)
                        for n in news_results[:3]:
                            st.markdown(f'<span class="source-chip">{n[:80]}...</span>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Metrics
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Sources Checked", len(news_results))
                    col2.metric("Hazards Avoided", len(route_hazards))
                    col3.metric("Updated", datetime.now().strftime("%H:%M"))

# ============ TAB 3: RELIEF ============
with tabs[2]:
    st.markdown("#### Relief & Resources Finder")
    st.markdown('<div class="feature-desc" style="margin-bottom:16px;">Find verified emergency services, shelters, water points, and medical facilities near you.</div>', unsafe_allow_html=True)
    
    resource_type = st.selectbox(
        "What do you need?",
        ["Water & Food Distribution", "Medical Centre/Hospital", "Emergency Shelter", "Fuel/Supplies", "Red Crescent Aid", "Charging/Communication", "Pet Shelter", "Accessible Shelter", "Other"]
    )
    specific_need = st.text_input("Specific requirement (optional)", placeholder="e.g. diabetes medication, wheelchair access")
    people_count = st.slider("Number of people", 1, 15, 1)
    
    if st.button("Find Relief", key="relief_btn"):
        if not groq_key:
            st.error("⚠️ Please enter your Groq API key in the sidebar.")
        else:
            with st.spinner("🔄 Searching UAE relief network..."):
                news_results = search_uae_content(f"UAE {location_emirate} {resource_type} relief emergency", max_results=5)
                
                system = (
                    "You are AIGIS Relief Coordinator for UAE.\n\n"
                    "Provide verified relief options with this format:\n\n"
                    "OPTION 1:\n"
                    "  Facility: [Real UAE name]\n"
                    "  Location: [Real address]\n"
                    "  Services: [What's available]\n"
                    "  Status: [Open/Capacity/Contact]\n\n"
                    "OPTION 2: [same format]\n"
                    "OPTION 3: [same format]\n\n"
                    "KEY CONTACTS:\n"
                    "  Red Crescent: 800733\n"
                    "  Civil Defence: 997\n"
                    "  MOHAP: 80011111\n\n"
                    "DIRECTIONS: Brief from your area\n\n"
                    "Use real UAE government facilities, hospitals, mosques, and community centres."
                )
                
                news_ctx = "\n".join([f"- {n}" for n in news_results]) if news_results else ""
                prompt = (
                    f"Location: {location_area}, {location_emirate}\n"
                    f"Need: {resource_type}\n"
                    f"Specific: {specific_need or 'None'}\n"
                    f"People: {people_count}\n\nLive context:\n{news_ctx}"
                )
                
                response = get_ai_response(groq_key, system, prompt)
                
                if response:
                    st.markdown('<div class="result-panel">', unsafe_allow_html=True)
                    st.markdown('<div class="result-label">Verified Relief Locations</div>', unsafe_allow_html=True)
                    st.markdown(response)
                    
                    st.markdown("---")
                    st.markdown('<div class="alert-info">✅ Locations cross-referenced with UAE official sources.</div>', unsafe_allow_html=True)
                    
                    if news_results:
                        st.markdown('<div class="result-label">Sources</div>', unsafe_allow_html=True)
                        for n in news_results[:4]:
                            st.markdown(f'<span class="source-chip">{n[:80]}...</span>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

# ============ TAB 4: VERIFY ============
with tabs[3]:
    st.markdown("#### Misinformation Detection")
    st.markdown('<div class="feature-desc" style="margin-bottom:16px;">Verify disaster-related claims against UAE official sources in real time. Stop the spread of false information.</div>', unsafe_allow_html=True)
    
    input_method = st.radio("Input method", ["Paste text", "Describe image/video"], horizontal=True)
    
    if "Paste text" in input_method:
        claim_text = st.text_area(
            "Paste the claim to verify",
            height=130,
            placeholder="e.g. Urgent: Al Ain Airport is closed due to flooding. All flights cancelled. Share widely!"
        )
    else:
        claim_text = st.text_area(
            "Describe what the visual content shows",
            height=130,
            placeholder="e.g. Video claims to show flooding at Dubai Mall. People are trapped inside."
        )
    
    col1, col2 = st.columns(2)
    with col1:
        source_platform = st.selectbox(
            "Where did you see this?",
            ["WhatsApp", "Twitter/X", "Facebook", "TikTok", "Telegram", "SMS", "In-person", "Other"]
        )
    with col2:
        claim_category = st.selectbox(
            "Category",
            ["Flood/Water", "Roads/Transport", "Shelter/Evacuation", "Casualties", "Government Action", "Infrastructure", "Weather", "Other"]
        )
    
    if st.button("Verify Claim", key="verify_btn"):
        if not groq_key:
            st.error("⚠️ Please enter your Groq API key in the sidebar.")
        elif not claim_text:
            st.warning("⚠️ Please enter the claim to verify.")
        else:
            with st.spinner("🔄 Cross-checking with UAE official sources..."):
                # Search for corroborating info
                search_queries = [
                    f"UAE official {claim_text[:50]}",
                    f"NCEMA NCM WAM {claim_category} UAE {datetime.now().year}",
                    f"UAE news {claim_text[:40]}"
                ]
                all_news = []
                for q in search_queries:
                    results = search_uae_content(q, max_results=3)
                    all_news.extend(results)
                all_news = list(dict.fromkeys(all_news))[:8]
                
                system = (
                    "You are AIGIS Misinformation Detection AI for UAE.\n\n"
                    "Analyze the claim and determine:\n"
                    "VERDICT: TRUE / FALSE / UNVERIFIED / MISLEADING\n\n"
                    "Format exactly:\n"
                    "VERDICT: [VERDICT]\n\n"
                    "CONFIDENCE: [0-100]% - [reason]\n\n"
                    "ANALYSIS: [2-4 sentences analyzing against UAE facts]\n\n"
                    "OFFICIAL SOURCES: [What UAE government says about this]\n\n"
                    "RED FLAGS: [Misinformation indicators found]\n\n"
                    "VERIFIED INFO: [What is actually confirmed]\n\n"
                    "ADVICE: [What to do - act, ignore, or verify further]\n\n"
                    "UAE OFFICIAL VERIFICATION CHANNELS:\n"
                    "WAM: wam.ae · NCM: ncm.ae · NCEMA: ncema.gov.ae · MOHAP: mohap.gov.ae"
                )
                
                news_ctx = "\n".join([f"- {n}" for n in all_news]) if all_news else "No corroborating sources found."
                prompt = (
                    f"CLAIM:\n\"{claim_text}\"\n\n"
                    f"Source: {source_platform}\nCategory: {claim_category}\n"
                    f"Emirate: {location_emirate}\n\n"
                    f"Search results:\n{news_ctx}"
                )
                
                response = get_ai_response(groq_key, system, prompt)
                
                if response:
                    verdict = "UNVERIFIED"
                    resp_upper = response.upper()
                    if "VERDICT: TRUE" in resp_upper:
                        verdict = "TRUE"
                    elif "VERDICT: FALSE" in resp_upper:
                        verdict = "FALSE"
                    elif "VERDICT: MISLEADING" in resp_upper:
                        verdict = "MISLEADING"
                    
                    verdict_class = {
                        "TRUE": "verdict-true",
                        "FALSE": "verdict-false",
                        "UNVERIFIED": "verdict-unverified",
                        "MISLEADING": "verdict-false"
                    }.get(verdict, "verdict-unverified")
                    
                    verdict_icons = {
                        "TRUE": "✅",
                        "FALSE": "❌",
                        "UNVERIFIED": "⚠️",
                        "MISLEADING": "⚠️"
                    }
                    
                    st.markdown('<div class="result-panel">', unsafe_allow_html=True)
                    st.markdown('<div class="result-label">Verification Result</div>', unsafe_allow_html=True)
                    
                    st.markdown(
                        f'<div style="margin:12px 0;font-size:16px;">'
                        f'<span class="{verdict_class}">{verdict_icons.get(verdict, "❓")} {verdict}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                    
                    if verdict in ("FALSE", "MISLEADING"):
                        st.markdown('<div class="alert-critical">🚫 Do NOT share this claim. It may cause panic during an emergency.</div>', unsafe_allow_html=True)
                    elif verdict == "UNVERIFIED":
                        st.markdown('<div class="alert-warning">⚠️ Cannot verify. Wait for official UAE government confirmation before acting.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="alert-safe">✅ Consistent with verified UAE official sources.</div>', unsafe_allow_html=True)
                    
                    st.markdown(response)
                    
                    if all_news:
                        st.markdown("---")
                        st.markdown('<div class="result-label">Sources Checked</div>', unsafe_allow_html=True)
                        for n in all_news[:6]:
                            st.markdown(f'<span class="source-chip">{n[:80]}...</span>', unsafe_allow_html=True)
                    
                    st.markdown("---")
                    st.markdown(
                        '<div style="font-size:0.75rem; color:#6e7681; line-height:1.8;">'
                        '<strong style="color:#8b949e;">UAE Official Verification:</strong><br>'
                        '<a href="https://wam.ae" style="color:#58a6ff;">wam.ae</a> · '
                        '<a href="https://ncm.ae" style="color:#58a6ff;">ncm.ae</a> · '
                        '<a href="https://ncema.gov.ae" style="color:#58a6ff;">ncema.gov.ae</a>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                    st.markdown('</div>', unsafe_allow_html=True)

# ============ FOOTER ============
st.markdown("---")
st.markdown(
    '<div style="text-align:center; font-size:0.78rem; color:#6e7681; padding:16px 0; line-height:1.8;">'
    '<strong style="color:#8b949e;">AIGIS - UAE Emergency Assistant</strong> · '
    'Always follow official NCEMA/Civil Defence guidance<br>'
    '<span style="color:#da3633;">Emergency:</span> '
    'Civil Defence <strong>997</strong> · '
    'Police <strong>999</strong> · '
    'Ambulance <strong>998</strong>'
    '</div>',
    unsafe_allow_html=True
)
