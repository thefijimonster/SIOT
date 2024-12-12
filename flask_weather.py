import boto3
import json
from flask import Flask, render_template
import plotly.graph_objects as go
import plotly.offline as py
import pandas as pd
from datetime import datetime

# Configure AWS credentials (replace with your actual credentials)
aws_access_key_id = ''
aws_secret_access_key = ''
bucket_name = 'weather-data-iot'


app = Flask(__name__)

# Create an S3 client
s3_client = boto3.client(
    's3', 
    aws_access_key_id=aws_access_key_id, 
    aws_secret_access_key=aws_secret_access_key
)

def process_object(object_key):
    """Downloads an object from S3 and parses its JSON content."""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        object_content = response['Body'].read().decode('utf-8', errors='ignore')
        data = json.loads(object_content)

        # Convert 'timestamp' to datetime, handling "Unknown"
        timestamp = data.get('timestamp')
        if timestamp != "Unknown":
             timestamp = datetime.fromisoformat(timestamp)
        data['timestamp'] = timestamp
        
        return data
    except Exception as e:
        print(f"Error processing {object_key}: {e}")
        return None

def scrape_all_s3_objects():
    """Scrapes all objects from the specified S3 bucket and returns data."""
    all_data = []
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)

        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    object_key = obj['Key']
                    print(f"Processing object: {object_key}")
                    object_data = process_object(object_key)
                    if object_data:
                         all_data.append(object_data)
            else:
                print("Bucket is empty or does not contain any objects")
    except Exception as e:
        print(f"Error listing objects from bucket: {e}")
    return all_data


def create_plot(all_data):
        """Creates a Plotly graph from the scraped data."""
        if not all_data:
             return "No data to display"

        df = pd.DataFrame(all_data)
        #Convert timestamp column to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        #drop na values
        df.dropna(subset = 'timestamp', inplace=True)

        # Sort values by time.
        df.sort_values(by='timestamp', inplace=True)
        
        fig = go.Figure()

        # Function to add a trace to the figure for the given attribute
        def add_attribute_trace(attribute, color):
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df[attribute],
                                    mode='lines',
                                    name=attribute,
                                    line=dict(color=color)))
        
        add_attribute_trace('temperature', 'red')
        add_attribute_trace('humidity', 'blue')
        add_attribute_trace('wind_gust', 'green')
        add_attribute_trace('precipitation', 'purple')
        add_attribute_trace('cloud_cover', 'orange')


        fig.update_layout(
            title='Weather Attributes over Time',
            xaxis_title='Time',
            yaxis_title='Value',
            hovermode='x unified'
        )
        return py.plot(fig, output_type='div')

@app.route('/')
def index():
    all_data = scrape_all_s3_objects()
    plot_div = create_plot(all_data)
    return render_template('index.html', plot_div=plot_div)

if __name__ == '__main__':
    app.run(debug=True)
