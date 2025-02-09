import sqlite3
import speech_recognition as sr
import pyttsx3
from datetime import datetime

# Database setup
def initialize_database():
    """
    Initializes the SQLite database and creates necessary tables.
    Inserts sample data for a specific restaurant.
    """
    conn = sqlite3.connect("restaurant.db")
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Restaurants (
            id INTEGER PRIMARY KEY,
            name TEXT,
            capacity INTEGER,
            opening_time TEXT,
            closing_time TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Bookings (
            id INTEGER PRIMARY KEY,
            restaurant_id INTEGER,
            customer_name TEXT,
            customer_phone TEXT,
            reservation_time TEXT,
            party_size INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Availability (
            id INTEGER PRIMARY KEY,
            restaurant_id INTEGER,
            date TEXT,
            available_slots INTEGER
        )
    """)
    
    # Insert specific restaurant data
    cursor.execute("INSERT OR IGNORE INTO Restaurants (id, name, capacity, opening_time, closing_time) VALUES (1, 'The Gourmet Haven', 100, '10:00', '23:00')")
    
    # Insert sample availability data for the next 7 days
    sample_dates = ["2023-10-15", "2023-10-16", "2023-10-17", "2023-10-18", "2023-10-19", "2023-10-20", "2023-10-21"]
    for date in sample_dates:
        cursor.execute("INSERT OR IGNORE INTO Availability (restaurant_id, date, available_slots) VALUES (1, ?, 100)", (date,))
    
    conn.commit()
    return conn


# Booking Agent
class BookingAgent:
    """
    Handles booking, modification, and cancellation of reservations.
    Validates real-time availability to prevent overbooking.
    """
    def __init__(self, db_connection):
        self.db = db_connection

    def book_table(self, restaurant_id, customer_name, customer_phone, reservation_time, party_size):
        """
        Books a table if slots are available.
        """
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
        """
        Checks if slots are available for the given reservation time.
        """
        date = reservation_time.split(" ")[0]  # Extract date from timestamp
        available_slots = self.db.execute("""
            SELECT available_slots FROM Availability WHERE restaurant_id = ? AND date = ?
        """, (restaurant_id, date)).fetchone()
        
        if available_slots and available_slots[0] >= party_size:
            return True
        return False

    def modify_booking(self, booking_id, new_reservation_time, new_party_size):
        """
        Modifies an existing booking if slots are available.
        """
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
        """
        Cancels an existing booking.
        """
        self.db.execute("DELETE FROM Bookings WHERE id = ?", (booking_id,))
        self.db.commit()
        return "Booking canceled."


# Chatbot with Dual Input Mode (Voice and Text)
class Chatbot:
    def __init__(self, booking_agent):
        self.booking_agent = booking_agent
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()

    def listen(self):
        """
        Listens to user input via microphone and converts it to text.
        """
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
        """
        Converts text to speech and speaks it out loud.
        """
        self.engine.say(text)
        self.engine.runAndWait()

    def handle_message(self, message):
        """
        Processes user input and interacts with the booking agent.
        """
        if "book" in message.lower():
            restaurant_id = 1  # Specific restaurant ID
            customer_name = input("Enter your name: ")  # Get customer name
            customer_phone = input("Enter your phone number: ")  # Get customer phone
            reservation_time = input("Enter reservation date and time (YYYY-MM-DD HH:MM): ")  # Get reservation time
            party_size = int(input("Enter party size: "))  # Get party size
            return self.booking_agent.book_table(restaurant_id, customer_name, customer_phone, reservation_time, party_size)
        elif "modify" in message.lower():
            booking_id = int(input("Enter your booking ID: "))  # Get booking ID
            new_reservation_time = input("Enter new reservation date and time (YYYY-MM-DD HH:MM): ")  # Get new time
            new_party_size = int(input("Enter new party size: "))  # Get new party size
            return self.booking_agent.modify_booking(booking_id, new_reservation_time, new_party_size)
        elif "cancel" in message.lower():
            booking_id = int(input("Enter your booking ID: "))  # Get booking ID
            return self.booking_agent.cancel_booking(booking_id)
        else:
            return "Sorry, I didn't understand that."

    def run(self):
        """
        Runs the chatbot in an infinite loop for continuous interaction.
        """
        while True:
            print("\nChoose input mode:")
            print("1. Voice")
            print("2. Text")
            choice = input("Enter your choice (1 or 2): ")

            if choice == "1":
                user_input = self.listen()
            elif choice == "2":
                user_input = input("Type your request: ")
            else:
                print("Invalid choice. Please try again.")
                continue

            response = self.handle_message(user_input)
            print(response)
            self.speak(response)


# Restaurant Interface
class RestaurantInterface:
    """
    Provides an interface for restaurant staff to manage bookings and availability.
    """
    def __init__(self, db_connection):
        self.db = db_connection

    def view_bookings(self, restaurant_id):
        """
        Displays all bookings for a specific restaurant.
        """
        bookings = self.db.execute("SELECT * FROM Bookings WHERE restaurant_id = ?", (restaurant_id,)).fetchall()
        for booking in bookings:
            print(booking)

    def update_availability(self, restaurant_id, date, available_slots):
        """
        Updates the available slots for a specific date.
        """
        self.db.execute("UPDATE Availability SET available_slots = ? WHERE restaurant_id = ? AND date = ?",
                       (available_slots, restaurant_id, date))
        self.db.commit()
        print("Availability updated!")


# Main Function
def main():
    """
    Initializes the database, booking agent, and chatbot.
    Starts the chatbot for user interaction.
    """
    db = initialize_database()
    booking_agent = BookingAgent(db)
    chatbot = Chatbot(booking_agent)
    restaurant_interface = RestaurantInterface(db)

    # Run the chatbot
    print("Starting chatbot...")
    chatbot.run()


# Entry Point
if __name__ == "__main__":
    main()
