FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make scripts executable
RUN chmod +x run_validator.py block_creator.py

EXPOSE 8334 9092 8081

# Use a shell script to start both processes
RUN echo '#!/bin/bash\npython run_validator.py & \nsleep 10\npython block_creator.py\n' > start.sh && chmod +x start.sh

CMD ["./start.sh"]
