# Use official Python image
FROM python:3.10-slim

# Set working directory inside container
WORKDIR /app

# Copy everything from folder into container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

ENV FUNCTION_TARGET=train_models
CMD ["functions-framework", "--target=train_models", "--port=8080"]
