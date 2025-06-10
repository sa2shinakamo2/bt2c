FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY blockchain blockchain/
COPY config config/

COPY . .

RUN mkdir -p /root/.bt2c/wallets

EXPOSE 8001 26656

CMD ["uvicorn", "blockchain.__main__:app", "--host", "0.0.0.0", "--port", "8081", "--reload"]
