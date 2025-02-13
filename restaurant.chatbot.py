import sqlite3
import speech_recognition as sr
import pyttsx3
from datetime import datetime

# Database setup
def initialize_database():
    conn = sqlite3.connect("restaurant.db")
    cursor = conn.cursor()
    
    # Drop existing tables if they exist
    cursor.execute("DROP TABLE IF EXISTS Restaurants")
    cursor.execute("DROP TABLE IF EXISTS Bookings")
    cursor.execute("DROP TABLE IF EXISTS Availability")
    
    # Create tables with the correct schema
    cursor.execute("""
        CREATE TABLE Restaurants (
            id INTEGER PRIMARY KEY,
            name TEXT,
            capacity INTEGER,
            opening_time TEXT,
            closing_time TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Bookings (
            id INTEGER PRIMARY KEY,
            restaurant_id INTEGER,
            customer_name TEXT,
            customer_phone TEXT,
            reservation_time TEXT,
            party_size INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Availability (
            id INTEGER PRIMARY KEY,
            restaurant_id INTEGER,
            date TEXT,
            available_slots INTEGER
        )
    """)
    
    # Insert real-time restaurant data
    restaurants = [
        (1, "The Gourmet Kitchen", 50, "09:00", "22:00"),
        (2, "Pasta Paradise", 30, "10:00", "21:00"),
        (3, "Sushi Haven", 40, "11:00", "23:00"),
        (4, "Burger Barn", 60, "08:00", "20:00"),
        (5, "Taco Fiesta", 35, "12:00", "22:00")
    ]
    cursor.executemany("INSERT OR IGNORE INTO Restaurants (id, name, capacity, opening_time, closing_time) VALUES (?, ?, ?, ?, ?)", restaurants)
    
    # Insert real-time availability data for February 2025
    availability = []
    for restaurant_id in range(1, 6):  # 5 restaurants
        for day in range(1, 29):  # February has 28 days in 2025
            date = f"2025-02-{day:02d}"  # Format as YYYY-MM-DD
            capacity = restaurants[restaurant_id - 1][2]  # Get capacity from restaurant data
            availability.append((restaurant_id, date, capacity))
    
    cursor.executemany("INSERT OR IGNORE INTO Availability (restaurant_id, date, available_slots) VALUES (?, ?, ?)", availability)
    
    conn.commit()
    return conn

# Booking Agent
class BookingAgent:
    def __init__(self, db_connection):
        self.db = db_connection

    def book_table(self, restaurant_id, customer_name, customer_phone, reservation_time, party_size):
        if self.check_availability(restaurant_id, reservation_time, party_size):
            self.db.execute("""
                INSERT INTO Bookings (restaurant_id, customer_name, customer_phone, reservation_time, party_size)
                VALUES (?, ?, ?, ?, ?)
            """, (restaurant_id, customer_name, customer_phone, reservation_time, party_size))
            self.db.commit()
            return "Booking confirmed!"
        else:
            return "Sorry, no available slots at the requested time."

    def check_availability(self, restaurant_id, reservation_time, party_size):
        date = reservation_time.split(" ")[0]  # Extract date from timestamp
        available_slots = self.db.execute("""
            SELECT available_slots FROM Availability WHERE restaurant_id = ? AND date = ?
        """, (restaurant_id, date)).fetchone()
        
        if available_slots and available_slots[0] >= party_size:
            return True
        return False

    def modify_booking(self, booking_id, new_reservation_time, new_party_size):
        booking = self.db.execute("SELECT * FROM Bookings WHERE id = ?", (booking_id,)).fetchone()
        if booking:
            if self.check_availability(booking[1], new_reservation_time, new_party_size):
                self.db.execute("""
                    UPDATE Bookings SET reservation_time = ?, party_size = ? WHERE id = ?
                """, (new_reservation_time, new_party_size, booking_id))
                self.db.commit()
                return "Booking updated!"
            else:
                return "Sorry, no available slots at the requested time."
        return "Booking not found."

    def cancel_booking(self, booking_id):
        self.db.execute("DELETE FROM Bookings WHERE id = ?", (booking_id,))
        self.db.commit()
        return "Booking canceled."

# Chatbot with Voice and Text Integration
class VoiceChatbot:
    def __init__(self, booking_agent):
        self.booking_agent = booking_agent
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()

    def listen(self):
        with sr.Microphone() as source:
            print("Listening...")
            audio = self.recognizer.listen(source)
            try:
                text = self.recognizer.recognize_google(audio)
                print(f"You said: {text}")
                return text
            except sr.UnknownValueError:
                return "Sorry, I didn't catch that."

    def speak(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

    def handle_message(self, message):
        if "book" in message.lower():
            # Ask for restaurant ID, customer details, and reservation time
            restaurant_id = int(input("Enter restaurant ID: "))
            customer_name = input("Enter your name: ")
            customer_phone = input("Enter your phone number: ")
            reservation_time = input("Enter reservation time (YYYY-MM-DD HH:MM:SS): ")
            party_size = int(input("Enter party size: "))
            return self.booking_agent.book_table(restaurant_id, customer_name, customer_phone, reservation_time, party_size)
        elif "modify" in message.lower():
            # Ask for booking ID, new reservation time, and new party size
            booking_id = int(input("Enter booking ID: "))
            new_reservation_time = input("Enter new reservation time (YYYY-MM-DD HH:MM:SS): ")
            new_party_size = int(input("Enter new party size: "))
            return self.booking_agent.modify_booking(booking_id, new_reservation_time, new_party_size)
        elif "cancel" in message.lower():
            # Ask for booking ID
            booking_id = int(input("Enter booking ID: "))
            return self.booking_agent.cancel_booking(booking_id)
        else:
            return "Sorry, I didn't understand that."

    def run(self):
        while True:
            print("Choose input method: 1. Speech 2. Text")
            choice = input("Enter choice (1 or 2): ")
            if choice == "1":
                user_input = self.listen()
            elif choice == "2":
                user_input = input("Enter your message: ")
            else:
                print("Invalid choice. Please try again.")
                continue
            response = self.handle_message(user_input)
            self.speak(response)

# Restaurant Interface
class RestaurantInterface:
    def __init__(self, db_connection):
        self.db = db_connection

    def view_bookings(self, restaurant_id):
        bookings = self.db.execute("SELECT * FROM Bookings WHERE restaurant_id = ?", (restaurant_id,)).fetchall()
        for booking in bookings:
            print(booking)

    def update_availability(self, restaurant_id, date, available_slots):
        self.db.execute("UPDATE Availability SET available_slots = ? WHERE restaurant_id = ? AND date = ?",
                       (available_slots, restaurant_id, date))
        self.db.commit()
        print("Availability updated!")

# Main Function
def main():
    db = initialize_database()
    booking_agent = BookingAgent(db)
    chatbot = VoiceChatbot(booking_agent)
    restaurant_interface = RestaurantInterface(db)

    # Run the chatbot
    print("Starting chatbot...")
    chatbot.run()

if __name__ == "__main__":
    main()
