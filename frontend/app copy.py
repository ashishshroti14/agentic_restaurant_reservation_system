import streamlit as st
import requests
import json
from datetime import datetime
import time

# API Configuration
API_BASE_URL = "http://127.0.0.1:8000"
CHAT_API_ENDPOINT = f"{API_BASE_URL}/chat/message"
AUTH_SEND_OTP_ENDPOINT = f"{API_BASE_URL}/auth/send-otp"
AUTH_VERIFY_OTP_ENDPOINT = f"{API_BASE_URL}/auth/verify-otp"

# Page configuration
st.set_page_config(
    page_title="FoodieSpot - Restaurant Reservation Assistant",
    page_icon="🍽️",
    layout="centered"
)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    
if "session_id" not in st.session_state:
    st.session_state.session_id = None
    
if "auth_state" not in st.session_state:
    st.session_state.auth_state = "not_authenticated"  # Possible values: not_authenticated, phone_entered, authenticated

if "phone_number" not in st.session_state:
    st.session_state.phone_number = ""

if "user_data" not in st.session_state:
    st.session_state.user_data = None
    
if "access_token" not in st.session_state:
    st.session_state.access_token = None

# Create a persistent requests session
if "http_session" not in st.session_state:
    st.session_state.http_session = requests.Session()

# Authentication functions
def send_otp(phone_number):
    try:
        response = st.session_state.http_session.post(
            AUTH_SEND_OTP_ENDPOINT,
            json={"phone_number": phone_number}
        )
        response.raise_for_status()
        return response.json(), True
    except requests.RequestException as e:
        st.error(f"Failed to send OTP: {str(e)}")
        return None, False

def verify_otp(phone_number, otp):
    try:
        response = st.session_state.http_session.post(
            AUTH_VERIFY_OTP_ENDPOINT,
            json={"phone_number": phone_number, "otp": otp}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Store access token directly in session state
            if "access_token" in data:
                st.session_state.access_token = data["access_token"]
                
                # Set the token for all future requests in this session
                st.session_state.http_session.headers.update({
                    "Authorization": f"Bearer {data['access_token']}"
                })
            
            return data, True
        else:
            st.error("Invalid OTP. Please try again.")
            return None, False
    except requests.RequestException as e:
        st.error(f"OTP verification failed: {str(e)}")
        return None, False

def send_message_to_api(message):
    try:
        payload = {
            "message": message,
            "session_id": st.session_state.session_id
        }
        
        # Access token is already included in the session headers
        # but we can check and add it here as well for redundancy
        if st.session_state.access_token:
            st.session_state.http_session.headers.update({
                "Authorization": f"Bearer {st.session_state.access_token}"
            })
        
        response = st.session_state.http_session.post(
            CHAT_API_ENDPOINT, 
            json=payload
        )
        
        # Handle authentication errors
        if response.status_code == 401:
            st.warning("Your session has expired. Please login again.")
            st.session_state.auth_state = "not_authenticated"
            st.session_state.access_token = None
            st.session_state.user_data = None
            st.session_state.http_session.headers.pop("Authorization", None)
            st.rerun()
        
        response.raise_for_status()
        
        data = response.json()
        st.session_state.session_id = data["session_id"]
        
        return {
            "role": "assistant",
            "content": data["message"]["content"],
            "suggested_actions": data.get("suggested_actions", []),
            "intent": data.get("intent", "unknown")  # Capture the intent from the API response
        }
    except requests.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return {
            "role": "assistant",
            "content": f"Sorry, I encountered an error connecting to the server: {str(e)}",
            "suggested_actions": [],
            "intent": "error"
        }

# Add debug section to sidebar
with st.sidebar:
    with st.expander("Debug Info"):
        st.write("Authentication State:", st.session_state.auth_state)
        st.write("Session ID:", st.session_state.session_id)
        st.write("Has access token:", st.session_state.access_token is not None)
        st.write("HTTP Session headers:", dict(st.session_state.http_session.headers))
        
        if st.button("Clear All Session Data"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# Header
st.title("🍽️ FoodieSpot Assistant")

# Authentication UI
if st.session_state.auth_state == "not_authenticated":
    st.markdown("Please log in to continue:")
    
    with st.form("phone_form"):
        phone_number = st.text_input("Enter your phone number (with country code):", placeholder="+1234567890")
        submit_phone = st.form_submit_button("Send OTP")
        
        if submit_phone and phone_number:
            # Validate phone number format (very basic validation)
            if not phone_number.startswith("+") or len(phone_number) < 8:
                st.error("Please enter a valid phone number with country code (e.g., +1234567890)")
            else:
                response, success = send_otp(phone_number)
                if success:
                    st.session_state.phone_number = phone_number
                    st.session_state.auth_state = "phone_entered"
                    st.rerun()

elif st.session_state.auth_state == "phone_entered":
    st.markdown(f"OTP sent to **{st.session_state.phone_number}**")
    
    with st.form("otp_form"):
        otp = st.text_input("Enter the OTP received via SMS:", max_chars=6)
        submit_otp = st.form_submit_button("Verify OTP")
        
        if submit_otp and otp:
            response, success = verify_otp(st.session_state.phone_number, otp)
            if success:
                st.session_state.user_data = response
                st.session_state.auth_state = "authenticated"
                
                # Display the cookies and tokens received
                st.write("Authentication successful!")
                
                # Add a welcome message
                welcome_message = {
                    "role": "assistant",
                    "content": f"👋 Welcome {response.get('user', {}).get('name', 'there')}! I'm your FoodieSpot assistant. I can help you find restaurants and make reservations. What are you looking for today?",
                    "suggested_actions": [
                        "Find Italian restaurants",
                        "Check restaurants in Downtown",
                        "Make a reservation for tonight"
                    ],
                    "intent": "greeting"
                }
                st.session_state.chat_history.append(welcome_message)
                st.rerun()
    
    if st.button("Change phone number"):
        st.session_state.auth_state = "not_authenticated"
        st.session_state.phone_number = ""
        st.rerun()

# Chat UI - Only show when authenticated
elif st.session_state.auth_state == "authenticated":
    st.markdown("Chat with our AI assistant to find and book restaurants.")
    
    # Chat container
    chat_container = st.container()
    
    # Display chat history
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"**You:** {message['content']}")
            else:
                # Display intent with the assistant's message
                intent_display = f"<small><i>Intent: {message.get('intent', 'unknown')}</i></small>"
                st.markdown(f"**Assistant:** {message['content']}")
                st.markdown(intent_display, unsafe_allow_html=True)
                
                # Display suggested actions if available
                if message.get("suggested_actions"):
                    st.markdown("**Suggested actions:**")
                    for action in message["suggested_actions"]:
                        if st.button(action, key=f"action_{action}_{time.time()}"):
                            # When a suggested action is clicked, send it as a user message
                            st.session_state.chat_history.append({
                                "role": "user",
                                "content": action
                            })
                            
                            # Get response from API
                            assistant_response = send_message_to_api(action)
                            st.session_state.chat_history.append(assistant_response)
                            
                            # Rerun the app to update the UI immediately
                            st.rerun()
    
    # Message input
    with st.form("chat_input_form", clear_on_submit=True):
        user_input = st.text_input("Type your message:", placeholder="e.g., Find Italian restaurants in Downtown")
        submit_button = st.form_submit_button("Send")
        
        if submit_button and user_input:
            # Add user message to chat history
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Send message to API and get response
            assistant_response = send_message_to_api(user_input)
            st.session_state.chat_history.append(assistant_response)
            
            # Rerun the app to update the UI with the new messages
            st.rerun()
                
    # Sidebar for authenticated users
    with st.sidebar:
        st.header("About FoodieSpot")
        st.write("FoodieSpot is an intelligent restaurant reservation system that helps you find and book restaurants based on your preferences.")
        
        st.subheader("User Info")
        if st.session_state.user_data and "user" in st.session_state.user_data:
            user = st.session_state.user_data["user"]
            st.write(f"Name: {user.get('full_name', 'Not provided')}")
            st.write(f"Phone: {user.get('phone', 'Not provided')}")
        
        if st.button("Logout"):
            # Clear session state properly
            st.session_state.auth_state = "not_authenticated"
            st.session_state.user_data = None
            st.session_state.access_token = None
            st.session_state.chat_history = []
            st.session_state.session_id = None
            
            # Clear authorization header
            if "Authorization" in st.session_state.http_session.headers:
                del st.session_state.http_session.headers["Authorization"]
            
            st.rerun()
        
        if st.button("Start New Conversation"):
            st.session_state.chat_history = []
            st.session_state.session_id = None
            
            # Re-add welcome message
            welcome_message = {
                "role": "assistant",
                "content": f"👋 Welcome back! I'm your FoodieSpot assistant. How can I help you today?",
                "suggested_actions": [
                    "Find Italian restaurants",
                    "Check restaurants in Downtown",
                    "Make a reservation for tonight"
                ],
                "intent": "greeting"
            }
            st.session_state.chat_history.append(welcome_message)
            st.rerun()

# If there's no welcome message yet in authenticated state, add one
if st.session_state.auth_state == "authenticated" and len(st.session_state.chat_history) == 0:
    welcome_message = {
        "role": "assistant",
        "content": "👋 Hello! I'm your FoodieSpot assistant. I can help you find restaurants and make reservations. What are you looking for today?",
        "suggested_actions": [
            "Find Italian restaurants",
            "Check restaurants in Downtown",
            "Make a reservation for tonight"
        ],
        "intent": "greeting"
    }
    st.session_state.chat_history.append(welcome_message)
    st.rerun()
