FROM python:3.12-slim

WORKDIR /app
COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./
COPY frontend/ /frontend/
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers 2 --access-logfile - --error-logfile -"]
