import boto3
import os

# Configure AWS credentials (replace with your actual credentials)
aws_access_key_id = ''
aws_secret_access_key = ''
bucket_name = 'weather-data-iot'  # Replace with your bucket name


# Create an S3 client
s3_client = boto3.client(
    's3', 
    aws_access_key_id=aws_access_key_id, 
    aws_secret_access_key=aws_secret_access_key
)

def process_object(object_key):
    """Downloads an object from S3 and prints its content."""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        object_content = response['Body'].read().decode('utf-8', errors='ignore')
        print(f"Content of {object_key}:\n{object_content}\n---")
        # Add your specific processing logic here
    except Exception as e:
       print(f"Error processing {object_key}: {e}")


def scrape_all_s3_objects():
    """Scrapes all objects from the specified S3 bucket."""
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    object_key = obj['Key']
                    print(f"Downloading object: {object_key}")
                    process_object(object_key) 
            else:
                print("Bucket is empty or does not contain any objects")
    except Exception as e:
        print(f"Error listing objects from bucket: {e}")
        
    


if __name__ == '__main__':
    scrape_all_s3_objects()
