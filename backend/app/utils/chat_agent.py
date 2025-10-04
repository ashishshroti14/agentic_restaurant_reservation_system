import os
import json
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI
from ..models.chat import ChatMessage, ChatSession
from ..db.database import get_restaurant, get_restaurants, check_availability, add_reservation
from .agent_tools import AVAILABLE_TOOLS
from .logging_utils import log_llm_interaction, logger
from .datetime_utils import standardize_object_for_json, json_dumps, to_standard_datetime_string

# Load environment variables
load_dotenv()

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL")


# Session storage (replace with database in production)
sessions: Dict[str, ChatSession] = {}  # This in-memory storage is problematic for persistence

# System prompt for the restaurant assistant
SYSTEM_PROMPT = """You are an intelligent restaurant assistant. Answer concisely based on the user's queries.
 an intelligent restaurant assistant for FoodieSpot, a restaurant reservation platform. 
Your name is FoodieBot. Your goal is to help users find restaurants and make reservations.

{user_context}

You can:
1. Help users find restaurants by cuisine, location, or other criteria.
2. Check availability for reservations at specific restaurants.
3. Make reservations for users.
4. Cancel existing reservations.
5. Provide information about restaurants (opening hours, cuisine, contact details).
6. Do not make up information about restaurants or reservations.
7. If you don't know the answer, say "I don't know" or "I'm not sure."
8. If you need to ask the user for more information, do so politely.
9. If the user asks for something outside your expertise, politely redirect them to the appropriate service.
10. If the user asks for a specific restaurant, provide information about it if available.
11. If the user asks for a reservation, ask for the date, time, party size, and restaurant name.

CRITICAL TOOL USAGE INSTRUCTIONS:
1. ALWAYS ask the user for ALL required parameters before using a tool. Do not make assumptions.
2. NEVER make up or invent values for missing parameters - ask the user explicitly.
3. For reservations: You MUST have restaurant name, date, time, and party size before checking availability.
4. For searches: You MUST clarify search criteria (cuisine type, location, etc.) with the user first.
5. If the user provides incomplete information, ask follow-up questions to gather all necessary details.
6. Only after you have all required information should you proceed with the tool call.
7. When gathering information, clearly explain to the user which details you still need.
8. LOOK AT THE TOOL OUTPUTS CAREFULLY - they will provide the exact information you need to respond. 
9. You wont ever need to ask the user to wait for a response - the tools will return results immediately, determine if the tool ran successfully or not, and then respond to the user accordingly.
10. NEVER EVER GIVE AN EMPTY RESPONSE - always provide a meaningful answer based on the tool results.
11. DO NOT ASK THE USER TO WAIT - you can respond immediately based on tool results.

IMPORTANT: Always include relevant IDs in your responses to help with workflow continuity.
- When listing restaurants, include their IDs.
- When showing reservation details, include the reservation ID.
- Always mention these IDs clearly so they can be referenced in follow-up conversations.
- IDs are ESSENTIAL for the system to function properly - never omit them!

You will receive access to tools with complete descriptions, input requirements, and output formats.

CRITICAL ANTI-HALLUCINATION INSTRUCTIONS:
1. NEVER invent or make up restaurant names, information, or details.
2. ONLY discuss restaurants that are explicitly returned by search tools.
3. If no restaurants are found, clearly state "I couldn't find any restaurants matching your criteria" - DO NOT suggest fictional alternatives.
4. Always use the search_restaurants tool before discussing any restaurant.
5. If you're unsure about a restaurant's existence, tell the user "I don't have information about that restaurant in our database."
6. ALL restaurant information MUST come from database tools, never from your training data.
7. When in doubt, tell the user you need to search the database rather than providing potentially made-up information.
8. No email is going to be sent to the user.

Do not reveal any information about any user with a different phone number.

The current date and time is: {current_datetime}."""

# Agent patterns (renamed from intent patterns)
RESTAURANT_FINDER_PATTERN = re.compile(r'(find|search|looking for|suggest|recommend).*restaurant', re.IGNORECASE)
AVAILABILITY_CHECKER_PATTERN = re.compile(r'(check|available|availability|open|book)', re.IGNORECASE)
RESERVATION_CREATOR_PATTERN = re.compile(r'(make|book|reserve|reservation)', re.IGNORECASE)
RESERVATION_RETRIEVER_PATTERN = re.compile(r'(find|get|show|view|my|list|retrieve)(\s+my)?(\s+reservations?)', re.IGNORECASE)
RESERVATION_MODIFIER_PATTERN = re.compile(r'(change|update|modify|edit|reschedule)(\s+my)?(\s+reservations?)', re.IGNORECASE)

# Agent to intent mapping for parameter extraction (for backward compatibility)
AGENT_TO_INTENT_MAP = {
    "restaurant_finder": "find_restaurant",
    "availability_checker": "check_availability",
    "reservation_creator": "make_reservation",
    "reservation_retriever": "retrieve_reservation",
    "reservation_modifier": "modify_reservation",
    "general_assistant": "general_inquiry"
}

def standardize_phone_number(phone: str) -> str:
    """
    Standardize a phone number by removing spaces, dashes, parentheses, etc.
    Returns a clean phone number with only digits and possibly a leading +
    """
    if not phone:
        return phone
        
    # Keep the + sign if it exists at the beginning
    has_plus = phone.startswith('+')
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Add back the + if it was there
    if has_plus:
        return f"+{digits_only}"
    return digits_only

def get_or_create_session(session_id: Optional[str] = None, user_id: Optional[str] = None, phone_number: Optional[str] = None) -> ChatSession:
    """Get an existing chat session or create a new one"""
    # Standardize phone number if provided
    if phone_number:
        phone_number = standardize_phone_number(phone_number)
        
    # Session lookup logic here - this maintains context for existing sessions
    # But uses in-memory storage which doesn't persist across server restarts
    if session_id and session_id in sessions:
        session = sessions[session_id]
        # Update phone number if provided and different from what's stored
        if phone_number and session.phone_number != phone_number:
            session.phone_number = phone_number
            logger.info(f"Updated phone number to standardized format: {phone_number}")
        return session
    
    # Create a new session with system prompt
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_context = ""
    if phone_number:
        user_context = f"USER INFORMATION:\nPhone Number: {phone_number}"
        
    system_msg = ChatMessage(
        role="system", 
        content=SYSTEM_PROMPT.format(current_datetime=current_time, user_context=user_context)
    )
    
    session = ChatSession(user_id=user_id, phone_number=phone_number)
    session.messages.append(system_msg)
    
    # Store session
    sessions[session.id] = session
    return session

def detect_agent(message: str, session: Optional[ChatSession] = None) -> str:
    """Detect the user's agent from their message using LLM with full conversation context"""
    
    # Extract conversation history from session if available
    conversation_history = []
    if session:
        # Get only user and assistant messages (skip system messages)
        history_messages = [msg for msg in session.messages 
                           if msg.role in ["user", "assistant", "system"]][-50:]

        # Format conversation history
        for msg in history_messages:
            conversation_history.append(f"{msg.role.capitalize()}: {msg.content}")
    
    # Use LLM for agent classification with updated agent categories
    try:
        client = OpenAI(
            base_url=OPENROUTER_URL,
            api_key=OPENROUTER_API_KEY,
        )
        
        # Create a comprehensive prompt for agent classification with full conversation context
        agent_prompt = f"""
        You are analyzing a conversation between a user and FoodieSpot, a restaurant reservation platform assistant.

        {'No conversation history available.' if not conversation_history else f'''CONVERSATION HISTORY:

         {''.join(conversation_history)}
         '''}

        CURRENT USER MESSAGE: "{message}"
        
        Based on the full conversation context, classify which agent should handle this request:
        
        1. restaurant_finder: 
           - User is looking for restaurant suggestions or recommendations
           - User wants to discover new places to eat
           - User is asking about restaurants with specific cuisine, location, or features
           - Examples: "Can you suggest Italian restaurants?", "Find me a romantic restaurant for dinner"
        
        2. availability_checker: 
           - User wants to check if a restaurant has available seating/tables
           - User is inquiring about specific dates, times for dining
           - User wants to know if they can get a table without making a reservation
           - Examples: "Is Bella Italia available this Friday?", "Do you have a table for 4 tomorrow at 7pm?"
        
        3. reservation_creator: 
           - User explicitly wants to book a table
           - User wants to reserve seating for a specific time, date, and party size
           - User is ready to confirm a booking
           - Examples: "Book a table for 2 at La Trattoria", "I want to make a reservation at Sushi Express"
           
        4. reservation_retriever:
           - User wants to see or find their existing reservations
           - User is asking about bookings they've already made
           - Examples: "Show my reservations", "What bookings do I have?", "Find my reservation"
           
        5. reservation_modifier:
           - User wants to change an existing reservation
           - User wants to update details like time, date, party size for an existing booking
           - User wants to cancel an existing reservation
           - User wants to delete or remove a booking they previously made
           - User is responding affirmatively to a cancellation confirmation
           - Examples: "Change my reservation time", "Update my booking", "Reschedule my reservation", "Cancel my reservation", "Delete my booking", "Yes, please cancel it"
        
        6. general_assistant: 
           - Any other questions about restaurants, dining, or the platform
           - User is asking about how the service works
        
        Your response must be EXACTLY ONE of these agent names: restaurant_finder, availability_checker, reservation_creator, reservation_retriever, reservation_modifier, general_assistant
        """
        
        # Log that we're making an agent detection LLM call
        logger.info(f"Making agent detection LLM call for message: {message}")
        logger.info(f"Including {len(conversation_history)} conversation history items")
        
        start_time = time.time()
        completion = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "You are an agent classification system for a restaurant reservation platform. Only respond with the exact agent name. Always choose one of the provided agents."},
                {"role": "user", "content": agent_prompt}
            ],
             temperature=0,
            # max_tokens=200
        )
        execution_time = time.time() - start_time
        print(completion.choices, "aaaaaaaaaaaaaaaaaaa")
        
        # Extract and normalize agent name
        agent = completion.choices[0].message.content.strip().lower()
        
        # Log the agent detection
        log_llm_interaction(
            model=DEFAULT_MODEL,
            prompt=agent_prompt,
            response=agent,
            execution_time=execution_time,
            metadata={"operation": "agent_detection", "session_id": session.id if session else None}
        )
        
        # Validate agent name
        valid_agents = ["restaurant_finder", "availability_checker", "reservation_creator", 
                        "reservation_retriever", "reservation_modifier", "general_assistant"]
        
        if agent in valid_agents:
            logger.info(f"Detected agent: '{agent}'")
            return agent
        else:
            # Fallback to general assistant if agent not recognized
            logger.warning(f"Unrecognized agent '{agent}', falling back to general_assistant")
            return "general_assistant"
            
    except Exception as e:
        # Log the error and fall back to regex matching
        logger.error(f"Error in LLM agent detection: {str(e)}", exc_info=True)
        
        # Fallback to regex-based detection with direct agent naming
        if RESERVATION_RETRIEVER_PATTERN.search(message):
            return "reservation_retriever"
        elif RESERVATION_MODIFIER_PATTERN.search(message):
            return "reservation_modifier"
        elif RESTAURANT_FINDER_PATTERN.search(message):
            return "restaurant_finder"
        elif AVAILABILITY_CHECKER_PATTERN.search(message):
            return "availability_checker"
        elif RESERVATION_CREATOR_PATTERN.search(message):
            return "reservation_creator"
        else:
            return "general_assistant"

def extract_parameters(message: str, agent: str, session: Optional[ChatSession] = None) -> Dict[str, Any]:
    """Extract parameters from the user message based on agent using LLM with full conversation context"""
    # Convert agent to intent for parameter extraction (for backward compatibility)
    intent = AGENT_TO_INTENT_MAP.get(agent, "general_inquiry")
    
    if not OPENROUTER_API_KEY:
        # Return empty params if no API key is available
        return {}
    
    try:
        # Initialize OpenAI client here before using it
        client = OpenAI(
            base_url=OPENROUTER_URL,
            api_key=OPENROUTER_API_KEY,
        )
        
        # Extract conversation history and system context if session is provided
        conversation_context = ""
        system_context = ""
        user_phone = None
        
        if session and session.phone_number:
            user_phone = session.phone_number
            logger.info(f"Using phone number {user_phone} from session {session.id} for parameter extraction")
        
        if session:
            # Get system messages for context
            system_messages = [msg for msg in session.messages if msg.role == "system"]
            if system_messages:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                user_context = ""
                if session.phone_number:
                    user_phone = session.phone_number
                    user_context = f"USER INFORMATION:\nPhone Number: {session.phone_number}"
                
                # Format system context
                system_context = system_messages[0].content.format(
                    current_datetime=current_time,
                    user_context=user_context
                )
            
            # Get conversation history (recent messages)
            history_messages = [msg for msg in session.messages 
                               if msg.role in ["user", "assistant", "system"]][-50:]  # Last 50 messages

            if history_messages:
                conversation_context = "RECENT CONVERSATION:\n"
                for msg in history_messages:
                    conversation_context += f"{msg.role.capitalize()}: {msg.content}\n"
        
        # Create a prompt based on the agent
        if agent == "restaurant_finder":
            extraction_prompt = f"""
            {system_context if system_context else ""}
            
            {conversation_context if conversation_context else ""}
            
            Extract the following parameters from the conversation in JSON format:
            1. cuisine: What type of food or cuisine are they looking for? (e.g., Italian, Chinese, vegan)
            2. location: Where do they want to find the restaurant? (e.g., downtown, north side, specific neighborhood)
            3. other_preferences: Any other preferences mentioned (e.g., outdoor seating, romantic, family-friendly)
            
            Current user message: "{message}"
            
            Respond ONLY with a valid JSON object containing these parameters. If a parameter is not mentioned, set its value to null.
            Example response: {{"cuisine": "Italian", "location": "downtown", "other_preferences": "outdoor seating"}}
            """
        elif agent in ["availability_checker", "reservation_creator"]:
            extraction_prompt = f"""
            {system_context if system_context else ""}
            
            {conversation_context if conversation_context else ""}
            
            Extract the following reservation parameters from the conversation in JSON format:
            1. date_utc: The date and time for the reservation in ISO format (YYYY-MM-DDTHH:MM:SS)
            3. party_size: How many people in their party? (as a number)
            4. restaurant: What restaurant name did they mention?
            5. phone: What phone number should be used for this reservation? If not explicitly mentioned but available in system context, use that.
            
            Current user message: "{message}"
            
            Respond ONLY with a valid JSON object containing these parameters. If a parameter is not mentioned, set its value to null.
            If the user's phone number is available in the system context, always include it in the response.
            Example response: {{"date_utc": "2023-05-26T21:00:00", "party_size": 4, "restaurant": "La Trattoria", "phone": "+1234567890"}}
            """

        elif agent == "reservation_retriever":
            # For reservation_retriever, always try to use the phone number from context
            extraction_prompt = f"""
            {system_context if system_context else ""}
            
            {conversation_context if conversation_context else ""}
            
            Extract the following parameters from the conversation in JSON format:
            2. phone_number: The value of the phone number associated with the user (if available in system context, use that)
            
            Current user message: "{message}"
            
            IMPORTANT: If the user has a phone number in the system context, ALWAYS use "phone" as the identifier_type 
            and that phone number as the identifier_value, unless the user explicitly specifies another identifier.
            
            Respond ONLY with a valid JSON object containing these parameters. If a parameter is not mentioned and not available in context, set its value to null.
            Example with system phone: {{"identifier_type": "phone", "identifier_value": "{user_phone if user_phone else '+1234567890'}"}}
            """
        elif agent == "reservation_modifier":
            extraction_prompt = f"""
            {system_context if system_context else ""}
            
            {conversation_context if conversation_context else ""}
            
            Extract the following parameters from the conversation in JSON format:
            1. reservation_id: Any specific reservation ID mentioned
            2. phone_number: The value of the phone number associated with the user (if available in system context, use that)
            3. date_utc: The new date and time for the reservation in ISO format (YYYY-MM-DDTHH:MM:SS)

            Current user message: "{message}"

            Respond ONLY with a valid JSON object containing these parameters. If a parameter is not mentioned and not available in context, set its value to null.
            Example with system phone: {{"reservation_id": null, "phone_number": "{user_phone if user_phone else '+1234567890'}", "date": null}}
            """
        else:
            # For general inquiries, extract any potential parameters
            extraction_prompt = f"""
            {system_context if system_context else ""}
            
            {conversation_context if conversation_context else ""}
            
            Extract any relevant parameters from the conversation in JSON format.
            Look for information like:
            1. topic: What is the main topic of their inquiry?
            2. specific_item: Any specific item or service they're asking about?
            3. phone: If the user has a phone number in the system context, include it
            
            Current user message: "{message}"
            
            Respond ONLY with a valid JSON object. If a parameter is not mentioned, set its value to null.
            Example response: {{"topic": "opening hours", "specific_item": null, "phone": "{user_phone if user_phone else 'null'}"}}
            """
        
        # Log that we're making a parameter extraction LLM call
        logger.info(f"Making parameter extraction LLM call for agent: {agent} with full context")
        
        start_time = time.time()
        completion = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "You are a parameter extraction system. Only respond with the requested JSON format."},
                {"role": "user", "content": extraction_prompt}
            ],
             temperature=0,
        )
        execution_time = time.time() - start_time
        
        # Extract and parse the JSON response
        response_text = completion.choices[0].message.content.strip()
        
        # Log the parameter extraction
        log_llm_interaction(
            model=DEFAULT_MODEL,
            prompt=extraction_prompt,
            response=response_text,
            execution_time=execution_time,
            metadata={"operation": "parameter_extraction", "agent": agent}
        )
        
        # Remove any markdown formatting if present
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()
            
        # Parse the JSON response
        params = json.loads(response_text)
        
        # Clean up the parameters - remove None values and convert types where needed
        cleaned_params = {}
        for key, value in params.items():
            if value is not None and value != "null" and value != "":
                # Standardize phone numbers
                if key in ["phone", "phone_number", "customer_phone", "identifier_value"] and isinstance(value, str):
                    if key == "identifier_value" and params.get("identifier_type") == "phone":
                        cleaned_params[key] = standardize_phone_number(value)
                    elif key != "identifier_value":
                        cleaned_params[key] = standardize_phone_number(value)
                # Convert party_size to int if possible
                elif key == "party_size" and not isinstance(value, int):
                    try:
                        if isinstance(value, str) and value.isdigit():
                            cleaned_params[key] = int(value)
                        elif isinstance(value, str):
                            # Try to extract digits from strings like "4 people"
                            digit_match = re.search(r'\d+', value)
                            if digit_match:
                                cleaned_params[key] = int(digit_match.group())
                    except ValueError:
                        # If conversion fails, keep the original value
                        cleaned_params[key] = value
                else:
                    cleaned_params[key] = value
        
        # IMPORTANT: Ensure phone number is always added for reservation-related agents
        # This is critical for ensuring the phone number is used in tool calls
        if session and session.phone_number and agent in ["reservation_creator", "reservation_retriever", "reservation_modifier"]:
            if "phone" not in cleaned_params or not cleaned_params.get("phone"):
                cleaned_params["phone"] = session.phone_number
                logger.info(f"Added session phone {session.phone_number} to parameters for {agent}")
            
            # Also ensure it's in the correct format for get_customer_reservations
            if agent == "reservation_retriever":
                cleaned_params["identifier_type"] = "phone"
                cleaned_params["identifier_value"] = session.phone_number
                logger.info(f"Set identifier to phone {session.phone_number} for {agent}")
        
        return cleaned_params
        
    except Exception as e:
        # Log the error and return empty parameters
        logger.error(f"Error in LLM parameter extraction: {str(e)}", exc_info=True)
        return {}

def execute_tool_call(tool_call, session):
    """
    Execute a single tool call and format its result for the LLM.
    
    Args:
        tool_call: String representing the tool call expression
        session: The current chat session
        
    Returns:
        Tuple containing (formatted_result, raw_result, tool_name, params)
    """
    # Extract tool name and parameters
    tool_match = re.match(r'(\w+)\((.*)\)', tool_call)
    if not tool_match:
        return (f"Error: Invalid tool call format: {tool_call}", None, None, None)
        
    tool_name = tool_match.group(1)
    params_str = tool_match.group(2)
    
    # Parse parameters
    params = {}
    param_pattern = r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|([^,)]+))'
    param_matches = re.findall(param_pattern, params_str)
    
    for match in param_matches:
        param_name = match[0]
        param_value = match[1] or match[2] or match[3]
        
        # Convert value types as needed
        if param_value.isdigit():
            params[param_name] = int(param_value)
        elif param_value.lower() in ["true", "false"]:
            params[param_name] = param_value.lower() == "true"
        else:
            params[param_name] = param_value
    
    # Special handling for search_restaurants criteria parameter
    if tool_name == "search_restaurants" and "criteria" in params and isinstance(params["criteria"], str):
        try:
            # Check if the criteria looks like a dictionary string
            if params["criteria"].strip().startswith("{") and params["criteria"].strip().endswith("}"):
                # Try to parse it as a literal Python dictionary
                import ast
                parsed_criteria = ast.literal_eval(params["criteria"])
                if isinstance(parsed_criteria, dict):
                    params["criteria"] = parsed_criteria
                    logger.info(f"Successfully parsed criteria string to dictionary: {parsed_criteria}")
                else:
                    logger.warning(f"Criteria was parsed but is not a dictionary: {parsed_criteria}")
            else:
                # Handle case where criteria might be a single key-value pair
                parts = params["criteria"].split(":")
                if len(parts) == 2:
                    key = parts[0].strip().strip("'\"")
                    value = parts[1].strip().strip("'\"")
                    params["criteria"] = {key: value}
                    logger.info(f"Created simple criteria dictionary: {params['criteria']}")
        except Exception as e:
            logger.error(f"Error parsing criteria string: {str(e)}")
            # Keep as string if parsing fails
    
    # Handle special cases for phone numbers and identifiers
    if tool_name in ["get_customer_reservations", "create_reservation", "modify_reservation"] and session.phone_number:
        if "identifier_type" in params and params["identifier_type"] in ["phone", "your_phone_number"]:
            if params.get("identifier_value") in ["your_phone_number", "null", "phone_number", "", "your phone number"]:
                params["identifier_value"] = session.phone_number
            else:
                params["identifier_value"] = standardize_phone_number(params["identifier_value"])
        
        if tool_name in ["get_customer_reservations"] and ("identifier_type" not in params or "identifier_value" not in params):
            params["identifier_type"] = "phone"
            params["identifier_value"] = session.phone_number
        
        if tool_name == "create_reservation" and "customer_phone" in params:
            params["customer_phone"] = standardize_phone_number(params["customer_phone"])
    
    # Execute the tool
    if tool_name in AVAILABLE_TOOLS:
        try:
            # Get tool metadata
            tool = AVAILABLE_TOOLS[tool_name]
            tool_schema = tool.get_schema()
            
            # Special handling for different tools
            if tool_name == "search_restaurants":
                # Make sure criteria is a dictionary and not a string
                if "criteria" in params:
                    if isinstance(params["criteria"], str):
                        # If all attempts to parse failed above, create a simple cuisine search
                        params["criteria"] = {"cuisine": params["criteria"]}
                else:
                    # If no criteria provided, use all parameters as criteria
                    params["criteria"] = {k: v for k, v in params.items() if k != "criteria"}
                
                logger.info(f"Executing search_restaurants with criteria: {params['criteria']}")
                result = tool(criteria=params["criteria"])
            elif tool_name == "create_reservation":
                reservation_time = to_standard_datetime_string(params.get("reservation_time"))
                if not reservation_time:
                    reservation_time = to_standard_datetime_string(datetime.now())

                required_params = {
                    "restaurant_id": params.get("restaurant_id", "unknown"),
                    "customer_name": params.get("customer_name", "Guest User"),
                    "customer_email": params.get("customer_email", "guest@example.com"),
                    "customer_phone": params.get("customer_phone", session.phone_number or "0000000000"),
                    "party_size": params.get("party_size", 2),
                    "reservation_time": reservation_time
                }
                result = tool(**required_params)
            elif tool_name == "check_restaurant_availability":
                # Check if we need to find restaurant ID by name
                restaurant_id = params.get("restaurant_id")
                restaurant_name = params.get("restaurant_name") or params.get("restaurant")
                
                if not restaurant_id and restaurant_name:
                    # Search for restaurant by name first
                    search_tool = AVAILABLE_TOOLS["search_restaurants"]
                    search_result = search_tool(criteria={"name": restaurant_name})
                    search_data = json.loads(search_result)
                    
                    if search_data.get("status") == "success" and search_data.get("results"):
                        restaurant_id = search_data["results"][0]["id"]
                        logger.info(f"Found restaurant ID {restaurant_id} for name {restaurant_name}")
                    else:
                        return (f"Error: Could not find restaurant named '{restaurant_name}'", 
                                None, tool_name, params)
                
                # Handle date parsing if needed
                date_utc = params.get("date_utc")
                
                # Standardize the date_utc format to remove timezone information
                if date_utc:
                    # Use the to_standard_datetime_string utility to remove timezone info
                    date_utc = to_standard_datetime_string(date_utc)
                    logger.info(f"Standardized date_utc: {date_utc}")
                
                if not date_utc:
                    date_str = params.get("date")
                    time_str = params.get("time")
                    
                    if date_str:
                        # Try to construct a proper ISO datetime
                        try:
                            # Convert relative dates
                            if date_str.lower() == "tomorrow":
                                date_part = (datetime.now() + timedelta(days=1)).date()
                            elif date_str.lower() == "today":
                                date_part = datetime.now().date()
                            else:
                                date_part = datetime.strptime(date_str, "%Y-%m-%d").date()
                                
                            # Default time is 7:00 PM if not specified
                            time_part = "19:00:00"
                            
                            # Parse time if provided
                            if time_str:
                                if "pm" in time_str.lower():
                                    hour = int(re.search(r'(\d+)', time_str).group(1))
                                    if hour < 12:
                                        hour += 12
                                    time_part = f"{hour}:00:00"
                                elif "am" in time_str.lower():
                                    hour = int(re.search(r'(\d+)', time_str).group(1))
                                    time_part = f"{hour:02d}:00:00"
                                else:
                                    # Assume 24-hour format
                                    time_part = time_str
                                    
                            # Construct ISO datetime without timezone information
                            date_utc = f"{date_part.isoformat()}T{time_part}"
                            logger.info(f"Constructed date_utc: {date_utc}")
                        except Exception as e:
                            # Use tomorrow at 7 PM as fallback
                            logger.error(f"Error parsing date/time: {str(e)}")
                            tomorrow = datetime.now() + timedelta(days=1)
                            date_utc = f"{tomorrow.date().isoformat()}T19:00:00"
                            logger.info(f"Using fallback date_utc: {date_utc}")
                
                # Call availability check with proper parameters
                logger.info(f"Checking availability with: restaurant_id={restaurant_id}, date_utc={date_utc}, party_size={params.get('party_size', 2)}")
                
                # Parse the datetime string to verify it's in the correct format
                try:
                    parsed_dt = datetime.fromisoformat(date_utc)
                    logger.info(f"Parsed requested datetime: {parsed_dt}")
                except Exception as e:
                    logger.error(f"Error parsing date_utc: {str(e)}")
                
                result = tool(
                    restaurant_id=restaurant_id,
                    date_utc=date_utc,
                    party_size=params.get("party_size", 2)
                )
            elif tool_name == "get_customer_reservations":
                result = tool(
                    identifier_type="phone",
                    identifier_value=session.phone_number,
                )
            # elif tool_name == "modify_reservation":
            #     reservation_id = params.get("reservation_id")
            #     if not reservation_id:
            #         return (f"Error: Reservation ID is required for modification", None, tool_name, params)
                
            #     # Ensure date_utc is standardized
            #     date_utc = to_standard_datetime_string(params.get("date_utc"))
            #     if not date_utc:
            #         return (f"Error: Invalid date format for modification", None, tool_name, params)
                
            #     result = tool(
            #         reservation_id=reservation_id,
            #         reservation_time=date_utc,
            #         party_size=params.get("party_size", 2),
            #     )
            else:
                result = tool(**params)
            
            # Format the result for the LLM
            formatted_result = f"""TOOL EXECUTION RESULT:
Tool: {tool_name}
Description: {tool_schema['description']}
Parameters: {json_dumps(params, indent=2)}
Output: {result}
"""
            return (formatted_result, result, tool_name, params)
            
        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return (f"TOOL EXECUTION ERROR:\nTool: {tool_name}\nParameters: {json_dumps(params, indent=2)}\nError: {error_msg}", 
                None, tool_name, params)
    else:
        error_msg = f"Tool {tool_name} not found in AVAILABLE_TOOLS"
        logger.warning(error_msg)
        return (f"TOOL EXECUTION ERROR:\nTool: {tool_name}\nError: {error_msg}", None, tool_name, params)
    
def generate_response(session: ChatSession, user_message: str, restaurant_id: Optional[str] = None) -> Tuple[str, Optional[List[str]], str]:
    """Generate a response using the model from OpenRouter and return the detected agent"""
    if not OPENROUTER_API_KEY:
        # If no API key, use rule-based responses
        agent = detect_agent(user_message)
        params = extract_parameters(user_message, agent, session)
        response_text = "I'm sorry, but I don't have access to the restaurant database right now. Please try again later."
        suggested_actions = None
        return response_text, suggested_actions, agent

    # Get agent with full conversation context
    agent = detect_agent(user_message, session)
    
    # Extract parameters with full conversation context
    params = extract_parameters(user_message, agent, session)
    
    # Format conversation history for the API
    messages = []
    
    # Create user context string with enhanced phone number information
    user_context = ""
    if session.phone_number:
        # Use standardized phone number for display and examples
        std_phone = session.phone_number  # Already standardized when session was created
        logger.info(f"Including phone number {std_phone} in user context for session {session.id}")
        user_context = f"""USER INFORMATION:
Phone Number: {std_phone}

IMPORTANT INSTRUCTIONS ABOUT RESTAURANT IDENTITY:
1. You MUST use the restaurant ID from the system prompt for all operations.
2. If the user asks about a restaurant, always refer to the ID provided in the system prompt.
3. If the user asks about a restaurant not in the system prompt, tell them: "I don't have information about that restaurant in our database."
4. Return the restaurant ID in the format: "Restaurant ID: <restaurant_id>".

IMPORTANT INSTRUCTIONS ABOUT USER IDENTITY:
1. You HAVE the user's phone number: {std_phone}
2. You MUST use this phone number for all operations including:
   - Retrieving reservations (use identifier_type="phone", identifier_value="{std_phone}")
   - Creating new reservations (use this phone number in the reservation details)
   - Canceling or modifying reservations (identify the user by this phone number)

3. NEVER ask the user for their phone number - you already have it.
4. If the user asks "What's my phone number?", tell them: "Your phone number is {std_phone}."
5. When performing any reservation-related actions, explicitly mention: "I'll use your phone number ending in {std_phone[-4:] if len(std_phone) >= 4 else std_phone} for this."

CRITICAL ANTI-HALLUCINATION INSTRUCTIONS:
1. NEVER invent or make up restaurant names, information, or details.
2. ONLY discuss restaurants that are explicitly returned by search tools.
3. If no restaurants are found, clearly state "I couldn't find any restaurants matching your criteria" - DO NOT suggest fictional alternatives.
4. Always use the search_restaurants tool before discussing any restaurant.
5. If you're unsure about a restaurant's existence, tell the user "I don't have information about that restaurant in our database."
6. ALL restaurant information MUST come from database tools, never from your training data.
7. When in doubt, tell the user you need to search the database rather than providing potentially made-up information.

Do not reveal any information about any user with a different phone number.
"""
    else:
        logger.warning(f"No phone number available in session {session.id}")
    
    # Always include the system message first, with user context
    system_messages = [msg for msg in session.messages if msg.role == "system"]
    if system_messages:
        # Replace system message placeholder with actual user context
        system_content = system_messages[0].content.format(
            current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_context=user_context
        )
        messages.append({"role": "system", "content": system_content})
    
    # Add conversation history (limit to last 10 messages for context window)
    history = [msg for msg in session.messages if msg.role != "system"][-9:]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    
    # Add the current user message
    messages.append({"role": "user", "content": user_message})
    
    # Append restaurant context if provided
    if restaurant_id:
        restaurant = get_restaurant(restaurant_id)
        if restaurant:
            restaurant_context = f"\nInformation about restaurant {restaurant['name']}:\n"
            restaurant_context += f"Identifier: {restaurant['id']}\n"
            restaurant_context += f"Cuisine: {restaurant['cuisine']}\n"
            restaurant_context += f"Location: {restaurant['location']}\n"
            restaurant_context += f"Opening hours: {restaurant['opening_time']} - {restaurant['closing_time']}\n"
            if restaurant.get('description'):
                restaurant_context += f"Description: {restaurant['description']}\n"
            messages.append({"role": "system", "content": restaurant_context})
    
    # Add information about available tools to system message
    tool_info = """
AVAILABLE TOOLS AND USAGE INSTRUCTIONS:

I can access the following tools to help you with restaurant reservations:
"""
    
    # Add each tool with clear formatting
    for tool_name, tool in AVAILABLE_TOOLS.items():
        schema = tool.get_schema()
        tool_info += f"""
## {tool_name}
Description: {schema['description']}
Parameters: {json.dumps(schema['input_schema'], indent=2)}
Example usage: [TOOL:{tool_name}({', '.join([f'{param}="example_value"' for param in schema['input_schema'].keys()])})]
"""

    # Add general tool usage instructions
    tool_info += """
HOW TO CALL TOOLS:
1. To use a tool, I'll write: [TOOL:tool_name(parameter1="value1", parameter2="value2", ...)]
2. I will only use information from tool results - never inventing details
3. I will always check for restaurant IDs from previous tool calls
4. I will format dates and times as: YYYY-MM-DDTHH:MM:SS (no timezone)

COMMON EXAMPLES:
- Search for restaurants: [TOOL:search_restaurants(cuisine="Italian")]
- Check availability: [TOOL:check_restaurant_availability(restaurant_id="123", date_utc="2023-06-01T19:00:00", party_size=4)]
- Get user reservations: [TOOL:get_customer_reservations(identifier_type="phone", identifier_value="1234567890")]
- Create reservation: [TOOL:create_reservation(restaurant_id="123", customer_name="John Doe", party_size=4, reservation_time="2023-06-01T19:00:00")]
"""

    # Add consolidated tool information to messages (single message instead of multiple)
    messages.append({"role": "system", "content": tool_info})
    
    
    # Add instructions for tool usage
    tool_usage_instructions = """
    TOOL USAGE INSTRUCTIONS:
    1. To use a tool, write ONLY: [TOOL:tool_name(parameter1="value1", parameter2="value2", ...)]
    2. NEVER generate fake tool responses or [DATA] sections - the system will execute the tool and provide real results
    3. DO NOT invent, hallucinate, or simulate what the tool might return
    4. After generating a tool call, STOP - do not continue with additional text
    5. NEVER format responses like [DATA]{...}[/DATA] - this is handled by the system
    6. ALWAYS CHECK FOR THE RESTAURANT ID IN SYSTEM PROMPT

    IMPORTANT DATETIME FORMAT:
    - For all date and time values, use format: YYYY-MM-DDTHH:MM:SS
    - DO NOT include timezone information (Z or +00:00) in any datetime values

    IMPORTANT FORMATTING EXAMPLES:
    - For search_restaurants with simple criteria:
    [TOOL:search_restaurants(cuisine="Italian")]

    - For search_restaurants with multiple criteria:
    [TOOL:search_restaurants(cuisine="Italian", location="Downtown")]

    - For check_restaurant_availability:
    [TOOL:check_restaurant_availability(restaurant_id="<restaurant_id from previous tool call>", date="2023-06-01", time="7:00 PM", party_size=4)]

    - For get_customer_reservations:
    [TOOL:get_customer_reservations(identifier_type="phone", identifier_value="1234567890")]

    - For create_reservation:
    [TOOL:create_reservation(restaurant_id="<restaurant_id from previous tool call>", customer_name="John Doe", party_size=4, reservation_time="2023-06-01T19:00:00")]

    - For modify_reservation:
    [TOOL:modify_reservation(reservation_id="12345", date_utc="2023-06-01T19:00:00", party_size=4)]

    - For retrieve_reservation:
    [TOOL:retrieve_reservation(identifier_type="phone", identifier_value="1234567890", date="2023-06-01T19:00:00")]

    - For cancel_reservation:
    [TOOL:cancel_reservation(reservation_id="12345")]

    7. If you need to use a tool, generate the tool call and stop - DO NOT continue with additional text.
    8. If you need to provide a final response, do so based on the real tool results.
    9. If you need to use another tool, just generate the tool call: [TOOL:tool_name(params)]
    10. Only call the tools with the parameters that have been talked about in the function definitions above.
    11. NEVER call a tool with parameters that have not been explicitly mentioned in the conversation

    """
    messages.append({"role": "system", "content": tool_usage_instructions})
    
    # Initialize client
    client = OpenAI(
        base_url=OPENROUTER_URL,
        api_key=OPENROUTER_API_KEY,
    )
    
    # Process the conversation with potential multiple tool calls
    max_tool_calls = 5  # Limit the number of sequential tool calls to prevent infinite loops
    tool_call_count = 0
    max_wait_occurs = 3  # Maximum number of times to wait for LLM response
    wait_count = 0  # Counter for how many times we've waited
    max_empty_responses = 3  # Maximum number of empty responses before stopping
    empty_response_count = 0  # Counter for empty responses
    final_response = None
    tool_results = []
    
    try:
        # Start the conversation loop
        tool_pattern = r'\[TOOL:([^\]]+)\]'
        while tool_call_count < max_tool_calls:
            # Generate a response from the LLM
            start_time = time.time()
            completion = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                 temperature=0,
                # max_tokens=1000
            )
            execution_time = time.time() - start_time
            
            response_text = completion.choices[0].message.content
            print(completion.choices)
            print(f"LLM response: {response_text}")

            if response_text == "" or response_text.isspace():
                # If the response is empty, we can't proceed
                logger.warning("Received empty response from LLM")
                empty_response_count += 1
                if empty_response_count >= max_empty_responses:
                    logger.error("Max empty responses reached, stopping execution")
                    break
                continue

            # if check_if_llm_has_asked_to_wait(response_text= response_text):
            #     # If the LLM asks to wait, we should pause and not log this as an interaction
            #     logger.info("LLM requested to wait, pausing execution")
            #     wait_count += 1
            #     if wait_count > max_wait_occurs:
            #         logger.warning("Max wait count exceeded, stopping execution")
            #         break
            #     continue

            # Log the LLM interaction
            log_llm_interaction(
                model=DEFAULT_MODEL,
                prompt=json.dumps(messages[-5:]),  # Only log the most recent messages to avoid huge logs
                response=response_text,
                execution_time=execution_time,
                metadata={"agent": agent, "session_id": session.id, "tool_call_count": tool_call_count}
            )
            
            # Check for tool calls in the response
            tool_pattern = r'\[TOOL:([^\]]+)\]'
            tool_calls = re.findall(tool_pattern, response_text)

            # response_text = response_text.split("[DATA]")[0].strip()  # Remove any [DATA] sections
            # Clean up the response text by removing any tool call placeholders
            response_text = re.sub(tool_pattern, '', response_text).strip()
            
            if not tool_calls:
                # No more tool calls, we have the final response
                final_response = response_text
                print(f"Final response generated without tool calls: {final_response}")
                break

            
            # Execute the first tool call and add result to conversation
            tool_call = tool_calls[0]
            formatted_result, raw_result, tool_name, params = execute_tool_call(tool_call, session)
            
            # Save the tool result
            if raw_result:
                tool_results.append({
                    "tool": tool_name,
                    "params": params,
                    "result": raw_result
                })
            
            # Add only the tool call part to the conversation
            tool_call_msg = f"I need to use the {tool_name} tool: [TOOL:{tool_call}]"
            messages.append({"role": "assistant", "content": tool_call_msg})

            print(f"Executing tool call: {tool_call} -> {raw_result}")

            # Add the tool result to messages with clearer instructions
            messages.append({"role": "system", "content": 
                f"""
                {raw_result}
                IMPORTANT INSTRUCTIONS:
                1. Use ONLY this actual tool result above - NEVER invent additional data
                2. If you need another tool, just generate the tool call: [TOOL:tool_name(params)]
                3. DO NOT generate fake [DATA] sections or simulate tool responses
                4. If no further tool calls are needed, provide a final response to the user based solely on the real tool results
                6. The things are not updated unless you explicitly call a tool. With out a tool call result confirmation, do not assume anything.
                """
            })
            
            # Increment tool call count
            tool_call_count += 1
        
        # If we reached max tool calls without a final response, generate one now
        if final_response is None:
            # Add a message indicating we've reached the tool call limit
            messages.append({"role": "system", "content": 
                "You have reached the maximum number of sequential tool calls. "
                "Please provide a final response to the user based on the information gathered so far."
            })
            
            # Generate final response
            completion = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                 temperature=0,
                # max_tokens=1000
            )
            final_response = completion.choices[0].message.content
        
        # Clean up the final response by removing any remaining tool calls
        final_response = re.sub(tool_pattern, '', final_response).strip()
        
        # Parse suggested actions from response
        actions = re.findall(r'\[ACTION:\s*([^\]]+)\]', final_response)
        if actions:
            suggested_actions = actions
            final_response = re.sub(r'\[ACTION:\s*[^\]]+\]', '', final_response).strip()
        else:
            suggested_actions = None

        print(f"Final response generated: {final_response}")
        
        return final_response, suggested_actions, agent
        
    except Exception as e:
        logger.error(f"Error during response generation: {str(e)}", exc_info=True)
        return f"Sorry, I encountered an error: {str(e)}", None, agent

def perform_action(agent: str, params: Dict[str, Any], session_id: str) -> str:
    """Perform an action based on the detected agent and parameters"""
    # Validate inputs before processing
    if not isinstance(agent, str) or not isinstance(params, dict) or not isinstance(session_id, str):
        return "I'm sorry, but I encountered an error with your request. Please try again."
        
    # Fallback response for non-API mode
    return "I'm here to help with restaurant recommendations and reservations. What can I do for you today?"

def process_user_message(
    session_id: Optional[str], 
    user_message: str,
    user_id: Optional[str] = None, 
    restaurant_id: Optional[str] = None,
    phone_number: Optional[str] = None
) -> Tuple[ChatSession, ChatMessage, Optional[List[str]], str]:
    """Process a user message and generate a response, also returning detected agent"""
    # Get or create session with phone number
    session = get_or_create_session(session_id, user_id, phone_number)
    
    # Add user message to session
    user_msg = ChatMessage(role="user", content=user_message)
    session.messages.append(user_msg)
    
    # Generate response
    response_text, suggested_actions, agent = generate_response(session, user_message, restaurant_id)
    
    # Add assistant response to session
    assistant_msg = ChatMessage(role="assistant", content=response_text)
    session.messages.append(assistant_msg)
    
    # Update session
    session.updated_at = datetime.now()
    sessions[session.id] = session
    
    return session, assistant_msg, suggested_actions, agent

def check_if_llm_has_asked_to_wait(response_text: str) -> bool:
    """
    Check if the LLM response indicates it is waiting for further processing.
    
    Args:
        response_text: The text response from the LLM
        
    Returns:
        True if the response indicates waiting, False otherwise
    """
    SYSTEM_PROMPT = f"""
Check whether the given response text indicates that the LLM is waiting for further processing.
{response_text}
Give a simple 'true' or 'false' answer.
    """

    client = OpenAI(
        base_url=OPENROUTER_URL,
        api_key=OPENROUTER_API_KEY,
    )


    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {"role": "user", "content": SYSTEM_PROMPT}
        ]
    )


    return "true" in response.choices[0].message.content.lower()
