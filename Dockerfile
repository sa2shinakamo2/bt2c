FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY blockchain blockchain/
COPY config config/

COPY . .

RUN mkdir -p /root/.bt2c/wallets

EXPOSE 8001 26656

CMD ["uvicorn", "blockchain.__main__:app", "--host", "0.0.0.0", "--port", "8081", "--reload"]
