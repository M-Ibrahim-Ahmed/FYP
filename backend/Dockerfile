# ScamShield Backend
FROM python:3.11-slim

# Live log output in Docker
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=3 -r requirements.txt

# Copy backend source code
COPY backend/ .

# Copy model and data files from project root
COPY rf_phishing_model.pkl .
COPY url_features_extracted1.csv .
COPY ["blacklist_dataset_cleaned (2).csv", "."]

EXPOSE 5000

# Use gunicorn for production, fallback to Flask dev server
CMD ["python", "app.py"]
