
import streamlit as st
from db import init_database, get_chat_requests, mark_notifications_read_by_request, add_chat_request, get_users
from ui import show_login_page, show_admin_portal, show_doctor_portal, show_patient_portal
from utils import set_page_style, init_session_state
import time

def main():
    set_page_style()
    init_session_state()

    # Ensure database connection is initialized
    if 'db_conn' not in st.session_state:
        st.session_state.db_conn = init_database()

    query_params = st.query_params
    if 'view' in query_params and query_params['view'] == 'LiveChat' and 'req_id' in query_params:
        try:
            req_id = int(query_params['req_id'])
            if st.session_state.logged_in:
                request = next((r for r in get_chat_requests() if r['request_id'] == req_id), None)
                if request and request['status'] != 'Closed' and (
                        request['patient_email'] == st.session_state.user_profile.get('email') or
                        request['doctor_email'] == st.session_state.user_profile.get('email')):
                    st.session_state.active_chat_request = req_id
                    st.session_state.portal_view = "LiveChat"
                    mark_notifications_read_by_request(req_id, st.session_state.user_profile.get('email'))
                    st.query_params.clear()
        except:
            pass
    elif 'assign_chat' in query_params and 'patient_email' in query_params and 'doctor_email' in query_params:
        if st.session_state.logged_in and st.session_state.user_profile['role'] == 'admin':
            patient_email = query_params['patient_email']
            doctor_email = query_params['doctor_email']
            users = get_users()
            if patient_email in users and doctor_email in users and users[doctor_email]['role'] == 'doctor':
                new_request = {
                    "request_id": st.session_state.next_request_id,
                    "patient_email": patient_email,
                    "doctor_email": doctor_email,
                    "specialty": users[doctor_email]['specialty'],
                    "doctor_name": users[doctor_email]['name'],
                    "doctor_id": users[doctor_email]['doc_id'],
                    "qualification": users[doctor_email]['qualification'],
                    "query": f"Admin-initiated chat between {users[patient_email]['name']} and {users[doctor_email]['name']}",
                    "status": "Accepted",
                    "patient_name": users[patient_email]['name'],
                    "patient_id": "P" + users[patient_email].get('mobile', '000').replace('-', ''),
                    "flag": "N",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                add_chat_request(new_request)
                st.session_state.next_request_id += 1
                st.query_params.clear()
                st.success(f"Chat request {new_request['request_id']} created between {new_request['patient_name']} and {new_request['doctor_name']}.")
                st.rerun()

    if st.session_state.logged_in:
        role = st.session_state.user_profile['role']
        if role == 'admin':
            show_admin_portal()
        elif role == 'doctor':
            show_doctor_portal()
        elif role == 'patient':
            show_patient_portal()
    else:
        show_login_page()

if __name__ == "__main__":
    main()
