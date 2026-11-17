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
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 1. Home / Stock View Page
@app.route('/')
def index():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM items').fetchall()
    conn.close()
    return render_template('index.html', items=items)

# 2. Add Item Page
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
    return render_template('add_item.html')

# 3. Billing / Sale Page
@app.route('/bill', methods=('GET', 'POST'))
def bill():
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM items').fetchall()
    
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        qty = int(request.form['quantity'])
        
        item = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
        
        if item and item['stock'] >= qty:
            total_price = item['rate'] * qty
            new_stock = item['stock'] - qty
            
            # Update stock and record sale
            conn.execute('UPDATE items SET stock = ? WHERE id = ?', (new_stock, item_id))
            conn.execute('INSERT INTO sales (item_name, quantity, total_price) VALUES (?, ?, ?)', 
                         (item['name'], qty, total_price))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
            
    conn.close()
    return render_template('billing.html', items=items)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)


# Sales Table Model
class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    qty_sold = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(50), nullable=False)

# Report Route
@app.route('/report')
def report():
    items = Item.query.all()
    sales = Sale.query.all()
    
    total_stock_value = sum(item.rate * item.stock for item in items)
    total_sales_amount = sum(sale.total_price for sale in sales)
    
    return render_template('report.html', items=items, sales=sales, total_stock_value=total_stock_value, total_sales_amount=total_sales_amount)
