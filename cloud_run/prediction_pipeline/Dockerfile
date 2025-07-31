# Use official Python image
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Copy everything from the shared folder
COPY ../shared /app/shared
# Copy everything from folder into container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Declares which function handles HTTP requests
ENV FUNCTION_TARGET=predict

# Starts the Functions Framework server to listen on port 8080
CMD ["functions-framework", "--target=predict", "--port=8080"]
 