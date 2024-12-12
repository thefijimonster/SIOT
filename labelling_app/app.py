from flask import Flask, render_template, jsonify, request
import boto3
import json
import time
import cv2
import os
from datetime import datetime

app = Flask(__name__)

# AWS S3 credentials and bucket info
AWS_ACCESS_KEY = ""
AWS_SECRET_KEY = ""
BUCKET_NAME = "weather-iot-data"

# Initialize S3 client
s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)

# Track session state
session_active = False

# Initialize camera for image capture (we'll use a placeholder as we are not streaming)
camera = cv2.VideoCapture(0)  # Placeholder for actual camera if needed

def upload_image_to_s3(image, label):
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"{label}_{timestamp}.jpg"
    
    # Upload image to the respective bucket (either sitting-down or standing-up)
    bucket_name = f"{label}-data"  # Use sitting-down-data or standing-up-data buckets
    s3.put_object(Body=image, Bucket=bucket_name, Key=filename)
    print(f"Uploaded {filename} to {bucket_name}.")

@app.route('/')
def index():
    global session_active
    return render_template('index.html', session_active=session_active)

@app.route('/start_session', methods=['POST'])
def start_session():
    global session_active
    session_active = True
    return jsonify({"message": "Session started!"})

@app.route('/stop_session', methods=['POST'])
def stop_session():
    global session_active
    session_active = False
    return jsonify({"message": "Session stopped!"})

@app.route('/capture/<label>', methods=['POST'])
def capture(label):
    global session_active
    if not session_active:
        return jsonify({'error': 'Session is not active. Please start the session first.'}), 400

    # Check if the label is valid
    if label not in ['sitting_down', 'standing_up']:
        return jsonify({'error': 'Invalid label'}), 400

    # Capture a snapshot (simulated by grabbing a frame from the camera)
    ret, frame = camera.read()
    if not ret:
        return jsonify({'error': 'Failed to capture image'}), 500

    # Encode the image to JPEG
    _, buffer = cv2.imencode('.jpg', frame)
    image = buffer.tobytes()

    # Upload the image to S3
    upload_image_to_s3(image, label)

    return jsonify({'message': f"Image labeled as '{label}' and uploaded to S3."})

if __name__ == '__main__':
    app.run(debug=True)

