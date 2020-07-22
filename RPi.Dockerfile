#Build (on x86): docker buildx build --platform linux/arm/v7 -t YOURDOCKERHUB/image:latest --push .
#Takes ages to build so hold tight!

FROM balenalib/raspberrypi3-debian-python:3.7-latest
#FROM balenalib/raspberry-pi-debian-python:3.7.4

#downloading sources & update
RUN echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add - \
    && apt-get update 

#install libraries for camera and opencv2
RUN apt-get install -y --no-install-recommends build-essential wget  pkg-config libjpeg-dev \ 
    zlib1g-dev python3-scipy libraspberrypi0 libraspberrypi-dev libraspberrypi-doc libraspberrypi-bin \
    libfreetype6-dev libxml2 libopenjp2-7 cmake libatlas-base-dev libjasper-dev libqtgui4 libqt4-test \
    libavformat-dev libswscale-dev libedgetpu1-std python3-opencv python3-edgetpu libssl1.1 libssl-dev make g++ openssl

#downloading library file & install
RUN wget https://dl.google.com/coral/python/tflite_runtime-2.1.0.post1-cp37-cp37m-linux_armv7l.whl \ 
    && pip3 install tflite_runtime-2.1.0.post1-cp37-cp37m-linux_armv7l.whl \
    && rm tflite_runtime-2.1.0.post1-cp37-cp37m-linux_armv7l.whl 

#install web server python libraries
RUN python3 -m pip install flask Werkzeug itsdangerous tornado Jinja2 MarkupSafe Werkzeug imutils awscrt awsiotsdk

RUN apt-get autoremove \
    && rm -rf /tmp/* \
    && rm -rf /var/lib/apt/lists/*

#opencv2 bug on arm (Undefined reference to __atomic)
ENV LD_PRELOAD "/usr/lib/arm-linux-gnueabihf/libatomic.so.1.2.0"

WORKDIR /inference

ADD models /inference/models
ADD utils /inference/utils
ADD templates /inference/templates
ADD app /inference/
ADD vol /inference/vol

ENTRYPOINT ["python3", "face-mask-iot.py"]

#EXPOSE 5000

#set stop signal
#STOPSIGNAL SIGTERM

