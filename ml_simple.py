"""
Simple ML Model for Pharmacy Demand Forecasting
Works with minimal data
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import joblib
import mysql.connector
from datetime import datetime, timedelta
import os

class SimpleDemandPredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = 'models/simple_demand_model.pkl'
        self.scaler_path = 'models/simple_scaler.pkl'
        
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
    
    def fetch_data(self):
        conn = self.get_db_connection()
        if not conn:
            return pd.DataFrame()
        
        query = """
        SELECT 
            s.medicine_id,
            m.name as medicine_name,
            s.quantity_sold,
            s.sale_date,
            DAYOFWEEK(s.sale_date) as day_of_week,
            MONTH(s.sale_date) as month
        FROM sales s
        JOIN medicines m ON s.medicine_id = m.id
        WHERE s.sale_date >= DATE_SUB(NOW(), INTERVAL 90 DAY)
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    
    def train(self):
        print("=" * 60)
        print("🚀 Training Simple Demand Prediction Model")
        print("=" * 60)
        
        df = self.fetch_data()
        
        if df.empty:
            print("❌ No sales data found!")
            return False
        
        print(f"✅ Found {len(df)} sales records")
        print(f"   Medicines: {df['medicine_id'].nunique()}")
        
        # Calculate average sales per medicine
        avg_sales = df.groupby('medicine_id')['quantity_sold'].mean().reset_index()
        avg_sales.columns = ['medicine_id', 'avg_daily_sales']
        
        print(f"✅ Calculated average daily sales for {len(avg_sales)} medicines")
        
        # Simple model - just store averages
        self.model = avg_sales
        
        # Save model
        joblib.dump(self.model, self.model_path)
        
        print(f"\n✅ Model saved to: {self.model_path}")
        print("\n📊 Model is ready for predictions!")
        return True
    
    def predict_demand(self, medicine_id, days=30):
        """Predict demand based on historical averages"""
        if self.model is None:
            self.model = joblib.load(self.model_path)
        
        medicine_data = self.model[self.model['medicine_id'] == medicine_id]
        
        if medicine_data.empty:
            return None
        
        daily_avg = medicine_data['avg_daily_sales'].iloc[0]
        total_demand = daily_avg * days
        
        # Get current stock
        conn = self.get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT quantity FROM medicines WHERE id = %s", (medicine_id,))
        stock = cursor.fetchone()
        conn.close()
        
        current_stock = stock['quantity'] if stock else 0
        
        return {
            'medicine_id': medicine_id,
            'predicted_demand_30d': round(total_demand, 0),
            'daily_average': round(daily_avg, 2),
            'current_stock': current_stock,
            'suggested_order': max(0, round(total_demand - current_stock, 0)),
            'days_until_stockout': round(current_stock / daily_avg) if daily_avg > 0 else 999
        }
    
    def get_all_predictions(self):
        """Get predictions for all medicines"""
        if self.model is None:
            self.model = joblib.load(self.model_path)
        
        predictions = []
        for _, row in self.model.iterrows():
            pred = self.predict_demand(row['medicine_id'])
            if pred:
                predictions.append(pred)
        
        return predictions

if __name__ == "__main__":
    predictor = SimpleDemandPredictor()
    predictor.train()
    
    print("\n" + "=" * 60)
    print("📊 PREDICTIONS:")
    print("=" * 60)
    
    predictions = predictor.get_all_predictions()
    for p in predictions:
        print(f"\nMedicine ID: {p['medicine_id']}")
        print(f"  Daily Average: {p['daily_average']} units/day")
        print(f"  Current Stock: {p['current_stock']} units")
        print(f"  Predicted 30-day Demand: {p['predicted_demand_30d']} units")
        print(f"  Suggested Order: {p['suggested_order']} units")