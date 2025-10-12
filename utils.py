
import streamlit as st
import random
import time
from db import get_users, add_user, add_chat_request, add_submission, add_chat_message, get_db_cursor, remove_user

PRIMARY_BLUE = 'rgb(0, 102, 180)'
SECONDARY_BLUE = 'rgb(50, 150, 250)'
NAV_BAR_BG = '#1e1e1e'

MOCK_SPECIALTIES = ["Cardiology", "Orthopedics (Bone)", "Pulmonology (Lung)", "Nephrology (Kidney)", "Neurology", "Pediatrics"]

def set_page_style():
    st.markdown(f"""
    <style>
    .stApp {{
        background-color: #000000; /* Changed from #f0f8ff to black */
        font-family: 'Inter', sans-serif;
        color: #ffffff; /* Added to ensure default text is white for readability */
    }}
    .header-bar {{
        background: linear-gradient(90deg, {PRIMARY_BLUE}, {SECONDARY_BLUE});
        padding: 20px;
        color: white;
        text-align: left;
        margin: -1rem -1rem 1rem -1rem;
        border-radius: 8px 8px 0 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        display: flex;
        align-items: center;
        gap: 20px;
    }}
    .header-bar img {{
        border-radius: 50%;
        background: #000000; /* Changed from white to black */
        padding: 5px;
        height: 80px;
        width: 80px;
    }}
    .header-bar h1 {{
        font-size: 2.5em;
        font-weight: 800;
        letter-spacing: 2px;
        margin: 0;
        flex-grow: 1;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.3);
    }}
    .notification-badge {{
        background-color: #ef4444;
        color: white;
        border-radius: 50%;
        padding: 2px 8px;
        font-size: 0.8em;
        font-weight: bold;
        margin-left: 5px;
        vertical-align: middle;
    }}
    .notification-container {{
        background-color: #000000; /* Changed from white to black */
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        padding: 15px;
        margin-bottom: 20px;
        color: #ffffff; /* Added to ensure text is readable */
    }}
    .notification-item {{
        padding: 10px;
        border-bottom: 1px solid #333; /* Changed from #eee to darker gray for contrast */
    }}
    .notification-item:last-child {{
        border-bottom: none;
    }}
    .notification-unread {{
        background-color: #1e40af; /* Changed from #e1f5fe to a darker blue for contrast */
        font-weight: bold;
        color: #ffffff; /* Added for readability */
    }}
    .st-emotion-cache-1ftrux {{
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
        border-top: 5px solid {PRIMARY_BLUE};
        padding: 20px;
        background-color: #000000; /* Changed from white to black */
        color: #ffffff; /* Added for readability */
    }}
    .stButton>button {{
        border-radius: 8px;
        border: none;
        transition: all 0.2s;
    }}
    .st-emotion-cache-nahz7x > button > div > p {{
        font-weight: bold !important;
        font-size: 1.1em !important;
        color: white !important;
        line-height: 1.2 !important;
    }}
    .st-emotion-cache-nahz7x:has(> button > div > p) {{
        width: 150px;
        height: 150px;
        margin: 10px auto;
        border-radius: 50%;
        background: radial-gradient(circle, {SECONDARY_BLUE} 0%, {PRIMARY_BLUE} 100%);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.4);
        border: 4px solid #000000; /* Changed from #fff to black */
    }}
    .st-emotion-cache-nahz7x:hover {{
        transform: scale(1.05);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.5);
    }}
    .login-container {{
        text-align: center;
        margin-top: 30px;
        background-color: #000000; /* Changed from #f8fafc to black */
        color: #ffffff; /* Added for readability */
    }}
    .login-container h2 {{
        margin-bottom: 25px;
        color: {PRIMARY_BLUE};
    }}
    .post-login-nav {{
        display: flex;
        justify-content: space-between;
        background-color: {NAV_BAR_BG};
        padding: 10px 20px;
        margin: -1rem -1rem 1rem -1rem;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.4);
    }}
    .post-login-nav .stButton > button {{
        background: transparent;
        border: none;
        color: white;
        padding: 8px 15px;
        font-weight: 600;
        cursor: pointer;
        transition: background-color 0.2s;
        border-radius: 4px;
        width: 100%;
    }}
    .post-login-nav .stButton > button:hover {{
        background-color: #333;
    }}
    #nav_btn_logout {{
        background-color: #ef4444;
    }}
    #nav_btn_logout:hover {{
        background-color: #dc2626;
    }}
    .accept-link {{
        color: {PRIMARY_BLUE};
        font-weight: bold;
        cursor: pointer;
    }}
    .accept-link:hover {{
        text-decoration: underline;
    }}
    .chat-container {{
        background-color: #000000; /* Changed from white to black */
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
        padding: 20px;
        color: #ffffff; /* Added for readability */
    }}
    .chat-messages {{
        height: 400px;
        overflow-y: auto;
        padding: 10px;
        border: 1px solid #333; /* Changed from #ccc to darker gray for contrast */
        border-radius: 8px;
        margin-bottom: 15px;
        background-color: #1e1e1e; /* Changed from #f9f9f9 to dark gray for contrast */
        color: #ffffff; /* Added for readability */
    }}
    .chat-message {{
        margin-bottom: 15px;
        padding: 10px;
        border-radius: 8px;
        max-width: 80%;
    }}
    .user-message {{
        background-color: #1e40af; /* Changed from #e1f5fe to darker blue for contrast */
        margin-left: auto;
        text-align: right;
        color: #ffffff; /* Added for readability */
    }}
    .doctor-message {{
        background-color: #166534; /* Changed from #e8f5e9 to darker green for contrast */
        margin-right: auto;
        text-align: left;
        color: #ffffff; /* Added for readability */
    }}
    .message-sender {{
        font-weight: bold;
        font-size: 0.8em;
        color: #d1d5db; /* Changed from #555 to light gray for readability */
    }}
    .chat-input-area {{
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 0;
    }}
    .chat-textarea {{
        flex-grow: 1;
        border-radius: 5px;
        border: 1px solid #333; /* Changed from #ccc to darker gray */
        padding: 8px;
        min-height: 40px;
        background-color: #1e1e1e; /* Added for consistency */
        color: #ffffff; /* Added for readability */
    }}
    .chat-submit-btn {{
        background-color: {PRIMARY_BLUE};
        color: white;
        padding: 8px 15px;
        border-radius: 5px;
        cursor: pointer;
    }}
    .stDataFrame table thead th {{
        background-color: #4ac1e2 !important;
        color: white !important;
        font-weight: bold !important;
        border-bottom: none !important;
    }}
    .stDataFrame table tbody tr:nth-child(even) {{
        background-color: #333333; /* Changed from #f7f7f7 to darker gray */
        color: #ffffff; /* Added for readability */
    }}
    .stDataFrame table tbody tr:hover {{
        background-color: #1e40af !important; /* Changed from #e0f7fa to darker blue */
        color: #ffffff !important; /* Added for readability */
    }}
    </style>
    """, unsafe_allow_html=True)

def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = None
    if 'selected_role' not in st.session_state:
        st.session_state.selected_role = 'patient'
    if 'admin_view' not in st.session_state:
        st.session_state.admin_view = "AddDoctor"
    if 'portal_view' not in st.session_state:
        st.session_state.portal_view = "Dashboard"
    if 'next_doc_id' not in st.session_state:
        st.session_state.next_doc_id = f"{random.randint(200, 999)}"
    if 'next_request_id' not in st.session_state:
        c = get_db_cursor()
        c.execute('SELECT MAX(request_id) FROM chat_requests')
        max_id = c.fetchone()[0]
        st.session_state.next_request_id = (max_id + 1) if max_id else 10001
    if 'active_chat_request' not in st.session_state:
        st.session_state.active_chat_request = None

    c = get_db_cursor()
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        initial_users = [
            ("admin@app.com", "admin", "System Admin", "N/A", None, None, None),
            ("doctor@app.com", "doctor", "Dr. Afzal", "7260023491", "Cardiology", "101", "MD"),

        ]
        for user in initial_users:
            add_user(*user)

        initial_requests = [
            {
                "request_id": 10000,
                "patient_email": "patient@app.com",
                "doctor_email": "doctor@app.com",
                "specialty": "Cardiology",
                "doctor_name": "Dr. Afzal",
                "doctor_id": "101",
                "qualification": "MD",
                "query": "Follow-up question on blood test results.",
                "status": "Accepted",
                "patient_name": "Patient User",
                "patient_id": "P5555678",
                "flag": "N",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "request_id": 10001,
                "patient_email": "jdoe@user.com",
                "doctor_email": "doctor2@app.com",
                "specialty": "Cardiology",
                "doctor_name": "Dr. Sadab",
                "doctor_id": "103",
                "qualification": "MD, PhD",
                "query": "Chest pain during exercise.",
                "status": "Pending",
                "patient_name": "Arshad",
                "patient_id": "P5559012",
                "flag": "N",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "request_id": 10002,
                "patient_email": "jdoe@user.com",
                "doctor_email": "doc_ortho@app.com",
                "specialty": "Orthopedics (Bone)",
                "doctor_name": "Dr. Ali",
                "doctor_id": "102",
                "qualification": "MBBS, MS",
                "query": "Knee pain after a fall.",
                "status": "Pending",
                "patient_name": "Aarju",
                "patient_id": "P5559012",
                "flag": "N",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
        for req in initial_requests:
            add_chat_request(req)

        add_submission({
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "symptoms": "Severe pain in right knee after a fall yesterday.",
            "prediction": "AI suggests consulting Orthopedics immediately for potential ligament damage.",
            "patient_email": "jdoe@user.com"
        })

        initial_messages = [
            (10000, "Dr. Afzal", "doctor", "Hello, thank you for submitting your chat request. I am Dr.Afzal. How can I assist you with your follow-up results?", "10:00 AM"),
            (10000, "Patient User", "patient", "Hello Dr. Carter. I received the lab report link and I'm a bit concerned about my high cholesterol reading. What steps should I take next?", "10:05 AM")
        ]
        for msg in initial_messages:
            add_chat_message(*msg)

        st.session_state.next_request_id = 10003

def login_attempt(email, role):
    users = get_users()
    if email in users and users[email]["role"] == role:
        st.session_state.logged_in = True
        st.session_state.user_profile = users[email]
        st.session_state.user_profile['email'] = email
        st.session_state.portal_view = "Dashboard"
        st.rerun()
    else:
        st.error("Invalid credentials or role selected.")

def logout():
    st.session_state.logged_in = False
    st.session_state.user_profile = None
    st.session_state.selected_role = 'patient'
    st.session_state.admin_view = "AddDoctor"
    st.session_state.portal_view = "Dashboard"
    st.session_state.active_chat_request = None
    st.rerun()

def add_doctor(doc_id, name, email, specialty, qualification, mobile):
    if add_user(email, "doctor", name, mobile, specialty, doc_id, qualification):
        st.success(f"Successfully added Doctor: **{name}** (ID: {doc_id})")
        return True
    else:
        st.error(f"Error: User with email **{email}** or ID **{doc_id}** already exists.")
        return False

def remove_doctor(email):
    name = remove_user(email)
    if name:
        st.warning(f"Successfully removed Doctor: **{name}**")
        return True
    else:
        st.error(f"Error: Doctor with email **{email}** not found.")
        return False
