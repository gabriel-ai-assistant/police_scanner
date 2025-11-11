FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything including jobs/
COPY . .

CMD ["python", "scheduler.py"]
