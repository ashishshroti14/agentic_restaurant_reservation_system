import streamlit as st
import requests
import json
import re
from datetime import datetime
import time
import uuid  # Add this import for generating unique IDs
from dotenv import load_dotenv
import os
import pandas as pd  # Add pandas for dataframe manipulation for the map
import folium  # Add folium for better map customization
from streamlit_folium import folium_static  # Add this to display folium maps in Streamlit

# Load environment variables
load_dotenv()

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
CHAT_API_ENDPOINT = f"{API_BASE_URL}/chat/message"
AUTH_SEND_OTP_ENDPOINT = f"{API_BASE_URL}/auth/send-otp"
AUTH_VERIFY_OTP_ENDPOINT = f"{API_BASE_URL}/auth/verify-otp"
RESTAURANTS_API_ENDPOINT = f"{API_BASE_URL}/restaurants"
RESERVATIONS_API_ENDPOINT = f"{API_BASE_URL}/get-reservations/"

# Development mode flag - controls visibility of debug elements
DEV_MODE = os.getenv("DEV_MODE", "False").lower() == "true"

# Initialize http_session in session state
if "http_session" not in st.session_state:
    st.session_state.http_session = requests.Session()
    # Set any default headers if needed
    st.session_state.http_session.headers.update({
        "User-Agent": "FoodieSpot/1.0",
        "Content-Type": "application/json"
    })
    # If access token exists, add it to headers
    if "access_token" in st.session_state and st.session_state.access_token:
        st.session_state.http_session.headers.update({
            "Authorization": f"Bearer {st.session_state.access_token}"
        })
    

# Helper functions for rendering cards
# Initialize a counter in session state for unique keys
if "restaurant_key_counter" not in st.session_state:
    st.session_state.restaurant_key_counter = 0

# Initialize callback state
if "button_click" not in st.session_state:
    st.session_state.button_click = {
        "clicked": False,
        "value": ""
    }

# ADDED: Initialize text_input_value to ensure it's always present
if "text_input_value" not in st.session_state:
    st.session_state.text_input_value = ""

# Add a hidden_id variable to store IDs separately from visible text
if "hidden_id" not in st.session_state:
    st.session_state.hidden_id = None

# Initialize selected_restaurant to track which restaurant is highlighted
if "selected_restaurant" not in st.session_state:
    st.session_state.selected_restaurant = None

# Initialize selected_reservation to track which reservation is highlighted
if "selected_reservation" not in st.session_state:
    st.session_state.selected_reservation = None

# Add callback function for button clicks
def on_card_button_click(query, entity_id=None, entity_type=None, restaurant_id=None):
    """
    Callback for card button clicks that updates session state directly
    
    Args:
        query: The query text to display
        entity_id: The ID of the entity (restaurant or reservation)
        entity_type: Type of entity - 'restaurant' or 'reservation'
    """
    st.session_state.button_click["clicked"] = True
    st.session_state.button_click["value"] = query
    
    # Create a clean version of the query without the ID
    clean_query = query
    if entity_id is not None:
        # Remove the ID from the visible query
        clean_query = re.sub(r'\(ID: [^)]+\)', '', query).strip()
    
    # Set clean query to text input
    st.session_state.text_input_value = clean_query
    
    # Store the ID in the appropriate variable based on entity type
    if entity_type == "restaurant":
        st.session_state.restaurant_hidden_id = entity_id
        st.session_state.reservation_hidden_id = None
        # Also set the selected restaurant for highlighting
        st.session_state.selected_restaurant = entity_id
    elif entity_type == "reservation":
        st.session_state.reservation_hidden_id = entity_id
        st.session_state.restaurant_hidden_id = restaurant_id
    else:
        # If entity type is not specified, don't store any ID
        st.session_state.restaurant_hidden_id = None
        st.session_state.reservation_hidden_id = None
        
    print(f"Card button clicked: {clean_query} (Entity type: {entity_type}, ID: {entity_id})")
    print(f"Restaurant ID: {st.session_state.restaurant_hidden_id}, Reservation ID: {st.session_state.reservation_hidden_id}")

# Add callback to select a restaurant when clicking on a card
def select_restaurant(restaurant_id):
    """Select or deselect a restaurant"""
    # Toggle selection state
    if st.session_state.selected_restaurant == restaurant_id:
        st.session_state.selected_restaurant = None
    else:
        st.session_state.selected_restaurant = restaurant_id
        # Clear reservation selection when a restaurant is selected
        st.session_state.selected_reservation = None
        # Also clear reservation hidden ID
        st.session_state.reservation_hidden_id = None
    
    print(f"Restaurant selected: {st.session_state.selected_restaurant}")
    print(f"Reservation selection cleared: {st.session_state.selected_reservation}")

# Add callback to select a reservation when clicking on a card
def select_reservation(reservation_id):
    """Select or deselect a reservation"""
    # Toggle selection state
    if st.session_state.selected_reservation == reservation_id:
        st.session_state.selected_reservation = None
    else:
        st.session_state.selected_reservation = reservation_id
        # Clear restaurant selection when a reservation is selected
        st.session_state.selected_restaurant = None
        # Also clear restaurant hidden ID
        st.session_state.restaurant_hidden_id = None
    
    print(f"Reservation selected: {st.session_state.selected_reservation}")
    print(f"Restaurant selection cleared: {st.session_state.selected_restaurant}")

def render_restaurant_card(restaurant, index=None, context="default"):
    """
    Renders a restaurant information card using Streamlit native components
    
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
    
    # Check if this restaurant is selected
    restaurant_id = restaurant.get('id', '')
    is_selected = st.session_state.selected_restaurant == restaurant_id
    
    # Create a card container with styling
    with st.container():
        # Create a border effect with padding
        # st.markdown("---")
        
        # Restaurant name with star if selected
        name_prefix = "🌟 " if is_selected else ""
        st.subheader(f"{name_prefix}{restaurant.get('name', 'Restaurant')}")
        
        # Restaurant details in columns
        col1, col2 = st.columns([1, 3])
        
        with col1:
            # Restaurant image
            st.image("https://cdn-icons-png.flaticon.com/512/2702/2702391.png", width=100)
            
            # Selection button
            select_key = f"{context}_select_{restaurant.get('id', '')}_{index}_{unique_id}"
            if st.button(
                "✓ Selected" if is_selected else "Select", 
                key=select_key,
                on_click=select_restaurant,
                args=(restaurant_id,),
                type="primary" if is_selected else "secondary"
            ):
                pass  # Button action handled by callback
        
        with col2:
            # Restaurant details
            st.markdown(f"**Cuisine:** {restaurant.get('cuisine', 'Various')}")
            st.markdown(f"**Location:** {restaurant.get('location', 'Unknown')}")
            st.markdown(f"**Hours:** {restaurant.get('opening_time', '9AM')} - {restaurant.get('closing_time', '10PM')}")
            
            if 'description' in restaurant:
                st.markdown(f"*{restaurant.get('description', '')}*")
        
        # Action buttons
        st.markdown("#### Actions")
        col1, col2 = st.columns(2)
        
        with col1:
            # Check availability button - Include ID in original query but it will be removed in display
            check_query = f"Check availability at {restaurant.get('name', '')} (ID: {restaurant_id}) for tonight"
            check_key = f"{context}_check_{restaurant.get('id', '')}_{index}_{unique_id}"
            
            if st.button(
                "Check Availability", 
                key=check_key, 
                on_click=on_card_button_click, 
                args=(check_query, restaurant_id, "restaurant"),
                use_container_width=True
            ):
                pass  # Button action handled by callback
    
        with col2:
            # Make reservation button
            reserve_query = f"Make a reservation at {restaurant.get('name', '')} (ID: {restaurant_id})"
            reserve_key = f"{context}_reserve_{restaurant.get('id', '')}_{index}_{unique_id}"
            
            if st.button(
                "Make Reservation", 
                key=reserve_key, 
                on_click=on_card_button_click, 
                args=(reserve_query, restaurant_id, "restaurant"),
                use_container_width=True
            ):
                pass  # Button action handled by callback
        # if DEV_MODE:
        print("Access token set in session state:", st.session_state.get("access_token", "None"))
        
        st.markdown("---")

def render_booking_card(booking, index=None):
    """Renders a booking information card using Streamlit native components"""
    # Generate a unique ID for this specific render
    unique_id = str(uuid.uuid4())
    
    # Use an index if provided
    if index is None:
        index = 0
    
    # Get reservation ID and check if it's selected
    reservation_id = booking.get('reservation_id', booking.get('id', ''))
    is_selected = st.session_state.selected_reservation == reservation_id
    
    # Get reservation status
    status = booking.get('status', 'Active').capitalize()
    
    # Determine status styling
    status_color = "green"
    status_icon = "✓"
    
    if status.lower() == "cancelled" or status.lower() == "canceled":
        status_color = "red"
        status_icon = "✗"
    elif status.lower() == "pending":
        status_color = "orange"
        status_icon = "⏳"
    elif status.lower() == "confirmed":
        status_color = "green"
        status_icon = "✓"
    else:
        status_color = "blue"
        status_icon = "ℹ"
    
    # Create the card container with styling
    with st.container():
        # Create a border effect with padding
        # st.markdown("---")
        
        # Reservation name with star if selected
        name_prefix = "🌟 " if is_selected else ""
        st.subheader(f"{name_prefix}Reservation at {booking.get('restaurant_name', booking.get('restaurant', {}).get('name', 'Restaurant'))}")
        
        # Reservation details in columns - matching restaurant card layout
        col1, col2 = st.columns([1, 3])
        
        with col1:
            # Reservation image - using a calendar icon for reservations
            st.image("https://cdn-icons-png.flaticon.com/512/3480/3480428.png", width=100)
            
            # Selection button
            select_key = f"select_reservation_{reservation_id}_{index}_{unique_id}"
            if st.button(
                "✓ Selected" if is_selected else "Select", 
                key=select_key,
                on_click=select_reservation,
                args=(reservation_id,),
                type="primary" if is_selected else "secondary"
            ):
                pass  # Button action handled by callback
        
        with col2:
            # Display status with appropriate color - inline with other details
            if status_color == "green":
                st.success(f"{status_icon} {status}")
            elif status_color == "red":
                st.error(f"{status_icon} {status}")
            elif status_color == "orange":
                st.warning(f"{status_icon} {status}")
            else:
                st.info(f"{status_icon} {status}")
            
            # Format the date if it's in ISO format
            reservation_time = booking.get('reservation_time', '')
            formatted_time = reservation_time
            try:
                if 'T' in reservation_time:
                    dt = datetime.fromisoformat(reservation_time.replace('Z', '+00:00'))
                    formatted_time = dt.strftime("%I:%M %p on %A, %B %d, %Y")
            except:
                formatted_time = booking.get('formatted_time', reservation_time)
            
            # Reservation details
            st.markdown(f"**Reservation ID:** {reservation_id}")
            st.markdown(f"**Date & Time:** {formatted_time}")
            st.markdown(f"**Party Size:** {booking.get('party_size', 'Unknown')} people")
            
            # Additional details if available
            if 'special_requests' in booking and booking['special_requests']:
                st.markdown(f"**Special Requests:** {booking['special_requests']}")
        
        # Action buttons section
        if status.lower() not in ["cancelled", "canceled"]:
            st.markdown("#### Actions")
            button_col1, button_col2 = st.columns(2)
            
            with button_col1:
                # Modify reservation button - ID in query but will be hidden in display
                reservation_id = booking.get('reservation_id', booking.get('id', ''))
                restaurant_name = booking.get('restaurant_name', booking.get('restaurant', {}).get('name', 'Restaurant'))
                modify_query = f"Modify my reservation for {restaurant_name} (ID: {reservation_id})"
                modify_key = f"modify_{reservation_id}_{index}_{unique_id}"
                
                if st.button(
                    "✏️ Modify Reservation", 
                    key=modify_key, 
                    on_click=on_card_button_click, 
                    args=(modify_query, reservation_id, "reservation", booking.get('restaurant_id', '')),
                    use_container_width=True
                ):
                    pass  # Button action handled by callback
            
            with button_col2:
                # Cancel reservation button
                reservation_id = booking.get('reservation_id', booking.get('id', ''))
                restaurant_name = booking.get('restaurant_name', booking.get('restaurant', {}).get('name', 'Restaurant'))
                cancel_query = f"Cancel my reservation for {restaurant_name} (ID: {reservation_id})"
                cancel_key = f"cancel_{reservation_id}_{index}_{unique_id}"
                
                if st.button(
                    "❌ Cancel Reservation",
                    key=cancel_key,
                    on_click=on_card_button_click,
                    args=(cancel_query, reservation_id, "reservation", booking.get('restaurant_id', '')),
                    use_container_width=True
                ):
                    pass  # Button action handled by callback
        else:
            # For cancelled reservations
            st.info("This reservation has been cancelled and cannot be modified.")
        
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

# Page configuration - Switch to wide layout to support right sidebar
st.set_page_config(
    page_title="FoodieSpot - Restaurant Reservation Assistant",
    page_icon="🍽️",
    layout="wide"  # Changed from "centered" to "wide" to support right sidebar
)

# Add custom CSS to make the sidebar wider and create sticky map
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        min-width: 45vw !important;
        max-width: 45vw !important;
    }
    
    /* Adjust main content area to accommodate wider sidebar */
    .main .block-container {
        max-width: 95%;
        padding-left: 2rem;
        padding-right: 1rem;
    }
    
    /* Make content in the sidebar more readable with wider width */
    [data-testid="stSidebar"] .block-container {
        padding: 2rem 1rem;
    }
    
    /* Highlight style for selected restaurant */
    .selected-restaurant {
        border: 2px solid #4CAF50 !important;
        background-color: rgba(76, 175, 80, 0.1) !important;
        border-radius: 8px !important;
        padding: 15px !important;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important;
        margin-bottom: 15px !important;
    }
    
    /* Make restaurant card look clickable */
    .restaurant-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        transition: all 0.3s ease;
        background-color: #f9f9f9;
    }
    
    .restaurant-card:hover {
        border-color: #4CAF50;
        background-color: rgba(76, 175, 80, 0.05);
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    }
    
    /* Restaurant card styling */
    .restaurant-card h3, .selected-restaurant h3 {
        margin-top: 0;
        color: #2C3E50;
        font-weight: bold;
    }
    
    .restaurant-card p, .selected-restaurant p {
        margin: 8px 0;
        color: #34495E;
    }
    
    /* Add scrollable container style */
    .scrollable-container {
        height: 600px;
        overflow-y: auto;
        padding-right: 10px;
        border-radius: 5px;
    }
    
    /* Make the map column sticky when scrolling */
    .sticky-map {
        position: sticky;
        top: 0;
        height: calc(100vh - 100px);
        overflow-y: hidden;
        z-index: 1;
        padding-bottom: 1rem;
    }
    
    /* Make sure the map container stays fixed */
    .sticky-map .element-container {
        height: calc(100vh - 180px);
    }
    
    /* Ensure map is visible in the sticky container */
    .sticky-map iframe {
        height: 100% !important;
    }
</style>

<script>
function selectRestaurant(restaurantId) {
    // This function doesn't directly work with Streamlit's session state
    // It's here for future JavaScript integration if needed
    console.log("Selected restaurant: " + restaurantId);
}
</script>
""", unsafe_allow_html=True)

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

# ADDED: Initialize text_input_value to ensure it's always present
if "text_input_value" not in st.session_state:
    st.session_state.text_input_value = ""

# Add a hidden_id variable to store IDs separately from visible text
if "hidden_id" not in st.session_state:
    st.session_state.hidden_id = None

# Add separate ID variables for restaurants and reservations
if "restaurant_hidden_id" not in st.session_state:
    st.session_state.restaurant_hidden_id = None

if "reservation_hidden_id" not in st.session_state:
    st.session_state.reservation_hidden_id = None

# Initialize selected_restaurant to track which restaurant is highlighted
if "selected_restaurant" not in st.session_state:
    st.session_state.selected_restaurant = None

# Initialize selected_reservation to track which reservation is highlighted
if "selected_reservation" not in st.session_state:
    st.session_state.selected_reservation = None

# ADDED: Function to update the input text value
def update_input_text(value):
    """Helper function to update the input text value consistently"""
    print(f"Setting input text to: {value}")
    # Only update our custom session state key, not the widget key directly
    st.session_state["text_input_value"] = value
    # Clear any stored hidden IDs when directly setting text
    st.session_state["restaurant_hidden_id"] = None
    st.session_state["reservation_hidden_id"] = None
    # Do NOT update sidebar_chat_input_field directly as it belongs to a widget
    # st.session_state["sidebar_chat_input_field"] = value  # This line causes the error

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
                print(f"Access token set in session state: {st.session_state.access_token}")
                
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
        # but we can check and add it here for redundancy
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
            "agent": data.get("agent", "unknown")  # Capture the agent from the API response
        }
    except requests.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return {
            "role": "assistant",
            "content": f"Sorry, I encountered an error connecting to the server: {str(e)}",
            "suggested_actions": [],
            "agent": "error"
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

# Add debug section to sidebar - only in dev mode
with st.sidebar:
    if DEV_MODE:
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

# Add a simple navbar when authenticated
if st.session_state.auth_state == "authenticated":
    # Create a simple navbar with columns
    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
    
    with nav_col3:
        # Right-aligned logout button
        if st.button("🚪 Logout", key="navbar_logout"):
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
                    "agent": "greeting"
                }
                st.session_state.chat_history.append(welcome_message)
                st.rerun()
    
    if st.button("Change phone number"):
        st.session_state.auth_state = "not_authenticated"
        st.session_state.phone_number = ""
        st.rerun()

# Chat UI - Only show when authenticated
elif st.session_state.auth_state == "authenticated":
    # Create a 3-column layout: sidebar (built-in), main content, right sidebar
    # Right sidebar container
    right_sidebar = st.sidebar.container()
    
    # We'll move the actual sidebar content to the right_sidebar later
    # First, let's use the built-in left sidebar for the chat assistant
    with st.sidebar:
        st.header("Chat Assistant")
        
        # Add a small note about the sidebar size
        st.markdown("<small>Chat interface is now in expanded view</small>", unsafe_allow_html=True)
        
        # Chat container in sidebar
        with st.container():
            # Create a fixed height container using CSS
            st.markdown("""
            <style>
            .chat-container {
                height: 350px;
                overflow-y: auto;
                border: 1px solid #e0e0e0;
                padding: 10px;
                margin-bottom: 15px;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Use Streamlit native elements for the chat (more reliable than HTML/CSS)
            with st.container():
                # Display last 10 messages to avoid cluttering
                st.subheader("Conversation")
                for message in st.session_state.chat_history[-10:]:
                    if message["role"] == "user":
                        st.markdown(f"**👤 You:** {message['content']}")
                    else:
                        st.markdown(f"**🤖 Assistant:** {message['content']}")
                        # Add agent for debugging - only in dev mode
                        st.markdown(f"<small><i>Agent: {message.get('agent', 'unknown')}</i></small>", unsafe_allow_html=True)

            suggested_actions = []
            agent = message.get('agent', 'unknown')
            if agent == 'reservation_creator':
                suggested_actions = [
                    "Create a new reservation",
                    "View existing reservations",
                    "Cancel a reservation"
                ]
            elif agent == 'restaurant_finder':
                suggested_actions = [
                    "Find Italian restaurants",
                    "Check restaurants in Downtown",
                    "Make a reservation for tonight"
                ]
            elif agent == 'reservation_modifier':
                suggested_actions = [
                    "Modify an existing reservation",
                    "Change the reservation time",
                    "Update the number of guests"
                ]
            elif agent == 'reservation_retriever':
                suggested_actions = [
                    "View my reservations",
                    "Check reservation status",
                    "Cancel a reservation"
                ]
            elif agent == 'availability_checker':
                suggested_actions = [
                    "Check table availability",
                    "Find available time slots",
                    "Check if a restaurant is open"
                ]
            elif agent == 'general_assistant':
                suggested_actions = [
                    "Ask about restaurant hours",
                    "Get restaurant recommendations",
                    "Find nearby restaurants"
                ]
            else:
                # Default suggested actions if no specific agent is matched
                suggested_actions = [
                    "Find restaurants",
                    "Make a reservation",
                    "Check my reservations"
                ]
            # Display count of suggested actions for debugging - only in dev mode
            if DEV_MODE and st.session_state.chat_history:
                last_message = st.session_state.chat_history[-1]
                if last_message["role"] == "assistant":
                    # Ensure suggested_actions is never None by providing a default empty list
                    suggested_actions = last_message.get("suggested_actions", []) or []
                    st.write(f"Debug: Found {len(suggested_actions)} suggested actions")
            
            # SUGGESTED ACTIONS SECTION - Make it very prominent
            st.markdown("---")
            st.markdown("### 🔍 Suggested Actions")
            
            # Get the most recent message from the assistant
            assistant_messages = [msg for msg in st.session_state.chat_history if msg["role"] == "assistant"]
            if assistant_messages:
                latest_assistant_message = assistant_messages[-1]
                # Fix: Ensure suggested_actions is never None
                # suggested_actions = latest_assistant_message.get("suggested_actions", []) or []
                
                if suggested_actions:
                    # Create a grid of buttons for suggested actions
                    for i, action in enumerate(suggested_actions):
                        # Make each button full width and styled prominently
                        # We don't modify suggested actions as they come from the backend and may already include IDs
                        if st.button(
                            f"🔹 {action}", 
                            key=f"action_{i}_{hash(action)}",
                            use_container_width=True,
                        ):
                            # UPDATED: Use the helper function to update text
                            update_input_text(action)
                            st.rerun()
                else:
                    st.info("No suggested actions available.")
            else:
                st.info("Start chatting to get suggestions.")
            
            st.markdown("---")
        
        st.markdown("### 💬 Send a message")
        
        # Debug output for session state values - only in dev mode
        if DEV_MODE:
            st.write("Debug - Text input value:", st.session_state.get("text_input_value", "None"))
            st.write("Debug - Button click state:", st.session_state.button_click)

        with st.form("sidebar_chat_input_form", clear_on_submit=True):
            # Get the current value from session state - ONLY use text_input_value
            current_value = st.session_state.get("text_input_value", "")
            
            # Debug info - only in dev mode
            if DEV_MODE:
                st.write(f"Debug - Using value in form: {current_value}")
            
            # Create the text input with the current value
            user_input = st.text_area(
                "Type your message:", 
                value=current_value,  # Pass our custom session state value here
                placeholder="Ask about restaurants or reservations...",
                key="sidebar_chat_input_field",
                height=80  # Make the input box larger
            )
            
            # Create a row for the buttons
            button_cols = st.columns([4, 1])
            
            # Main send button in the first (wider) column
            with button_cols[0]:
                submit_button = st.form_submit_button("📤 Send", use_container_width=True)
            
            # New conversation button (smaller) in the second column
            with button_cols[1]:
                clear_chat = st.form_submit_button("🗑️", help="Start a new conversation", use_container_width=True)
            
            # Handle form submissions
            if submit_button and user_input:
                # Get hidden IDs if available
                restaurant_id = st.session_state.get("restaurant_hidden_id")
                reservation_id = st.session_state.get("reservation_hidden_id")
                
                # Determine which ID to use based on the query content
                message_to_send = user_input
                
                if reservation_id:
                    message_to_send = f"{user_input} (Reservation ID: {reservation_id}) (Restaurant ID: {restaurant_id})"
                elif restaurant_id:
                    message_to_send = f"{user_input} (Restaurant ID: {restaurant_id})"
                
                # Add user message to chat history (show what the user typed)
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_input  # Show the clean version in the chat
                })
                
                # Send the message with the ID to the API
                assistant_response = send_message_to_api(message_to_send)
                st.session_state.chat_history.append(assistant_response)
                
                # Clear the input and hidden IDs
                st.session_state["text_input_value"] = ""
                # st.session_state["restaurant_hidden_id"] = None
                # st.session_state["reservation_hidden_id"] = None
                
                # Force a rerun to update the UI with the new messages
                st.rerun()

            # Handle new conversation button
            if clear_chat:
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
                    "agent": "greeting"
                }
                st.session_state.chat_history.append(welcome_message)
                st.rerun()

    # Main content area - Restaurants and Reservations
    # Adjust column widths to account for the wider sidebar
    st.markdown("## Find and Book Restaurants")
    
    # Create tabs instead of columns for better organization and space utilization
    restaurant_tab, reservation_tab = st.tabs(["🍽️ Restaurants", "📅 Reservations"])
    
    # Top Restaurants section in first tab
    with restaurant_tab:
        # Create two columns for the layout - map on left, list on right
        map_col, list_col = st.columns([1, 1])
        
        # Add the sticky-map class to the map column
        # map_col.markdown('<div class="sticky-map">', unsafe_allow_html=True)
        
        with map_col:
            st.subheader("Restaurant Locations")
            
            # Fetch and display restaurants on a map
            with st.spinner("Loading map..."):
                # Get the restaurants data
                restaurants, success = fetch_top_restaurants(limit=20)  # Get more restaurants for the map
                
                if success and restaurants:
                    # Create data for the map
                    map_data = []
                    selected_restaurant_data = None
                    
                    for restaurant in restaurants:
                        # Only add restaurants with valid location data
                        if restaurant.get('latitude') and restaurant.get('longitude'):
                            restaurant_data = {
                                'id': restaurant.get('id', ''),
                                'name': restaurant.get('name', 'Unknown'),
                                'lat': restaurant.get('latitude'),
                                'lon': restaurant.get('longitude'),
                                'location': restaurant.get('location', 'Unknown'),
                                'cuisine': restaurant.get('cuisine', 'Various'),
                                'is_selected': restaurant.get('id') == st.session_state.selected_restaurant
                            }
                            map_data.append(restaurant_data)
                            
                            # Save the selected restaurant data separately for centering the map
                            if restaurant_data['is_selected']:
                                selected_restaurant_data = restaurant_data
                    
                    if map_data:
                        # Determine the map center
                        if selected_restaurant_data:
                            # Center on selected restaurant
                            map_center = [selected_restaurant_data['lat'], selected_restaurant_data['lon']]
                            zoom_start = 14  # Closer zoom when a restaurant is selected
                        else:
                            # Center on the average of all coordinates
                            avg_lat = sum(r['lat'] for r in map_data) / len(map_data)
                            avg_lon = sum(r['lon'] for r in map_data) / len(map_data)
                            map_center = [avg_lat, avg_lon]
                            zoom_start = 12  # Default zoom level
                        
                        # Create a folium map
                        m = folium.Map(location=map_center, zoom_start=zoom_start)
                        
                        # Add markers for each restaurant
                        for r in map_data:
                            # Create popup content with HTML
                            popup_html = f"""
                            <div style="width:200px">
                                <h4>{r['name']}</h4>
                                <p><b>Cuisine:</b> {r['cuisine']}</p>
                                <p><b>Location:</b> {r['location']}</p>
                            </div>
                            """
                            
                            # Create a popup with the HTML content
                            popup = folium.Popup(popup_html, max_width=300)
                            
                            if r['is_selected']:
                                # Special marker for selected restaurant
                                folium.Marker(
                                    location=[r['lat'], r['lon']],
                                    popup=popup,
                                    tooltip=r['name'],
                                    icon=folium.Icon(color='red', icon='star', prefix='fa'),
                                ).add_to(m)
                                
                                # Add a circle to highlight the selected restaurant
                                folium.Circle(
                                    location=[r['lat'], r['lon']],
                                    radius=50,
                                    color='red',
                                    fill=True,
                                    fill_color='red',
                                    fill_opacity=0.2
                                ).add_to(m)
                            else:
                                # Standard marker for other restaurants
                                folium.Marker(
                                    location=[r['lat'], r['lon']],
                                    popup=popup,
                                    tooltip=r['name'],
                                    icon=folium.Icon(color='blue', icon='utensils', prefix='fa'),
                                ).add_to(m)
                        
                        # Display the folium map in Streamlit
                        folium_static(m)
                        
                        # Display a legend or list below the map
                        with st.expander("Restaurants on Map", expanded=False):
                            for i, r in enumerate(map_data):
                                if r['is_selected']:
                                    st.markdown(f"{i+1}. **{r['name']} 🌟** - {r['location']}")
                                else:
                                    st.write(f"{i+1}. **{r['name']}** - {r['location']}")
                    else:
                        st.info("No restaurants with location data available to display on map.")
                elif success:
                    st.info("No restaurants found to display on map.")
                else:
                    st.error("Failed to load restaurant locations. Please try again later.")
        
        # Close the sticky map container
        map_col.markdown('</div>', unsafe_allow_html=True)
        
        with list_col:
            st.subheader("Top Restaurants")
            
            # Create a container specifically for the restaurant list
            restaurant_list = st.container()
            
            # Apply CSS to create a scrollable area specifically for this container
            st.markdown("""
            <style>
            /* Target the restaurant list container to make it scrollable */
            section:has(div.element-container:has(div.stMarkdown h3:contains("Top Restaurants"))) > div:nth-child(3) {
                max-height: 600px;
                overflow-y: auto !important;
                overflow-x: hidden;
                padding-right: 10px;
                margin-bottom: 15px;
                border-radius: 5px;
                border: 1px solid #f0f0f0;
                background-color: rgba(255, 255, 255, 0.5);
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Put the restaurant cards inside the container to make them scrollable
            with restaurant_list:
                # Fetch and display top restaurants
                with st.spinner("Loading restaurants..."):
                    # We've already fetched restaurants for the map, so let's use them if available
                    if 'restaurants' in locals() and restaurants and success:
                        for idx, restaurant in enumerate(restaurants):  # Show all restaurants in scrollable list
                            render_restaurant_card(restaurant, idx, context="top")
                    else:
                        # If we don't have the data already, fetch it
                        restaurants, success = fetch_top_restaurants(limit=15)  # Increased limit for scrolling
                        if success and restaurants:
                            for idx, restaurant in enumerate(restaurants):
                                render_restaurant_card(restaurant, idx, context="top")
                        elif success:
                            st.info("No restaurants found.")
                        else:
                            st.error("Failed to load restaurants. Please try again later.")
    
    # My Reservations section in second tab
    with reservation_tab:
        st.subheader("My Reservations")
        
        # Fetch and display user reservations
        with st.spinner("Loading your reservations..."):
            reservations, success = fetch_user_reservations()
            
            if success and reservations:
                # Sort reservations - active ones first, cancelled ones last
                sorted_reservations = sorted(reservations, 
                                        key=lambda x: 1 if x.get('status', '').lower() in ['cancelled', 'canceled'] else 0)
                
                for idx, reservation in enumerate(sorted_reservations):
                    render_booking_card(reservation, idx)
            elif success:
                st.info("You don't have any reservations yet.")
            else:
                st.error("Failed to load reservations. Please try again later.")
                
        # Add a button to manage all reservations
        if st.button("Manage All Reservations", on_click=on_card_button_click, args=("Show all my reservations",)):
            # This code runs after the callback, just in case the callback doesn't trigger rerun
            pass
    
    # Create a new column all the way to the right for our custom "right sidebar"
    _, right_area = st.columns([2, 1])
    
    # Right sidebar for details
    with right_area:
        st.markdown("### FoodieSpot Details")
        
        # About FoodieSpot in collapsible section
        with st.expander("About FoodieSpot", expanded=False):
            st.write("FoodieSpot is an intelligent restaurant reservation system that helps you find and book restaurants based on your preferences.")
            
            # Add app screenshot or logo here if needed
            st.image("https://cdn-icons-png.flaticon.com/512/2702/2702391.png", width=300)
        
        # User Info in collapsible section
        with st.expander("User Info", expanded=False):
            if st.session_state.user_data and "user" in st.session_state.user_data:
                user = st.session_state.user_data["user"]
                st.write(f"**Name:** {user.get('full_name', 'Not provided')}")
                st.write(f"**Phone:** {user.get('phone', 'Not provided')}")
            else:
                st.write("User information not available.")
        
        # Enhanced State Variables Section - only in dev mode
        if DEV_MODE:
            with st.expander("State Variables", expanded=True):
                # Add tabs for different categories of state variables
                state_tabs = st.tabs(["IDs & Selection", "Authentication", "Chat", "All Variables"])
                
                with state_tabs[0]:
                    # ID and selection variables
                    st.subheader("ID & Selection Variables")
                    id_vars = {
                        "Selected Restaurant": st.session_state.selected_restaurant,
                        "Selected Reservation": st.session_state.selected_reservation,
                        "Restaurant Hidden ID": st.session_state.restaurant_hidden_id,
                        "Reservation Hidden ID": st.session_state.reservation_hidden_id,
                        "Generic Hidden ID": st.session_state.hidden_id
                    }
                    
                    # Display in a more readable format
                    for key, value in id_vars.items():
                        st.write(f"**{key}:** {value if value is not None else 'None'}")
                
                with state_tabs[1]:
                    # Authentication variables
                    st.subheader("Authentication Variables")
                    auth_vars = {
                        "Auth State": st.session_state.auth_state,
                        "Phone Number": st.session_state.phone_number,
                        "Access Token Present": st.session_state.access_token is not None,
                        "Session ID": st.session_state.session_id
                    }
                    
                    for key, value in auth_vars.items():
                        st.write(f"**{key}:** {value}")
                
                with state_tabs[2]:
                    # Chat variables
                    st.subheader("Chat Variables")
                    chat_vars = {
                        "Text Input Value": st.session_state.text_input_value,
                        "Chat History Length": len(st.session_state.chat_history),
                        "Button Click State": st.session_state.button_click
                    }
                    
                    for key, value in chat_vars.items():
                        st.write(f"**{key}:** {value}")
                
                with state_tabs[3]:
                    # All session state variables
                    st.subheader("All Session State Variables")
                    
                    # Add a search filter
                    search_term = st.text_input("Filter variables:", placeholder="Enter variable name...")
                    
                    # Filter and display all session state variables
                    filtered_vars = {k: v for k, v in st.session_state.items() 
                                    if not search_term or search_term.lower() in k.lower()}
                    
                    # Show count of variables
                    st.write(f"Showing {len(filtered_vars)} of {len(st.session_state)} variables")
                    
                    # Create a clean table view
                    if filtered_vars:
                        data = []
                        for k, v in filtered_vars.items():
                            # Handle different types of values for display
                            if isinstance(v, (dict, list)):
                                val = f"{type(v).__name__} with {len(v)} items"
                            elif isinstance(v, str) and len(v) > 50:
                                val = f"{v[:50]}..."
                            else:
                                val = str(v)
                        
                            data.append({"Variable": k, "Value": val, "Type": type(v).__name__})
                        
                        # Display as a dataframe for better readability
                        st.dataframe(data, use_container_width=True)
                    else:
                        st.info("No variables match your filter.")
        
        # Debug Info in collapsible section - only in dev mode
        if DEV_MODE:
            with st.expander("Debug Actions", expanded=False):
                st.write("Authentication State:", st.session_state.auth_state)
                st.write("Session ID:", st.session_state.session_id)
                st.write("Has access token:", st.session_state.access_token is not None)
                st.write("Restaurant ID:", st.session_state.restaurant_hidden_id)
                st.write("Reservation ID:", st.session_state.reservation_hidden_id)
                
                if st.button("Clear All Session Data", key="right_sidebar_clear"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()
        
        # Session actions - Removed the buttons that were moved elsewhere
        st.markdown("### App Information")
        st.write("FoodieSpot helps you discover and book restaurants easily.")
        st.write("Use the chat assistant to find restaurants, check availability, and make reservations.")

# Check if a button was clicked and handle it
if st.session_state.button_click["clicked"]:
    # Reset the clicked state
    st.session_state.button_click["clicked"] = False
    # The value should already be in text_input_value from the callback
    # Force a rerun to update the UI
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
        "agent": "greeting"
    }
    st.session_state.chat_history.append(welcome_message)
    st.rerun()