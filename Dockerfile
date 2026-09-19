FROM python:3.11-slim

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir .

# Cloud hosts inject $PORT; default to 8000 locally.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "python -m prehype serve --port ${PORT:-8000}"]
