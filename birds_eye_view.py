#/usr/bin/python
# Grab an image from a webcam and display it on the screen. Used for a camera
# mounted on a pole looking over the 2016 field.

import cv2
import sys
import time

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Unable to open capture device")
    sys.exit(1)


cap.set(cv2.cv.CV_CAP_PROP_FOURCC, cv2.cv.CV_FOURCC('M', 'J', 'P', 'G'))
#cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 432)
#cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 240)
print cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)
print cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT)

cv2.namedWindow('birds eye', cv2.WINDOW_NORMAL)
start_time = time.time()
frame_num = 0
while True:
    result,image = cap.read()
    current_timestamp = time.time()
    frame_num += 1
    print "fps: %.1f" %(frame_num/(current_timestamp - start_time))

    if not result:
        print("Unable to get an image from the camera")
        time.sleep(1)
        continue
    cv2.imshow('birds eye', image)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        cap.release()
        cv2.destroyAllWindows()
        sys.exit(0)
