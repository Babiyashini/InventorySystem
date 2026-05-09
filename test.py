from flask import Flask, jsonify
import mysql.connector

app = Flask(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'pharmacy_db'
}

@app.route('/')
def home():
    return "Flask is working!"

@app.route('/get-users-test')
def get_users_test():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, role FROM users LIMIT 5")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(users)

if __name__ == '__main__':
    app.run(debug=True, port=5001)