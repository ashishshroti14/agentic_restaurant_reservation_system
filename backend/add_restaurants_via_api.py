import requests
import json
import uuid

# Make sure the API is running before executing this script
API_URL = "http://localhost:8000/restaurants/"

# Sample restaurants data (same as above)
restaurants = [
    {
        "id": str(uuid.uuid4()),
        "name": "Bella Italia",
        "location": "Downtown",
        # ... rest of the restaurant data
    },
    # ... other restaurants
]

def main():
    print("Adding restaurants via API...")
    
    successful = 0
    failed = 0
    
    for restaurant in restaurants:
        try:
            response = requests.post(API_URL, json=restaurant)
            
            if response.status_code == 200 or response.status_code == 201:
                print(f"Added restaurant: {restaurant['name']} ({restaurant['cuisine']})")
                successful += 1
            else:
                print(f"Failed to add {restaurant['name']}: {response.status_code} - {response.text}")
                failed += 1
                
        except Exception as e:
            print(f"Error adding {restaurant['name']}: {str(e)}")
            failed += 1
    
    print(f"\nSummary:")
    print(f"Successfully added: {successful} restaurants")
    print(f"Failed to add: {failed} restaurants")

if __name__ == "__main__":
    main()
