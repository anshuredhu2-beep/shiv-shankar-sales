from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'shiv_shankar_master_secret_key_999'

def get_db_connection():
    conn = sqlite3.connect('shop.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            shop_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'shop'
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT NOT NULL,
            name TEXT NOT NULL,
            rate REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            date TEXT NOT NULL
        )
    ''')
    
    # Default Master Admin
    admin_exist = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not admin_exist:
        conn.execute('INSERT INTO users (username, password, shop_name, role) VALUES (?, ?, ?, ?)', 
                     ('admin', 'admin123', 'Master Admin Panel', 'admin'))
        
    # Default 3 Shops
    default_users = [
        ('dukan1', '111', 'Shiv Shankar Sales - Dukan 1'),
        ('dukan2', '222', 'Shiv Shankar Sales - Dukan 2'),
        ('dukan3', '333', 'Shiv Shankar Sales - Dukan 3')
    ]
    for u, p, s in default_users:
        existing = conn.execute('SELECT * FROM users WHERE username = ?', (u,)).fetchone()
        if not existing:
            conn.execute('INSERT INTO users (username, password, shop_name, role) VALUES (?, ?, ?, ?)', (u, p, s, 'shop'))
            
    conn.commit()
    conn.close()

init_db()

@app.route('/login', methods=('GET', 'POST'))
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['shop_name'] = user['shop_name']
            session['role'] = user['role']
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            error = 'Galat Username ya Password hai!'
            
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/', methods=('GET', 'POST'))
def index():
    if 'user_id' not in session or session.get('role') != 'shop':
        return redirect(url_for('login'))
        
    current_shop = session['shop_name']
    conn = get_db_connection()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_item':
            name = request.form['name'].strip()
            rate = float(request.form['rate'])
            stock = int(request.form['stock'])
            
            existing = conn.execute('SELECT * FROM items WHERE shop_name = ? AND name = ?', (current_shop, name)).fetchone()
            if existing:
                new_stock = existing['stock'] + stock
                conn.execute('UPDATE items SET stock = ?, rate = ? WHERE id = ?', (new_stock, rate, existing['id']))
            else:
                conn.execute('INSERT INTO items (shop_name, name, rate, stock) VALUES (?, ?, ?, ?)', (current_shop, name, rate, stock))
            conn.commit()
            
        elif action == 'sell_item':
            item_id = int(request.form['item_id'])
            qty = int(request.form['quantity'])
            
            item = conn.execute('SELECT * FROM items WHERE id = ? AND shop_name = ?', (item_id, current_shop)).fetchone()
            if item and item['stock'] >= qty:
                total_price = item['rate'] * qty
                new_stock = item['stock'] - qty
                
                conn.execute('UPDATE items SET stock = ? WHERE id = ?', (new_stock, item_id))
                
                sale_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn.execute('INSERT INTO sales (shop_name, item_name, quantity, total_price, date) VALUES (?, ?, ?, ?, ?)',
                             (current_shop, item['name'], qty, total_price, sale_date))
                conn.commit()
                
        conn.close()
        return redirect(url_for('index'))

    items = conn.execute('SELECT * FROM items WHERE shop_name = ?', (current_shop,)).fetchall()
    sales = conn.execute('SELECT * FROM sales WHERE shop_name = ? ORDER BY id DESC', (current_shop,)).fetchall()
    
    total_stock_value = sum(item['rate'] * item['stock'] for item in items)
    total_sales_amount = sum(sale['total_price'] for sale in sales)
    
    conn.close()
    return render_template('index.html', items=items, sales=sales, 
                           total_stock_value=total_stock_value, 
                           total_sales_amount=total_sales_amount,
                           current_shop=current_shop)

@app.route('/edit/<int:id>', methods=('GET', 'POST'))
def edit_item(id):
    if 'user_id' not in session or session.get('role') != 'shop':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    item = conn.execute('SELECT * FROM items WHERE id = ? AND shop_name = ?', (id, session['shop_name'])).fetchone()
    if not item:
        conn.close()
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        name = request.form['name'].strip()
        rate = float(request.form['rate'])
        stock = int(request.form['stock'])
        conn.execute('UPDATE items SET name = ?, rate = ?, stock = ? WHERE id = ?', (name, rate, stock, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
        
    conn.close()
    return render_template('edit.html', item=item)

@app.route('/delete/<int:id>')
def delete_item(id):
    if 'user_id' not in session or session.get('role') != 'shop':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    conn.execute('DELETE FROM items WHERE id = ? AND shop_name = ?', (id, session['shop_name']))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/settings', methods=('GET', 'POST'))
def shop_settings():
    if 'user_id' not in session or session.get('role') != 'shop':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        new_shop_name = request.form['shop_name'].strip()
        new_password = request.form['password'].strip()
        
        conn.execute('UPDATE users SET shop_name = ?, password = ? WHERE id = ?', (new_shop_name, new_password, session['user_id']))
        conn.execute('UPDATE items SET shop_name = ? WHERE shop_name = ?', (new_shop_name, user['shop_name']))
        conn.execute('UPDATE sales SET shop_name = ? WHERE shop_name = ?', (new_shop_name, user['shop_name']))
        conn.commit()
        conn.close()
        session['shop_name'] = new_shop_name
        return redirect(url_for('index'))
        
    conn.close()
    return render_template('settings.html', user=user)

@app.route('/admin', methods=('GET', 'POST'))
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_shop':
            username = request.form['username'].strip()
            password = request.form['password'].strip()
            shop_name = request.form['shop_name'].strip()
            try:
                conn.execute('INSERT INTO users (username, password, shop_name, role) VALUES (?, ?, ?, ?)',
                             (username, password, shop_name, 'shop'))
                conn.commit()
            except sqlite3.IntegrityError:
                pass
                
        elif action == 'delete_shop':
            shop_id = request.form['shop_id']
            shop = conn.execute('SELECT * FROM users WHERE id = ?', (shop_id,)).fetchone()
            if shop and shop['username'] != 'admin':
                conn.execute('DELETE FROM users WHERE id = ?', (shop_id,))
                conn.execute('DELETE FROM items WHERE shop_name = ?', (shop['shop_name'],))
                conn.execute('DELETE FROM sales WHERE shop_name = ?', (shop['shop_name'],))
                conn.commit()
                
        conn.close()
        return redirect(url_for('admin_dashboard'))

    shops = conn.execute('SELECT * FROM users WHERE role = "shop"').fetchall()
    all_sales = conn.execute('SELECT * FROM sales ORDER BY id DESC').fetchall()
    all_items = conn.execute('SELECT * FROM items').fetchall()
    
    grand_total_sales = sum(s['total_price'] for s in all_sales)
    grand_total_stock = sum(i['rate'] * i['stock'] for i in all_items)
    
    conn.close()
    return render_template('admin.html', shops=shops, all_sales=all_sales, 
                           grand_total_sales=grand_total_sales, 
                           grand_total_stock=grand_total_stock)

@app.route('/admin/edit_shop/<int:id>', methods=('GET', 'POST'))
def admin_edit_shop(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    shop = conn.execute('SELECT * FROM users WHERE id = ?', (id,)).fetchone()
    
    if request.method == 'POST':
        new_shop_name = request.form['shop_name'].strip()
        new_password = request.form['password'].strip()
        
        conn.execute('UPDATE users SET shop_name = ?, password = ? WHERE id = ?', (new_shop_name, new_password, id))
        conn.execute('UPDATE items SET shop_name = ? WHERE shop_name = ?', (new_shop_name, shop['shop_name']))
        conn.execute('UPDATE sales SET shop_name = ? WHERE shop_name = ?', (new_shop_name, shop['shop_name']))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))
        
    conn.close()
    return render_template('admin_edit.html', shop=shop)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
