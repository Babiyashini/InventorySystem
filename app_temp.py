import os
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
from functools import wraps
import mysql.connector
import pandas as pd
from datetime import datetime, date, timedelta
import json
import warnings
warnings.filterwarnings('ignore')
from ml_advanced import AdvancedDemandPredictor

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# =====================================================
# DATABASE CONFIGURATION - FIXED
# =====================================================
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'pharmacy-inventory-dev-db.cmnkiqqqcwe5.us-east-1.rds.amazonaws.com'),
    'user': os.environ.get('DB_USER', 'pharmacy_admin'),
    'password': os.environ.get('DB_PASSWORD', 'YourStrongPassword2024!'),
    'database': os.environ.get('DB_NAME', 'pharmacy_db')
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as err:
        print(f"Database Connection Error: {err}")
        return None

# Rest of your routes go here...
# (Copy your existing routes)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
