FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1

# Create directories for data and incoming files
RUN mkdir -p /app/data /app/data/incoming

# Entry point to handle both modes
ENTRYPOINT ["python", "app.py"]
CMD ["--mode", "daemon"]

