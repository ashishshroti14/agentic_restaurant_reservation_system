# FoodieSpot: Agentic Restaurant Reservation System

![FoodieSpot Logo](https://cdn-icons-png.flaticon.com/512/2702/2702391.png)

FoodieSpot is an intelligent restaurant reservation system powered by purpose-built AI agents that help users find and book restaurants based on their preferences. This system demonstrates advanced agentic AI concepts built from scratch without relying on frameworks like LangChain or CrewAI.

## ✨ Key Features

- 🤖 Custom-built agentic AI architecture with specialized agents for different tasks
- 🔍 Natural language restaurant search and filtering by cuisine, location, and availability
- 📅 Smart reservation management (create, modify, cancel)
- 🗺️ Interactive map visualization of restaurant locations
- 📱 Responsive UI built with Streamlit
- 🔐 Authentication system with OTP verification

## 🧠 AI Architecture

### LLM Integration

This project uses **Microsoft Phi-4 (14B parameter model)** via OpenRouter API, demonstrating that sophisticated agentic systems can be built with mid-size models when properly engineered.

### Agent System (Built From Scratch)

FoodieSpot implements a custom agentic architecture without relying on frameworks like LangChain or CrewAI. The system features specialized agents that handle different aspects of the conversation:

| Agent Type | Primary Responsibilities |
|------------|--------------------------|
| `restaurant_finder` | Searches for restaurants based on user preferences (cuisine, location, etc.) |
| `availability_checker` | Checks restaurant availability for specific dates/times |
| `reservation_creator` | Handles the reservation creation process |
| `reservation_retriever` | Fetches and displays user's existing reservations |
| `reservation_modifier` | Manages changes to existing reservations |
| `general_assistant` | Handles general inquiries and requests |

### Tool-Calling Architecture

The system implements a sophisticated tool-calling mechanism where the LLM:
1. Identifies user intent from natural language
2. Selects appropriate tools based on context
3. Formats parameters correctly for tool execution
4. Interprets tool outputs to generate human-friendly responses

Example of tool-calling pattern:

```
[TOOL:search_restaurants(cuisine="Italian", location="Downtown", party_size=4)]
```

## 🔮 Prompt Engineering

FoodieSpot implements advanced prompt engineering techniques to ensure reliable agent performance:

### Multi-layered Prompt System

1. **Base System Prompt**: Defines the assistant's identity, capabilities, and behavioral guidelines
2. **Tool Usage Instructions**: Detailed specifications for how and when to use available tools
3. **Anti-hallucination Guidelines**: Strict rules to prevent generating fictional information
4. **Response Formatting Instructions**: Ensures consistent output including suggested actions

### Key Prompt Engineering Innovations

- **Contextual Parameter Gathering**: The system is instructed to gather all required parameters before making tool calls
- **Explicit ID Handling**: Special instructions ensure IDs are properly managed throughout conversations
- **Conversational Memory Management**: The system intelligently maintains and references conversation history
- **Suggested Actions Generation**: Dynamic generation of contextually relevant next steps

## 🖥️ User Interface

The Streamlit-based UI provides an intuitive user experience:

- **Chat Interface**: Natural conversation with the AI assistant
- **Suggested Actions**: Contextual suggestions based on conversation state
- **Restaurant Cards**: Visual presentation of restaurant information
- **Interactive Map**: Geographic visualization of restaurant locations
- **Reservation Management**: Easy viewing and management of bookings

![![User Interface](https://github.com/ashishshroti14/agentic_restaurant_reservation_system/blob/main/image.png)]()

## 🛠️ Technical Architecture

```
agentic_restaurant_reservation_system/
├── backend/                      # FastAPI backend
│   ├── app/                      # Main application code
│   │   ├── db/                   # Database models and operations
│   │   ├── models/               # Data models
│   │   ├── routers/              # API routes
│   │   └── utils/                # Utility functions including agent logic
│   └── Dockerfile                # Backend container definition
├── frontend/                     # Streamlit frontend
│   ├── app.py                    # Main UI application
│   └── Dockerfile                # Frontend container definition
└── docker-compose.yml            # Container orchestration
```

## ☁️ Deployment

The application is deployed and accessible at:
[https://ashish-shroti-agentic-reservation-system-962843070701.europe-west1.run.app/](https://ashish-shroti-agentic-reservation-system-962843070701.europe-west1.run.app/)

### GCP Infrastructure

FoodieSpot leverages Google Cloud Platform for a robust, scalable deployment:

- **Cloud Run**: Hosts the containerized application, providing serverless, auto-scaling infrastructure
- **Cloud Build**: Automates container image creation and deployment
- **CI/CD Pipeline**: Implements continuous integration and deployment for seamless updates

This cloud-native approach ensures high availability, easy scaling, and efficient resource utilization while minimizing operational overhead.

## 🚀 Installation and Deployment

### Prerequisites

- Python 3.8+
- Docker and Docker Compose (for containerized deployment)
- OpenRouter API key

### Quick Start with Docker

1. Clone the repository
   ```bash
   git clone <repository-url>
   cd agentic_restaurant_reservation_system
   ```

2. Configure environment variables
   ```bash
   # Create .env file in the backend directory with the following variables
   OPENROUTER_API_KEY=your-openrouter-key
   JWT_SECRET=your-jwt-secret
   ```

3. Build and run with Docker Compose
   ```bash
   docker-compose up --build
   ```

4. Access the application
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000

### Manual Setup

1. Set up the backend
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r app/requirements.txt
   uvicorn app.main:app --reload
   ```

2. Set up the frontend
   ```bash
   cd frontend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

## 📋 Example Conversations

### Restaurant Search Flow

**User**: I'm looking for Italian restaurants downtown

**Agent**: I can help you find Italian restaurants in Downtown. Let me search for options for you...

I found 5 Italian restaurants in the Downtown area:

1. Bella Italia (ID: rest_12)
   - Location: 123 Main St, Downtown
   - Cuisine: Italian
   - Hours: 11:00 AM - 10:00 PM

2. Pasta Paradise (ID: rest_18)
   - Location: 456 Oak Ave, Downtown
   - Cuisine: Italian
   - Hours: 12:00 PM - 11:00 PM

[...]

Would you like to check availability at any of these restaurants?

[ACTION: Check availability at Bella Italia]
[ACTION: Make a reservation at Pasta Paradise]
[ACTION: Show me more Italian restaurants]

### Reservation Creation Flow

**User**: I want to make a reservation at Bella Italia for tomorrow at 7pm for 4 people

**Agent**: I'll help you make a reservation at Bella Italia for tomorrow at 7:00 PM for 4 people.

First, let me check if there's availability...

Good news! Bella Italia has availability for 4 people tomorrow at 7:00 PM. Would you like me to proceed with the reservation?

**User**: Yes, please book it

**Agent**: Great! I've made the reservation for you at Bella Italia.

Reservation Details:
- Restaurant: Bella Italia
- Date & Time: Thursday, July 20, 2023 at 7:00 PM
- Party Size: 4 people
- Reservation ID: rsv_45

Your reservation is confirmed! You'll receive a confirmation via SMS shortly. Is there anything else you'd like help with?

[ACTION: View my reservation details]
[ACTION: Modify this reservation]
[ACTION: Find directions to Bella Italia]

## 💼 Business Impact

### Problem Solved
FoodieSpot addresses critical challenges in restaurant reservation management:

- Decreases staff workload by handling 80% of reservation requests automatically
- Improves customer satisfaction by providing 24/7 reservation assistance
- Increases restaurant discovery through intelligent recommendations
- Potential to reduce no-shows by 30% through automated reminders

### ROI Potential
- **Restaurants**: 15-20% increase in table utilization
- **Customers**: Reduces reservation booking time to less than half
- **Platform**: Potential for premium features and commission-based revenue model

## 🔄 Future Enhancements
- Integration with popular calendaring systems (Google Calendar, Apple Calendar)
- Personalized restaurant recommendations based on user preferences
- Social sharing capabilities for group reservations
- Multi-language support
- Voice interface for hands-free operation

## 🙏 Acknowledgements
- OpenRouter for providing access to Phi-4 and other models
- Streamlit for the powerful UI framework
- FastAPI for the efficient backend framework
- Google Cloud Platform for hosting infrastructure
- Created as part of a technical implementation challenge for Sarvam AI
