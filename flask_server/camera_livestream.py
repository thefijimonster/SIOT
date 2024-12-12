from flask import Flask, Response
from picamera2 import Picamera2
import time
import cv2
import io
import numpy as np

app = Flask(__name__)

# Initialize Picamera2
picam2 = Picamera2()
camera_config = picam2.create_preview_configuration(main={"format": 'RGB888', "size": (1920, 1080)}) # Use main with a larger size
picam2.configure(camera_config)
picam2.start()
time.sleep(1)


FPS = 10 # Target FPS
SLEEP_DURATION = 1/FPS


def generate_frames():
    while True:
        array = picam2.capture_array()
        ret, buffer = cv2.imencode('.jpg', array)
        if not ret:
            break
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(SLEEP_DURATION) # Adjust sleep time for desired frame rate

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
    picam2.close()
