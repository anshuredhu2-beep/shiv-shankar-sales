from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('shop.db')
    conn.row_factory = sqlite3.Row
    return conn

# Database initialize karna
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rate REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            date TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM items').fetchall()
    conn.close()
    return render_template('index.html', items=items)

@app.route('/add', methods=('GET', 'POST'))
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        rate = float(request.form['rate'])
        stock = int(request.form['stock'])
        
        conn = get_db_connection()
        conn.execute('INSERT INTO items (name, rate, stock) VALUES (?, ?, ?)', (name, rate, stock))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/billing', methods=('GET', 'POST'))
def billing():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM items').fetchall()
    
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        qty = int(request.form['quantity'])
        
        item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
        if item and item['stock'] >= qty:
            total_price = item['rate'] * qty
            new_stock = item['stock'] - qty
            
            # Update stock
            conn.execute('UPDATE items SET stock = ? WHERE id = ?', (new_stock, item_id))
            
            # Record sale with current date
            sale_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn.execute('INSERT INTO sales (item_name, quantity, total_price, date) VALUES (?, ?, ?, ?)',
                         (item['name'], qty, total_price, sale_date))
            conn.commit()
        
        conn.close()
        return redirect(url_for('index'))
        
    conn.close()
    return render_template('billing.html', items=items)

@app.route('/report')
def report():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM items').fetchall()
    sales = conn.execute('SELECT * FROM sales').fetchall()
    
    total_stock_value = sum(item['rate'] * item['stock'] for item in items)
    total_sales_amount = sum(sale['total_price'] for sale in sales)
    
    conn.close()
    return render_template('report.html', items=items, sales=sales, total_stock_value=total_stock_value, total_sales_amount=total_sales_amount)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
