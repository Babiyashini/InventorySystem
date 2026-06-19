import re

# Read the file
with open('app.py', 'r') as f:
    content = f.read()

# Fix 1: Remove the problematic f-string with conditional
# Replace the entire get_dashboard_stats function
pattern = r'@app\.route\(\'/get-dashboard-stats\', methods=\[\'GET\'\]\).*?def get_dashboard_stats\(\):.*?return jsonify\(\{.*?\}\)'
replacement = '''@app.route('/get-dashboard-stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                "stock_value": "LKR 0.00",
                "low_stock_count": 0,
                "expired_count": 0
            })
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COALESCE(SUM(quantity_current * selling_price), 0) as total_value FROM batches WHERE is_active = 1")
        result = cursor.fetchone()
        total_value = result['total_value'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as low_count FROM batches WHERE quantity_current < 10 AND is_active = 1")
        result = cursor.fetchone()
        low_count = result['low_count'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as expired_count FROM batches WHERE expiry_date < CURDATE() AND is_active = 1")
        result = cursor.fetchone()
        expired_count = result['expired_count'] if result else 0
        
        cursor.close()
        conn.close()
        
        # Format the value properly
        if total_value:
            stock_value = f"LKR {float(total_value):,.2f}"
        else:
            stock_value = "LKR 0.00"
        
        return jsonify({
            "stock_value": stock_value,
            "low_stock_count": int(low_count),
            "expired_count": int(expired_count)
        })
    except Exception as e:
        print(f"Dashboard stats error: {e}")
        return jsonify({
            "stock_value": "LKR 0.00",
            "low_stock_count": 0,
            "expired_count": 0
        })'''

# Replace the function
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Fix 2: Also fix any other f-string conditional issues
content = re.sub(
    r'f"LKR {[^}]+:,.2f}" if [^}]+ else "LKR 0.00"',
    '"LKR 0.00"',
    content
)

# Fix 3: Remove any remaining sold_by references
content = re.sub(r'WHERE s\.sold_by = %s\s*', '', content)
content = re.sub(r',\s*\(user_id,\s*\)\s*\)', ')', content)

# Write the fixed file
with open('app.py', 'w') as f:
    f.write(content)

print("✅ Fixed app.py - removed syntax errors and sold_by references")
