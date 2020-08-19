
## IoT Greengrass Face Mask Detection

In a previous post, I illustrated the steps required to train your own Tensorlow Lite SSD model to identify masked and unmasked faces. But a model on its own doesn't offer much business value. 

I wanted to build upon the previous work and use the model to create a reference architecture for a detector that could be used out to derive a tangible business benefit.

With many places around the world now mandating the usage of face masks in public areas,  compliance with the rules is an important issue that organisations need to report upon.

### What can be done to help?

Provide to ability to access up to date statistics on face mask usage compliance in an accessible, cost effective and scalable manner.

This would then assist leaders in being able to make appropriate decisions on how to address any issues that arise from lack of compliance in areas under their jurisdiction. 

This project is a Proof of Concept (PoC) for a detection solution that captures whether a person is wearing a mask (*Masked* or *Unmasked*) and in which direction they are traveling (*In* or *Out*), which is defined by a configurable line on the image. 

The solution provides two forms of data output: messages to an MQTT topic containing a JSON payload with the aforementioned variables.  It can also provide a web interface that shows the video output stream for visual inspection of an area.

### Solution Architecture

The following diagram represents the overall architecture of the solution.

AWS Services:
-   [AWS IoT Greengrass](https://aws.amazon.com/greengrass/)
-   [AWS IoT Core](https://aws.amazon.com/iot-core/)
-   [AWS IoT Analytics](https://aws.amazon.com/iot-analytics/)
-   [AWS Glue](https://aws.amazon.com/glue/)
-   [Amazon Quicksight](https://aws.amazon.com/quicksight/)
-   [Amazon S3](http://aws.amazon.com/s3) 
-   [Amazon SageMaker](https://aws.amazon.com/sagemaker/)

Physical hardware:
- Raspberry Pi or x86_64 device/host
- Google Coral USB Edge TPU 
- USB or Network camera

Software:
- [Face Mask Detection](https://github.com/cloud-commander/face-mask-iot) application 
- Docker Engine
- Docker Compose

At this stage, I have configured the services manually via the interface but for a production system, delivered at scale a *CloudFormation* or *CDK* template would be employed. I have been working on those but I have not yet completed them.

![Solution Architecture](https://raw.githubusercontent.com/cloud-commander/face-mask-iot/master/face-mask-detector-diagram.png)


The solution can be thought of as containing three distinct activities:

- Object detection and telemetry transmission on Greengrass
- Data logging, processing and visualisation with IoT Core, Analytics, Glue and Quicksight
- Model retraining on Sagemaker to improve accuracy (optional)

### Walkthrough

####  Object detection 
![Raspberry Pi with Coral USB Edge TPU](https://raw.githubusercontent.com/cloud-commander/face-mask-detection/master/data/rpicoral.jpg)
First we start by configuring the IoT Greengrass device which can either be a Raspberry Pi or an x86_64 host.

There is an excellent guide on the [AWS IoT Greengrass developer guide](https://docs.aws.amazon.com/greengrass/latest/developerguide/gg-gs.html) to I wont repeat that here just go over the high level points.


- Clone [Github repo](https://github.com/cloud-commander/face-mask-iot.git)
- Setup the Rasbperry Pi, dont forget to enable hard/sym links and ggc_user/group
- Install the latest version of [Docker engine](https://docs.docker.com/install/) and [Docker Compose](https://docs.docker.com/compose/install/) on your Pi
- Make sure you add ggc_user to Docker group `sudo usermod -aG docker ggc_user`
- The Greengrass group role should be configured to allow the s3:GetObject action on the S3 bucket that contains your Compose file

- Create a Greengrass group and core on IOT Core
- Download the security resources 
- Transfer the resources to the your Pi using _scp_ command
- Download the Greengrass software to your Pi and extract
- Extract security resources into your Greengrass folder
- Update _config.json_ file with the correct file paths for your Greengrass folder
- Start the Greengrass process
- Within the Greengrass group on IoT Core, add a device/Thing 
- Download the security resources for your device/Thing
- Create Thing folder on Pi; e.g. */home/pi/Thing*
- Dont forget to download the CA certificate for your core and Thing
- Edit *docker-compose.yml* to reflect the Thing folder location
- Add the [Docker Application Deployment connector](https://docs.aws.amazon.com/greengrass/latest/developerguide/docker-app-connector.html) and select the Docker Compose file from the GitHub page that you have stored in an S3 bucket
- Add a subscription with the Docker Application Deployment as the source and IoT Cloud as the target
- Make sure you have the *config.ini* file with the correct settings in your Thing folder
- Deploy the Greengrass group on IoT Core
- On IoT Core, click on Test and Subscribe to the topic *face-mask/detections* to see the incoming messages
- You can also view the video feed from the detector by going to the IP address of the detector on port 5000.

At the heart of the detection process is a python script that utilises a TensorFlow Lite model, trained to perform object detection on images of masked and unmasked faces. 

I wanted to keep this solution as low cost as possible and to make sure of readily available hardware which led me to the Raspberry Pi. Unfortunately however the Pi isnt powerful enough to perform inference on its own at a usable speed. Which is where the Coral USB Edge TPU comes into provide an affordable way of accelerating inference speeds for TensorFlow Lite models.

The TPU however requires multiple external libraries and has several other dependency issues which make it challenging to employ as part of a Lambda function. Therefore, I decided to package the objection detection python script along with all the required dependencies into a Docker image.

The Docker image is also configured as a Greengrass device so that is able to transmit back the telemetry via MQTT. You supply the container the necessary credentials so it can communicate back to the AWS Cloud. 

You can also configure the settings on the detector via the `config.ini` file which lets you choose a variety of settings such as where on the screen the counting line should appear, which direction counts as *in* or *out*, if you wish to use a different object detection model than the provided one, if you want use a usb webcam or a network camera etc.

####  Data processing and visualisation 

##### IoT Analytics
- It is advisable to run the `generate_test_data.py` script first to assist you (you will need boto3 configured)
- Go to quick start and give a name and  `face-mask/detections` as the topic filter which should now create your channel, pipeline, data store and data set
- Go to the data set you created and click edit on the SQL query then test query to make sure it is receiving data. Click save
- Click on add schedule and set an interval. Lets go with 5 mins.
- Click on content delivery rules and select an S3 location in which to store the CSV files
- Click run now on the data set and then go to the S3 bucket you specified to confirm that CSV files were saved

![](https://raw.githubusercontent.com/cloud-commander/face-mask-iot/master/screenshots/Capture15_200723051528.png)

##### Quicksight
- Click on new analysis and  new dataset then select AWS IoT Analytics and the data set you just created
- You need to filter the data as required and you will end up with a chart showing you the total number of masked and unmasked people at a location separated into In and Out directions.

![Solution Architecture](https://raw.githubusercontent.com/cloud-commander/face-mask-iot/master/screenshots/chart_200723051536.png)

#####  Retrain model
I am not going to go into how to retrain a model on Sagemaker as that is a post all by itself, perhaps I will revisit it though in the future.
