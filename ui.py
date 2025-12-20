# ui.py
import streamlit as st
import pandas as pd
import time
from random import randint
from db import (
    register_patient, get_patient, get_doctor, get_all_doctors,
    get_chat_requests, add_chat_request, update_chat_request_status,
    get_chat_messages, add_chat_message, get_submissions, add_submission,
    get_feedback, add_feedback, get_notifications, mark_notification_read,
    mark_notifications_read_by_request, add_doctor,
    save_otp, get_otp, increment_otp_attempts, delete_otp, send_verification_email,
    check_password
)
from utils import (
    PRIMARY_BLUE, SECONDARY_BLUE, NAV_BAR_BG, MOCK_SPECIALTIES,
    logout, set_page_style
)

if 'patient_show_register' not in st.session_state:
    st.session_state.patient_show_register = False


def show_notifications():
    user_email = st.session_state.user_profile['email']
    notifications = get_notifications(user_email)
    unread_count = len([n for n in notifications if n['status'] == 'unread'])

    st.markdown(f"## Notifications <span class='notification-badge'>{unread_count}</span>", unsafe_allow_html=True)
    st.markdown('<div class="notification-container">', unsafe_allow_html=True)

    if not notifications:
        st.info("No notifications at this time.")
    else:
        for notification in notifications:
            notification_class = "notification-unread" if notification['status'] == 'unread' else ""
            st.markdown(
                f'<div class="notification-item {notification_class}">'
                f'<span>{notification["message"]} <small>({notification["timestamp"]})</small></span>',
                unsafe_allow_html=True
            )
            if notification['request_id'] and notification['status'] == 'unread':
                if st.button("View", key=f"notification_{notification['id']}"):
                    mark_notification_read(notification['id'])
                    if notification['request_id']:
                        st.session_state.active_chat_request = notification['request_id']
                        st.session_state.portal_view = "LiveChat"
                    st.rerun()
        if st.button("Mark All as Read"):
            for n in notifications:
                if n['status'] == 'unread':
                    mark_notification_read(n['id'])
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def draw_post_login_navbar(view_options):
    st.markdown(
        """
        <div style="background-color: #000000; padding: 0px 20px 0 20px; margin: -1rem -1rem 0 -1rem; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.4);">
            <div style="background: linear-gradient(90deg, #10b981, #34d399); height: 5px;"></div>
        </div>
        """, unsafe_allow_html=True
    )
    st.markdown('<div class="post-login-nav" style="margin-top:0;">', unsafe_allow_html=True)

    cols = st.columns(len(view_options) + 1)
    i = 0
    for display_name, internal_key in view_options.items():
        with cols[i]:
            if st.button(display_name, key=f"nav_btn_{internal_key}", type="secondary"):
                if internal_key in ["ViewDoctors", "Dashboard", "RequestChat", "GiveFeedback", "DoctorDetails",
                                    "ViewUsers", "ViewRequests", "AddDoctor", "ViewFeedback", "AssignChat"]:
                    st.session_state.active_chat_request = None
                if st.session_state.user_profile['role'] == 'admin':
                    st.session_state.admin_view = internal_key
                else:
                    st.session_state.portal_view = internal_key
                st.rerun()
        i += 1

    with cols[-1]:
        if st.button("Logout", key="nav_btn_logout", type="primary"):
            logout()

    st.markdown('</div>', unsafe_allow_html=True)


def show_admin_portal():
    user = st.session_state.user_profile
    st.markdown(
        f'<div class="header-bar" style="background: linear-gradient(90deg, #ef4444, #f87171);"><h1>Admin Portal</h1><p>Welcome, {user["name"]} (Admin)</p></div>',
        unsafe_allow_html=True)

    nav_options = {
        "Add Doctor": "AddDoctor",
        "View Doctor": "ViewDoctors",
        "View User": "ViewUsers",
        "View Feedback": "ViewFeedback",
        "Assign Chat": "AssignChat",
    }
    draw_post_login_navbar(nav_options)

    view = st.session_state.admin_view
    if view == "AddDoctor":
        show_add_doctor_form()
    elif view == "ViewDoctors":
        show_view_doctors_for_portal()
    elif view == "ViewUsers":
        show_view_users()
    elif view == "ViewFeedback":
        show_view_feedback()
    elif view == "AssignChat":
        show_assign_chat_form()


def show_add_doctor_form():
    st.header("Add New Doctor")
    st.markdown("---")
    with st.form("add_doctor_form"):
        doc_id = st.text_input("Doctor ID", value=st.session_state.next_doc_id)
        name = st.text_input("Doctor Name")
        email = st.text_input("Email")
        specialty = st.selectbox("Specialty", MOCK_SPECIALTIES)
        qualification = st.text_input("Qualification")
        mobile = st.text_input("Mobile")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Add Doctor")

        if submitted:
            if not all([doc_id, name, email, specialty, qualification, mobile, password]):
                st.error("Please fill in all fields.")
            elif add_doctor(email, password, name, mobile, specialty, doc_id, qualification):
                st.session_state.next_doc_id = f"{randint(200, 999)}"
                st.success("Doctor added successfully!")
                st.rerun()
            else:
                st.error("Failed to add doctor. Email or ID may already exist.")


def show_login_page():
    if 'nav_view' not in st.session_state:
        st.session_state.nav_view = "Home"
    if 'verify_email' not in st.session_state:
        st.session_state.verify_email = None

    st.markdown(
        """
        <style>
        /* Global */
        .nav-container {background: linear-gradient(90deg, #1d4ed8, #3b82f6); padding: 15px 20px; margin: -1rem -1rem 1rem -1rem; display: flex; justify-content: center; gap: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.2);}
        .nav-button {background: transparent; color: white; font-weight: 500; padding: 8px 16px; border: none; border-radius: 20px; cursor: pointer; transition:0.3s;}
        .nav-button.active {background: #4ac1e2; font-weight: bold;}
        .header-bar {display: flex; align-items: center; gap: 15px; margin-bottom: 20px; padding: 20px; background: #111827; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);}
        .login-container {padding: 30px; background: #1f2937; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.4); color: white; max-width: 500px; margin: 0 auto;}
        .otp-input {width: 50px; height: 50px; text-align: center; font-size: 1.5em; margin: 0 5px; border-radius: 8px; border: 1px solid #4b5563;}

        /* Home Page */
        .hero {background: linear-gradient(135deg, #0ea5e9, #3b82f6); color: white; padding: 60px 20px; border-radius: 16px; text-align: center; margin: 20px 0;}
        .feature-card {background:#1f2937; padding:25px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.3); text-align:center; transition:0.3s; height:100%;}
        .feature-card:hover {transform:translateY(-8px); box-shadow:0 12px 25px rgba(0,0,0,0.4);}
        .stats-card {background:#10b981; color:white; padding:20px; border-radius:12px; text-align:center; font-weight:bold; font-size:1.1rem;}
        .team-card {background:#1f2937; padding:20px; border-radius:12px; text-align:center; box-shadow:0 4px 12px rgba(0,0,0,0.3);}
        .team-card img {width:120px; height:120px; border-radius:50%; object-fit:cover; margin-bottom:15px; border:4px solid #10b981;}
        .contact-form {background:#1f2937; padding:30px; border-radius:12px; box-shadow:0 4px 15px rgba(0,0,0,0.3);}
        .footer {background:#111827; color:#9ca3af; padding:40px 20px; margin-top:60px; font-size:0.95rem;}
        .footer a {color:#60a5fa; text-decoration:none; margin:0 12px;}
        .footer a:hover {text-decoration:underline;}
        </style>
        """, unsafe_allow_html=True
    )

    st.markdown(
        """
        <style>
        .header-bar {
            display: flex; 
            align-items: center; 
            gap: 15px; 
            margin-bottom: 20px; 
            padding: 20px; 
            background: #111827; 
            border-radius: 12px; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        </style>
        """, unsafe_allow_html=True
    )

    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        try:
            st.image("assets/Logo1.png", width=80)
        except Exception as e:
            st.image("https://via.placeholder.com/80?text=Logo", width=80)
    with col_title:
        st.markdown("""
        <h1 style="margin:0; color:#0ea5e9;">E-Healthcare System</h1>
        <p style="margin:0; font-size:1.1em; color:#9ca3af;">Digital Access Portal</p>
        """, unsafe_allow_html=True)

    # Nav
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    nav_cols = st.columns(4)
    nav_options = ["Home", "About Us", "Contact Us", "Login"]
    for i, option in enumerate(nav_options):
        with nav_cols[i]:
            is_active = st.session_state.nav_view == option
            if st.button(option, key=f"nav_{option.lower()}", type="primary" if is_active else "secondary"):
                st.session_state.nav_view = option
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.nav_view == "Home":
        st.markdown("""
        <div class="hero">
            <h1>Healthcare, Reimagined</h1>
            <p style="font-size:1.3rem; max-width:800px; margin:0 auto;">
                AI-powered symptom checker • Live doctor chat • Secure & private
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
            <h2 style="color:#0ea5e9;">Your Health, Our Priority</h2>
            <p style="color:#e5e7eb; font-size:1.1rem;">
                Get instant health insights using advanced AI, connect with verified specialists in real-time, and manage your health securely — all in one platform.
            </p>
            <ul style="color:#d1d5db; font-size:1rem;">
                <li>AI Symptom Checker with 95% accuracy</li>
                <li>Live chat with doctors in under 2 minutes</li>
                <li>End-to-end encrypted patient data</li>
                <li>Available 24/7 on web and mobile</li>
            </ul>
            """, unsafe_allow_html=True)
        with col2:
            st.image("assets/Logo1.png", use_container_width=True)

        st.markdown("---")
        st.markdown("<h2 style='text-align:center; color:#0ea5e9;'>Why Choose E-Healthcare?</h2>",
                    unsafe_allow_html=True)
        cols = st.columns(3)
        features = [
            ("AI Symptom Checker", "Get instant diagnosis suggestions using cutting-edge AI.", "brain"),
            ("Live Doctor Chat", "Connect with verified specialists via secure real-time chat.", "message"),
            ("Secure & Private", "Your data is encrypted and HIPAA-compliant.", "lock")
        ]
        for col, (title, desc, icon) in zip(cols, features):
            with col:
                st.markdown(f"""
                <div class="feature-card">
                    <h3 style="color:#10b981;">{icon} {title}</h3>
                    <p style="color:#d1d5db;">{desc}</p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("<h2 style='text-align:center; color:#0ea5e9;'>Trusted by Thousands</h2>", unsafe_allow_html=True)
        stats_cols = st.columns(4)
        stats = [("50K+", "Active Patients"), ("200+", "Verified Doctors"), ("4.9", "Average Rating"),
                 ("24/7", "Support")]
        for col, (num, label) in zip(stats_cols, stats):
            with col:
                st.markdown(f"""
                <div class="stats-card">
                    <h3>{num}</h3>
                    <p>{label}</p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("<h2 style='text-align:center; color:#0ea5e9;'>Ready to Get Started?</h2>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            if st.button("Login Now", type="primary", use_container_width=True):
                st.session_state.nav_view = "Login"
                st.rerun()

    elif st.session_state.nav_view == "About Us":
        st.markdown("<h1 style='text-align:center; color:#0ea5e9;'>About E-Healthcare</h1>", unsafe_allow_html=True)
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <h3>Our Mission</h3>
            <p style="color:#e5e7eb;">
                To democratize healthcare by providing instant, accurate, and secure access to medical expertise using AI and real-time communication.
            </p>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <h3>Our Vision</h3>
            <p style="color:#e5e7eb;">
                A world where quality healthcare is accessible to everyone, anytime, anywhere.
            </p>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("<h2 style='text-align:center; color:#0ea5e9;'>Our Core Values</h2>", unsafe_allow_html=True)
        vals = st.columns(3)
        values = [
            ("Trust", "We prioritize patient privacy and data security."),
            ("Innovation", "Leveraging AI to improve healthcare delivery."),
            ("Accessibility", "Healthcare for all, without barriers.")
        ]
        for col, (title, desc) in zip(vals, values):
            with col:
                st.markdown(f"""
                <div style="background:#1f2937; padding:20px; border-radius:12px; text-align:center;">
                    <h4 style="color:#10b981;">{title}</h4>
                    <p style="color:#d1d5db; font-size:0.95rem;">{desc}</p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("<h2 style='text-align:center; color:#0ea5e9;'>Meet Our Team</h2>", unsafe_allow_html=True)

        team_cols = st.columns(3)
        team = [
            ("Dr. Md Afzal", "Chief Medical Officer", "assets/Profile.jpg"),
            ("Dr. Arshad Ali", "Head of AI Research", "assets/Profile.jpg"),
            ("Dr. Ajaj Ahmad", "Lead Developer", "assets/Profile.jpg")
        ]

        for col, (name, role, img_path) in zip(team_cols, team):
            with col:
                # Use st.image() — this is the ONLY reliable way
                try:
                    st.image(img_path, width=120, use_container_width=False)
                except:
                    st.image("https://via.placeholder.com/120?text=No+Image", width=120)

                st.markdown(f"""
                <div style="text-align:center; margin-top:10px;">
                    <h4 style="color:#0ea5e9; margin:5px 0;">{name}</h4>
                    <p style="color:#9ca3af; font-size:0.9rem; margin:0;">{role}</p>
                </div>
                """, unsafe_allow_html=True)

    elif st.session_state.nav_view == "Contact Us":
        st.markdown("<h1 style='text-align:center; color:#0ea5e9;'>Get in Touch</h1>", unsafe_allow_html=True)
        st.markdown("---")

        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("""
            <div class="contact-form">
                <h3>Send us a Message</h3>
                <form>
                    <input type="text" placeholder="Your Name" style="width:100%; padding:12px; margin:10px 0; border-radius:8px; border:1px solid #4b5563; background:#111827; color:white;">
                    <input type="email" placeholder="Your Email" style="width:100%; padding:12px; margin:10px 0; border-radius:8px; border:1px solid #4b5563; background:#111827; color:white;">
                    <textarea placeholder="Your Message" style="width:100%; height:120px; padding:12px; margin:10px 0; border-radius:8px; border:1px solid #4b5563; background:#111827; color:white;"></textarea>
                    <button type="submit" style="background:#10b981; color:white; padding:12px 24px; border:none; border-radius:8px; cursor:pointer; font-weight:bold;">Send Message</button>
                </form>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <h3>Contact Information</h3>
            <p><strong>Email:</strong> support@ehealthcare.com</p>
            <p><strong>Phone:</strong> +91 72600 23491</p>
            <p><strong>Address:</strong> 123 Health Street, Mumbai, India</p>
            <p><strong>Hours:</strong> 24/7 Support</p>
            """, unsafe_allow_html=True)
            st.markdown("""
            <div style="background:#1f2937; padding:15px; border-radius:12px; margin-top:20px;">
                <iframe src="https://www.google.com/maps/embed?pb=..." width="100%" height="200" style="border:0; border-radius:8px;" allowfullscreen="" loading="lazy"></iframe>
            </div>
            """, unsafe_allow_html=True)

    elif st.session_state.nav_view == "Login":
        st.markdown("<h1 style='text-align:center; color:#0ea5e9;'>Welcome Back</h1>", unsafe_allow_html=True)
        if st.session_state.verify_email:
            show_verification_page()
        else:
            show_login_options()

    st.markdown("---")
    st.markdown("""
    <div class="footer">
        <div style="max-width:1200px; margin:0 auto; text-align:center;">
            <p><strong>E-Healthcare System</strong> © 2025. All rights reserved.</p>
            <p>
                <a href="#">Privacy Policy</a> • 
                <a href="#">Terms of Service</a> • 
                <a href="#">Help Center</a>
            </p>
            <p style="margin-top:15px;">
                <a href="#">Facebook</a> • 
                <a href="#">Twitter</a> • 
                <a href="#">LinkedIn</a>
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)



def show_verification_page():
    email = st.session_state.verify_email
    st.markdown(f"<h3 style='text-align:center;'>Verify Your Email: <strong>{email}</strong></h3>",
                unsafe_allow_html=True)
    st.info("A 6-digit code has been sent. Check your inbox/spam.")

    with st.form("verify_form"):
        cols = st.columns(6)
        otp_digits = []
        for i in range(6):
            with cols[i]:
                digit = st.text_input("", max_chars=1, key=f"otp_{i}", placeholder=str(i + 1),
                                      label_visibility="collapsed", help=None)
                otp_digits.append(digit)

        col1, col2 = st.columns([1, 1])
        with col1:
            verify_btn = st.form_submit_button("Verify", type="primary")
        with col2:
            resend_btn = st.form_submit_button("Resend OTP")

        if verify_btn:
            entered_otp = "".join(otp_digits)
            if len(entered_otp) != 6 or not entered_otp.isdigit():
                st.error("Enter a valid 6-digit code.")
            else:
                stored = get_otp(email)
                if stored and entered_otp == stored["otp"]:
                    delete_otp(email)
                    user = get_patient(email)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user_profile = user
                        st.session_state.portal_view = "Dashboard"
                        st.success("Email verified! Logging you in...")
                        st.rerun()
                else:
                    increment_otp_attempts(email)
                    st.error("Invalid OTP. Try again.")

        if resend_btn:
            otp = str(randint(100000, 999999))
            save_otp(email, otp)
            if send_verification_email(email, otp):
                st.success("New OTP sent!")
            else:
                st.error("Failed to send OTP.")



def show_login_options():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center; color:#0ea5e9;'>Login Access</h2>", unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Patient Login", use_container_width=True):
            st.session_state.selected_role = 'patient'
            st.session_state.patient_show_register = False
    with col2:
        if st.button("Doctor Login", use_container_width=True):
            st.session_state.selected_role = 'doctor'
    with col3:
        if st.button("Admin Login", use_container_width=True):
            st.session_state.selected_role = 'admin'

    role = st.session_state.get("selected_role", "patient")
    st.info(f"Selected: **{role.upper()}**")

    if role == "patient":
        if st.session_state.patient_show_register:
            with st.form("patient_register_form"):
                st.subheader("Patient Registration")
                name = st.text_input("Full Name *")
                email = st.text_input("Email *")
                mobile = st.text_input("Phone Number (10 digits) *")
                password = st.text_input("Password *", type="password")
                confirm = st.text_input("Confirm Password *", type="password")

                col1, col2 = st.columns(2)
                with col1:
                    register_btn = st.form_submit_button("Register")
                with col2:
                    if st.form_submit_button("Back to Login"):
                        st.session_state.patient_show_register = False
                        st.rerun()

                if register_btn:
                    if not all([name, email, mobile, password, confirm]):
                        st.error("All fields are required.")
                    elif password != confirm:
                        st.error("Passwords do not match.")
                    elif len(mobile) != 10 or not mobile.isdigit():
                        st.error("Enter a valid 10-digit phone number.")
                    elif register_patient(email, password, name, mobile):
                        otp = str(randint(100000, 999999))
                        save_otp(email, otp)
                        if send_verification_email(email, otp):
                            st.session_state.verify_email = email
                            st.success("OTP sent! Check your email.")
                            st.rerun()
                        else:
                            st.error("Failed to send OTP.")
                    else:
                        st.warning(
                            "This **email is already registered**. Please **log in** or use a **different email**.")

        else:
            with st.form("patient_login_form"):
                st.subheader("Patient Login")
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")

                col1, col2 = st.columns(2)
                with col1:
                    login_btn = st.form_submit_button("Login")
                with col2:
                    if st.form_submit_button("Register"):
                        st.session_state.patient_show_register = True
                        st.rerun()

                if login_btn:
                    user = get_patient(email)
                    if user and check_password(password, user["password"]):
                        st.session_state.logged_in = True
                        st.session_state.user_profile = user
                        st.session_state.portal_view = "Dashboard"
                        st.rerun()
                    else:
                        st.error("Invalid credentials.")

    elif role == "doctor":
        with st.form("doctor_form"):
            st.subheader("Doctor Login")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                user = get_doctor(email)
                if user and check_password(password, user["password"]):
                    st.session_state.logged_in = True
                    st.session_state.user_profile = user
                    st.session_state.portal_view = "Dashboard"
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

    elif role == "admin":
        with st.form("admin_form"):
            st.subheader("Admin Login")
            email = st.text_input("Email", value="admin@app.com")
            password = st.text_input("Password", type="password", value="admin")
            if st.form_submit_button("Login"):
                if email == "admin@app.com" and password == "admin":
                    st.session_state.logged_in = True
                    st.session_state.user_profile = {"email": email, "role": "admin", "name": "System Admin"}
                    st.rerun()
                else:
                    st.error("Invalid admin credentials.")

    st.markdown('</div>', unsafe_allow_html=True)



def show_doctor_portal():
    user = st.session_state.user_profile
    st.markdown(
        f'<div class="header-bar" style="background: linear-gradient(90deg, #1d4ed8, #3b82f6);"><h1>Doctor Portal</h1><p>Welcome, {user["name"]} (Doctor)</p></div>',
        unsafe_allow_html=True)

    nav_options = {
        "Pending Requests": "Dashboard",
        "Details": "DoctorDetails",
        "View User": "ViewUsers",
        "View Request": "ViewRequests"
    }
    draw_post_login_navbar(nav_options)

    view = st.session_state.portal_view
    if view == "Dashboard":
        show_doctor_dashboard()
    elif view == "LiveChat":
        show_live_chat_interface()
    elif view == "DoctorDetails":
        show_doctor_details()
    elif view == "ViewUsers":
        show_view_users()
    elif view == "ViewRequests":
        show_view_requests()
    else:
        show_doctor_dashboard()


def show_doctor_dashboard():
    show_notifications()

    try:
        doc = st.session_state.user_profile
        st.markdown(
            f'''
            <h2 style="color:#0ea5e9; text-align:center; margin-bottom:0;">Pending Request</h2>
            <p style="text-align:center; margin-top:5px; font-size:1rem; color:#e5e7eb;">
                Requests for Dr. {doc.get("name", "Unknown")} ({doc.get("specialty", "N/A")}).
            </p>
            ''',
            unsafe_allow_html=True
        )
        st.markdown("---")
    except Exception as e:
        st.error(f"Profile error: {e}")
        return

    try:
        my_email = doc.get("email", "")
        if not my_email:
            st.error("Doctor email not found.")
            return

        all_requests = get_chat_requests() or []
        pending = [
            r for r in all_requests
            if r.get("doctor_email") == my_email and r.get("status") == "Pending"
        ]
    except Exception as e:
        st.error(f"Failed to load requests: {e}")
        return

    if not pending:
        st.success("No pending requests.")
        return

    query_params = st.query_params
    if "accept_request" in query_params:
        req_id = query_params["accept_request"]
        try:
            if update_chat_request_status(req_id, "Accepted"):
                st.session_state.active_chat_request = req_id
                st.session_state.portal_view = "LiveChat"
                st.success(f"Request {req_id} accepted!")
            else:
                st.error("Failed to accept request.")
        except Exception as e:
            st.error(f"Accept error: {e}")
        finally:
            st.query_params.clear()
            st.rerun()

    html = """
    <style>
    .pending-table {width:100%; max-width:100%; border-collapse:collapse; font-family:Arial, sans-serif; margin:0 auto;}
    .pending-table th {
        background:#0ea5e9; color:white; padding:10px 8px; text-align:center; font-weight:bold;
        font-size:0.95rem; border-right:1px solid #0891b2;
    }
    .pending-table th:last-child {border-right:none;}
    .pending-table td {
        padding:10px 8px; border-bottom:1px solid #374151; text-align:center;
        font-size:0.95rem; color:#e5e7eb; vertical-align:middle;
    }
    .pending-table tr:hover {background:#1f2937;}
    .accept-btn {
        background:#10b981; color:white; border:none; padding:6px 14px;
        border-radius:6px; cursor:pointer; font-weight:bold; font-size:0.9rem;
    }
    .accept-btn:hover {background:#059669;}
    </style>
    <table class="pending-table">
      <thead>
        <tr>
          <th>Accept</th><th>RId</th><th>PId</th><th>PName</th>
          <th>DId</th><th>DName</th><th>Flag</th><th>Email</th>
        </tr>
      </thead>
      <tbody>
    """

    for r in pending:
        html += f"""
        <tr>
          <td>
            <form method="get" style="margin:0; display:inline;">
              <input type="hidden" name="accept_request" value="{r.get('request_id', '')}">
              <button type="submit" class="accept-btn">Yes</button>
            </form>
          </td>
          <td>{r.get('request_id', 'N/A')}</td>
          <td>{r.get('patient_id', 'PN/A')}</td>
          <td>{r.get('patient_name', 'N/A')}</td>
          <td>{r.get('doctor_id', 'N/A')}</td>
          <td>{r.get('doctor_name', 'N/A')}<br><small style="color:#9ca3af;">{r.get('specialty', '')}</small></td>
          <td>{r.get('flag', 'N')}</td>
          <td><a href="mailto:{r.get('patient_email', '')}" style="color:#60a5fa; text-decoration:none;">{r.get('patient_email', 'N/A')}</a></td>
        </tr>
        """

    html += """
      </tbody>
    </table>
    <p style="text-align:center; margin-top:20px; color:#9ca3af; font-size:0.9rem;">
        Click 'Yes' to accept a pending request and start a live chat session.
    </p>
    """

    st.markdown(html, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Patient Details")

    for idx, r in enumerate(pending):
        with st.expander(f"Request ID: {r.get('request_id', 'N/A')} — {r.get('patient_name', 'N/A')}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Patient ID**", r.get('patient_id', 'N/A'))
                st.write("**Name**", r.get('patient_name', 'N/A'))
                st.write("**Email**", r.get('patient_email', 'N/A'))
                st.write("**Mobile**", r.get('patient_mobile', 'N/A') or "Not provided")
            with col2:
                st.write("**Specialty**", r.get('specialty', 'N/A'))
                st.write("**Doctor**", r.get('doctor_name', 'N/A'))
                st.write("**Timestamp**", r.get('timestamp', 'N/A'))

            st.markdown("**Query / Concern:**")
            st.info(r.get('query', 'No query provided.'))

            if st.button("Accept & Start Chat", key=f"accept_expander_{r.get('request_id')}"):
                try:
                    update_chat_request_status(r.get('request_id'), "Accepted")
                    st.session_state.active_chat_request = r.get('request_id')
                    st.session_state.portal_view = "LiveChat"
                    st.success("Chat started!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to accept: {e}")


def show_doctor_details():
    u = st.session_state.user_profile
    st.header("Profile")
    st.metric("Name", u.get('name', 'N/A'))
    st.metric("Specialty", u.get('specialty', 'N/A'))
    st.metric("ID", u.get('doc_id', 'N/A'))


def show_view_requests():
    st.header("All Chat Requests")
    requests = get_chat_requests()
    if not requests:
        st.info("No chat requests found.")
        return

    data = []
    for r in requests:
        status_color = {
            "Pending": "#f59e0b",
            "Accepted": "#10b981",
            "Closed": "#ef4444"
        }.get(r.get('status', ''), "#6b7280")

        data.append({
            "ID": r.get('request_id', 'N/A'),
            "Patient": r.get('patient_name', 'N/A'),
            "Doctor": r.get('doctor_name', 'N/A'),
            "Specialty": r.get('specialty', 'N/A'),
            "Query": (r.get('query', '')[:50] + "..." if len(r.get('query', '')) > 50 else r.get('query', '')),
            "Status": f"<span style='color:{status_color}; font-weight:bold;'>{r.get('status', 'N/A')}</span>",
            "Time": r.get('timestamp', 'N/A')
        })

    df = pd.DataFrame(data)
    st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)

    doctor_email = st.session_state.user_profile.get('email', '')
    pending_for_me = [r for r in requests if r.get('doctor_email') == doctor_email and r.get('status') == 'Pending']

    if pending_for_me:
        st.markdown("---")
        st.subheader("Accept Pending Request")
        for r in pending_for_me:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(
                    f"**{r.get('request_id', 'N/A')}** – {r.get('patient_name', 'N/A')} ({r.get('query', '')[:60]}...)")
            with col2:
                if st.button("Accept", key=f"accept_doc_{r.get('request_id', '')}"):
                    try:
                        update_chat_request_status(r.get('request_id'), 'Accepted')
                        st.session_state.active_chat_request = r.get('request_id')
                        st.session_state.portal_view = "LiveChat"
                        st.rerun()
                    except:
                        st.error("Failed to accept.")


def show_patient_portal():
    user = st.session_state.user_profile
    st.markdown(
        f'<div class="header-bar" style="background: linear-gradient(90deg, #10b981, #34d399);"><h1>Patient Portal</h1><p>Welcome, {user["name"]} (Patient)</p></div>',
        unsafe_allow_html=True)

    nav_options = {
        "View Doctors": "ViewDoctors",
        "Symptom Check": "Dashboard",
        "Request Chat": "RequestChat",
        "Give Feedback": "GiveFeedback"
    }
    draw_post_login_navbar(nav_options)
    show_notifications()

    view = st.session_state.portal_view
    if view == "LiveChat":
        show_live_chat_interface()
    elif view == "Dashboard":
        show_patient_symptom_checker()
    elif view == "ViewDoctors":
        show_view_doctors_for_portal()
    elif view == "RequestChat":
        show_request_chat_form()
    elif view == "GiveFeedback":
        show_feedback_form()


def show_live_chat_interface():
    rid = st.session_state.active_chat_request
    if not rid:
        st.error("No active chat selected.")
        return

    req = next((r for r in get_chat_requests() if r.get('request_id') == rid), None)
    if not req or req.get('status') == 'Closed':
        st.error("This chat is closed.")
        st.session_state.active_chat_request = None
        st.rerun()
        return

    interlocutor = req.get('doctor_name') if st.session_state.user_profile['role'] == 'patient' else req.get(
        'patient_name')
    st.markdown(f"### Chat with **{interlocutor}**")

    messages = get_chat_messages(rid)
    st.markdown('<div class="chat-messages">', unsafe_allow_html=True)
    for m in messages:
        sender_name = m.get('sender', 'Unknown')
        is_user = sender_name == st.session_state.user_profile.get('name')
        cls = "user-message" if is_user else "doctor-message"
        st.markdown(
            f'<div class="chat-message {cls}">'
            f'<div class="message-sender">{sender_name}</div>'
            f'<div>{m.get("text", "")}</div>'
            f'<small>{m.get("timestamp", "")}</small>'
            f'</div>',
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

    with st.form("chat_form", clear_on_submit=True):
        msg = st.text_area("Type your message...", height=80)
        col1, col2 = st.columns([1, 4])
        with col1:
            send = st.form_submit_button("Send")
        with col2:
            end = st.form_submit_button("End Session")
        if send and msg.strip():
            add_chat_message(rid, st.session_state.user_profile.get('name'), st.session_state.user_profile.get('role'),
                             msg)
            st.rerun()
        if end:
            update_chat_request_status(rid, "Closed")
            st.session_state.active_chat_request = None
            st.success("Chat ended.")
            st.rerun()


def show_view_doctors_for_portal():
    docs = get_all_doctors()
    df = pd.DataFrame([{
        "Name": d.get('name', 'N/A'), "Specialty": d.get('specialty', 'N/A'),
        "Qualification": d.get('qualification', 'N/A'), "ID": d.get('doc_id', 'N/A'), "Email": d.get('email', 'N/A')
    } for d in docs])
    st.dataframe(df, use_container_width=True)


def show_patient_symptom_checker():
    st.subheader("Symptom Checker")
    with st.form("symptom_form"):
        sym = st.text_area("Describe your symptoms")
        if st.form_submit_button("Analyze"):
            pred = "Consult Orthopedics" if "knee" in sym.lower() else "Consult General Physician"
            add_submission({"date": time.strftime("%Y-%m-%d %H:%M:%S"), "symptoms": sym, "prediction": pred,
                            "patient_email": st.session_state.user_profile.get('email')})
            st.success(pred)


def show_request_chat_form():
    st.subheader("Request Chat with Doctor")

    with st.form("request_chat_form"):
        specialty = st.selectbox("Specialty", ["--"] + MOCK_SPECIALTIES)

        docs = [d for d in get_all_doctors() if d.get('specialty') == specialty]
        if specialty == "--" or not docs:
            doctor_options = ["No doctors available"]
            doc = doctor_options[0]
        else:
            doctor_options = [f"{d.get('name', 'N/A')} ({d.get('doc_id', 'N/A')})" for d in docs]
            doc = st.selectbox("Doctor", doctor_options)

        query = st.text_area("Reason for consultation", placeholder="Describe your concern...")

        submitted = st.form_submit_button("Submit Request")

        if submitted:
            if specialty == "--":
                st.error("Please select a specialty.")
            elif "No doctors available" in doc:
                st.error("No doctor available for selected specialty.")
            elif not query.strip():
                st.error("Please enter a reason for consultation.")
            else:
                try:
                    doc_id = doc.split(' (')[1][:-1]
                    d = next(d for d in docs if d.get('doc_id') == doc_id)
                    req = {
                        "request_id": st.session_state.next_request_id,
                        "patient_email": st.session_state.user_profile.get('email'),
                        "patient_name": st.session_state.user_profile.get('name'),
                        "patient_id": "P" + st.session_state.user_profile.get('mobile', '000')[-6:],
                        "doctor_email": d.get('email'),
                        "doctor_name": d.get('name'),
                        "doctor_id": d.get('doc_id'),
                        "qualification": d.get('qualification'),
                        "specialty": specialty,
                        "query": query,
                        "status": "Pending",
                        "flag": "N",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    add_chat_request(req)
                    st.session_state.next_request_id += 1
                    st.success("Request sent successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to send request: {e}")


def show_feedback_form():
    st.subheader("Give Feedback")
    with st.form("feedback_form"):
        fb = st.text_area("Your feedback")
        if st.form_submit_button("Submit"):
            try:
                add_feedback({"user_email": st.session_state.user_profile.get('email'), "feedback": fb,
                              "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})
                st.success("Thank you!")
            except:
                st.error("Failed to submit feedback.")


def show_view_users():
    st.header("All Patients")
    try:
        c = st.session_state.patients_conn.cursor()
        c.execute('SELECT email, name, mobile, patient_id FROM patients')
        patients = [{"email": r[0], "name": r[1], "mobile": r[2], "patient_id": r[3]} for r in c.fetchall()]
        df = pd.DataFrame(patients)
        st.dataframe(df)
    except Exception as e:
        st.error(f"DB Error: {e}")


def show_view_feedback():
    st.header("User Feedback")
    try:
        fb = get_feedback()
        df = pd.DataFrame(fb)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error loading feedback: {e}")


def show_assign_chat_form():
    st.header("Assign Chat (Admin)")
    try:
        c = st.session_state.patients_conn.cursor()
        patients = c.execute('SELECT email, name FROM patients').fetchall()
        doctors = get_all_doctors()
        p_email = st.selectbox("Patient", [f"{p[1]} ({p[0]})" for p in patients])
        d_email = st.selectbox("Doctor", [f"{d['name']} ({d['email']})" for d in doctors])
        if st.button("Assign"):
            p_email = p_email.split(' (')[1][:-1]
            d_email = d_email.split(' (')[1][:-1]
            st.query_params["assign_chat"] = "1"
            st.query_params["patient_email"] = p_email
            st.query_params["doctor_email"] = d_email
            st.rerun()
    except Exception as e:
        st.error(f"Assign error: {e}")

__all__ = [
    'show_login_page', 'show_patient_portal',
    'show_doctor_portal', 'show_admin_portal'
]