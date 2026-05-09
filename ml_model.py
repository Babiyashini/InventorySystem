import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
import joblib
import mysql.connector

class DemandPredictor:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        
    def fetch_training_data(self):
        """Fetch historical sales data from database"""
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="pharmacy_db"
        )
        
        query = """
        SELECT 
            m.id as medicine_id,
            m.name,
            m.price,
            s.quantity_sold,
            s.sale_date,
            DAYOFWEEK(s.sale_date) as day_of_week,
            MONTH(s.sale_date) as month
        FROM sales s
        JOIN medicines m ON s.medicine_id = m.id
        WHERE s.sale_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    
    def prepare_features(self, df):
        """Prepare features for ML model"""
        # Aggregate by medicine and date
        df['date'] = pd.to_datetime(df['sale_date']).dt.date
        
        features = df.groupby(['medicine_id', 'date']).agg({
            'quantity_sold': 'sum',
            'day_of_week': 'first',
            'month': 'first',
            'price': 'first'
        }).reset_index()
        
        return features
    
    def train(self):
        """Train the ML model"""
        print("Fetching training data...")
        data = self.fetch_training_data()
        
        if data.empty:
            print("No training data available")
            return False
            
        print(f"Training with {len(data)} records")
        features = self.prepare_features(data)
        
        X = features[['day_of_week', 'month', 'price']]
        y = features['quantity_sold']
        
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        
        # Save model
        joblib.dump(self.model, 'demand_model.pkl')
        joblib.dump(self.scaler, 'scaler.pkl')
        
        print("Model trained and saved successfully")
        return True
    
    def predict_demand(self, medicine_id, days_ahead=30):
        """Predict demand for specific medicine"""
        # Load model if not loaded
        if not hasattr(self, 'model') or self.model is None:
            self.model = joblib.load('demand_model.pkl')
            self.scaler = joblib.load('scaler.pkl')
        
        # Get medicine details
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="pharmacy_db"
        )
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT price FROM medicines WHERE id = %s", (medicine_id,))
        medicine = cursor.fetchone()
        conn.close()
        
        if not medicine:
            return 0
        
        # Predict for each day
        predictions = []
        for day in range(days_ahead):
            future_date = datetime.now() + timedelta(days=day)
            features = np.array([[
                future_date.weekday() + 1,  # day_of_week
                future_date.month,           # month
                medicine['price']             # price
            ]])
            
            features_scaled = self.scaler.transform(features)
            pred = self.model.predict(features_scaled)[0]
            predictions.append(max(0, pred))  # No negative predictions
        
        return sum(predictions)
    
    def get_reorder_suggestions(self):
        """Get medicines that need reordering"""
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="pharmacy_db"
        )
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, quantity, price 
            FROM medicines 
            WHERE quantity < 20
        """)
        
        low_stock = cursor.fetchall()
        conn.close()
        
        suggestions = []
        for med in low_stock:
            predicted_demand = self.predict_demand(med['id'], 30)
            suggested_qty = max(0, predicted_demand - med['quantity'])
            
            if suggested_qty > 0:
                suggestions.append({
                    'medicine_id': med['id'],
                    'name': med['name'],
                    'current_stock': med['quantity'],
                    'predicted_demand_30d': round(predicted_demand, 0),
                    'suggested_order': round(suggested_qty, 0),
                    'priority': 'High' if med['quantity'] < 10 else 'Medium'
                })
        
        return suggestions

# Run training
if __name__ == "__main__":
    predictor = DemandPredictor()
    predictor.train()
    
    print("\nReorder Suggestions:")
    suggestions = predictor.get_reorder_suggestions()
    for s in suggestions:
        print(f"- {s['name']}: Current={s['current_stock']}, "
              f"Predicted Demand={s['predicted_demand_30d']}, "
              f"Order={s['suggested_order']} ({s['priority']} priority)")