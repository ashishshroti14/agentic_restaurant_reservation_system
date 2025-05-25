import streamlit as st
import requests
import json
import re
from datetime import datetime
import time
import uuid  # Add this import for generating unique IDs

# API Configuration
API_BASE_URL = "http://127.0.0.1:8000"
CHAT_API_ENDPOINT = f"{API_BASE_URL}/chat/message"
AUTH_SEND_OTP_ENDPOINT = f"{API_BASE_URL}/auth/send-otp"
AUTH_VERIFY_OTP_ENDPOINT = f"{API_BASE_URL}/auth/verify-otp"
RESTAURANTS_API_ENDPOINT = f"{API_BASE_URL}/restaurants"
RESERVATIONS_API_ENDPOINT = f"{API_BASE_URL}/get-reservations"

# Helper functions for rendering cards
# Initialize a counter in session state for unique keys
if "restaurant_key_counter" not in st.session_state:
    st.session_state.restaurant_key_counter = 0

def render_restaurant_card(restaurant, index=None, context="default"):
    """
    Renders a restaurant information card
    
    Args:
        restaurant: The restaurant data dictionary
        index: Optional index for disambiguation
        context: String identifier for where this card is being rendered (e.g., "top", "search")
    """
    # Generate a unique index if not provided
    if index is None:
        st.session_state.restaurant_key_counter += 1
        index = st.session_state.restaurant_key_counter
    
    # Generate a completely unique ID for this specific render instance
    unique_id = str(uuid.uuid4())
    
    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image("https://via.placeholder.com/150?text=Restaurant", width=100)
        
        with col2:
            st.markdown(f"### {restaurant.get('name', 'Restaurant')}")
            st.markdown(f"**Cuisine:** {restaurant.get('cuisine', 'Various')}")
            st.markdown(f"**Location:** {restaurant.get('location', 'Unknown')}")
            st.markdown(f"**Hours:** {restaurant.get('opening_time', '9AM')} - {restaurant.get('closing_time', '10PM')}")
            
            if 'description' in restaurant:
                st.markdown(f"*{restaurant.get('description', '')}*")
            
            # Add action buttons with completely unique keys
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                if st.button("Check Availability", 
                            key=f"{context}_check_{restaurant.get('id', '')}_{index}_{unique_id}"):
                    query = f"Check availability at {restaurant.get('name', '')} for tonight"
                    st.session_state.chat_history.append({"role": "user", "content": query})
                    assistant_response = send_message_to_api(query)
                    st.session_state.chat_history.append(assistant_response)
                    st.rerun()
            
            with col2_2:
                if st.button("Make Reservation", 
                            key=f"{context}_reserve_{restaurant.get('id', '')}_{index}_{unique_id}"):
                    query = f"Make a reservation at {restaurant.get('name', '')}"
                    st.session_state.chat_history.append({"role": "user", "content": query})
                    assistant_response = send_message_to_api(query)
                    st.session_state.chat_history.append(assistant_response)
                    st.rerun()
        
        st.markdown("---")

def render_booking_card(booking, index=None):
    """Renders a booking information card"""
    # Generate a unique ID for this specific render
    unique_id = str(uuid.uuid4())
    
    # Use an index if provided
    if index is None:
        index = 0
    
    with st.container():
        st.markdown(f"### Reservation at {booking.get('restaurant_name', booking.get('restaurant', {}).get('name', 'Restaurant'))}")
        
        # Create columns for booking details
        col1, col2 = st.columns(2)
        
        # Format the date if it's in ISO format
        reservation_time = booking.get('reservation_time', '')
        formatted_time = reservation_time
        try:
            if 'T' in reservation_time:
                dt = datetime.fromisoformat(reservation_time.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%I:%M %p on %A, %B %d, %Y")
        except:
            formatted_time = booking.get('formatted_time', reservation_time)
        
        with col1:
            st.markdown(f"**Reservation ID:** {booking.get('reservation_id', booking.get('id', 'Unknown'))}")
            st.markdown(f"**Date & Time:** {formatted_time}")
            st.markdown(f"**Party Size:** {booking.get('party_size', 'Unknown')}")
        
        with col2:
            # Action buttons with unique keys
            if st.button("Modify", 
                        key=f"modify_{booking.get('reservation_id', booking.get('id', ''))}_{index}_{unique_id}"):
                query = f"Modify my reservation with ID {booking.get('reservation_id', booking.get('id', ''))}"
                st.session_state.chat_history.append({"role": "user", "content": query})
                assistant_response = send_message_to_api(query)
                st.session_state.chat_history.append(assistant_response)
                st.rerun()
            
            if st.button("Cancel", 
                        key=f"cancel_{booking.get('reservation_id', booking.get('id', ''))}_{index}_{unique_id}"):
                query = f"Cancel my reservation with ID {booking.get('reservation_id', booking.get('id', ''))}"
                st.session_state.chat_history.append({"role": "user", "content": query})
                assistant_response = send_message_to_api(query)
                st.session_state.chat_history.append(assistant_response)
                st.rerun()
        
        st.markdown("---")

def extract_json_content(text):
    """Attempts to extract JSON content from a message"""
    try:
        # Look for common patterns that might contain JSON
        json_patterns = [
            r'\{.*\}',  # Standard JSON object
            r'\[.*\]',  # JSON array
            r'```json\s*([\s\S]*?)\s*```',  # Markdown code block with JSON
            r'```\s*([\s\S]*?)\s*```',  # Generic code block that might contain JSON
            r'\[DATA\](.*?)\[/DATA\]'  # Custom data format used in some responses
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    # Try to parse as JSON
                    return json.loads(match)
                except:
                    continue
        
        return None
    except:
        return None

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

# Add new functions to fetch restaurants and reservations
def fetch_top_restaurants(limit=10):
    try:
        response = st.session_state.http_session.get(
            f"{RESTAURANTS_API_ENDPOINT}?limit={limit}"
        )
        response.raise_for_status()
        return response.json(), True
    except requests.RequestException as e:
        st.error(f"Failed to fetch restaurants: {str(e)}")
        return [], False

def fetch_user_reservations():
    try:
        # Get the user's phone number from session state
        user_phone = None
        if st.session_state.user_data and "user" in st.session_state.user_data:
            user_phone = st.session_state.user_data["user"].get("phone")
        
        if not user_phone:
            st.warning("Phone number not found in user data")
            return [], False
        
        # Log the phone number for debugging
        print(f"Fetching reservations for phone number: {user_phone}")
        
        # Make a POST request with the phone number
        response = st.session_state.http_session.post(
            RESERVATIONS_API_ENDPOINT,
            json={"phone_number": user_phone}
        )
        
        # Debug response
        print(f"Reservation API Response Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Error response content: {response.text}")
            
        response.raise_for_status()
        data = response.json()
        print(f"Reservations data received: {data}")
        return data, True
    except requests.RequestException as e:
        error_msg = f"Failed to fetch reservations: {str(e)}"
        print(error_msg)
        st.error(error_msg)
        return [], False

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
    
    # Add tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Chat", "Top Restaurants", "My Reservations"])
    
    with tab1:
        if "text_input_value" not in st.session_state:
            st.session_state.text_input_value = ""
        
        # Chat container
        chat_container = st.container()
        
        # Display chat history
        with chat_container:
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    st.markdown(f"**You:** {message['content']}")
                else:
                    # Extract any potential JSON content from the message
                    content = message['content']
                    json_data = extract_json_content(content)
                    
                    # Check if the message contains restaurant info or booking info based on intent
                    intent = message.get('intent', 'unknown')
                    
                    # First display the text content
                    st.markdown(f"**Assistant:** {content}")
                    
                    # Display cards based on intent and content
                    if intent in ['restaurant_search', 'find_restaurant'] or 'restaurant' in intent:
                        # Try to extract restaurant information
                        if json_data and ('restaurants' in json_data or 'results' in json_data):
                            restaurants = json_data.get('restaurants', json_data.get('results', []))
                            if restaurants:
                                st.markdown("### Found Restaurants")
                                for idx, restaurant in enumerate(restaurants):
                                    render_restaurant_card(restaurant, idx, context="search")
                
                    elif intent in ['reservation_lookup', 'get_reservations', 'view_bookings']:
                        # Try to extract booking information
                        if json_data and 'reservations' in json_data:
                            reservations = json_data.get('reservations', [])
                            if reservations:
                                st.markdown("### Your Bookings")
                                for idx, booking in enumerate(reservations):
                                    render_booking_card(booking, idx)
                
                # Display intent with the assistant's message (debug info)
                intent_display = f"<small><i>Intent: {intent}</i></small>"
                st.markdown(intent_display, unsafe_allow_html=True)
                
                                # Display suggested actions if available
                if message.get("suggested_actions"):
                    st.markdown("**Suggested actions:**")
                    
                    # Create columns for a cleaner layout
                    action_cols = st.columns(min(3, len(message["suggested_actions"])))
                    
                    # Add a button for each suggested action that populates the text field
                    for i, action in enumerate(message["suggested_actions"]):
                        col_index = i % len(action_cols)
                        with action_cols[col_index]:
                            # Use a specific key for each button that doesn't change on each rerun
                            button_key = f"action_{hash(action)}_{i}"
                            if st.button(action, key=button_key):
                                # Set the value in session state
                                st.session_state["text_input_value"] = action
                                # Force a rerun to update the form with the new value
                                st.rerun()
    
    with tab2:
        st.header("Top Restaurants")
        
        # Fetch and display top restaurants
        with st.spinner("Loading restaurants..."):
            restaurants, success = fetch_top_restaurants()
            
            if success and restaurants:
                for idx, restaurant in enumerate(restaurants):
                    render_restaurant_card(restaurant, idx, context="top")
            elif success:
                st.info("No restaurants found.")
            else:
                st.error("Failed to load restaurants. Please try again later.")
    
    with tab3:
        st.header("My Reservations")
        
        # Fetch and display user reservations
        with st.spinner("Loading your reservations..."):
            reservations, success = fetch_user_reservations()
            
            if success and reservations:
                for idx, reservation in enumerate(reservations):
                    render_booking_card(reservation, idx)
            elif success:
                st.info("You don't have any reservations yet.")
            else:
                st.error("Failed to load reservations. Please try again later.")
    
    # Message input - keep inside tab1 if you want it only in the chat tab
    with tab1:
        with st.form("chat_input_form", clear_on_submit=True):
            # Get the current value from session state before creating the text input
            current_value = st.session_state.get("text_input_value", "")
            
            # Create the text input with the current value
            user_input = st.text_input(
                "Type your message:", 
                value=current_value,
                placeholder="e.g., Find Italian restaurants in Downtown",
                key="chat_input_field"
            )
            
            # Add the submit button
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
                
                # Clear the text input value for next time
                st.session_state["text_input_value"] = ""
                
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