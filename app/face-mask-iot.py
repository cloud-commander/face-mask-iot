
from utils.centroidtracker import CentroidTracker
from utils.trackableobject import TrackableObject
from utils.tracking import track_objects, draw_bounding_boxes
from imutils.video import VideoStream
from imutils.video import FPS

from flask import Flask, render_template, Response
from edgetpu.detection.engine import DetectionEngine
from edgetpu.utils import dataset_utils

from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder

from PIL import Image

import numpy as np
import configparser
import imutils
import time
import cv2
import threading
import datetime
import os
import json


# load config file
config = configparser.ConfigParser()

config.read('vol/config.ini')

# get config file values
model = config['DETECTION']['model']
labels = config['DETECTION']['labels']
orientation = config['COUNTER']['orientation']
inDirection = config['COUNTER']['inDirection']
confidence = float(config['DETECTION']['confidence'])
coord = int(config['COUNTER']['coord'])
endpoint = config['IOT-DEVICE']['endpoint']
client_id = config['IOT-DEVICE']['client_id']
path_to_cert = config['IOT-DEVICE']['path_to_cert']
path_to_key = config['IOT-DEVICE']['path_to_key']
path_to_root = config['IOT-DEVICE']['path_to_root']
my_topic = config['IOT-DEVICE']['topic']

# Spin up resources
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint=endpoint,
    cert_filepath=path_to_cert,
    pri_key_filepath=path_to_key,
    client_bootstrap=client_bootstrap,
    ca_filepath=path_to_root,
    client_id=client_id,
    clean_session=False,
    keep_alive_secs=6
)
# Make the connect() call
connect_future = mqtt_connection.connect()
# Future.result() waits until a result is available
connect_future.result()


lock = threading.Lock()
engine = DetectionEngine(model)
labels = dataset_utils.read_label_file(labels)

ct1 = CentroidTracker(maxDisappeared=600, maxDistance=900)
ct2 = CentroidTracker(maxDisappeared=600, maxDistance=900)

app = Flask(__name__)

print(config.has_option("APP", "input"))

if config['APP']['input'] == "webcam":
    print("[INFO] starting video stream...")
    vs = VideoStream(src=0).start()
    time.sleep(2.0)
    vidcap = False
else:
    print("[INFO] opening network camera or video file...")
    vidcap = True
    vs = cv2.VideoCapture(config['APP']['input'])


# start the frames per second throughput estimator
fps = FPS().start()


@app.route("/")
def index():
    return render_template("index.html")


def detect_objects():

    global cap, outputFrame, lock

    # initialize the total number of frames processed thus far, along
    # with the total number of objects that have moved either up or down
    totalFrames = 0

    # individial count to be sent across MQTT
    count_unmasked = []
    count_masked = []

    # list to display totals locally
    totals_unmasked = [0, 0]
    totals_masked = [0, 0]

    trackableObjects_unmasked = {}
    trackableObjects_masked = {}

    (H, W) = (None, None)

    while True:

        # grab the next frame and handle if we are reading from either
        # VideoCapture or VideoStream
        frame = vs.read()
        if vidcap:
            frame = frame[1]
        else:
            frame

        frame = imutils.resize(frame, width=480)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        prepimg = Image.fromarray(rgb)

        ans = engine.detect_with_image(
            prepimg,
            threshold=confidence,
            keep_aspect_ratio=True,
            relative_coord=False,
            top_k=20)

        # if the frame dimensions are empty, set them
        if W is None or H is None:
            (H, W) = frame.shape[:2]

        if orientation == "V":
            line_pt1 = (coord, 0)
            line_pt2 = (coord, H)
        elif orientation == "H":
            line_pt1 = (0, coord)
            line_pt2 = (W, coord)

        # Draw dividing line
        cv2.line(frame, (line_pt1), (line_pt2), (0, 255, 255), 2)

        # initialise variables
        rects_unmasked = []
        rects_masked = []
        payload = {}
        payload['deviceID'] = client_id

        # loop through detections
        if ans:
            for obj in ans:

                if obj.label_id == 0:
                    rects_unmasked, frame = draw_bounding_boxes(
                        obj, labels, frame, rects_unmasked)
                elif obj.label_id == 1:
                    rects_masked, frame = draw_bounding_boxes(
                        obj, labels, frame, rects_masked)

        objects_unmasked = ct1.update(rects_unmasked)
        objects_masked = ct2.update(rects_masked)

        trackableObjects_unmasked, count_unmasked = track_objects(
            objects_unmasked, trackableObjects_unmasked, orientation, coord, inDirection)
        trackableObjects_masked, count_masked = track_objects(
            objects_masked, trackableObjects_masked, orientation, coord, inDirection)

        if count_unmasked[0]:
            payload['maskState'] = "Unmasked"
            payload['personDirection'] = "In"
            payload['dateTime'] = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S")
            mqtt_connection.publish(topic=my_topic, payload=json.dumps(
                payload), qos=mqtt.QoS.AT_LEAST_ONCE)
            totals_unmasked[0] += count_unmasked[0]
        if count_unmasked[1]:
            payload['maskState'] = "Unmasked"
            payload['personDirection'] = "Out"
            payload['dateTime'] = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S")
            mqtt_connection.publish(topic=my_topic, payload=json.dumps(
                payload), qos=mqtt.QoS.AT_LEAST_ONCE)
            totals_unmasked[1] += count_unmasked[1]
        if count_masked[0]:
            payload['maskState'] = "Masked"
            payload['personDirection'] = "In"
            payload['dateTime'] = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S")
            mqtt_connection.publish(topic=my_topic, payload=json.dumps(
                payload), qos=mqtt.QoS.AT_LEAST_ONCE)
            totals_masked[0] += count_masked[0]
        if count_masked[1]:
            payload['maskState'] = "Masked"
            payload['personDirection'] = "Out"
            payload['dateTime'] = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S")
            mqtt_connection.publish(topic=my_topic, payload=json.dumps(
                payload), qos=mqtt.QoS.AT_LEAST_ONCE)
            totals_masked[1] += count_masked[1]

        # Build screen text output
        text_masked = "IN: {} OUT: {}".format(
            totals_masked[0], totals_masked[1])
        cv2.putText(frame, text_masked, (W-120, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        text_unmasked = "IN: {} OUT: {}".format(
            totals_unmasked[0], totals_unmasked[1])
        cv2.putText(frame, text_unmasked, (W-120, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # grab the current timestamp and draw it on the frame
        timestamp = datetime.datetime.now()
        cv2.putText(frame, timestamp.strftime("%d/%m/%y %H:%M:%S"), (W-120, H - 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 2)

        # increment the total number of frames processed thus far and
        # then update the FPS counter
        totalFrames += 1
        fps.update()

        # stop the timer and display FPS information
        fps.stop()
        # print("[INFO] elapsed time: {:.2f}".format(fps.elapsed()))
        # print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

        with lock:
            outputFrame = cv2.resize(frame, (640, 480))


def generate():

    global outputFrame, lock

    while True:
        with lock:
            if outputFrame is None:
                continue

            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

            if not flag:
                continue

        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
              bytearray(encodedImage) + b'\r\n')


@ app.route("/video_feed")
def video_feed():
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == '__main__':
    t = threading.Thread(target=detect_objects)
    t.daemon = True
    t.start()
    app.run(host=config['APP']['host'], port=config['APP']['port'], debug=True,
            threaded=True, use_reloader=False)

disconnect_future = mqtt_connection.disconnect()
disconnect_future.result()
vs.stop()
cv2.destroyAllWindows()
