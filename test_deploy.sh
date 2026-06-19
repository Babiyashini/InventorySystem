#!/bin/bash
echo "Testing deployment script..."

cd /home/ec2-user/InventorySystem

# Build
docker build -t pharmacy-app .

# Stop old container
docker stop pharmacy-app 2>/dev/null || true
docker rm pharmacy-app 2>/dev/null || true

# Run with RDS
docker run -d \
  --name pharmacy-app \
  -p 5000:5000 \
  -e DB_HOST='pharmacy-inventory-dev-db.cmnkiqqqcwe5.us-east-1.rds.amazonaws.com' \
  -e DB_USER='pharmacy_admin' \
  -e DB_PASSWORD='YOUR_ACTUAL_PASSWORD' \
  -e DB_NAME='pharmacy_db' \
  --restart unless-stopped \
  pharmacy-app

sleep 5

# Test
if curl -s http://localhost:5000/check-flask | grep -q "Flask is alive"; then
  echo "Success!"
else
  echo "Failed!"
  docker logs pharmacy-app --tail 20
fi
