import streamlit as st
from random import random
import pandas as pd
import time
from db import (get_users, add_user, remove_user, get_chat_requests, add_chat_request,
                update_chat_request_status, get_chat_messages, add_chat_message,
                get_submissions, add_submission, get_feedback, add_feedback,
                get_notifications, mark_notification_read, mark_notifications_read_by_request)
from utils import PRIMARY_BLUE, SECONDARY_BLUE, NAV_BAR_BG, MOCK_SPECIALTIES, login_attempt, logout, add_doctor, \
    remove_doctor

# Define color constants (override if different in utils.py)
PRIMARY_BLUE = "#4ac1e2"
SECONDARY_BLUE = "#3b82f6"


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
            for notification in notifications:
                if notification['status'] == 'unread':
                    mark_notification_read(notification['id'])
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def draw_post_login_navbar(view_options):
    st.markdown(
        """
        <div style="background-color: #000000; padding: 0px 20px 0 20px; margin: -1rem -1rem 0 -1rem; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.4);">
            <div style="background-color: #000000; height: 5px;"></div>
            <div style="background: linear-gradient(90deg, #10b981, #34d399); height: 5px;"></div>
        </div>
        """, unsafe_allow_html=True
    )
    st.markdown('<div class="post-login-nav" style="margin-top:0;">', unsafe_allow_html=True)

    cols = st.columns(len(view_options) + 1)
    i = 0
    for display_name, internal_key in view_options.items():
        with cols[i]:
            if st.button(
                    display_name,
                    key=f"nav_btn_{internal_key}",
                    help=f"Navigate to {display_name}",
                    type="secondary"
            ):
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
        submitted = st.form_submit_button("Add Doctor")

        if submitted:
            if not all([doc_id, name, email, specialty, qualification, mobile]):
                st.error("Please fill in all fields.")
            elif add_doctor(doc_id, name, email, specialty, qualification, mobile):
                st.session_state.next_doc_id = f"{random.randint(200, 999)}"
                st.rerun()


def show_assign_chat_form():
    st.header("Assign Chat to Doctor")
    st.markdown("---")

    users = get_users()
    patients = {email: data for email, data in users.items() if data['role'] == 'patient'}
    doctors = {email: data for email, data in users.items() if data['role'] == 'doctor'}

    with st.form("assign_chat_form"):
        patient_email = st.selectbox("Select Patient", options=["--Select--"] + sorted(
            [f"{data['name']} ({email})" for email, data in patients.items()]))
        doctor_email = st.selectbox("Select Doctor", options=["--Select--"] + sorted(
            [f"{data['name']} ({email})" for email, data in doctors.items()]))
        submitted = st.form_submit_button("Assign Chat")

        if submitted:
            if patient_email == "--Select--" or doctor_email == "--Select--":
                st.error("Please select both a patient and a doctor.")
            else:
                patient_email = patient_email.split(' (')[1][:-1]
                doctor_email = doctor_email.split(' (')[1][:-1]
                st.query_params.update(
                    {"assign_chat": "true", "patient_email": patient_email, "doctor_email": doctor_email})
                st.rerun()


def show_view_feedback():
    st.header("View User Feedback")
    st.markdown("---")

    feedback_list = get_feedback()
    if feedback_list:
        df_feedback = pd.DataFrame(feedback_list).sort_values(by='timestamp', ascending=False)
        st.dataframe(
            df_feedback[['user_email', 'feedback', 'timestamp']],
            column_config={
                "user_email": "User Email",
                "feedback": st.column_config.TextColumn("Feedback", width="large"),
                "timestamp": st.column_config.DatetimeColumn("Submitted", format="YYYY-MM-DD HH:mm")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No feedback submitted yet.")


def show_doctor_dashboard():
    user = st.session_state.user_profile
    show_notifications()
    st.markdown(
        f'<img src="image/Profile.jpg/{PRIMARY_BLUE}?text=Doctor" style="float: left; margin-right: 20px; margin-bottom: 20px;" alt="Doctor Image">',
        unsafe_allow_html=True)

    st.markdown(
        '<div style="text-align: center; margin-bottom: 30px; margin-top: 50px; font-size: 1.8em; font-weight: bold; color: #4ac1e2;">Pending Request</div>',
        unsafe_allow_html=True)

    st.write(f"Requests for Dr. **{user['name']}** ({user['specialty']}).")

    pending_requests = [
        r for r in get_chat_requests()
        if r['doctor_email'] == user['email'] and r['status'] == 'Pending'
    ]

    if pending_requests:
        data = [
            {
                "RId": req['request_id'],
                "PId": req.get('patient_id', 'N/A'),
                "PName": req.get('patient_name', 'N/A'),
                "DId": req.get('doctor_id', 'N/A'),
                "DName": req.get('doctor_name', 'N/A'),
                "Flag": req.get('flag', 'N'),
                "Email": req['patient_email']
            } for req in pending_requests
        ]

        df_pending = pd.DataFrame(data)
        st.markdown("---")

        header_cols = st.columns([0.15, 0.1, 0.1, 0.2, 0.1, 0.1, 0.1, 0.2])
        header_labels = ["Accept", "RId", "PId", "PName", "DId", "DName", "Flag", "Email"]

        st.markdown(
            """
            <div style="display: flex; background-color: #4ac1e2; color: white; font-weight: bold; padding: 10px; border-radius: 4px 4px 0 0;">
                <div style="flex: 0.15;">Accept</div>
                <div style="flex: 0.1;">RId</div>
                <div style="flex: 0.1;">PId</div>
                <div style="flex: 0.2;">PName</div>
                <div style="flex: 0.1;">DId</div>
                <div style="flex: 0.1;">DName</div>
                <div style="flex: 0.1;">Flag</div>
                <div style="flex: 0.2;">Email</div>
            </div>
            """, unsafe_allow_html=True
        )

        for i, req in enumerate(pending_requests):
            col_list = st.columns([0.15, 0.1, 0.1, 0.2, 0.1, 0.1, 0.1, 0.2])
            with col_list[0]:
                if st.button("Yes", key=f"accept_{req['request_id']}", help="Accept this request"):
                    update_chat_request_status(req['request_id'], 'Accepted')
                    st.session_state.active_chat_request = req['request_id']
                    mark_notifications_read_by_request(req['request_id'], user['email'])
                    st.success(f"Request **{req['request_id']}** accepted! Starting chat session.")
                    st.session_state.portal_view = "LiveChat"
                    st.rerun()
            with col_list[1]:
                st.write(f"**{req['request_id']}**")
            with col_list[2]:
                st.write(req.get('patient_id', 'N/A'))
            with col_list[3]:
                st.write(req.get('patient_name', 'N/A'))
            with col_list[4]:
                st.write(req.get('doctor_id', 'N/A'))
            with col_list[5]:
                st.write(req.get('doctor_name', 'N/A'))
            with col_list[6]:
                st.write(req.get('flag', 'N'))
            with col_list[7]:
                st.write(req['patient_email'])
            if i < len(pending_requests) - 1:
                st.markdown("<hr style='margin: 0; padding: 0;'>", unsafe_allow_html=True)

        st.markdown("---")
        st.caption("Click 'Yes' to accept a pending request and start a live chat session.")
    else:
        st.success("You have no pending chat requests at this time. All caught up!")

    st.markdown('<div style="clear: both;"></div>', unsafe_allow_html=True)


def show_doctor_portal():
    user = st.session_state.user_profile
    st.markdown(
        f'<div class="header-bar" style="background: linear-gradient(90deg, #1d4ed8, #3b82f6);"><h1>Doctor Portal</h1><p>Welcome, {user["name"]} ({user["role"].capitalize()})</p></div>',
        unsafe_allow_html=True)

    nav_options = {
        "Pending Requests": "Dashboard",
        "Details": "DoctorDetails",
        "View User": "ViewUsers",
        "View Request": "ViewRequests",
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


def show_doctor_details():
    user = st.session_state.user_profile
    st.header("My Profile Details")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Name", user['name'])
        st.metric("Specialty", user.get('specialty', 'N/A'))
        st.metric("Mobile", user.get('mobile', 'N/A'))
    with col2:
        st.metric("Doctor ID", user.get('doc_id', 'N/A'))
        st.metric("Qualification", user.get('qualification', 'N/A'))
        st.metric("Email (Login)", user['email'])

    st.markdown("---")
    st.info("You can request the Admin to update these details.")


def show_view_users():
    st.header("System User Directory")
    st.write("This lists all registered Patient and Doctor accounts.")
    st.markdown("---")

    all_users = get_users()
    user_list = [
        {
            "Role": data['role'].capitalize(),
            "Name": data['name'],
            "Email": email,
            "Specialty": data.get('specialty', 'N/A') if data['role'] == 'doctor' else 'N/A',
            "ID": data.get('doc_id', 'N/A') if data['role'] == 'doctor' else 'N/A',
        } for email, data in all_users.items()
    ]

    df_users = pd.DataFrame(user_list).sort_values(by=['Role', 'Name'], ascending=[False, True])
    st.dataframe(df_users, use_container_width=True, hide_index=True)


def show_view_requests():
    user = st.session_state.user_profile
    st.header("Full Chat Request History")
    st.write(f"Showing all chat requests associated with Dr. **{user['name']}** ({user['email']}).")
    st.markdown("---")

    df_chat_requests = pd.DataFrame(get_chat_requests())
    doctor_requests = df_chat_requests[
        (df_chat_requests['doctor_email'] == user['email'])
    ].sort_values(by='timestamp', ascending=False)

    if not doctor_requests.empty:
        st.dataframe(
            doctor_requests[['request_id', 'patient_email', 'timestamp', 'query', 'status', 'specialty']],
            column_config={
                "request_id": "ID",
                "patient_email": "Patient Email",
                "timestamp": st.column_config.DatetimeColumn("Date/Time", format="YYYY-MM-DD HH:mm"),
                "query": st.column_config.TextColumn("Reason", width="medium"),
                "status": "Status",
                "specialty": "Specialty"
            },
            key="full_request_history",
            use_container_width=True,
            hide_index=True,
        )
        st.caption("This view shows the complete log of all requests (Pending, Accepted, and Closed).")
    else:
        st.info("No chat request history found.")


def show_login_page():
    # Initialize session state for navigation if not set
    if 'nav_view' not in st.session_state:
        st.session_state.nav_view = "Login"  # Default to Login view

    # Inject custom CSS for enhanced navigation styling
    st.markdown(
        """
        <style>
        .nav-container {
            background: linear-gradient(90deg, #1d4ed8, #3b82f6);
            padding: 15px 20px;
            margin: -1rem -1rem 1rem -1rem;
            display: flex;
            justify-content: center;
            gap: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
            border-radius: 0 0 8px 8px;
        }
        .nav-button {
            background-color: transparent;
            color: white;
            font-size: 1.1em;
            font-weight: 500;
            padding: 8px 16px;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
        }
        .nav-button:hover {
            background-color: rgba(255, 255, 255, 0.2);
            transform: scale(1.05);
        }
        .nav-button.active {
            background-color: #4ac1e2;
            font-weight: bold;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        .header-bar {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
        }
        .login-container {
            padding: 20px;
            background-color: #f8fafc;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        .team-container {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
            margin-top: 20px;
        }
        .team-card {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 15px;
            width: 200px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
        }
        .team-card:hover {
            transform: translateY(-5px);
        }
        .team-card img {
            border-radius: 50%;
            width: 100px;
            height: 100px;
            object-fit: cover;
            margin-bottom: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Header
    st.markdown(
        f'''
        <div class="header-bar">
            <img src="image/Profile.jpg/{PRIMARY_BLUE}?text=Rx" alt="Logo">
            <div>
                <h1>E-Healthcare System</h1>
                <p style="margin:0; font-size: 1.1em;">Digital Access Portal</p>
            </div>
        </div>
        ''', unsafe_allow_html=True
    )

    # Navigation bar with buttons
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    nav_cols = st.columns(4)
    nav_options = ["Home", "About Us", "Contact Us", "Login"]

    for i, option in enumerate(nav_options):
        with nav_cols[i]:
            is_active = st.session_state.nav_view == option
            if st.button(
                    option,
                    key=f"nav_{option.lower().replace(' ', '_')}",
                    type="primary" if is_active else "secondary",
                    help=f"Navigate to {option}"
            ):
                st.session_state.nav_view = option
                st.rerun()
            # Display button label with active state styling
            st.markdown(
                f'<button class="nav-button {"active" if is_active else ""}">{option}</button>',
                unsafe_allow_html=True
            )
    st.markdown('</div>', unsafe_allow_html=True)

    # Display content based on selected navigation view
    if st.session_state.nav_view == "Home":
        st.header("Welcome to E-Healthcare System")
        st.markdown("---")
        st.write("""
            This is the home page of our digital healthcare portal. 
            Explore our services, connect with doctors, or log in to access your personalized dashboard.
            - **Symptom Checker**: Get AI-driven insights into your health concerns.
            - **Connect with Doctors**: Request live consultations with specialists.
            - **Secure Platform**: Your data is protected with top-tier security.
        """)
        st.image("image/Profile.jpg", width=2050)

    elif st.session_state.nav_view == "About Us":
        st.header("About Us")
        st.markdown("---")
        st.write("""
            **E-Healthcare System** is a state-of-the-art platform designed to connect patients with healthcare professionals seamlessly.
            Our mission is to provide accessible, efficient, and high-quality medical consultations through digital means.
            **Key Features**:
            - **Symptom Checker**: AI-powered analysis to guide you to the right specialist.
            - **Live Chat**: Real-time consultations with verified doctors.
            - **Feedback System**: Share your experience to help us improve.
            Founded in 2025, we aim to revolutionize healthcare delivery with cutting-edge technology.
        """)
        st.image("image/Profile.jpg", width=2050)
        st.markdown("### Our Team")
        st.markdown('<div class="team-container">', unsafe_allow_html=True)
        team_members = [
            {"name": "Dr. Saddab", "role": "Chief Medical Officer", "specialty": "Cardiology"},
            {"name": "Dr. Afzal", "role": "Lead Specialist", "specialty": "Orthopedics"},
            {"name": "Dr. Arshad", "role": "Platform Manager", "specialty": "N/A"}
        ]
        for member in team_members:
            st.markdown(
                f'''
                <div class="team-card">
                    <img src="image/Profile.jpg={member["name"][0]}" alt="{member["name"]}">
                    <h4>{member["name"]}</h4>
                    <p>{member["role"]}</p>
                    <p><i>{member["specialty"]}</i></p>
                </div>
                ''',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.nav_view == "Contact Us":
        st.header("Contact Us")
        st.markdown("---")
        st.write("""
            Have questions or need support? Reach out to us!
            - **Email**: support@ehealthcare.com
            - **Phone**: 7260023491
            - **Address**: 360003 Gujarat., Rajkot City, Marwadi University
        """)
        with st.form("contact_form"):
            name = st.text_input("Your Name")
            email = st.text_input("Your Email")
            message = st.text_area("Your Message")
            if st.form_submit_button("Send Message"):
                if name and email and message:
                    st.success("Thank you for your message! We'll get back to you soon.")
                else:
                    st.error("Please fill in all fields.")

    elif st.session_state.nav_view == "Login":
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.subheader("Login Access")
        st.markdown("---")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.button('Admin Login', on_click=lambda: st.session_state.update(selected_role='admin'),
                      help="Test account: admin@app.com")
        with col2:
            st.button('Doctor Login', on_click=lambda: st.session_state.update(selected_role='doctor'),
                      help="Test account: doctor@app.com")
        with col3:
            st.button('Patient Login', on_click=lambda: st.session_state.update(selected_role='patient'),
                      help="Test account: patient@app.com")

        st.markdown('</div>', unsafe_allow_html=True)
        current_role = st.session_state.selected_role
        st.info(f"Selected Role: **{current_role.upper()}**")

        with st.form("login_form"):
            st.subheader(f"{current_role.capitalize()} Credentials (Demo)")
            default_email = next((k for k, v in get_users().items() if v['role'] == current_role),
                                 f"{current_role}@app.com")
            email = st.text_input("Email", value=default_email, disabled=True)
            password = st.text_input("Password (Disabled for Demo)", type="password", value="********", disabled=True)
            submitted = st.form_submit_button("Log In to Dashboard")

            if submitted:
                login_attempt(email, current_role)


def show_patient_portal():
    user = st.session_state.user_profile
    st.markdown(
        f'<div class="header-bar" style="background: linear-gradient(90deg, #10b981, #34d399);"><h1>Patient Portal</h1><p>Welcome, {user["name"]} ({user["role"].capitalize()})</p></div>',
        unsafe_allow_html=True)

    nav_options = {
        "View Doctors": "ViewDoctors",
        "Symptom Check": "Dashboard",
        "Request Chat": "RequestChat",
        "Give Feedback": "GiveFeedback",
    }
    draw_post_login_navbar(nav_options)

    show_notifications()

    view = st.session_state.portal_view
    if view == "LiveChat":
        show_live_chat_interface()
    elif view == "Dashboard":
        st.header("Symptom Checker & AI Analysis")
        show_patient_symptom_checker()
    elif view == "ViewDoctors":
        st.header("View All Doctors")
        show_view_doctors_for_portal()
    elif view == "RequestChat":
        st.header("Request Doctor")
        show_request_chat_form()
    elif view == "GiveFeedback":
        show_feedback_form()


def show_feedback_form():
    st.header("Give System Feedback")
    st.markdown("---")

    with st.form("feedback_form"):
        feedback = st.text_area("Enter your feedback about the system:", height=150)
        submitted = st.form_submit_button("Submit Feedback")

        if submitted:
            if not feedback:
                st.error("Please enter some feedback.")
            else:
                add_feedback({
                    "user_email": st.session_state.user_profile['email'],
                    "feedback": feedback,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                st.success("Thank you for your feedback! It has been submitted successfully.")
                st.rerun()


def show_live_chat_interface():
    request_id = st.session_state.active_chat_request
    if request_id is None:
        st.error("No active chat session found. Please request a chat first.")
        st.session_state.portal_view = "RequestChat" if st.session_state.user_profile[
                                                            'role'] == 'patient' else "Dashboard"
        st.rerun()
        return

    current_request = next((r for r in get_chat_requests() if r['request_id'] == request_id), None)
    if current_request is None:
        st.error(f"Chat request ID {request_id} not found.")
        st.session_state.portal_view = "RequestChat" if st.session_state.user_profile[
                                                            'role'] == 'patient' else "Dashboard"
        st.rerun()
        return

    if current_request['status'] == 'Closed':
        st.error("This chat session has been closed and cannot accept new messages.")
        st.session_state.active_chat_request = None
        st.session_state.portal_view = "RequestChat" if st.session_state.user_profile[
                                                            'role'] == 'patient' else "Dashboard"
        st.rerun()
        return

    current_user_role = st.session_state.user_profile['role']
    patient_name = current_request.get('patient_name', current_request['patient_email'])
    doctor_name = current_request.get('doctor_name', 'Doctor')

    mark_notifications_read_by_request(request_id, st.session_state.user_profile['email'])

    st.markdown("## Session", unsafe_allow_html=True)
    st.markdown(f"### Chat between **{doctor_name}** and **{patient_name}**", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    st.markdown('<div class="chat-messages">', unsafe_allow_html=True)

    messages = get_chat_messages(request_id)
    if not messages:
        st.info("This is the start of your chat. Send your first message!")
    else:
        for msg in messages:
            message_class = "user-message" if msg['sender'] == st.session_state.user_profile[
                'name'] else "doctor-message"
            st.markdown(
                f'<div class="chat-message {message_class}">'
                f'<span class="message-sender">{msg["sender"]} ({msg["role"].capitalize()}) at {msg["timestamp"]}</span><br>'
                f'{msg["text"]}'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown('</div>', unsafe_allow_html=True)

    with st.form(key=f"chat_input_form_{request_id}", clear_on_submit=True):
        col_text, col_submit = st.columns([0.85, 0.15])
        with col_text:
            new_message = st.text_area(
                "Type your message...",
                key=f"new_chat_message_{request_id}",
                height=40,
                label_visibility="collapsed"
            )
        with col_submit:
            st.markdown('<div style="margin-top: 10px;">', unsafe_allow_html=True)
            submit_message = st.form_submit_button("Submit")
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---", unsafe_allow_html=True)
        col_photo_label, col_photo_file, col_send = st.columns([0.15, 0.65, 0.2])
        with col_photo_label:
            st.markdown('<div style="margin-top: 5px;">Photo :- </div>', unsafe_allow_html=True)
        with col_photo_file:
            uploaded_file = st.file_uploader("Choose file", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed",
                                             key=f"chat_photo_upload_{request_id}")
        with col_send:
            send_photo = st.form_submit_button("Send", key=f"send_photo_btn_{request_id}")

        if submit_message and new_message:
            add_chat_message(
                request_id,
                st.session_state.user_profile['name'],
                current_user_role,
                new_message,
                time.strftime("%I:%M %p")
            )
            st.rerun()

        if send_photo and uploaded_file:
            st.info(f"Photo '{uploaded_file.name}' submitted successfully! (This is a mock upload.)")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")
    if st.button("End Session and View Requests", key=f"exit_chat_btn_{request_id}"):
        update_chat_request_status(request_id, "Closed")
        st.session_state.active_chat_request = None
        st.session_state.portal_view = "RequestChat" if current_user_role == 'patient' else "Dashboard"
        st.success(f"Chat session {request_id} has been closed.")
        st.rerun()


def show_request_chat_form():
    st.subheader("Request a Chat with a Doctor")
    st.markdown("Select a specialty to see all available doctors and choose one to send your chat request.")
    st.markdown("---")

    all_doctors = {k: v for k, v in get_users().items() if v['role'] == 'doctor'}
    st.write(f"**Request ID:** **`{st.session_state.next_request_id}`**")

    selected_specialty = st.selectbox(
        "Select Specialty",
        options=["--Select--"] + MOCK_SPECIALTIES,
        key="chat_specialty_select",
        index=0,
        help="Choose a medical specialty to view all available doctors."
    )

    filtered_doctors = {}
    if selected_specialty and selected_specialty != "--Select--":
        filtered_doctors = {
            email: data for email, data in all_doctors.items()
            if data.get('specialty') == selected_specialty
        }

    if filtered_doctors:
        st.markdown("### Available Doctors")
        doctor_list = [
            {
                "Name": data['name'],
                "Doctor ID": data['doc_id'],
                "Qualification": data['qualification'],
                "Email": email
            } for email, data in filtered_doctors.items()
        ]
        df_doctors = pd.DataFrame(doctor_list).sort_values(by='Name')
        st.dataframe(
            df_doctors,
            column_config={
                "Name": "Doctor Name",
                "Doctor ID": "ID",
                "Qualification": st.column_config.TextColumn("Qualification", width="medium"),
                "Email": "Contact Email"
            },
            hide_index=True,
            use_container_width=True
        )
    elif selected_specialty != "--Select--":
        st.warning(f"No doctors available for {selected_specialty}. Please try another specialty.")

    doctor_options = ["--Select--"] + sorted(
        [f"{doc['name']} (ID: {doc['doc_id']}, {doc['qualification']})" for doc in filtered_doctors.values()])
    selected_doctor = st.selectbox(
        "Select Doctor",
        options=doctor_options,
        key="chat_doctor_select",
        index=0,
        help="Choose a doctor from all available doctors in the selected specialty."
    )

    selected_doc_details = {}
    doc_id = 'N/A'
    qualification = 'N/A'
    doc_email = 'N/A'

    if selected_doctor and selected_doctor != "--Select--":
        selected_doc_name = selected_doctor.split(" (ID:")[0]
        for email, doc in filtered_doctors.items():
            if doc['name'] == selected_doc_name:
                selected_doc_details = doc
                doc_id = selected_doc_details.get('doc_id', 'N/A')
                qualification = selected_doc_details.get('qualification', 'N/A')
                doc_email = email
                break

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.text_input("Doctor ID", value=doc_id, disabled=True)
    with col_d2:
        st.text_input("Qualification", value=qualification, disabled=True)

    with st.form("request_chat_form"):
        query = st.text_area("Reason for Chat Request (Query)", height=100,
                             help="Describe your medical concern or reason for the chat.")
        confirm = st.checkbox("Confirm your doctor selection: " + (
            selected_doc_details.get('name', 'None') if selected_doctor != "--Select--" else "None"))
        submit_request = st.form_submit_button("Submit Request")

        if submit_request:
            if selected_doctor == "--Select--" or selected_specialty == "--Select--" or not query:
                st.error("Please select a specialty, a doctor, and enter a reason for your request.")
            elif not confirm:
                st.error("Please confirm your doctor selection.")
            else:
                new_request = {
                    "request_id": st.session_state.next_request_id,
                    "patient_email": st.session_state.user_profile['email'],
                    "patient_name": st.session_state.user_profile['name'],
                    "patient_id": "P" + st.session_state.user_profile.get('mobile', '000').replace('-', ''),
                    "doctor_email": doc_email,
                    "doctor_name": selected_doc_details.get('name'),
                    "doctor_id": selected_doc_details.get('doc_id'),
                    "qualification": selected_doc_details.get('qualification'),
                    "specialty": selected_specialty,
                    "query": query,
                    "status": "Pending",
                    "flag": "N",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                add_chat_request(new_request)
                st.session_state.next_request_id += 1
                st.success(
                    f"Request **{new_request['request_id']}** submitted to **{selected_doc_details['name']}** ({selected_specialty}). Status: **Pending**.")
                st.rerun()

    st.markdown("---")
    st.subheader("My Request Status")

    patient_requests = [
        r for r in get_chat_requests()
        if r['patient_email'] == st.session_state.user_profile['email']
    ]

    if patient_requests:
        df_requests = pd.DataFrame(patient_requests)
        df_display = df_requests[
            ['request_id', 'doctor_name', 'specialty', 'query', 'status', 'timestamp']].sort_values(
            by='timestamp', ascending=False)

        df_display['Action'] = df_display.apply(
            lambda row: f"**[Chat Now!](?view=LiveChat&req_id={row['request_id']})**"
            if row['status'] == 'Accepted' else 'Closed' if row['status'] == 'Closed' else 'Wait',
            axis=1
        )

        st.dataframe(
            df_display,
            column_config={
                "request_id": "ID",
                "doctor_name": "Doctor",
                "specialty": "Type",
                "query": st.column_config.TextColumn("Query", width="medium"),
                "status": "Status",
                "timestamp": st.column_config.DatetimeColumn("Submitted", format="YYYY-MM-DD HH:mm"),
                "Action": st.column_config.Column("Action")
            },
            hide_index=True,
            use_container_width=True
        )

        for req in patient_requests:
            if req['status'] == 'Accepted':
                if st.button(f"Chat Now with Dr. {req['doctor_name']} (ID: {req['request_id']})",
                             key=f"chat_{req['request_id']}"):
                    st.session_state.active_chat_request = req['request_id']
                    st.session_state.portal_view = "LiveChat"
                    mark_notifications_read_by_request(req['request_id'], st.session_state.user_profile['email'])
                    st.rerun()
    else:
        st.info("You have no active or past chat requests.")


def show_view_doctors_for_portal():
    st.subheader("View All Doctors")
    st.markdown("Browse all doctors in the system and request a chat directly.")
    st.markdown("---")

    all_doctors = {k: v for k, v in get_users().items() if v['role'] == 'doctor'}
    if not all_doctors:
        st.info("No doctors registered in the system.")
        return

    doctor_list = [
        {
            "Name": data['name'],
            "Specialty": data['specialty'],
            "Qualification": data['qualification'],
            "Doctor ID": data['doc_id'],
            "Email": email,
            "Action": f"Request Chat with {data['name']}"
        } for email, data in all_doctors.items()
    ]

    df_doctors = pd.DataFrame(doctor_list).sort_values(by='Specialty')
    st.dataframe(
        df_doctors,
        column_config={
            "Doctor ID": "ID",
            "Specialty": st.column_config.TextColumn("Specialty", width="medium"),
            "Qualification": st.column_config.TextColumn("Qualification", width="medium"),
            "Action": st.column_config.LinkColumn("Action", help="Click to request a chat with this doctor")
        },
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")
    st.write("**Request a Chat Directly**")
    selected_doctor = st.selectbox(
        "Select a Doctor to Request a Chat",
        options=["--Select--"] + sorted([f"{doc['Name']} ({doc['Specialty']})" for doc in doctor_list]),
        key="direct_chat_select"
    )

    if selected_doctor and selected_doctor != "--Select--":
        selected_doc_name = selected_doctor.split(" (")[0]
        selected_doc = next((doc for doc in doctor_list if doc['Name'] == selected_doc_name), None)
        if selected_doc:
            with st.form(f"direct_chat_form_{selected_doc['Email']}"):
                query = st.text_area("Reason for Chat Request", height=100, key=f"direct_query_{selected_doc['Email']}")
                confirm = st.checkbox(f"Confirm selection: {selected_doc['Name']} ({selected_doc['Specialty']})")
                submit_direct = st.form_submit_button("Submit Chat Request")
                if submit_direct:
                    if not query:
                        st.error("Please enter a reason for your request.")
                    elif not confirm:
                        st.error("Please confirm your doctor selection.")
                    else:
                        new_request = {
                            "request_id": st.session_state.next_request_id,
                            "patient_email": st.session_state.user_profile['email'],
                            "patient_name": st.session_state.user_profile['name'],
                            "patient_id": "P" + st.session_state.user_profile.get('mobile', '000').replace('-', ''),
                            "doctor_email": selected_doc['Email'],
                            "doctor_name": selected_doc['Name'],
                            "doctor_id": selected_doc['Doctor ID'],
                            "qualification": selected_doc['Qualification'],
                            "specialty": selected_doc['Specialty'],
                            "query": query,
                            "status": "Pending",
                            "flag": "N",
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        add_chat_request(new_request)
                        st.session_state.next_request_id += 1
                        st.success(
                            f"Request **{new_request['request_id']}** submitted to **{selected_doc['Name']}** ({selected_doc['Specialty']}).")
                        st.rerun()


def show_patient_symptom_checker():
    user = st.session_state.user_profile

    with st.form("symptom_form"):
        st.subheader("Symptom Input")
        symptoms = st.text_area(
            "Describe your current symptoms (e.g., location, severity, duration):",
            key="symptom_input",
            height=150
        )
        submitted = st.form_submit_button("Analyze Symptoms")

        if submitted and symptoms:
            with st.spinner("Analyzing symptoms..."):
                time.sleep(1.5)
            pred_text = "AI could not determine a specific illness. Please consult a General Practitioner or use the 'Request Chat' feature."
            pred_specialty = "General"
            if "pain in right knee" in symptoms.lower() or "fall" in symptoms.lower():
                pred_text = "AI suggests consulting Orthopedics immediately for potential ligament damage."
                pred_specialty = "Orthopedics (Bone)"
            elif "chest pain" in symptoms.lower() or "difficulty breathing" in symptoms.lower():
                pred_text = "AI suggests consulting Cardiology/Pulmonology as soon as possible."
                pred_specialty = "Cardiology"

            prediction_result = f"**Predicted Specialty:** {pred_specialty}\n\n**AI Recommendation:** {pred_text}"
            add_submission({
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "symptoms": symptoms,
                "prediction": prediction_result,
                "patient_email": user['email']
            })
            st.success("Analysis complete!")
            st.info(prediction_result, icon="🧠")

    st.markdown("---")
    st.subheader("Prediction History")

    patient_submissions = get_submissions(user['email'])
    if patient_submissions:
        df_history = pd.DataFrame(patient_submissions).sort_values(by='date', ascending=False)
        df_display = df_history.rename(columns={
            'date': 'Date',
            'symptoms': 'Symptoms Entered',
            'prediction': 'AI Recommendation'
        })[['Date', 'Symptoms Entered', 'AI Recommendation']]

        st.dataframe(
            df_display,
            column_config={
                "Date": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD HH:mm"),
                "Symptoms Entered": st.column_config.TextColumn("Symptoms Entered", width="medium"),
                "AI Recommendation": st.column_config.TextColumn("AI Recommendation", width="large")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Your symptom checker history is currently empty.")