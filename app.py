import streamlit as st
import pandas as pd
import numpy_financial as npf
from babel.numbers import get_currency_symbol, get_currency_name
from fpdf import FPDF
import uuid
from datetime import datetime, timedelta, date
import streamlit_authenticator as stauth
import bcrypt

# ==========================================
# 1. SETUP & PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="REAL ESTATE STRUCTURE",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. AUTHENTICATION & USER DATABASE
# ==========================================

# Helper function to hash passwords
def hash_pass(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Initialize User Database in Session State (Simulating a DB)
if 'user_db' not in st.session_state:
    st.session_state.user_db = {
        'jsmith': {
            'name': 'John Smith',
            'password': hash_pass('abc')
        },
        'rbriggs': {
            'name': 'Rebecca Briggs',
            'password': hash_pass('def')
        }
    }

# Build the Config Dictionary from our Session State DB
config = {
    'credentials': {
        'usernames': st.session_state.user_db
    },
    'cookie': {
        'expiry_days': 30,
        'key': 'random_signature_key',
        'name': 'real_estate_cookie'
    },
    'preauthorized': {
        'emails': []
    }
}

# Initialize Authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# --- LOGIN / SIGNUP TABS ---
if st.session_state["authentication_status"] is not True:
    # Create tabs for cleaner UI
    tab_login, tab_signup = st.tabs(["Login", "Create Account"])
    
    with tab_login:
        authenticator.login()
        if st.session_state["authentication_status"] is False:
            st.error('Username/password is incorrect')
        elif st.session_state["authentication_status"] is None:
            st.warning('Please enter your credentials')

    with tab_signup:
        st.subheader("New User Registration")
        with st.form("signup_form"):
            new_name = st.text_input("Full Name")
            new_user = st.text_input("Username")
            new_pass = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Create Account")
            
            if submitted:
                if new_user in st.session_state.user_db:
                    st.error("Username already exists!")
                elif not new_user or not new_pass:
                    st.error("Please fill in all fields.")
                else:
                    # Add to our "Database"
                    st.session_state.user_db[new_user] = {
                        'name': new_name,
                        'password': hash_pass(new_pass)
                    }
                    st.success("Account created! Go to the Login tab to sign in.")
                    # We don't rerun immediately so the user sees the success message
    
    # STOP APP HERE IF NOT LOGGED IN
    st.stop()

# ==========================================
# 3. MAIN APP (ONLY RUNS IF LOGGED IN)
# ==========================================

# Add Logout Button to Sidebar
with st.sidebar:
    st.write(f"Welcome, **{st.session_state['name']}**")
    authenticator.logout('Logout', 'main')
    st.divider()

# --- INITIALIZE SESSION STATE ---
if 'saved_scenarios' not in st.session_state:
    st.session_state.saved_scenarios = []
if 'current_results' not in st.session_state:
    st.session_state.current_results = None
if 'grid_key' not in st.session_state:
    st.session_state.grid_key = str(uuid.uuid4())

# Default Grid Data
default_grid_data = pd.DataFrame([
    {"Years": 0.0, "Frequency": "Specific Date", "Target Date": date(2025, 6, 15), "Payment %": 10.0, "Fixed Payment": 0.0, "Interest Rate %": 5.0, "Notes": "10% Deposit"},
    {"Years": 0.0, "Frequency": "Specific Date", "Target Date": date(2025, 12, 15), "Payment %": 5.0, "Fixed Payment": 0.0, "Interest Rate %": 5.0, "Notes": "5% Installment"},
    {"Years": 3.0, "Frequency": "Monthly", "Target Date": None, "Payment %": 0.0, "Fixed Payment": 0.0, "Interest Rate %": 5.0, "Notes": "Balance Amortization"},
])

if 'active_grid_df' not in st.session_state:
    st.session_state.active_grid_df = default_grid_data

# --- LUXURY CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Lato:wght@300;400;700&display=swap');
    
    .stApp { background-color: #FAFAFA; font-family: 'Lato', sans-serif; }
    h1, h2, h3 { color: #111111; font-family: 'Playfair Display', serif; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px; }
    section[data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E5E5E5; }
    div[data-testid="stMetric"] { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-top: 3px solid #C5A059; padding: 20px; border-radius: 0px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); }
    div[data-testid="stMetricLabel"] { font-family: 'Lato', sans-serif; font-size: 11px; font-weight: 700; color: #888888; letter-spacing: 2px; text-transform: uppercase; }
    div[data-testid="stMetricValue"] { font-family: 'Playfair Display', serif; color: #111111; font-weight: 500; font-size: 30px; }
    div.stButton > button { width: 100%; border-radius: 0px; font-family: 'Lato', sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; transition: all 0.4s ease; height: 50px; font-size: 13px; }
    button[kind="primary"] { background-color: #111111; border: 1px solid #111111; color: #FFFFFF; }
    button[kind="primary"]:hover { background-color: #FFFFFF; color: #111111; border: 1px solid #111111; }
    button[kind="secondary"] { background-color: #FFFFFF; border: 1px solid #E0E0E0; color: #444444; }
    button[kind="secondary"]:hover { border-color: #111111; color: #111111; }
    button[key*="load_"] { height: 35px !important; font-size: 11px !important; border: 1px solid #C5A059 !important; color: #C5A059 !important; }
    button[key*="load_"]:hover { background-color: #C5A059 !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

ACTIVE_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'CNY', 'AED', 'SAR', 'CAD', 'AUD', 'CHF', 'INR', 'RUB', 'TRY', 'ZAR']

def format_currency_label(code):
    try:
        symbol = get_currency_symbol(code, locale='en_US')
        name = get_currency_name(code, locale='en_US')
        return f"{code} ({symbol}) - {name}"
    except:
        return code

# ==========================================
# 4. PDF GENERATOR
# ==========================================
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'INVESTMENT ANALYSIS REPORT', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf(project_name, currency_symbol, t_cost, t_int, npv, price, down, df_schedule, start_date):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"PROJECT: {project_name}", 0, 1)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, f"Start Date: {start_date.strftime('%B %d, %Y')}", 0, 1)
    pdf.ln(5)
    
    pdf.set_fill_color(250, 250, 250)
    pdf.set_font("Arial", '', 10)
    pdf.cell(95, 8, f"Property Price: {currency_symbol}{price:,.0f}", 1, 0, 'L', 1)
    pdf.cell(95, 8, f"Down Payment: {currency_symbol}{down:,.0f}", 1, 1, 'L', 1)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(63, 10, f"TOTAL COST: {currency_symbol}{t_cost:,.0f}", 1, 0, 'L')
    pdf.cell(63, 10, f"TOTAL INTEREST: {currency_symbol}{t_int:,.0f}", 1, 0, 'L')
    pdf.cell(64, 10, f"NPV: {currency_symbol}{npv:,.0f}", 1, 1, 'L')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 10, "PAYMENT SCHEDULE", 0, 1)
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(30, 8, "Date", 1)
    pdf.cell(40, 8, "Payment", 1)
    pdf.cell(40, 8, "Interest", 1)
    pdf.cell(40, 8, "Principal", 1)
    pdf.ln()
    
    pdf.set_font("Arial", '', 9)
    for index, row in df_schedule.head(30).iterrows():
        date_str = row['Payment Date'].strftime('%b %Y')
        pdf.cell(30, 7, date_str, 1)
        pdf.cell(40, 7, f"{row['Payment']:,.0f}", 1)
        pdf.cell(40, 7, f"{row['Interest']:,.0f}", 1)
        pdf.cell(40, 7, f"{row['Principal']:,.0f}", 1)
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. CALCULATION ENGINE
# ==========================================
def calculate_schedule(price, down_payment, discount_rate, phases_df, start_date):
    freq_map = {'Daily': 365, 'Weekly': 52, 'Bi-Weekly': 26, 'Monthly': 12, 
                'Bi-Monthly': 6, 'Quarterly': 4, 'Semi-Annually': 2, 'Annually': 1,
                'Specific Date': 0}
    
    current_balance = price - down_payment
    schedule = []
    cash_flows_npv = [-down_payment]
    
    current_date = pd.to_datetime(start_date)
    
    for index, row in phases_df.iterrows():
        if current_balance <= 0.1: break

        freq_type = row['Frequency']
        rate_annual = row['Interest Rate %'] / 100
        
        payment_pct = row.get('Payment %', 0.0)
        fixed_payment = row.get('Fixed Payment', 0.0)
        
        calculated_payment = 0.0
        is_fixed_input = False
        
        if payment_pct > 0:
            calculated_payment = price * (payment_pct / 100)
            is_fixed_input = True
        elif fixed_payment > 0:
            calculated_payment = fixed_payment
            is_fixed_input = True
        
        # --- PATH A: SPECIFIC DATE ---
        if freq_type == 'Specific Date':
            target_date = pd.to_datetime(row['Target Date'])
            if pd.isna(target_date): continue 
            
            days_diff = (target_date - current_date).days
            if days_diff < 0: days_diff = 0
            years_diff = days_diff / 365.25
            
            interest_amount = current_balance * rate_annual * years_diff
            
            if is_fixed_input:
                payment = calculated_payment
            else:
                payment = current_balance + interest_amount

            principal = payment - interest_amount
            current_balance -= principal
            
            schedule.append({
                "Phase": f"Phase {index + 1}", "Payment Date": target_date,
                "Payment": payment, "Interest": interest_amount, "Principal": principal, "Balance": max(0, current_balance)
            })
            cash_flows_npv.append(-payment)
            current_date = target_date

        # --- PATH B: STANDARD FREQUENCY ---
        else:
            if pd.isna(row['Years']) or row['Years'] <= 0: continue
            
            n_per_year = freq_map[freq_type]
            rate_per_period = rate_annual / n_per_year
            total_periods = int(row['Years'] * n_per_year)
            
            if is_fixed_input:
                payment = calculated_payment
            else:
                if rate_annual == 0: 
                    payment = current_balance / total_periods
                else: 
                    payment = (current_balance * rate_per_period) / (1 - (1 + rate_per_period)**(-total_periods))

            for p in range(1, total_periods + 1):
                interest = current_balance * rate_per_period
                principal = payment - interest
                current_balance -= principal
                
                days_to_add = int(365.25 / n_per_year)
                current_date = current_date + timedelta(days=days_to_add)
                
                schedule.append({
                    "Phase": f"Phase {index + 1}", "Payment Date": current_date,
                    "Payment": payment, "Interest": interest, "Principal": principal, "Balance": max(0, current_balance)
                })
                cash_flows_npv.append(-payment)

    df_schedule = pd.DataFrame(schedule)
    npv = 0 if len(cash_flows_npv) == 0 else npf.npv(discount_rate/100/12, cash_flows_npv)
    t_paid = df_schedule['Payment'].sum() + down_payment if not df_schedule.empty else down_payment
    t_int = df_schedule['Interest'].sum() if not df_schedule.empty else 0
    return df_schedule, t_paid, t_int, npv

# ==========================================
# 6. SIDEBAR - SCENARIO MANAGER
# ==========================================
with st.sidebar:
    st.title("INVESTMENT MODELER")
    
    if st.button("RESET TO DEFAULT", type="secondary"):
        st.session_state.current_results = None
        st.session_state.active_grid_df = default_grid_data
        st.session_state.grid_key = str(uuid.uuid4())
        st.rerun()

    st.markdown("---")
    view_mode = st.radio("VIEW MODE", ["CALCULATOR", "COMPARISON"], index=0, label_visibility="collapsed")
    st.markdown("---")
    
    if st.session_state.saved_scenarios:
        st.subheader("SAVED SCENARIOS")
        st.caption("CLICK 'LOAD' TO RESTORE VARIABLES")
        for i, scen in enumerate(st.session_state.saved_scenarios):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{scen['name']}**")
                curr = scen.get('currency_symbol', '$') 
                cost = scen.get('cost', 0)
                st.caption(f"{curr}{cost:,.0f}")
            with c2:
                if st.button("LOAD", key=f"load_{i}"):
                    st.session_state.proj_name_input = scen['inputs']['project_name']
                    st.session_state.currency_input = scen['inputs']['currency_code']
                    st.session_state.start_date_input = scen['inputs']['start_date']
                    st.session_state.price_input = scen['inputs']['price']
                    st.session_state.down_input = scen['inputs']['down_payment']
                    st.session_state.disc_input = scen['inputs']['discount_rate']
                    st.session_state.active_grid_df = scen['inputs']['grid_df']
                    st.session_state.grid_key = str(uuid.uuid4())
                    st.success(f"LOADED: {scen['name']}")
                    st.rerun()
        if st.button("CLEAR ALL HISTORY", type="secondary"):
            st.session_state.saved_scenarios = []
            st.rerun()
        st.markdown("---")

    with st.expander("1. CURRENCY & SETTINGS", expanded=True):
        default_idx = ACTIVE_CURRENCIES.index('USD') if 'USD' in ACTIVE_CURRENCIES else 0
        currency_code = st.selectbox("Currency", ACTIVE_CURRENCIES, index=default_idx, format_func=format_currency_label, key='currency_input')
        currency_symbol = get_currency_symbol(currency_code, locale='en_US')
        project_name = st.text_input("Project Name", "Project Alpha", key='proj_name_input')
        start_date = st.date_input("Start Date", datetime.today(), key='start_date_input')

    with st.expander("2. FINANCIAL PARAMETERS", expanded=True):
        price = st.number_input(f"Price ({currency_symbol})", value=1000000.0, step=10000.0, key='price_input')
        down_payment = st.number_input(f"Down Payment ({currency_symbol})", value=200000.0, step=5000.0, key='down_input')
        discount_rate = st.number_input("Inflation / Discount Rate (%)", value=5.0, step=0.1, format="%.2f", key='disc_input')

# ==========================================
# 7. MAIN DASHBOARD LOGIC
# ==========================================

if view_mode == "CALCULATOR":
    st.title(f"REAL ESTATE STRUCTURE: {project_name}")
    st.caption("DEFINE PAYMENT PHASES. USE 'PAYMENT %' FOR PERCENTAGE OF TOTAL PRICE.")

    # GRID EDITOR
    edited_phases = st.data_editor(
        st.session_state.active_grid_df,
        key=st.session_state.grid_key,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Years": st.column_config.NumberColumn(
                "DURATION (YRS)", 
                help="Only for standard frequencies. Ignored for Specific Date.",
                format="%.1f"
            ),
            "Frequency": st.column_config.SelectboxColumn(
                "FREQUENCY", 
                options=['Specific Date', 'Monthly', 'Quarterly', 'Annually', 'Semi-Annually', 'Bi-Weekly', 'Weekly', 'Daily'], 
                required=True
            ),
            "Target Date": st.column_config.DateColumn("TARGET DATE"),
            "Payment %": st.column_config.NumberColumn(
                "PAYMENT %",
                help="% of Initial Property Price (e.g. 10 = 10%). Overrides Fixed Payment.",
                format="%.1f%%"
            ),
            "Fixed Payment": st.column_config.NumberColumn(
                "FIXED PAYMENT",
                help="Specific Currency Amount. Ignored if Payment % is set.",
                format="%.0f"
            ),
            "Interest Rate %": st.column_config.NumberColumn("INTEREST %", format="%.2f%%"),
            "Notes": st.column_config.TextColumn("NOTES")
        }
    )

    st.write("##")
    col_btn1, col_btn2 = st.columns([1, 3])
    with col_btn1:
        run_pressed = st.button("RUN ANALYSIS", type="primary")

    if run_pressed:
        df, t_paid, t_int, npv = calculate_schedule(price, down_payment, discount_rate, edited_phases, start_date)
        st.session_state.current_results = {'df': df, 't_paid': t_paid, 't_int': t_int, 'npv': npv}
        st.session_state.active_grid_df = edited_phases

    if st.session_state.current_results:
        res = st.session_state.current_results
        df, t_paid, t_int, npv = res['df'], res['t_paid'], res['t_int'], res['npv']
        def fmt(val): return f"{currency_symbol}{val:,.0f}"

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("TOTAL COST", fmt(t_paid))
        c2.metric("INTEREST PAID", fmt(t_int))
        c3.metric("NPV (ADJUSTED)", fmt(abs(npv)))
        c4.metric("PAYMENTS", len(df))

        st.write("##")
        if st.button("SAVE SNAPSHOT TO COMPARE"):
            scenario = {
                "name": f"{project_name} ({pd.Timestamp.now().strftime('%H:%M:%S')})",
                "cost": t_paid, "interest": t_int, "npv": abs(npv),
                "currency_symbol": currency_symbol,
                "inputs": {
                    "project_name": project_name, "currency_code": currency_code,
                    "start_date": start_date, "price": price,
                    "down_payment": down_payment, "discount_rate": discount_rate,
                    "grid_df": edited_phases
                }
            }
            st.session_state.saved_scenarios.append(scenario)
            st.success("SNAPSHOT SAVED WITH FULL DATA. CLICK 'LOAD' IN SIDEBAR TO RESTORE.")
            st.rerun()

        st.markdown("---")
        tab1, tab2 = st.tabs(["CASH FLOW CHARTS", "DETAILED DATA"])
        
        with tab1:
            if not df.empty:
                st.subheader("TIMELINE: PRINCIPAL VS INTEREST")
                chart_data = df.set_index("Payment Date")[["Interest", "Principal"]]
                st.bar_chart(chart_data, color=["#C5A059", "#111111"])
                st.caption("X-AXIS: CALENDAR DATES | GOLD: INTEREST | BLACK: PRINCIPAL")

        with tab2:
            disp_df = df.copy()
            disp_df['Payment Date'] = disp_df['Payment Date'].apply(lambda x: x.strftime('%b %d, %Y'))
            st.dataframe(disp_df, use_container_width=True)
            d1, d2 = st.columns(2)
            csv = df.to_csv(index=False).encode('utf-8')
            d1.download_button("DOWNLOAD CSV", csv, f"{project_name}.csv", "text/csv", use_container_width=True)
            try:
                pdf_bytes = create_pdf(project_name, currency_symbol, t_paid, t_int, abs(npv), price, down_payment, df, start_date)
                d2.download_button("DOWNLOAD PDF REPORT", pdf_bytes, f"{project_name}.pdf", "application/pdf", use_container_width=True)
            except: pass

elif view_mode == "COMPARISON":
    st.title("SCENARIO COMPARISON BOARD")
    if not st.session_state.saved_scenarios:
        st.info("NO SCENARIOS SAVED. PLEASE RUN AN ANALYSIS AND CLICK 'SAVE SNAPSHOT'.")
    else:
        st.caption("COMPARE FINANCIAL METRICS ACROSS SAVED SCENARIOS.")
        if st.button("CLEAR ALL SCENARIOS", type="secondary"):
            st.session_state.saved_scenarios = []
            st.rerun()
            
        comp_data = []
        for s in st.session_state.saved_scenarios:
            comp_data.append({
                "Scenario": s['name'], "Total Cost": s['cost'], "Total Interest": s['interest'], "NPV": s['npv']
            })
        df_comp = pd.DataFrame(comp_data).set_index("Scenario")
        
        c_chart1, c_chart2 = st.columns(2)
        with c_chart1:
            st.subheader("TOTAL COST COMPARISON")
            st.bar_chart(df_comp["Total Cost"], color="#111111")
        with c_chart2:
            st.subheader("INTEREST COST COMPARISON")
            st.bar_chart(df_comp["Total Interest"], color="#C5A059")
            
        st.subheader("METRICS TABLE")
        df_disp = df_comp.copy()
        for c in ["Total Cost", "Total Interest", "NPV"]:
            df_disp[c] = df_disp[c].apply(lambda x: f"{x:,.0f}")
        st.dataframe(df_disp, use_container_width=True)
