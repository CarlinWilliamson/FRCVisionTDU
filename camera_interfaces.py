'''
Handles talking to cameras and loading images in a background thread
for performance.

Some useful tips for dealing with muliple cameras from this CD thread:
  http://www.chiefdelphi.com/forums/showthread.php?t=147026


***IMPORTANT***
To lower the exposure of the Microsoft HD3000 Lifecam install v4l2-ctl
and run the following in a terminal

sudo apt-get install v4l-utils

v4l2-ctl --set-fmt-video=width=640,height=480,pixelformat=1
v4l2-ctl -d /dev/video0 -c brightness=80 -c contrast=0 -c saturation=200 -c white_balance_temperature_auto=0 -c power_line_frequency=2 -c white_balance_temperature=10000 -c sharpness=0 -c exposure_auto=1 -c exposure_absolute=5 -c pan_absolute=0 -c tilt_absolute=0 -c zoom_absolute=0; v4l2-ctl -d /dev/video1 -c brightness=80 -c contrast=0 -c saturation=200 -c white_balance_temperature_auto=0 -c power_line_frequency=2 -c white_balance_temperature=10000 -c sharpness=0 -c exposure_auto=1 -c exposure_absolute=5 -c pan_absolute=0 -c tilt_absolute=0 -c zoom_absolute=0


Solution was found here:
    https://www.chiefdelphi.com/forums/showthread.php?t=145829

Show how much USB bandwith devices are using:
    cat /sys/kernel/debug/usb/devices | grep "B: "
'''

import cv2
import time
import sys
import os
from subprocess import check_output
import threading
import traceback

# handles grabbing images from a usb camera
class UsbCameraInterface(threading.Thread):
    def __init__(self, id):
        threading.Thread.__init__(self)
        self.daemon = True
        self.capture_timestamp = None
        self.image = None
        self.broken = False
        self.ret = None
        self.enabled = True
        self.cap = cv2.VideoCapture(id)
        self.condition = threading.Condition()
        self.start()

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def set_broken(self, state):
        self.broken = state

    def is_broken(self):
        return self.broken

    # Grabs an image from a usb camera and notifies get_image
    def grab_image(self):
        try:
            #print("Trying to grab an image from %s" % self.cap)
            while True:
                capture_timestamp = time.time()
                ret, image = self.cap.read()
                if not ret:
                    print("Failed to get image from camera %s" % self.cap)
                    time.sleep(2)
                    return
                if image is None:
                    print("Got a null image from the camera, trying again")
                    continue
                image = image[0:480, 0:640]
                self.condition.acquire()
                self.capture_timestamp = capture_timestamp
                self.image = image
                self.condition.notify()
                self.condition.release()
        except Exception, e:
            print("Image grab failed: %s" % e)
            traceback.print_exc(file=sys.stdout)
            time.sleep(1)

    # called by the main processing thread to acquire a new image
    def get_image(self, old_timestamp):
        self.condition.acquire()
        if old_timestamp == self.capture_timestamp:
            self.condition.wait()
        self.condition.release()
        return self.image, self.capture_timestamp

    # get an image from the camera and check to make sure it is returning images
    # this may occur when a camera is not present on the robot or if it is already
    # in use
    def test_camera(self):
        ret, image = self.cap.read()
        if image is None:
            print "*************************************************************"
            print "ERROR: Failed to get a image from a camera, disabling it"
            print "*************************************************************"
            self.set_broken(True)

    def run(self):
        while not self.broken:
            if self.enabled:
                self.grab_image()
            else:
                time.sleep(0.005)

# handles grabbing images from a local file specified by image_name
class LocalFileCameraInterface(threading.Thread):
    def __init__(self, image_name):
        threading.Thread.__init__(self)
        self.broken = False
        self.daemon = True
        self.capture_timestamp = None
        self.image = None
        self.image_name = image_name
        self.condition = threading.Condition()
        self.start()

    def enable(self):
        pass

    def disable(self):
        pass

    def set_broken(self, state):
        self.broken = state

    def is_broken(self):
        return self.broken

    # Grabs an image from a usb camera and notifies get_image
    def grab_image(self):
        capture_timestamp = time.time()
        image = cv2.imread(self.image_name, 1)
        image = image[0:480, 0:640]
        self.condition.acquire()
        self.capture_timestamp = capture_timestamp
        self.image = image
        self.condition.notify()
        self.condition.release()

    # called by the main processing thread to acquire a new image
    def get_image(self, old_timestamp):
        self.condition.acquire()
        if old_timestamp == self.capture_timestamp:
            self.condition.wait()
        self.condition.release()
        return self.image, self.capture_timestamp

    # get an image from the camera and check to make sure it is returning images
    # this may occur when a camera is not present on the robot or if it is already
    # in use
    def test_camera(self):
        image = cv2.imread(self.image_name, 1)
        if image is None:
            print "*************************************************************"
            print "ERROR: Failed to get a image from camera_1, disabling it"
            print "*************************************************************"
            self.set_broken(True)

    def run(self):
        while not self.broken:
            time.sleep(1)
            self.grab_image()

# Test only code, streams images from the local camera.
if __name__ == "__main__":
    cap = cv2.VideoCapture(id)
    timestamp = 0
    while(True):
        image, timestamp = cap.get_image(timestamp)
        cv2.imshow('Image', image)
        cv2.waitKey(1)
