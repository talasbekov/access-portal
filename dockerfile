# Use the official Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables for timezone
ENV TZ=Asia/Yekaterinburg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc build-essential tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy requirements file
COPY ./requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY ./sql_app ./sql_app

# Expose the port the app runs on
EXPOSE 8000

# Run the Uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
