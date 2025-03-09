import sqlite3

def create_database():
    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()

    # Create cars table
    c.execute('''CREATE TABLE IF NOT EXISTS cars
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  brand TEXT,
                  model TEXT,
                  year INTEGER,
                  fuel_type TEXT,
                  status TEXT)''')

    # Create clients table
    c.execute('''CREATE TABLE IF NOT EXISTS clients
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  email TEXT,
                  phone TEXT,
                  driver_license TEXT)''')

    # Create reservations table
    c.execute('''CREATE TABLE IF NOT EXISTS reservations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  car_id INTEGER,
                  client_id INTEGER,
                  start_date TEXT,
                  end_date TEXT,
                  FOREIGN KEY (car_id) REFERENCES cars (id),
                  FOREIGN KEY (client_id) REFERENCES clients (id))''')

    # Create contracts table
    c.execute('''CREATE TABLE IF NOT EXISTS contracts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  reservation_id INTEGER,
                  total_price REAL,
                  FOREIGN KEY (reservation_id) REFERENCES reservations (id))''')

    # Create maintenance table
    c.execute('''CREATE TABLE IF NOT EXISTS maintenance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  car_id INTEGER,
                  task TEXT,
                  due_date TEXT,
                  status TEXT,
                  FOREIGN KEY (car_id) REFERENCES cars (id))''')

    # Create damage_reports table
    c.execute('''CREATE TABLE IF NOT EXISTS damage_reports
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  car_id INTEGER,
                  description TEXT,
                  report_date TEXT,
                  repair_status TEXT,
                  FOREIGN KEY (car_id) REFERENCES cars (id))''')

    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  role TEXT)''')

    conn.commit()
    conn.close()

create_database()