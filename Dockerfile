FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies (including python-dotenv)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    flask \
    flask-bcrypt \
    mysql-connector-python \
    numpy \
    pandas \
    scikit-learn \
    scipy \
    joblib \
    sqlalchemy \
    werkzeug \
    python-dotenv

# If you have a requirements.txt, also install from it
# RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create models directory if needed
RUN mkdir -p /app/models

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "-u", "app.py"]
