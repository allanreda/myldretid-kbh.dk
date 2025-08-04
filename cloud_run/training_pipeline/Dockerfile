FROM python:3.12-slim

WORKDIR /app

# Copy shared logic
COPY shared /app/shared

# Copy training pipeline code
COPY training_pipeline/requirements.txt /app/
COPY training_pipeline/ /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set entrypoint for Cloud Run Functions Framework
ENV FUNCTION_TARGET=train_models
CMD ["functions-framework", "--target=train_models", "--port=8080"]
