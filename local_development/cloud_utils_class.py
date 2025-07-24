from google.cloud import bigquery, storage
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CloudUtils:
    def __init__(self, bq_client, storage_client):
        self.bq_client = bq_client
        self.storage_client = storage_client
    
    # Function to fetch historical weather and traffic data from BigQuery
    def pull_historical_data(self, sql_query):
        try:
            # Define SQL query
            query = sql_query

            # Run the query and fetch data from BigQuery
            query_job = self.bq_client.query(query)

            # Convert to DataFrame
            raw_df = query_job.to_dataframe()

            # Ensure dataframe exists and actually contains data
            if not raw_df.empty:
                logger.info(f"Succesfully fetched {len(raw_df)} rows of historical data from BigQuery")
                return raw_df
            
        except Exception as e:
            logger.error(f"Error occured when fetching historical data from BigQuery: {e}")
            return None
        
    def upload_to_gcs(self, buffer, bucket_name, gcs_folder_name, filename, filetype):
        try:
            # Reset pointer to start
            buffer.seek(0)
            # Define bucket, folder and filename
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(f"{gcs_folder_name}/{filename}.{filetype}")
            # Upload blob
            blob.upload_from_file(buffer, content_type='application/octet-stream')

            logger.info(f"Successfully uploaded file: {filename}.{filetype} to folder: {gcs_folder_name} in bucket: {bucket_name}.")
        
        except Exception as e:
            logger.error(f"Error occured when uploading file: {filename}.{filetype} to folder: {gcs_folder_name} in bucket: {bucket_name}: {e}")
