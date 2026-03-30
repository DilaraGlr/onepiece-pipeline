FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY scraper.py .
COPY load_to_bigquery.py .
COPY ocr_pipeline.py .

# PIPELINE_MODE=scraper → lance le scraper
# PIPELINE_MODE=ocr     → lance l'OCR
CMD ["sh", "-c", "\
  if [ \"$PIPELINE_MODE\" = 'ocr' ]; then \
    python -u ocr_pipeline.py; \
  else \
    python -u scraper.py && python -u load_to_bigquery.py; \
  fi"]