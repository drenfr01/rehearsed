FROM python:3.13-slim

WORKDIR /app
RUN mkdir -p /app/backend
COPY . /app/backend
WORKDIR /app/backend

RUN apt update && apt install -y libpq-dev

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"