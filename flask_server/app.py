from flask import Flask, render_template, jsonify, request, Response
import boto3
import json
import matplotlib.pyplot as plt
import io
import base64
import re
import cv2
from datetime import datetime
import pandas as pd

app = Flask(__name__)

# AWS credentials and bucket names
AWS_ACCESS_KEY = ""
AWS_SECRET_KEY = ""
WEATHER_BUCKET_NAME = "weather-data-iot"
SITTING_BUCKET_NAME = "sitting-down-data"
STANDING_BUCKET_NAME = "standing-up-data"

# Initialize S3 client
s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)

# Camera setup for image capture
camera = cv2.VideoCapture(0)

# Session state
session_active = False

# Extract timestamp from S3 file name
def extract_timestamp_from_filename(filename):
    match = re.match(r"weather_data_(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})\.json", filename)
    if match:
        year, month, day, hour, minute, second = match.groups()
        return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
    return None

# Fetch weather data from S3
def fetch_data_from_s3():
    files = s3.list_objects_v2(Bucket=WEATHER_BUCKET_NAME)
    data = []
    for file in files.get('Contents', []):
        file_key = file['Key']
        timestamp = extract_timestamp_from_filename(file_key)
        if timestamp:
            response = s3.get_object(Bucket=WEATHER_BUCKET_NAME, Key=file_key)
            file_content = response['Body'].read().decode('utf-8')
            json_data = json.loads(file_content)
            json_data["timestamp"] = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            data.append(json_data)
    return data

# Low-pass filter for smoothing the data
def low_pass_filter(data, cloud_cover):
    alpha = cloud_cover / 100
    filtered_data = []
    for i in range(len(data)):
        if i == 0:
            filtered_data.append(data[i])
        else:
            smoothed_value = alpha * data[i] + (1 - alpha) * filtered_data[i-1]
            filtered_data.append(smoothed_value)
    return filtered_data

# Aggregate data based on granularity (minute, hour, day)
def aggregate_data(weather_data, granularity):
    df = pd.DataFrame(weather_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    if granularity == 'hour':
        return df.resample('H').mean()
    elif granularity == 'day':
        return df.resample('D').mean()
    return df

# Create plot for a given weather attribute
def create_plot(weather_data, weather_attribute, granularity):
    df_resampled = aggregate_data(weather_data, granularity)
    plt.figure(figsize=(10, 6))
    plt.plot(df_resampled.index, df_resampled[weather_attribute], label=weather_attribute, marker='o')
    plt.xlabel('Timestamp')
    plt.ylabel(weather_attribute.capitalize())
    plt.title(f'{weather_attribute.capitalize()} Over Time (Granularity: {granularity.capitalize()})')

    # Customize x-axis tick formatting based on granularity
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

# Upload image to the appropriate S3 bucket (sitting or standing)
def upload_image_to_s3(image, label):
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"{label}_{timestamp}.jpg"
    bucket_name = SITTING_BUCKET_NAME if label == "sitting_down" else STANDING_BUCKET_NAME
    s3.put_object(Body=image, Bucket=bucket_name, Key=filename)

# Routes
@app.route('/')
def index():
    global session_active
    granularity = request.args.get('granularity', 'minute')
    weather_data = fetch_data_from_s3()
    cloud_cover = weather_data[-1].get('cloud_cover', 50)  # Use latest cloud cover value
    plot_url = create_plot(weather_data, 'temperature', granularity)

    return render_template('index.html', plot_url=plot_url, weather_data=weather_data, default_attribute='temperature', granularity=granularity, cloud_cover=cloud_cover)

@app.route('/plot/<attribute>')
def plot(attribute):
    granularity = request.args.get('granularity', 'minute')
    weather_data = fetch_data_from_s3()
    plot_url = create_plot(weather_data, attribute, granularity)
    return jsonify({'plot_url': plot_url})

# Start session for image capture
@app.route('/start_session', methods=['POST'])
def start_session():
    global session_active
    session_active = True
    return jsonify({"message": "Session started!"})

# Stop session for image capture
@app.route('/stop_session', methods=['POST'])
def stop_session():
    global session_active
    session_active = False
    return jsonify({"message": "Session stopped!"})

# Capture image for sitting-down or standing-up
@app.route('/capture/<label>', methods=['POST'])
def capture(label):
    global session_active
    if not session_active:
        return jsonify({'error': 'Session is not active. Please start the session first.'}), 400

    if label not in ['sitting_down', 'standing_up']:
        return jsonify({'error': 'Invalid label'}), 400

    ret, frame = camera.read()
    if not ret:
        return jsonify({'error': 'Failed to capture image'}), 500

    _, buffer = cv2.imencode('.jpg', frame)
    image = buffer.tobytes()

    upload_image_to_s3(image, label)

    return jsonify({'message': f"Image labeled as '{label}' and uploaded to S3."})

# Video feed route for live camera stream
@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            ret, frame = camera.read()
            if not ret:
                break
            _, jpeg = cv2.imencode('.jpg', frame)
            frame = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)

