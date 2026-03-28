FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY scraper.py .
COPY load_to_bigquery.py .

# -u pour unbuffered output (logs en temps réel)
CMD ["sh", "-c", "python -u scraper.py && python -u load_to_bigquery.py"]