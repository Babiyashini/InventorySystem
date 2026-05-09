import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from datetime import timedelta
import mysql.connector
import json
from functools import wraps

load_dotenv()

from ml_advanced import AdvancedDemandPredictor
# Initialize predictor globally
advanced_predictor = AdvancedDemandPredictor()

app = Flask(__name__)
@app.route('/check-flask')
def check_flask():
    return "Flask is alive on port 5000!"

@app.route('/test-search')
def test_search():
    return "Test works!"

@app.route('/search-medicine', methods=['GET'])
def search_medicine_test():
    return [{"id": 1, "name": "Test Medicine"}]

app = Flask(__name__)

# =====================================================
# TEST ROUTE - PUT THIS FIRST
# =====================================================
@app.route('/test123')
def test123():
    return "Test route is working!"

@app.route('/search-test')
def search_test():
    return [{"id": 1, "name": "Paracetamol", "price": 5.50}]
# Add secret key for session management
app.secret_key = 'your-secret-key-here-change-this-in-production'
app.permanent_session_lifetime = timedelta(hours=24)

# --- DATABASE CONNECTION ---
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'pharmacy_db')
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as err:
        print(f"Database Connection Error: {err}")
        return None

# =====================================================
# AUTHENTICATION DECORATORS
# =====================================================

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login_page'))
        if session.get('role') != 'Admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('inventory_page'))
        return f(*args, **kwargs)
    return decorated_function

# =====================================================
# AUTHENTICATION ROUTES
# =====================================================

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, username, password, role, role_id FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user:
                # For demo, using plain text comparison
                if password == user['password']:
                    session.permanent = True
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['role'] = user['role']
                    
                    # Update last login
                    conn = get_db_connection()
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
                        conn.commit()
                        cursor.close()
                        conn.close()
                    
                    flash(f'Welcome back, {username}!', 'success')
                    
                    # Redirect based on role
                    if user['role'] == 'Admin':
                        return redirect(url_for('inventory_page'))
                    else:
                        return redirect(url_for('sales_page'))
                else:
                    flash('Invalid password', 'danger')
            else:
                flash('Username not found', 'danger')
        else:
            flash('Database connection error', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login_page'))

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT password FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        
        if user and old_password == user['password']:
            cursor.execute("UPDATE users SET password = %s WHERE id = %s", (new_password, session['user_id']))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"message": "Password changed successfully"}), 200
        else:
            cursor.close()
            conn.close()
            return jsonify({"error": "Invalid current password"}), 400
    
    return jsonify({"error": "Database error"}), 500

# =====================================================
# FRONTEND ROUTES (Protected)
# =====================================================

@app.route('/')
@app.route('/inventory')
@login_required
def inventory_page():
    return render_template('index.html')

@app.route('/insights')
@login_required
def insights_page():
    return render_template('insights.html')

@app.route('/sales')
@login_required
def sales_page():
    return render_template('sales.html')

@app.route('/suppliers')
@login_required
def suppliers_page():
    return render_template('suppliers.html')

@app.route('/batches')
@login_required
def batches_page():
    return render_template('batches.html')

@app.route('/reports')
@login_required
def reports_page():
    return render_template('reports.html')

@app.route('/dashboard')
@login_required
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/invoices')
@login_required
def invoices_page():
    return render_template('invoices.html')

@app.route('/profile')
@login_required
def profile_page():
    return render_template('profile.html')

@app.route('/stock-movements')
@login_required
def stock_movements_page():
    return render_template('stock_movements.html')

@app.route('/users')
@login_required
@admin_required
def users_page():
    return render_template('users.html')

@app.route('/purchase-orders')
@login_required
def purchase_orders_page():
    return render_template('purchase_orders.html')

# =====================================================
# MEDICINE MANAGEMENT ENDPOINTS
# =====================================================

@app.route("/get-medicines", methods=["GET"])
@login_required
def get_medicines():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                m.id,
                m.name,
                m.generic_name,
                m.category_id,
                c.category_name as category,
                m.supplier_id,
                s.name as supplier,
                m.quantity,
                m.price,
                m.expiry_date,
                m.dosage_form,
                m.strength,
                m.requires_prescription,
                m.storage_conditions,
                m.is_active,
                m.added_at,
                m.updated_at
            FROM medicines m
            LEFT JOIN categories c ON m.category_id = c.category_id
            LEFT JOIN suppliers s ON m.supplier_id = s.id
            WHERE m.is_active = 1
            ORDER BY m.id DESC
        """)
        rows = cursor.fetchall()
        
        # Format dates for JSON serialization
        for row in rows:
            if row['expiry_date']:
                row['expiry_date'] = row['expiry_date'].strftime('%Y-%m-%d')
            if row['added_at']:
                row['added_at'] = row['added_at'].strftime('%Y-%m-%d %H:%M:%S')
            if row['updated_at']:
                row['updated_at'] = row['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify(rows), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route("/add-medicine", methods=["POST"])
@login_required
def add_medicine():
    try:
        data = request.get_json()
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor()
        
        # Handle expiry date
        expiry_date = data.get('expiry_date')
        if expiry_date and expiry_date != '':
            try:
                expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
            except:
                expiry_date = None
        else:
            expiry_date = None
        
        # Get or create category
        category_id = None
        if data.get('category'):
            cursor.execute("SELECT category_id FROM categories WHERE category_name = %s", (data['category'],))
            result = cursor.fetchone()
            if result:
                category_id = result[0]
            else:
                cursor.execute("INSERT INTO categories (category_name) VALUES (%s)", (data['category'],))
                category_id = cursor.lastrowid
        
        # Get supplier ID
        supplier_id = None
        if data.get('supplier'):
            cursor.execute("SELECT id FROM suppliers WHERE name = %s", (data['supplier'],))
            result = cursor.fetchone()
            if result:
                supplier_id = result[0]
        
        query = """
            INSERT INTO medicines (
                name, generic_name, category_id, supplier_id, 
                quantity, price, expiry_date, dosage_form, 
                strength, requires_prescription, storage_conditions, is_active
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data.get('name', ''),
            data.get('generic_name', ''),
            category_id,
            supplier_id,
            data.get('quantity', 0),
            data.get('price', 0),
            expiry_date,
            data.get('dosage_form', ''),
            data.get('strength', ''),
            data.get('requires_prescription', False),
            data.get('storage_conditions', ''),
            1
        )
        cursor.execute(query, values)
        medicine_id = cursor.lastrowid
        
        # Create initial batch for this medicine
        cursor.execute("""
            INSERT INTO batches (
                medicine_id, batch_number, expiry_date, 
                purchase_price, selling_price, 
                quantity_initial, quantity_current, received_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            medicine_id,
            f"BATCH-{medicine_id}-001",
            expiry_date,
            data.get('price', 0) * 0.7,
            data.get('price', 0),
            data.get('quantity', 0),
            data.get('quantity', 0),
            date.today()
        ))
        
        conn.commit()
        return jsonify({"message": "Medicine added successfully!", "id": medicine_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route("/update-medicine/<int:id>", methods=["PUT"])
@login_required
def update_medicine(id):
    try:
        data = request.get_json()
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor()
        
        # Check if medicine exists
        cursor.execute("SELECT id FROM medicines WHERE id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"error": "Medicine not found"}), 404
        
        # Handle expiry date
        expiry_date = data.get('expiry_date')
        if expiry_date and expiry_date != '':
            try:
                expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
            except:
                expiry_date = None
        else:
            expiry_date = None
        
        # Get category ID
        category_id = None
        if data.get('category'):
            cursor.execute("SELECT category_id FROM categories WHERE category_name = %s", (data['category'],))
            result = cursor.fetchone()
            if result:
                category_id = result[0]
        
        # Get supplier ID
        supplier_id = None
        if data.get('supplier'):
            cursor.execute("SELECT id FROM suppliers WHERE name = %s", (data['supplier'],))
            result = cursor.fetchone()
            if result:
                supplier_id = result[0]
        
        query = """
            UPDATE medicines 
            SET name = %s, generic_name = %s, category_id = %s, supplier_id = %s,
                quantity = %s, price = %s, expiry_date = %s, dosage_form = %s,
                strength = %s, requires_prescription = %s, storage_conditions = %s
            WHERE id = %s
        """
        values = (
            data.get('name', ''),
            data.get('generic_name', ''),
            category_id,
            supplier_id,
            data.get('quantity', 0),
            data.get('price', 0),
            expiry_date,
            data.get('dosage_form', ''),
            data.get('strength', ''),
            data.get('requires_prescription', False),
            data.get('storage_conditions', ''),
            id
        )
        cursor.execute(query, values)
        
        # Update corresponding batch
        cursor.execute("""
            UPDATE batches 
            SET expiry_date = %s, selling_price = %s
            WHERE medicine_id = %s AND is_active = 1
            LIMIT 1
        """, (expiry_date, data.get('price', 0), id))
        
        conn.commit()
        return jsonify({"message": "Medicine updated successfully!"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route("/delete-medicine/<int:id>", methods=["DELETE"])
@login_required
def delete_medicine(id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor()
        
        # Check if medicine exists
        cursor.execute("SELECT id FROM medicines WHERE id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"error": "Medicine not found"}), 404
        
        # Soft delete - just mark as inactive
        cursor.execute("UPDATE medicines SET is_active = 0 WHERE id = %s", (id,))
        cursor.execute("UPDATE batches SET is_active = 0 WHERE medicine_id = %s", (id,))
        
        conn.commit()
        return jsonify({"message": "Medicine deactivated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route("/adjust-stock", methods=["POST"])
@login_required
def adjust_stock():
    try:
        data = request.get_json()
        medicine_id = data.get('id')
        adjustment_type = data.get('type')
        quantity = data.get('quantity')
        reason = data.get('reason', 'Manual adjustment')
        
        if not medicine_id or not quantity:
            return jsonify({"error": "Medicine ID and quantity are required"}), 400
        
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT batch_id, quantity_current, selling_price 
            FROM batches 
            WHERE medicine_id = %s AND is_active = 1
            LIMIT 1
        """, (medicine_id,))
        batch = cursor.fetchone()
        
        if not batch:
            return jsonify({"error": "No active batch found for this medicine"}), 404
        
        current_qty = batch['quantity_current']
        new_qty = current_qty
        
        if adjustment_type == 'add':
            new_qty = current_qty + quantity
            movement_type = 'IN'
        elif adjustment_type == 'remove':
            if quantity > current_qty:
                return jsonify({"error": f"Cannot remove {quantity} units. Only {current_qty} available."}), 400
            new_qty = current_qty - quantity
            movement_type = 'OUT'
        elif adjustment_type == 'set':
            new_qty = quantity
            movement_type = 'ADJUSTMENT'
        else:
            return jsonify({"error": "Invalid adjustment type"}), 400
        
        conn.start_transaction()
        
        cursor.execute(
            "UPDATE batches SET quantity_current = %s WHERE batch_id = %s",
            (new_qty, batch['batch_id'])
        )
        
        cursor.execute(
            "UPDATE medicines SET quantity = %s WHERE id = %s",
            (new_qty, medicine_id)
        )
        
        cursor.execute("""
            INSERT INTO stock_movements 
            (batch_id, movement_type, quantity, previous_quantity, new_quantity, 
             unit_price, total_value, reference_type, reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            batch['batch_id'],
            movement_type,
            abs(quantity),
            current_qty,
            new_qty,
            batch['selling_price'],
            abs(quantity) * batch['selling_price'],
            'ADJUSTMENT',
            reason
        ))
        
        conn.commit()
        
        return jsonify({
            "message": f"Stock adjusted successfully!",
            "previous_stock": current_qty,
            "new_stock": new_qty,
            "adjustment_type": adjustment_type,
            "quantity_adjusted": quantity
        }), 200
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# =====================================================
# SEARCH ENDPOINT
# =====================================================

@app.route('/search-medicine', methods=['GET'])
@login_required
def search_medicine():
    query = request.args.get('name', '')
    if not query or len(query) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                m.id, m.name, m.generic_name, 
                b.quantity_current as quantity, 
                m.price, m.expiry_date,
                c.category_name as category,
                s.name as supplier
            FROM medicines m
            LEFT JOIN batches b ON m.id = b.medicine_id AND b.is_active = 1
            LEFT JOIN categories c ON m.category_id = c.category_id
            LEFT JOIN suppliers s ON m.supplier_id = s.id
            WHERE m.name LIKE %s AND m.is_active = 1
            ORDER BY m.name 
            LIMIT 10
        """, (f"%{query}%",))
        results = cursor.fetchall()
        
        for item in results:
            if item['expiry_date']:
                item['expiry_date'] = item['expiry_date'].strftime('%Y-%m-%d')
            item['quantity'] = item['quantity'] or 0
        
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# =====================================================
# SALES ENDPOINTS
# =====================================================

@app.route("/record-sale", methods=["POST"])
@login_required
def record_sale():
    data = request.json
    med_id = data.get('medicine_id') 
    qty_sold = data.get('quantity_sold')
    sale_price = data.get('sale_price')
    customer_name = data.get('customer_name', 'Walk-in Customer')
    payment_method = data.get('payment_method', 'Cash')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "DB Connection Failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT b.batch_id, b.quantity_current, b.selling_price, 
                   m.name, m.price, m.expiry_date
            FROM batches b
            JOIN medicines m ON b.medicine_id = m.id
            WHERE m.id = %s AND b.is_active = 1
            LIMIT 1
        """, (med_id,))
        batch = cursor.fetchone()
        
        if not batch:
            return jsonify({"error": "Medicine not found or no active batch!"}), 400
        
        if batch['expiry_date'] and batch['expiry_date'] < date.today():
            return jsonify({"error": f"Cannot sell expired medicine: {batch['name']}"}), 400
        
        if batch['quantity_current'] < qty_sold:
            return jsonify({"error": f"Insufficient stock! Only {batch['quantity_current']} units available."}), 400
        
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
        
        conn.start_transaction()
        
        new_qty = batch['quantity_current'] - qty_sold
        cursor.execute(
            "UPDATE batches SET quantity_current = %s WHERE batch_id = %s",
            (new_qty, batch['batch_id'])
        )
        
        cursor.execute(
            "UPDATE medicines SET quantity = %s WHERE id = %s",
            (new_qty, med_id)
        )
        
        cursor.execute("""
            INSERT INTO sales 
            (medicine_id, quantity_sold, sale_price, sale_date)
            VALUES (%s, %s, %s, NOW())
        """, (
            med_id,
            qty_sold,
            sale_price
        ))
        
        conn.commit()
        
        return jsonify({
            "message": f"Sale recorded! Sold {qty_sold} units of {batch['name']}",
            "remaining_stock": new_qty
        }), 200
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# =====================================================
# FIXED GET SALES ENDPOINT - Works with your table structure
# =====================================================

@app.route('/get-sales', methods=['GET'])
@login_required
def get_sales():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Query only with columns that exist in your sales table
        cursor.execute("""
            SELECT 
                s.id,
                s.medicine_id,
                m.name as medicine_name,
                s.quantity_sold,
                s.sale_price,
                s.sale_date
            FROM sales s
            JOIN medicines m ON s.medicine_id = m.id
            ORDER BY s.sale_date DESC
            LIMIT 100
        """)
        sales = cursor.fetchall()
        
        # Format dates and add display-friendly fields
        for sale in sales:
            if sale['sale_date']:
                sale['sale_date'] = sale['sale_date'].strftime('%Y-%m-%d %H:%M:%S')
            # Add computed fields for the frontend
            sale['invoice_number'] = f"INV-{sale['id']}"
            sale['unit_price'] = round(sale['sale_price'] / sale['quantity_sold'], 2) if sale['quantity_sold'] > 0 else sale['sale_price']
            sale['final_price'] = sale['sale_price']
            sale['payment_method'] = 'Cash'
            sale['customer_name'] = 'Walk-in Customer'
            sale['total_price'] = sale['sale_price']
        
        return jsonify(sales), 200
    except Exception as e:
        print(f"Error in get_sales: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# =====================================================
# SUPPLIER ENDPOINTS
# =====================================================

@app.route("/get-suppliers", methods=["GET"])
@login_required
def get_suppliers():
    conn = get_db_connection()
    if not conn:
        return jsonify([]), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Remove 'address' column since it doesn't exist in your table
        cursor.execute("""
            SELECT id, name, contact_person, phone, email, medicine_type
            FROM suppliers
            ORDER BY name
        """)
        rows = cursor.fetchall()
        
        if rows is None:
            rows = []
            
        return jsonify(rows), 200
    except Exception as e:
        print(f"Error in get_suppliers: {e}")
        return jsonify([]), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/add-supplier", methods=["POST"])
@login_required
def add_supplier():
    try:
        data = request.get_json()
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor()
        # Remove 'address' from the query
        query = """
            INSERT INTO suppliers (name, contact_person, phone, email, medicine_type) 
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (
            data.get('name', ''),
            data.get('contact_person', ''),
            data.get('phone', ''),
            data.get('email', ''),
            data.get('medicine_type', '')
        )
        cursor.execute(query, values)
        conn.commit()
        return jsonify({"message": "Supplier added successfully!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
@app.route("/delete-supplier/<int:id>", methods=["DELETE"])
@login_required
def delete_supplier(id):
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM suppliers WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"message": "Supplier deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# =====================================================
# ML INSIGHTS ENDPOINTS
# =====================================================

@app.route('/get-ml-insights', methods=['GET'])
@login_required
def get_ml_insights():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        sales_df = pd.read_sql("""
            SELECT medicine_id, quantity_sold, sale_date 
            FROM sales 
            WHERE sale_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """, conn)
        
        stock_df = pd.read_sql("""
            SELECT 
                m.id, m.name, 
                SUM(b.quantity_current) as quantity,
                m.price,
                MIN(b.expiry_date) as expiry_date
            FROM medicines m
            JOIN batches b ON m.id = b.medicine_id AND b.is_active = 1
            WHERE m.is_active = 1
            GROUP BY m.id, m.name, m.price
        """, conn)
        
        today = date.today()
        
        if sales_df.empty:
            results = []
            for _, row in stock_df.iterrows():
                is_expired = False
                if pd.notnull(row['expiry_date']):
                    expiry_date = row['expiry_date']
                    if isinstance(expiry_date, str):
                        expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
                    is_expired = expiry_date < today if expiry_date else False
                
                results.append({
                    'medicine': row['name'],
                    'daily_velocity': 0,
                    'days_until_out': 999,
                    'status': 'Expired' if is_expired else 'No Sales Data',
                    'stock': row['quantity'],
                    'price': float(row['price']),
                    'expiry_date': row['expiry_date'].strftime('%Y-%m-%d') if pd.notnull(row['expiry_date']) else None,
                    'is_expired': is_expired
                })
            conn.close()
            return jsonify(results)
        
        sales_df['sale_date'] = pd.to_datetime(sales_df['sale_date'])
        sales_df['date_only'] = sales_df['sale_date'].dt.date
        
        daily_sales = sales_df.groupby(['medicine_id', 'date_only'])['quantity_sold'].sum().reset_index()
        velocity = daily_sales.groupby('medicine_id')['quantity_sold'].mean().reset_index()
        velocity.columns = ['medicine_id', 'daily_velocity']
        
        merged = pd.merge(stock_df, velocity, left_on='id', right_on='medicine_id', how='left')
        merged['daily_velocity'] = merged['daily_velocity'].fillna(0)
        
        results = []
        for _, row in merged.iterrows():
            vel = float(row['daily_velocity'])
            curr_qty = int(row['quantity'])
            
            is_expired = False
            if pd.notnull(row['expiry_date']):
                expiry_date = row['expiry_date']
                if isinstance(expiry_date, str):
                    expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()
                is_expired = expiry_date < today if expiry_date else False
            
            if vel > 0 and not is_expired:
                days_left = round(curr_qty / vel)
                if days_left < 3:
                    status = "Critical - Urgent Restock"
                elif days_left < 7:
                    status = "Urgent"
                elif days_left < 14:
                    status = "Warning"
                else:
                    status = "Stable"
            elif is_expired:
                days_left = 0
                status = "Expired - Remove from Stock"
            else:
                days_left = 999
                status = "No Sales Data"
            
            results.append({
                'medicine': row['name'],
                'daily_velocity': round(vel, 2),
                'days_until_out': days_left,
                'status': status,
                'stock': curr_qty,
                'price': float(row['price']),
                'expiry_date': row['expiry_date'].strftime('%Y-%m-%d') if pd.notnull(row['expiry_date']) else None,
                'is_expired': is_expired
            })
        
        urgency_order = {'Critical - Urgent Restock': 0, 'Urgent': 1, 'Warning': 2, 
                        'Expired - Remove from Stock': 3, 'Stable': 4, 'No Sales Data': 5}
        results.sort(key=lambda x: urgency_order.get(x['status'], 6))
        
        conn.close()
        return jsonify(results)
        
    except Exception as e:
        print(f"ML Insights Error: {e}")
        conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/get-dashboard-stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT SUM(b.quantity_current * b.selling_price) as total_value 
            FROM batches b
            JOIN medicines m ON b.medicine_id = m.id
            WHERE b.is_active = 1 AND (b.expiry_date IS NULL OR b.expiry_date >= CURDATE())
        """)
        result = cursor.fetchone()
        total_value = result['total_value'] if result and result['total_value'] else 0
        
        cursor.execute("""
            SELECT COUNT(DISTINCT m.id) as low_count 
            FROM medicines m
            JOIN batches b ON m.id = b.medicine_id AND b.is_active = 1
            WHERE b.quantity_current < 10 
            AND (b.expiry_date IS NULL OR b.expiry_date >= CURDATE())
        """)
        result = cursor.fetchone()
        low_count = result['low_count'] if result else 0
        
        cursor.execute("""
            SELECT COUNT(DISTINCT m.id) as expired_count 
            FROM medicines m
            JOIN batches b ON m.id = b.medicine_id
            WHERE b.expiry_date IS NOT NULL AND b.expiry_date < CURDATE()
        """)
        result = cursor.fetchone()
        expired_count = result['expired_count'] if result else 0
        
        return jsonify({
            "stock_value": f"LKR {total_value:,.2f}" if total_value else "LKR 0.00",
            "low_stock_count": low_count,
            "expired_count": expired_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# =====================================================
# CATEGORY ENDPOINTS
# =====================================================

@app.route("/get-categories", methods=["GET"])
@login_required
def get_categories():
    conn = get_db_connection()
    if not conn:
        return jsonify([]), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT category_id, category_name FROM categories ORDER BY category_name")
        rows = cursor.fetchall()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get-advanced-predictions', methods=['GET'])
@login_required
def get_advanced_predictions():
    try:
        if not advanced_predictor.load_model():
            return jsonify({"error": "Model not trained yet"}), 400
        
        predictions = advanced_predictor.get_all_predictions()
        return jsonify(predictions), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/retrain-model', methods=['POST'])
@login_required
def retrain_model():
    try:
        success = advanced_predictor.train()
        if success:
            return jsonify({"message": "Model retrained successfully!"}), 200
        else:
            return jsonify({"error": "Training failed. Need more data."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =====================================================
# BATCH MANAGEMENT ENDPOINTS
# =====================================================

@app.route('/get-batches', methods=['GET'])
@login_required
def get_batches():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                b.batch_id,
                b.medicine_id,
                m.name as medicine_name,
                m.generic_name,
                c.category_name,
                s.name as supplier_name,
                b.batch_number,
                b.manufacturing_date,
                b.expiry_date,
                b.purchase_price,
                b.selling_price,
                b.quantity_initial,
                b.quantity_current,
                b.received_date,
                b.is_active,
                DATEDIFF(b.expiry_date, CURDATE()) as days_until_expiry
            FROM batches b
            JOIN medicines m ON b.medicine_id = m.id
            LEFT JOIN categories c ON m.category_id = c.category_id
            LEFT JOIN suppliers s ON m.supplier_id = s.id
            WHERE b.is_active = 1
            ORDER BY b.expiry_date ASC
        """)
        
        batches = cursor.fetchall()
        
        for batch in batches:
            if batch['manufacturing_date']:
                batch['manufacturing_date'] = batch['manufacturing_date'].strftime('%Y-%m-%d')
            if batch['expiry_date']:
                batch['expiry_date'] = batch['expiry_date'].strftime('%Y-%m-%d')
            if batch['received_date']:
                batch['received_date'] = batch['received_date'].strftime('%Y-%m-%d')
        
        return jsonify(batches), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/get-expiry-alerts', methods=['GET'])
@login_required
def get_expiry_alerts():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                b.batch_id,
                m.id as medicine_id,
                m.name as medicine_name,
                b.batch_number,
                b.expiry_date,
                b.quantity_current,
                DATEDIFF(b.expiry_date, CURDATE()) as days_until_expiry,
                CASE 
                    WHEN b.expiry_date < CURDATE() THEN 'Expired'
                    WHEN DATEDIFF(b.expiry_date, CURDATE()) <= 30 THEN 'Expiring Soon'
                    ELSE 'Valid'
                END as expiry_status
            FROM batches b
            JOIN medicines m ON b.medicine_id = m.id
            WHERE b.is_active = 1
            AND (b.expiry_date < CURDATE() OR DATEDIFF(b.expiry_date, CURDATE()) <= 30)
            ORDER BY b.expiry_date ASC
        """)
        
        alerts = cursor.fetchall()
        
        for alert in alerts:
            if alert['expiry_date']:
                alert['expiry_date'] = alert['expiry_date'].strftime('%Y-%m-%d')
        
        return jsonify(alerts), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/get-stock-summary', methods=['GET'])
@login_required
def get_stock_summary():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT SUM(b.quantity_current * b.selling_price) as total_value
            FROM batches b
            WHERE b.is_active = 1 AND (b.expiry_date IS NULL OR b.expiry_date >= CURDATE())
        """)
        total_value = cursor.fetchone()['total_value'] or 0
        
        cursor.execute("""
            SELECT COUNT(DISTINCT m.id) as low_stock_count
            FROM medicines m
            JOIN batches b ON m.id = b.medicine_id
            WHERE b.quantity_current < 10 AND b.is_active = 1
            AND (b.expiry_date IS NULL OR b.expiry_date >= CURDATE())
        """)
        low_stock = cursor.fetchone()['low_stock_count'] or 0
        
        cursor.execute("""
            SELECT COUNT(DISTINCT m.id) as expired_count
            FROM medicines m
            JOIN batches b ON m.id = b.medicine_id
            WHERE b.expiry_date < CURDATE() AND b.is_active = 1
        """)
        expired = cursor.fetchone()['expired_count'] or 0
        
        return jsonify({
            "total_value": total_value,
            "low_stock_count": low_stock,
            "expired_count": expired
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# =====================================================
# PURCHASE ORDER ENDPOINTS
# =====================================================

@app.route('/get-purchase-orders', methods=['GET'])
@login_required
def get_purchase_orders():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                po.po_id,
                po.po_number,
                po.supplier_id,
                s.name as supplier_name,
                po.order_date,
                po.expected_delivery,
                po.total_amount,
                po.status,
                po.notes,
                po.created_at
            FROM purchase_orders po
            LEFT JOIN suppliers s ON po.supplier_id = s.id
            ORDER BY po.created_at DESC
        """)
        orders = cursor.fetchall()
        
        for order in orders:
            if order['order_date']:
                order['order_date'] = order['order_date'].strftime('%Y-%m-%d')
            if order['expected_delivery']:
                order['expected_delivery'] = order['expected_delivery'].strftime('%Y-%m-%d')
        
        return jsonify(orders), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get-po-items/<int:po_id>', methods=['GET'])
@login_required
def get_po_items(po_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                po_item_id,
                medicine_id,
                m.name as medicine_name,
                quantity_ordered,
                quantity_received,
                unit_price,
                total_price
            FROM po_items
            JOIN medicines m ON po_items.medicine_id = m.id
            WHERE po_id = %s
        """, (po_id,))
        items = cursor.fetchall()
        return jsonify(items), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/create-purchase-order', methods=['POST'])
@login_required
def create_purchase_order():
    data = request.get_json()
    supplier_id = data.get('supplier_id')
    items = data.get('items', [])
    expected_delivery = data.get('expected_delivery')
    notes = data.get('notes', '')
    
    if not supplier_id or not items:
        return jsonify({"error": "Supplier and items are required"}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    try:
        po_number = f"PO-{datetime.now().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M%S')}"
        order_date = date.today()
        
        total_amount = sum(item.get('quantity', 0) * item.get('unit_price', 0) for item in items)
        
        cursor.execute("""
            INSERT INTO purchase_orders (po_number, supplier_id, order_date, expected_delivery, total_amount, status, notes, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (po_number, supplier_id, order_date, expected_delivery, total_amount, 'Draft', notes, session['user_id']))
        
        po_id = cursor.lastrowid
        
        for item in items:
            cursor.execute("""
                INSERT INTO po_items (po_id, medicine_id, quantity_ordered, unit_price, total_price)
                VALUES (%s, %s, %s, %s, %s)
            """, (po_id, item['medicine_id'], item['quantity'], item['unit_price'], item['quantity'] * item['unit_price']))
        
        conn.commit()
        
        return jsonify({"message": "Purchase order created!", "po_id": po_id, "po_number": po_number}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/update-po-status/<int:po_id>', methods=['PUT'])
@login_required
def update_po_status(po_id):
    data = request.get_json()
    status = data.get('status')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE purchase_orders SET status = %s WHERE po_id = %s", (status, po_id))
        conn.commit()
        return jsonify({"message": f"Status updated to {status}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/receive-purchase-order/<int:po_id>', methods=['POST'])
@login_required
def receive_purchase_order(po_id):
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT po_id, status FROM purchase_orders WHERE po_id = %s", (po_id,))
        po = cursor.fetchone()
        
        if not po:
            return jsonify({"error": "Purchase order not found"}), 404
        
        if po['status'] != 'Confirmed':
            return jsonify({"error": "Purchase order must be confirmed before receiving"}), 400
        
        cursor.execute("SELECT po_item_id, medicine_id, quantity_ordered, unit_price FROM po_items WHERE po_id = %s", (po_id,))
        items = cursor.fetchall()
        
        conn.start_transaction()
        
        for item in items:
            cursor.execute("""
                UPDATE po_items SET quantity_received = quantity_ordered WHERE po_item_id = %s
            """, (item['po_item_id'],))
            
            # Update stock (add received quantity)
            cursor.execute("""
                UPDATE medicines SET quantity = quantity + %s WHERE id = %s
            """, (item['quantity_ordered'], item['medicine_id']))
            
            # Create or update batch
            cursor.execute("""
                INSERT INTO batches (medicine_id, batch_number, expiry_date, purchase_price, selling_price, quantity_initial, quantity_current, received_date)
                VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL 6 MONTH), %s, %s, %s, %s, NOW())
            """, (item['medicine_id'], f"PO-{po_id}-BATCH", item['unit_price'], item['unit_price'] * 1.3, item['quantity_ordered'], item['quantity_ordered']))
        
        cursor.execute("UPDATE purchase_orders SET status = 'Received' WHERE po_id = %s", (po_id,))
        
        conn.commit()
        
        return jsonify({"message": "Purchase order received and stock updated!"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# =====================================================
# USER MANAGEMENT API ENDPOINTS
# =====================================================
# =====================================================
# USER ACTIVITIES ENDPOINT (ADD THIS NEW ENDPOINT)
# =====================================================
@app.route('/get-user-activities/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_user_activities(user_id):
    """Get all activities for a specific user"""
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 1. Get user details
        cursor.execute("SELECT id, username, role, full_name, email, is_active FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # 2. Get user's sales (only columns that exist)
        cursor.execute("""
            SELECT s.id, m.name as medicine_name, s.quantity_sold, s.sale_price, s.sale_date
            FROM sales s
            JOIN medicines m ON s.medicine_id = m.id
            WHERE s.sold_by = %s
            ORDER BY s.sale_date DESC
            LIMIT 100
        """, (user_id,))
        sales = cursor.fetchall()
        
        for sale in sales:
            if sale.get('sale_date'):
                sale['sale_date'] = sale['sale_date'].strftime('%Y-%m-%d %H:%M:%S')
        
        # 3. Calculate statistics
        total_sales_amount = sum(float(s['sale_price']) for s in sales) if sales else 0
        total_transactions = len(sales)
        total_items_sold = sum(int(s['quantity_sold']) for s in sales) if sales else 0
        
        return jsonify({
            "user": user,
            "statistics": {
                "total_sales_amount": round(total_sales_amount, 2),
                "total_transactions": total_transactions,
                "total_items_sold": total_items_sold
            },
            "sales": sales
        }), 200
        
    except Exception as e:
        print(f"Error in get_user_activities: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/add-user', methods=['POST'])
@login_required
@admin_required
def add_user():
    data = request.get_json()
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (username, password, email, full_name, role, phone, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
        """, (
            data.get('username'), 
            data.get('password'), 
            data.get('email', ''), 
            data.get('full_name', ''), 
            data.get('role', 'Staff'),
            data.get('phone', '')
        ))
        conn.commit()
        return jsonify({"message": "User added successfully"}), 201
    except mysql.connector.IntegrityError as e:
        if 'Duplicate entry' in str(e):
            return jsonify({"error": "Username already exists"}), 400
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/delete-user/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    # Prevent deleting your own account
    if user_id == session['user_id']:
        return jsonify({"error": "Cannot delete your own account"}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/update-user/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    data = request.get_json()
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE users 
            SET email = %s, full_name = %s, phone = %s, role = %s
            WHERE id = %s
        """, (
            data.get('email', ''),
            data.get('full_name', ''),
            data.get('phone', ''),
            data.get('role', 'Staff'),
            user_id
        ))
        conn.commit()
        return jsonify({"message": "User updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/toggle-user-status/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def toggle_user_status(user_id):
    data = request.get_json()
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET is_active = %s WHERE id = %s", (data.get('is_active', True), user_id))
        conn.commit()
        return jsonify({"message": "User status updated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/reset-user-password/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def reset_user_password(user_id):
    data = request.get_json()
    new_password = data.get('password', 'password123')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (new_password, user_id))
        conn.commit()
        return jsonify({"message": "Password reset successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/get-stock-movements', methods=['GET'])
@login_required
def get_stock_movements():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                sm.movement_id,
                sm.batch_id,
                b.batch_number,
                m.name as medicine_name,
                sm.movement_type,
                sm.quantity,
                sm.previous_quantity,
                sm.new_quantity,
                sm.unit_price,
                sm.total_value,
                sm.reason,
                sm.created_at
            FROM stock_movements sm
            LEFT JOIN batches b ON sm.batch_id = b.batch_id
            LEFT JOIN medicines m ON b.medicine_id = m.id
            ORDER BY sm.created_at DESC
            LIMIT 200
        """)
        movements = cursor.fetchall()
        
        for movement in movements:
            if movement['created_at']:
                movement['created_at'] = movement['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify(movements), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# =====================================================
# MAIN - CORRECTED VERSION
# =====================================================


@app.route('/check-session')
@login_required
def check_session():
    return jsonify({
        "logged_in": True,
        "user_id": session.get('user_id'),
        "username": session.get('username'),
        "role": session.get('role')
    })

@app.route('/get-users', methods=['GET'])
@login_required
def get_users():
    conn = get_db_connection()
    if not conn:
        return jsonify([]), 500
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, username, role, email, full_name, phone, is_active FROM users ORDER BY id DESC")
        users = cursor.fetchall()
        
        for user in users:
            if not user.get('full_name'):
                user['full_name'] = ''
            if not user.get('email'):
                user['email'] = ''
            if not user.get('phone'):
                user['phone'] = ''
            if user.get('is_active') is None:
                user['is_active'] = 1
        
        return jsonify(users), 200
    except Exception as e:
        print(f"Error in get_users: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route('/admin-users')
@login_required
@admin_required
def admin_users_page():
    return render_template('admin_users.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
import os
from dotenv import load_dotenv
load_dotenv()

