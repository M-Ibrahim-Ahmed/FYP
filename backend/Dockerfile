# ScamShield Backend
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Copy model and data files from parent context (mounted via docker-compose volumes)
# The rf_phishing_model.pkl and CSV files are mounted as volumes in docker-compose.yml

EXPOSE 5000

CMD ["python", "app.py"]
