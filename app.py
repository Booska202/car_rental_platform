from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from datetime import datetime, timedelta
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

# Helper function to get alerts
def get_alerts():
    alerts = []
    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()

    # Check for upcoming maintenance tasks (due in the next 7 days)
    today = datetime.today().strftime('%Y-%m-%d')
    next_week = (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d')
    c.execute('''SELECT cars.brand, cars.model, maintenance.task, maintenance.due_date
                 FROM maintenance
                 JOIN cars ON maintenance.car_id = cars.id
                 WHERE maintenance.due_date BETWEEN ? AND ?''', (today, next_week))
    maintenance_alerts = c.fetchall()
    for alert in maintenance_alerts:
        alerts.append(f"Maintenance due for {alert[0]} {alert[1]}: {alert[2]} on {alert[3]}")

    # Check for upcoming reservations (starting in the next 2 days)
    c.execute('''SELECT cars.brand, cars.model, clients.name, reservations.start_date
                 FROM reservations
                 JOIN cars ON reservations.car_id = cars.id
                 JOIN clients ON reservations.client_id = clients.id
                 WHERE reservations.start_date BETWEEN ? AND ?''', (today, next_week))
    reservation_alerts = c.fetchall()
    for alert in reservation_alerts:
        alerts.append(f"Reservation for {alert[0]} {alert[1]} by {alert[2]} on {alert[3]}")

    # Check for unresolved damage reports
    c.execute('''SELECT cars.brand, cars.model, damage_reports.description
                 FROM damage_reports
                 JOIN cars ON damage_reports.car_id = cars.id
                 WHERE damage_reports.repair_status != 'Resolved' ''')
    damage_alerts = c.fetchall()
    for alert in damage_alerts:
        alerts.append(f"Unresolved damage for {alert[0]} {alert[1]}: {alert[2]}")

    conn.close()
    return alerts

# Home Page - Display All Cars
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cars")
    cars = c.fetchall()
    conn.close()
    alerts = get_alerts()
    return render_template('index.html', cars=cars, alerts=alerts, role=session.get('role'))

# Add Car Page
@app.route('/add_car', methods=['GET', 'POST'])
def add_car():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect('/login')

    if request.method == 'POST':
        brand = request.form['brand']
        model = request.form['model']
        year = request.form['year']
        fuel_type = request.form['fuel_type']
        status = request.form['status']

        conn = sqlite3.connect('car_rental.db')
        c = conn.cursor()
        c.execute("INSERT INTO cars (brand, model, year, fuel_type, status) VALUES (?, ?, ?, ?, ?)",
                  (brand, model, year, fuel_type, status))
        conn.commit()
        conn.close()
        return redirect('/')

    alerts = get_alerts()
    return render_template('add_car.html', alerts=alerts)

# View Clients Page
@app.route('/clients')
def clients():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect('/login')

    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute("SELECT * FROM clients")
    clients = c.fetchall()
    conn.close()
    alerts = get_alerts()
    return render_template('clients.html', clients=clients, alerts=alerts)

# Add Client Page
@app.route('/add_client', methods=['GET', 'POST'])
def add_client():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        driver_license = request.form['driver_license']

        conn = sqlite3.connect('car_rental.db')
        c = conn.cursor()
        c.execute("INSERT INTO clients (name, email, phone, driver_license) VALUES (?, ?, ?, ?)",
                  (name, email, phone, driver_license))
        conn.commit()
        conn.close()
        return redirect('/clients')

    alerts = get_alerts()
    return render_template('add_client.html', alerts=alerts)

# View Reservations Page
@app.route('/reservations')
def reservations():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute('''SELECT reservations.id, cars.brand, cars.model, clients.name, reservations.start_date, reservations.end_date
                 FROM reservations
                 JOIN cars ON reservations.car_id = cars.id
                 JOIN clients ON reservations.client_id = clients.id''')
    reservations = c.fetchall()
    conn.close()
    alerts = get_alerts()
    return render_template('reservations.html', reservations=reservations, alerts=alerts, role=session.get('role'))

# Add Reservation Page
@app.route('/add_reservation', methods=['GET', 'POST'])
def add_reservation():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect('/login')

    if request.method == 'POST':
        car_id = request.form['car_id']
        client_id = request.form['client_id']
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        conn = sqlite3.connect('car_rental.db')
        c = conn.cursor()

        # Check if the car is available
        c.execute("SELECT status FROM cars WHERE id = ?", (car_id,))
        car_status = c.fetchone()[0]
        if car_status == 'booked':
            conn.close()
            return "Car is already booked!"

        # Add the reservation
        c.execute("INSERT INTO reservations (car_id, client_id, start_date, end_date) VALUES (?, ?, ?, ?)",
                  (car_id, client_id, start_date, end_date))

        # Update car status to 'booked'
        c.execute("UPDATE cars SET status = 'booked' WHERE id = ?", (car_id,))

        conn.commit()
        conn.close()
        return redirect('/reservations')

    # Fetch available cars and clients for the form
    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cars WHERE status = 'available'")
    cars = c.fetchall()
    c.execute("SELECT * FROM clients")
    clients = c.fetchall()
    conn.close()
    alerts = get_alerts()
    return render_template('add_reservation.html', cars=cars, clients=clients, alerts=alerts)

# View Contracts Page
@app.route('/contracts')
def contracts():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute('''SELECT contracts.id, cars.brand, cars.model, clients.name, reservations.start_date, reservations.end_date, contracts.total_price
                 FROM contracts
                 JOIN reservations ON contracts.reservation_id = reservations.id
                 JOIN cars ON reservations.car_id = cars.id
                 JOIN clients ON reservations.client_id = clients.id''')
    contracts = c.fetchall()
    conn.close()
    alerts = get_alerts()
    return render_template('contracts.html', contracts=contracts, alerts=alerts, role=session.get('role'))

# Generate Contract Page
@app.route('/generate_contract/<int:reservation_id>', methods=['GET', 'POST'])
def generate_contract(reservation_id):
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect('/login')

    if request.method == 'POST':
        total_price = request.form['total_price']

        conn = sqlite3.connect('car_rental.db')
        c = conn.cursor()
        c.execute("INSERT INTO contracts (reservation_id, total_price) VALUES (?, ?)",
                  (reservation_id, total_price))
        conn.commit()
        conn.close()
        return redirect('/contracts')

    # Fetch reservation details
    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute('''SELECT cars.brand, cars.model, clients.name, reservations.start_date, reservations.end_date
                 FROM reservations
                 JOIN cars ON reservations.car_id = cars.id
                 JOIN clients ON reservations.client_id = clients.id
                 WHERE reservations.id = ?''', (reservation_id,))
    reservation = c.fetchone()
    conn.close()
    alerts = get_alerts()
    return render_template('generate_contract.html', reservation=reservation, alerts=alerts)

# View Maintenance Page
@app.route('/maintenance')
def maintenance():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute('''SELECT maintenance.id, cars.brand, cars.model, maintenance.task, maintenance.due_date, maintenance.status
                 FROM maintenance
                 JOIN cars ON maintenance.car_id = cars.id''')
    maintenance_tasks = c.fetchall()
    conn.close()
    alerts = get_alerts()
    return render_template('maintenance.html', maintenance_tasks=maintenance_tasks, alerts=alerts, role=session.get('role'))

# Add Maintenance Page
@app.route('/add_maintenance', methods=['GET', 'POST'])
def add_maintenance():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect('/login')

    if request.method == 'POST':
        car_id = request.form['car_id']
        task = request.form['task']
        due_date = request.form['due_date']
        status = request.form['status']

        conn = sqlite3.connect('car_rental.db')
        c = conn.cursor()
        c.execute("INSERT INTO maintenance (car_id, task, due_date, status) VALUES (?, ?, ?, ?)",
                  (car_id, task, due_date, status))
        conn.commit()
        conn.close()
        return redirect('/maintenance')

    # Fetch cars for the form
    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cars")
    cars = c.fetchall()
    conn.close()
    alerts = get_alerts()
    return render_template('add_maintenance.html', cars=cars, alerts=alerts)

# View Damage Reports Page
@app.route('/damage_reports')
def damage_reports():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute('''SELECT damage_reports.id, cars.brand, cars.model, damage_reports.description, damage_reports.report_date, damage_reports.repair_status
                 FROM damage_reports
                 JOIN cars ON damage_reports.car_id = cars.id''')
    damage_reports = c.fetchall()
    conn.close()
    alerts = get_alerts()
    return render_template('damage_reports.html', damage_reports=damage_reports, alerts=alerts, role=session.get('role'))

# Add Damage Report Page
@app.route('/add_damage_report', methods=['GET', 'POST'])
def add_damage_report():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect('/login')

    if request.method == 'POST':
        car_id = request.form['car_id']
        description = request.form['description']
        report_date = request.form['report_date']
        repair_status = request.form['repair_status']

        conn = sqlite3.connect('car_rental.db')
        c = conn.cursor()
        c.execute("INSERT INTO damage_reports (car_id, description, report_date, repair_status) VALUES (?, ?, ?, ?)",
                  (car_id, description, report_date, repair_status))
        conn.commit()
        conn.close()
        return redirect('/damage_reports')

    # Fetch cars for the form
    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cars")
    cars = c.fetchall()
    conn.close()
    alerts = get_alerts()
    return render_template('add_damage_report.html', cars=cars, alerts=alerts)

# Reports Page
@app.route('/reports')
def reports():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect('/login')

    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()

    # Revenue Report
    c.execute("SELECT SUM(total_price) FROM contracts")
    total_revenue = c.fetchone()[0] or 0

    # Car Utilization Report
    c.execute('''SELECT cars.brand, cars.model, COUNT(reservations.id) AS rental_count
                 FROM cars
                 LEFT JOIN reservations ON cars.id = reservations.car_id
                 GROUP BY cars.id''')
    car_utilization = c.fetchall()

    # Maintenance Report
    c.execute('''SELECT cars.brand, cars.model, maintenance.task, maintenance.due_date, maintenance.status
                 FROM maintenance
                 JOIN cars ON maintenance.car_id = cars.id''')
    maintenance_summary = c.fetchall()

    # Client Activity Report
    c.execute('''SELECT clients.name, COUNT(reservations.id) AS reservation_count
                 FROM clients
                 LEFT JOIN reservations ON clients.id = reservations.client_id
                 GROUP BY clients.id''')
    client_activity = c.fetchall()

    conn.close()
    alerts = get_alerts()
    return render_template('reports.html', total_revenue=total_revenue, car_utilization=car_utilization,
                          maintenance_summary=maintenance_summary, client_activity=client_activity, alerts=alerts)

# Export Revenue Report
@app.route('/export_revenue')
def export_revenue():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect('/login')

    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute("SELECT SUM(total_price) FROM contracts")
    total_revenue = c.fetchone()[0] or 0
    conn.close()

    # Create CSV data
    csv_data = StringIO()
    writer = csv.writer(csv_data)
    writer.writerow(['Total Revenue'])
    writer.writerow([total_revenue])

    # Return CSV file
    return Response(
        csv_data.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=revenue_report.csv'}
    )

# Export Car Utilization Report
@app.route('/export_car_utilization')
def export_car_utilization():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect('/login')

    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute('''SELECT cars.brand, cars.model, COUNT(reservations.id) AS rental_count
                 FROM cars
                 LEFT JOIN reservations ON cars.id = reservations.car_id
                 GROUP BY cars.id''')
    car_utilization = c.fetchall()
    conn.close()

    # Create CSV data
    csv_data = StringIO()
    writer = csv.writer(csv_data)
    writer.writerow(['Car', 'Rental Count'])
    for car in car_utilization:
        writer.writerow([f"{car[0]} {car[1]}", car[2]])

    # Return CSV file
    return Response(
        csv_data.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=car_utilization_report.csv'}
    )

# Export Maintenance Report
@app.route('/export_maintenance')
def export_maintenance():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect('/login')

    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute('''SELECT cars.brand, cars.model, maintenance.task, maintenance.due_date, maintenance.status
                 FROM maintenance
                 JOIN cars ON maintenance.car_id = cars.id''')
    maintenance_summary = c.fetchall()
    conn.close()

    # Create CSV data
    csv_data = StringIO()
    writer = csv.writer(csv_data)
    writer.writerow(['Car', 'Task', 'Due Date', 'Status'])
    for task in maintenance_summary:
        writer.writerow([f"{task[0]} {task[1]}", task[2], task[3], task[4]])

    # Return CSV file
    return Response(
        csv_data.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=maintenance_report.csv'}
    )

# Export Client Activity Report
@app.route('/export_client_activity')
def export_client_activity():
    if 'user_id' not in session or session.get('role') != 'Admin':
        return redirect('/login')

    conn = sqlite3.connect('car_rental.db')
    c = conn.cursor()
    c.execute('''SELECT clients.name, COUNT(reservations.id) AS reservation_count
                 FROM clients
                 LEFT JOIN reservations ON clients.id = reservations.client_id
                 GROUP BY clients.id''')
    client_activity = c.fetchall()
    conn.close()

    # Create CSV data
    csv_data = StringIO()
    writer = csv.writer(csv_data)
    writer.writerow(['Client', 'Reservation Count'])
    for client in client_activity:
        writer.writerow([client[0], client[1]])

    # Return CSV file
    return Response(
        csv_data.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=client_activity_report.csv'}
    )

if __name__ == '__main__':
    app.run(debug=True)