import sqlite3
import uuid

# Database path
DB_PATH = "C:\\Users\\Trill\\Documents\\TRILL\\Discord\\Trilo_Beta\\bot_data_keys.db"

# Generate a unique access key
def generate_access_key():
    return str(uuid.uuid4())

# Add new access keys to the database
def add_access_keys(num_keys):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    # Generate and insert keys
    new_keys = [generate_access_key() for _ in range(num_keys)]
    for key in new_keys:
        try:
            cursor.execute("INSERT INTO access_keys (key) VALUES (?)", (key,))
        except sqlite3.IntegrityError:
            print(f"Duplicate key detected, skipping: {key}")

    connection.commit()
    connection.close()
    print(f"Successfully added {len(new_keys)} new access keys.")

# Main entry point
if __name__ == "__main__":
    try:
        num_keys = int(input("How many access keys would you like to generate? "))
        add_access_keys(num_keys)
    except ValueError:
        print("Please enter a valid number.")
