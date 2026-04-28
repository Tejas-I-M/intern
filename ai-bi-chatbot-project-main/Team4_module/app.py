import streamlit as st
import requests
from streamlit_oauth import OAuth2Component
from visualization.dashboard import run_dashboard
from auth import load_users, save_users, hash_password

from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# ---------------- LOGIN FUNCTION ----------------
def login():
    oauth2 = OAuth2Component(
        CLIENT_ID,
        CLIENT_SECRET,
        "https://accounts.google.com/o/oauth2/auth",
        "https://oauth2.googleapis.com/token",
        "https://www.googleapis.com/oauth2/v1/userinfo",
    )

    users = load_users()
    st.set_page_config(layout="wide", page_title="Login")

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Inter:wght@300;400;500&display=swap');

    /* ── RESET ── */
    header, footer { visibility: hidden; }
    .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
    section[data-testid="stSidebar"] { display: none; }

    /* ── FULL DARK BG WITH SUBTLE GRID ── */
    .stApp {
        background-color: #070b14;
        background-image:
            linear-gradient(rgba(30,60,120,0.07) 1px, transparent 1px),
            linear-gradient(90deg, rgba(30,60,120,0.07) 1px, transparent 1px);
        background-size: 40px 40px;
        min-height: 100vh;
        font-family: 'Inter', sans-serif;
    }

    /* ── CARD WRAPPER ── */
    .login-card-top {
        width: 400px;
        margin: 0 auto;
        margin-top: calc(50vh - 320px);
        padding: 36px 34px 0px;
        background: rgba(10, 17, 32, 0.92);
        border: 1px solid rgba(56, 140, 240, 0.22);
        border-bottom: none;
        border-radius: 18px 18px 0 0;
        box-shadow:
            0 0 0 1px rgba(56,140,240,0.06),
            0 8px 60px rgba(0,0,0,0.7),
            0 0 80px rgba(37,99,235,0.07);
        backdrop-filter: blur(12px);
        position: relative;
    }

    /* corner decorations */
    .login-card-top::before {
        content: '';
        position: absolute;
        width: 18px; height: 18px;
        top: -1px; left: -1px;
        border: 2px solid rgba(56,189,248,0.55);
        border-right: none; border-bottom: none;
        border-radius: 4px 0 0 0;
    }

    /* ── LOGO RING ── */
    .logo-row {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 14px;
        margin-bottom: 20px;
    }
    .logo-line {
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(56,189,248,0.3));
    }
    .logo-line.r {
        background: linear-gradient(90deg, rgba(56,189,248,0.3), transparent);
    }
    .logo-circle {
        width: 46px; height: 46px;
        border-radius: 50%;
        border: 2px solid rgba(56,189,248,0.45);
        background: radial-gradient(circle at 35% 35%, rgba(37,99,235,0.4), rgba(7,11,20,0.95));
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 0 18px rgba(56,189,248,0.18), inset 0 0 14px rgba(37,99,235,0.25);
    }

    .login-title {
        font-family: 'Rajdhani', sans-serif;
        font-size: 26px; font-weight: 700;
        color: #f0f6ff;
        text-align: center;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .login-sub {
        font-size: 13px; color: #4b5e7a;
        text-align: center;
        margin-bottom: 24px;
    }

    /* ── TABS ── */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(255,255,255,0.03) !important;
        border-radius: 10px;
        border: 1px solid rgba(56,140,240,0.14) !important;
        padding: 3px; gap: 3px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        color: #3d5070 !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 13px !important; font-weight: 700 !important;
        letter-spacing: 1px; padding: 6px 20px !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(37,99,235,0.3) !important;
        color: #cce4ff !important;
    }
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] { display: none !important; }

    /* ── INPUTS ── */
    .stTextInput > div > div > input {
        background: rgba(5, 9, 18, 0.9) !important;
        color: #ddeeff !important;
        border: 1px solid rgba(56,140,240,0.18) !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 14px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: rgba(56,189,248,0.55) !important;
        box-shadow: 0 0 0 3px rgba(56,189,248,0.07) !important;
    }
    .stTextInput > div > div > input::placeholder { color: #243348 !important; }
    .stTextInput label {
        color: #4b6080 !important; font-size: 11px !important;
        font-family: 'Rajdhani', sans-serif !important;
        letter-spacing: 1px !important; text-transform: uppercase;
    }

    /* ── BUTTONS ── */
    .stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #1a45c8, #2563eb) !important;
        color: #fff !important;
        border: none !important; border-radius: 10px !important;
        padding: 11px !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 14px !important; font-weight: 700 !important;
        letter-spacing: 2px !important; text-transform: uppercase;
        box-shadow: 0 4px 22px rgba(37,99,235,0.3) !important;
        margin-top: 6px;
        transition: box-shadow 0.2s !important;
    }
    .stButton > button:hover {
        box-shadow: 0 6px 28px rgba(37,99,235,0.5) !important;
        opacity: 0.93 !important;
    }

    /* ── OR DIVIDER ── */
    .or-div {
        display: flex; align-items: center; gap: 12px;
        margin: 18px 0 16px;
        color: #253040;
        font-size: 11px;
        font-family: 'Rajdhani', sans-serif;
        letter-spacing: 2px;
    }
    .or-div::before, .or-div::after {
        content: ''; flex: 1; height: 1px;
        background: rgba(56,140,240,0.13);
    }

    /* ── BOTTOM CARD (holds OR + OAuth) ── */
    .login-card-bottom {
        width: 400px;
        margin: 0 auto;
        padding: 0 34px 32px;
        background: rgba(10, 17, 32, 0.92);
        border: 1px solid rgba(56, 140, 240, 0.22);
        border-top: none;
        border-radius: 0 0 18px 18px;
        backdrop-filter: blur(12px);
        position: relative;
    }
    .login-card-bottom::after {
        content: '';
        position: absolute;
        width: 18px; height: 18px;
        bottom: -1px; right: -1px;
        border: 2px solid rgba(56,189,248,0.55);
        border-left: none; border-top: none;
        border-radius: 0 0 4px 0;
    }

    /* ── ALERTS ── */
    .stAlert { border-radius: 8px !important; font-size: 13px !important; }

    </style>
    """, unsafe_allow_html=True)

    # ── TOP CARD: Logo + Title ──
    st.markdown("""
    <div class="login-card-top">
      <div class="logo-row">
        <div class="logo-line"></div>
        <div class="logo-circle">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
               stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12
                     M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12"/>
          </svg>
        </div>
        <div class="logo-line r"></div>
      </div>
      <div class="login-title">Welcome Back</div>
      <div class="login-sub">Sign in to continue to your dashboard</div>
    </div>
    """, unsafe_allow_html=True)

    # ── INTERACTIVE FORM (centered column) ──
    _, col, _ = st.columns([1, 1.15, 1])
    with col:
        tab1, tab2 = st.tabs(["LOGIN", "SIGN UP"])

        with tab1:
            username = st.text_input("Email / Username", key="login_user", placeholder="you@example.com")
            password = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")
            if st.button("LOGIN", key="login_btn"):
                u, p = username.strip().lower(), password.strip()
                if u in users:
                    if users[u] == hash_password(p):
                        st.session_state.logged_in = True
                        st.session_state.user = u
                        st.session_state.email = f"{u}@app.com"
                        st.rerun()
                    else:
                        st.error("Incorrect password.")
                else:
                    st.error("User not found.")

        with tab2:
            new_user = st.text_input("Username", key="reg_user", placeholder="choose a username")
            new_pass = st.text_input("Password", type="password", key="reg_pass", placeholder="create a password")
            if st.button("CREATE ACCOUNT", key="reg_btn"):
                nu, np = new_user.strip().lower(), new_pass.strip()
                if nu in users:
                    st.warning("Username already taken.")
                elif nu and np:
                    users[nu] = hash_password(np)
                    save_users(users)
                    st.success("Account created! Please log in.")
                else:
                    st.error("Please fill in all fields.")

        # OR divider
        st.markdown('<div class="or-div">OR CONTINUE WITH</div>', unsafe_allow_html=True)

        # Google OAuth
        result = oauth2.authorize_button(
            name="Continue with Google",
            redirect_uri="http://localhost:8501",
            scope="openid email profile",
        )

    # ── BOTTOM CARD CORNER DECORATION ──
    st.markdown('<div class="login-card-bottom"></div>', unsafe_allow_html=True)

    if result and "token" in result:
        resp = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {result['token']['access_token']}"}
        )
        info = resp.json()
        st.session_state.logged_in = True
        st.session_state.user = info.get("name", "User")
        st.session_state.email = info.get("email", "")
        st.rerun()


# ---------------- SESSION STATE ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- APP FLOW ----------------
if not st.session_state.logged_in:
    login()
    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.write(f"👋 Welcome, {st.session_state.user}")
st.sidebar.write(f"📧 {st.session_state.email}")

# ---------------- DASHBOARD ----------------
run_dashboard()
