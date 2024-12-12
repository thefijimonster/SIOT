Project Overview
This project lets you visualize weather data and stream live video from a camera. It fetches weather data from AWS S3, displays it in different time intervals, and captures images tagged as "sitting_down" or "standing_up." These images are uploaded to specific S3 buckets.

Files
API.py
Handles the backend logic. It fetches weather data from AWS, processes it, and provides routes for starting/stopping the camera session, capturing images, and uploading them to S3. It also generates weather plots based on the data.

app.py
The main Flask app. It serves the weather data and camera feed to the web interface, allowing users to select different weather attributes and granularity. It also supports capturing and uploading images.

index.html
The front-end page that displays the weather plot, live camera feed, and controls for adjusting the weather granularity, cloud cover, and session states. Users can also capture images with the session active.

camera_livestream.py
Streams the live video from the camera using Picamera2, providing real-time video for the user interface.

flask_weather.py
Integrates Flask with the weather data logic, handling the retrieval and processing of weather data and generating the visualizations that are displayed on the web page.

get_weather.py
Fetches and processes weather data from AWS S3, allowing it to be displayed in different granularities (e.g., minute, hour, day).

requirements.txt
Lists all the Python packages required to run the project, including Flask, Boto3 (for AWS S3), OpenCV, and more.
