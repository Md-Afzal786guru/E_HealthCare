import sqlite3
import time
import streamlit as st

def init_database():
    """Initializes the SQLite database and creates necessary tables."""
    conn = sqlite3.connect('healthcare.db', check_same_thread=False)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            mobile TEXT,
            specialty TEXT,
            doc_id TEXT,
            qualification TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_requests (
            request_id INTEGER PRIMARY KEY,
            patient_email TEXT,
            doctor_email TEXT,
            specialty TEXT,
            doctor_name TEXT,
            doctor_id TEXT,
            qualification TEXT,
            query TEXT,
            status TEXT,
            patient_name TEXT,
            patient_id TEXT,
            flag TEXT,
            timestamp TEXT,
            FOREIGN KEY (patient_email) REFERENCES users(email),
            FOREIGN KEY (doctor_email) REFERENCES users(email)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            symptoms TEXT,
            prediction TEXT,
            patient_email TEXT,
            FOREIGN KEY (patient_email) REFERENCES users(email)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            feedback TEXT,
            timestamp TEXT,
            FOREIGN KEY (user_email) REFERENCES users(email)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            sender TEXT,
            role TEXT,
            text TEXT,
            timestamp TEXT,
            FOREIGN KEY (request_id) REFERENCES chat_requests(request_id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            message TEXT,
            status TEXT DEFAULT 'unread',
            timestamp TEXT,
            request_id INTEGER,
            FOREIGN KEY (user_email) REFERENCES users(email),
            FOREIGN KEY (request_id) REFERENCES chat_requests(request_id)
        )
    ''')

    conn.commit()
    return conn

if 'db_conn' not in st.session_state:
    st.session_state.db_conn = init_database()

def get_db_cursor():
    return st.session_state.db_conn.cursor()

def commit_db():
    st.session_state.db_conn.commit()

def get_users():
    c = get_db_cursor()
    c.execute('SELECT * FROM users')
    rows = c.fetchall()
    users = {}
    for row in rows:
        users[row[0]] = {
            "email": row[0],
            "role": row[1],
            "name": row[2],
            "mobile": row[3],
            "specialty": row[4],
            "doc_id": row[5],
            "qualification": row[6]
        }
    return users

def add_user(email, role, name, mobile=None, specialty=None, doc_id=None, qualification=None):
    c = get_db_cursor()
    try:
        c.execute('''
            INSERT INTO users (email, role, name, mobile, specialty, doc_id, qualification)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (email, role, name, mobile, specialty, doc_id, qualification))
        commit_db()
        return True
    except sqlite3.IntegrityError:
        return False

def remove_user(email):
    c = get_db_cursor()
    c.execute('SELECT name, role FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    if user and user[1] == 'doctor':
        c.execute('DELETE FROM users WHERE email = ?', (email,))
        commit_db()
        return user[0]
    return None

def get_chat_requests():
    c = get_db_cursor()
    c.execute('SELECT * FROM chat_requests')
    rows = c.fetchall()
    return [{
        "request_id": row[0],
        "patient_email": row[1],
        "doctor_email": row[2],
        "specialty": row[3],
        "doctor_name": row[4],
        "doctor_id": row[5],
        "qualification": row[6],
        "query": row[7],
        "status": row[8],
        "patient_name": row[9],
        "patient_id": row[10],
        "flag": row[11],
        "timestamp": row[12]
    } for row in rows]

def add_chat_request(request):
    c = get_db_cursor()
    c.execute('''
        INSERT INTO chat_requests (
            request_id, patient_email, doctor_email, specialty, doctor_name, doctor_id,
            qualification, query, status, patient_name, patient_id, flag, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        request['request_id'], request['patient_email'], request['doctor_email'], request['specialty'],
        request['doctor_name'], request['doctor_id'], request['qualification'], request['query'],
        request['status'], request['patient_name'], request['patient_id'], request['flag'], request['timestamp']
    ))
    commit_db()
    add_notification(
        user_email=request['doctor_email'],
        message=f"New chat request from {request['patient_name']} (ID: {request['request_id']})",
        request_id=request['request_id']
    )

def update_chat_request_status(request_id, status):
    c = get_db_cursor()
    c.execute('SELECT patient_email, doctor_email, patient_name, doctor_name FROM chat_requests WHERE request_id = ?', (request_id,))
    request = c.fetchone()
    if request:
        patient_email, doctor_email, patient_name, doctor_name = request
        c.execute('UPDATE chat_requests SET status = ? WHERE request_id = ?', (status, request_id))
        commit_db()
        if status == 'Accepted':
            add_notification(
                user_email=patient_email,
                message=f"Your chat request (ID: {request_id}) has been accepted by Dr. {doctor_name}",
                request_id=request_id
            )
        elif status == 'Closed':
            add_notification(
                user_email=patient_email,
                message=f"Chat session (ID: {request_id}) with Dr. {doctor_name} has been closed",
                request_id=request_id
            )

def get_chat_messages(request_id):
    c = get_db_cursor()
    c.execute('SELECT sender, role, text, timestamp FROM chat_messages WHERE request_id = ?', (request_id,))
    rows = c.fetchall()
    return [{
        "sender": row[0],
        "role": row[1],
        "text": row[2],
        "timestamp": row[3]
    } for row in rows]

def add_chat_message(request_id, sender, role, text, timestamp):
    c = get_db_cursor()
    c.execute('''
        INSERT INTO chat_messages (request_id, sender, role, text, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (request_id, sender, role, text, timestamp))
    commit_db()
    c.execute('SELECT patient_email, doctor_email, patient_name, doctor_name FROM chat_requests WHERE request_id = ?', (request_id,))
    request = c.fetchone()
    if request:
        patient_email, doctor_email, patient_name, doctor_name = request
        recipient_email = doctor_email if role == 'patient' else patient_email
        recipient_name = doctor_name if role == 'patient' else patient_name
        add_notification(
            user_email=recipient_email,
            message=f"New message from {sender} in chat session (ID: {request_id})",
            request_id=request_id
        )

def get_submissions(patient_email=None):
    c = get_db_cursor()
    if patient_email:
        c.execute('SELECT id, date, symptoms, prediction, patient_email FROM submissions WHERE patient_email = ?', (patient_email,))
    else:
        c.execute('SELECT id, date, symptoms, prediction, patient_email FROM submissions')
    rows = c.fetchall()
    return [{
        "id": row[0],
        "date": row[1],
        "symptoms": row[2],
        "prediction": row[3],
        "patient_email": row[4]
    } for row in rows]

def add_submission(submission):
    c = get_db_cursor()
    c.execute('''
        INSERT INTO submissions (date, symptoms, prediction, patient_email)
        VALUES (?, ?, ?, ?)
    ''', (submission['date'], submission['symptoms'], submission['prediction'], submission['patient_email']))
    commit_db()

def get_feedback():
    c = get_db_cursor()
    c.execute('SELECT user_email, feedback, timestamp FROM feedback')
    rows = c.fetchall()
    return [{
        "user_email": row[0],
        "feedback": row[1],
        "timestamp": row[2]
    } for row in rows]

def add_feedback(feedback):
    c = get_db_cursor()
    c.execute('''
        INSERT INTO feedback (user_email, feedback, timestamp)
        VALUES (?, ?, ?)
    ''', (feedback['user_email'], feedback['feedback'], feedback['timestamp']))
    commit_db()

def add_notification(user_email, message, request_id=None):
    c = get_db_cursor()
    c.execute('''
        INSERT INTO notifications (user_email, message, status, timestamp, request_id)
        VALUES (?, ?, 'unread', ?, ?)
    ''', (user_email, message, time.strftime("%Y-%m-%d %H:%M:%S"), request_id))
    commit_db()

def get_notifications(user_email):
    c = get_db_cursor()
    c.execute('SELECT id, message, status, timestamp, request_id FROM notifications WHERE user_email = ? ORDER BY timestamp DESC', (user_email,))
    rows = c.fetchall()
    return [{
        "id": row[0],
        "message": row[1],
        "status": row[2],
        "timestamp": row[3],
        "request_id": row[4]
    } for row in rows]

def mark_notification_read(notification_id):
    c = get_db_cursor()
    c.execute('UPDATE notifications SET status = "read" WHERE id = ?', (notification_id,))
    commit_db()

def mark_notifications_read_by_request(request_id, user_email):
    c = get_db_cursor()
    c.execute('UPDATE notifications SET status = "read" WHERE request_id = ? AND user_email = ?', (request_id, user_email))
    commit_db()
