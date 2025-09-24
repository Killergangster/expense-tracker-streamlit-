import sqlite3
import hashlib

# Function to hash passwords
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Connect to the database (it will be created if it doesn't exist)
conn = sqlite3.connect('expenses.db')
c = conn.cursor()

# Create users table
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL
)
''')

# Create expenses table
c.execute('''
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    expense_date DATE NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    FOREIGN KEY (username) REFERENCES users (username)
)
''')

# Add default users (admin and demo)
try:
    # --- MODIFIED ADMIN CREDENTIALS ---
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
              ('Itachibanker19', make_hashes('Killer1980')))
    
    # --- DEMO USER REMAINS THE SAME ---
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
              ('demo', make_hashes('demo123')))

except sqlite3.IntegrityError:
    # This will happen if users already exist, which is fine.
    print("Default users already exist.")

# Commit changes and close the connection
conn.commit()
conn.close()

print("✅ expenses.db created with new admin & demo accounts!")
