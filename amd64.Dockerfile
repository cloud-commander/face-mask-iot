# build: docker build -f amd64.Dockerfile -t cloudcommanderdotnet/face-mask-iot:amd64 --push .

FROM amd64/debian:buster

RUN apt-get update && apt-get install -y wget gnupg usbutils

RUN echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | tee /etc/apt/sources.list.d/coral-edgetpu.list
RUN wget -qO - https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -

RUN apt-get update && apt-get install -y python3-pip pkg-config libedgetpu1-std python3-wget libedgetpu1-std python3-opencv python3-edgetpu python3-scipy

RUN python3 -m pip install https://dl.google.com/coral/python/tflite_runtime-2.1.0.post1-cp37-cp37m-linux_x86_64.whl 

RUN python3 -m pip install flask Werkzeug itsdangerous Jinja2 MarkupSafe Werkzeug imutils scipy opencv-python awscrt awsiotsdk

RUN apt-get autoremove \
    && rm -rf /tmp/* \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /inference

ADD models /inference/models
ADD utils /inference/utils
ADD templates /inference/templates
ADD app /inference/
ADD vol /inference/vol

ENTRYPOINT ["python3", "face-mask-iot.py"]

