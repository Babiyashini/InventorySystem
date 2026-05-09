"""
Advanced Machine Learning Model for Pharmacy Demand Forecasting
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import mysql.connector
from datetime import datetime, timedelta
import warnings
import os

warnings.filterwarnings('ignore')

class AdvancedDemandPredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None
        self.model_path = 'models/advanced_demand_model.pkl'
        self.scaler_path = 'models/advanced_scaler.pkl'
        
        if not os.path.exists('models'):
            os.makedirs('models')
    
    def get_db_connection(self):
        try:
            conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="pharmacy_db"
            )
            return conn
        except mysql.connector.Error as err:
            print(f"Database Error: {err}")
            return None
    
    def fetch_historical_data(self):
        conn = self.get_db_connection()
        if not conn:
            return pd.DataFrame()
        
        query = """
        SELECT 
            s.id as sale_id,
            s.medicine_id,
            m.name as medicine_name,
            m.price,
            s.quantity_sold,
            s.sale_price,
            s.sale_date,
            DAYOFWEEK(s.sale_date) as day_of_week,
            MONTH(s.sale_date) as month,
            WEEK(s.sale_date) as week_of_year,
            DAYOFMONTH(s.sale_date) as day_of_month,
            QUARTER(s.sale_date) as quarter,
            YEAR(s.sale_date) as year,
            CASE WHEN DAYOFWEEK(s.sale_date) IN (1,7) THEN 1 ELSE 0 END as is_weekend
        FROM sales s
        JOIN medicines m ON s.medicine_id = m.id
        WHERE s.sale_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    
    def create_features(self, df):
        if df.empty:
            return df, []
        
        df = df.sort_values(['medicine_id', 'sale_date']).copy()
        
        # Create lag features
        df['sales_lag_7'] = df.groupby('medicine_id')['quantity_sold'].shift(7).fillna(0)
        df['sales_lag_14'] = df.groupby('medicine_id')['quantity_sold'].shift(14).fillna(0)
        df['sales_lag_30'] = df.groupby('medicine_id')['quantity_sold'].shift(30).fillna(0)
        
        # Rolling averages
        df['sales_ma_7'] = df.groupby('medicine_id')['quantity_sold'].transform(
            lambda x: x.rolling(window=7, min_periods=1).mean()
        ).fillna(0)
        
        df['sales_ma_30'] = df.groupby('medicine_id')['quantity_sold'].transform(
            lambda x: x.rolling(window=30, min_periods=1).mean()
        ).fillna(0)
        
        # Price ratio
        df['price_ratio'] = df['price'] / df.groupby('medicine_id')['price'].transform('mean')
        df['price_ratio'] = df['price_ratio'].fillna(1)
        
        # Select features (removed season columns to avoid mismatch)
        feature_cols = [
            'day_of_week', 'month', 'week_of_year', 'day_of_month', 
            'quarter', 'price', 'is_weekend', 
            'sales_lag_7', 'sales_lag_14', 'sales_lag_30',
            'sales_ma_7', 'sales_ma_30', 'price_ratio'
        ]
        
        return df, feature_cols
    
    def train(self):
        print("=" * 60)
        print("🚀 Training Advanced Demand Prediction Model")
        print("=" * 60)
        
        df = self.fetch_historical_data()
        
        if df.empty:
            print("❌ No sales data found!")
            return False
        
        print(f"✅ Fetched {len(df)} sales records")
        print(f"   Unique medicines: {df['medicine_id'].nunique()}")
        
        df, feature_cols = self.create_features(df)
        
        X = df[feature_cols].fillna(0)
        y = df['quantity_sold']
        
        self.feature_names = feature_cols
        
        print(f"   Training samples: {len(X)}")
        
        if len(X) < 10:
            print("⚠️ Not enough data for advanced model. Need at least 10 samples.")
            return False
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        print(f"   Training set: {len(X_train)} samples")
        print(f"   Test set: {len(X_test)} samples")
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        print("\n🤖 Training Random Forest model...")
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        print("\n📈 MODEL PERFORMANCE:")
        print(f"   Mean Absolute Error: {mae:.2f} units")
        print(f"   Root Mean Square Error: {rmse:.2f} units")
        print(f"   R² Score: {r2:.4f}")
        
        # Save model
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        joblib.dump(self.feature_names, 'models/feature_names.pkl')
        
        print(f"\n✅ Model saved to: {self.model_path}")
        return True
    
    def load_model(self):
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                self.feature_names = joblib.load('models/feature_names.pkl')
                print("✅ Model loaded successfully")
                return True
            else:
                print("⚠️ No trained model found")
                return False
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def predict_medicine_demand(self, medicine_id, days=30):
        if self.model is None:
            if not self.load_model():
                return None
        
        conn = self.get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT m.price, m.name, COALESCE(SUM(b.quantity_current), 0) as current_stock
            FROM medicines m
            LEFT JOIN batches b ON m.id = b.medicine_id AND b.is_active = 1
            WHERE m.id = %s
            GROUP BY m.price, m.name
        """, (medicine_id,))
        
        medicine = cursor.fetchone()
        conn.close()
        
        if not medicine:
            return None
        
        # Simple prediction based on average sales
        conn = self.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT AVG(quantity_sold) as avg_daily
            FROM sales
            WHERE medicine_id = %s AND sale_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """, (medicine_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        daily_avg = result['avg_daily'] if result and result['avg_daily'] else 0
        
        total_demand = daily_avg * days
        
        return {
            'medicine_id': medicine_id,
            'medicine_name': medicine['name'],
            'current_stock': medicine['current_stock'],
            'daily_average': round(daily_avg, 2),
            'predicted_demand_30d': round(total_demand, 0),
            'suggested_order': max(0, round(total_demand - medicine['current_stock'], 0)),
            'days_until_stockout': round(medicine['current_stock'] / daily_avg) if daily_avg > 0 else 999
        }
    
    def get_all_predictions(self):
        conn = self.get_db_connection()
        if not conn:
            return []
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT DISTINCT id FROM medicines WHERE is_active = 1")
        medicines = cursor.fetchall()
        conn.close()
        
        predictions = []
        for med in medicines:
            pred = self.predict_medicine_demand(med['id'])
            if pred:
                predictions.append(pred)
        
        predictions.sort(key=lambda x: x['days_until_stockout'])
        return predictions
    
    def generate_insights_report(self):
        print("\n" + "=" * 60)
        print("📊 ADVANCED ML INSIGHTS REPORT")
        print("=" * 60)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        predictions = self.get_all_predictions()
        
        if not predictions:
            print("\n⚠️ No predictions available")
            return
        
        critical = [p for p in predictions if p['days_until_stockout'] < 7]
        urgent = [p for p in predictions if 7 <= p['days_until_stockout'] < 14]
        
        print(f"\n🚨 CRITICAL ITEMS (< 7 days left): {len(critical)}")
        for item in critical:
            print(f"   • {item['medicine_name']}: {item['current_stock']} units left, "
                  f"{item['days_until_stockout']} days remaining")
            print(f"     Suggested Order: {item['suggested_order']} units")
        
        print(f"\n⚠️ URGENT ITEMS (7-14 days left): {len(urgent)}")
        for item in urgent:
            print(f"   • {item['medicine_name']}: {item['current_stock']} units left, "
                  f"{item['days_until_stockout']} days remaining")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    predictor = AdvancedDemandPredictor()
    predictor.train()
    predictor.generate_insights_report()