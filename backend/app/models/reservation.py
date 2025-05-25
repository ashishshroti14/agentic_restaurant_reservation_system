from pydantic import BaseModel
import datetime

class Reservation(BaseModel):
    id: str
    restaurant_id: str
    customer_name: str
    customer_email: str
    customer_phone: str
    party_size: int
    reservation_time: datetime.datetime
    status: str = "confirmed"  # confirmed, cancelled, completed
