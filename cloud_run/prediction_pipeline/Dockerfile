FROM python:3.12-slim

WORKDIR /app

# Copy shared logic
COPY shared /app/shared

# Copy prediction pipeline code
COPY prediction_pipeline/requirements.txt /app/
COPY prediction_pipeline/ /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set entrypoint for Cloud Run Functions Framework
ENV FUNCTION_TARGET=predict
CMD ["functions-framework", "--target=predict", "--port=8080"]
