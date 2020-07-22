# Script to generate simulated IoT device parameters data

import json
import random
import datetime
import boto3
import time

my_topic = "face-mask/detections"
device = ['Shrewsbury', 'London', 'Manchester', 'Barcelona',
            'Munich', 'Seattle', 'New York', 'Singapore', 'Tokyo', 'Paris']
state = ['Masked', 'Unmasked']
direction = ['In', 'Out']

iot = boto3.client('iot-data')

# generate values
def getValues():
    data = {}
    data['deviceID'] = random.choice(device)
    data['maskState'] = random.choice(state)
    data['personDirection'] = random.choice(direction)
    data['dateTime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return data


# Generate data input
while True:
    time.sleep(random.randint(0, 3))
    rnd = random.random()
    data = json.dumps(getValues())
    print(data)
    response = iot.publish(topic=my_topic, payload=data, qos=0)
