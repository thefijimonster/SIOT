from flask import Flask, Response, render_template, jsonify, request
from picamera2 import Picamera2
import time
import cv2
import io
import numpy as np
import boto3
import json
import matplotlib.pyplot as plt
import base64
import re
from datetime import datetime
import pandas as pd

app = Flask(__name__)

# AWS S3 credentials and bucket info
AWS_ACCESS_KEY = ""
AWS_SECRET_KEY = ""
BUCKET_NAME = "weather-data-iot"

# Initialize S3 client
s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)

# Initialize Picamera2
picam2 = Picamera2()
camera_config = picam2.create_preview_configuration(main={"format": 'RGB888', "size": (1920, 1080)}) # Use main with a larger size
picam2.configure(camera_config)
picam2.start()
time.sleep(1)

FPS = 10  # Target FPS
SLEEP_DURATION = 1 / FPS


def extract_timestamp_from_filename(filename):
    match = re.match(r"weather_data_(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})\.json", filename)
    if match:
        year, month, day, hour, minute, second = match.groups()
        return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
    return None


def fetch_data_from_s3():
    files = s3.list_objects_v2(Bucket=BUCKET_NAME)
    data = []
    for file in files.get('Contents', []):
        file_key = file['Key']
        timestamp = extract_timestamp_from_filename(file_key)
        if timestamp:
            response = s3.get_object(Bucket=BUCKET_NAME, Key=file_key)
            file_content = response['Body'].read().decode('utf-8')
            json_data = json.loads(file_content)
            json_data["timestamp"] = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            data.append(json_data)
    return data


def low_pass_filter(data, cloud_cover):
    alpha = cloud_cover / 100
    filtered_data = []
    for i in range(len(data)):
        if i == 0:
            filtered_data.append(data[i])
        else:
            smoothed_value = alpha * data[i] + (1 - alpha) * filtered_data[i - 1]
            filtered_data.append(smoothed_value)
    return filtered_data


def aggregate_data(weather_data, granularity):
    df = pd.DataFrame(weather_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    if granularity == 'hour':
        df_resampled = df.resample('H').mean()
    elif granularity == 'day':
        df_resampled = df.resample('D').mean()
    else:
        df_resampled = df
    return df_resampled


def create_plot(weather_data, weather_attribute, granularity):
    df_resampled = aggregate_data(weather_data, granularity)
    plt.figure(figsize=(10, 6))
    plt.plot(df_resampled.index, df_resampled[weather_attribute], label=weather_attribute, marker='o')
    plt.xlabel('Timestamp')
    plt.ylabel(weather_attribute.capitalize())
    plt.title(f'{weather_attribute.capitalize()} Over Time (Granularity: {granularity.capitalize()})')

    if granularity == 'day':
        plt.xticks(df_resampled.index, df_resampled.index.strftime('%Y-%m-%d'), rotation=45)
    elif granularity == 'hour':
        plt.xticks(df_resampled.index, df_resampled.index.strftime('%Y-%m-%d %H:%M'), rotation=45)
    else:
        plt.xticks(df_resampled.index, df_resampled.index.strftime('%Y-%m-%d %H:%M:%S'), rotation=45)

    plt.grid(True)

    img_stream = io.BytesIO()
    plt.savefig(img_stream, format='png')
    img_stream.seek(0)
    plot_url = base64.b64encode(img_stream.getvalue()).decode('utf-8')
    plt.close()

    return plot_url


def generate_frames():
    while True:
        array = picam2.capture_array()
        ret, buffer = cv2.imencode('.jpg', array)
        if not ret:
            break
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(SLEEP_DURATION)  # Adjust sleep time for desired frame rate


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/')
def index():
    granularity = request.args.get('granularity', 'minute')
    cloud_cover = request.args.get('cloud_cover', 50, type=int)

    # Fetch weather data from S3
    weather_data = fetch_data_from_s3()
    
    # Apply low-pass filter to the temperature data based on cloud cover
    filtered_temperature = low_pass_filter([data['temperature'] for data in weather_data], cloud_cover)
    
    # Generate weather plot
    plot_url = create_plot(weather_data, 'temperature', granularity)

    return render_template('index.html', plot_url=plot_url, weather_data=weather_data, default_attribute='temperature', granularity=granularity, cloud_cover=cloud_cover)


@app.route('/plot/<attribute>')
def plot(attribute):
    granularity = request.args.get('granularity', 'minute')
    cloud_cover = request.args.get('cloud_cover', 50, type=int)

    # Fetch weather data from S3
    weather_data = fetch_data_from_s3()
    
    # Apply low-pass filter to the temperature data based on cloud cover
    filtered_temperature = low_pass_filter([data['temperature'] for data in weather_data], cloud_cover)
    
    # Generate the plot for the selected attribute
    plot_url = create_plot(weather_data, attribute, granularity)
    
    return jsonify({'plot_url': plot_url})


if __name__ == '__main__':
    app.run(debug=True)

