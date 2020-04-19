#!/usr/bin/python
# Implements a basic web server that intercepts some requests for images
# and supplies them from memory.

import SimpleHTTPServer
import SocketServer
import threading
import numpy as np
import cv2
import time

PORT = 5802

'''
Handles communication between the thread that is generating images
and the thread that is serving them.
We normally don't want to draw in the images where the goals are,
but if someone is waiting for an image, then draw on the next one
and supply it.
'''
class ImageSource(object):
    def __init__(self):
        self.condition = threading.Condition()
        self.waiting_for_image = False
        self.img = None

    # waits for the main processing thread to give us an image
    def wait_for_image(self):
        self.condition.acquire()
        self.waiting_for_image = True
        while self.img is None:
            # Block waiting for an image to be given to us.
            self.condition.wait()
        # there is an image available.
        image = self.img
        self.condition.release()
        return image

    # called by the main processing thread to determine if it should give
    # us an image. We draw all information on the images we give to the live
    # image server for debug purposes. Otherwise we draw less for performance and
    # to preserve the images (the ones we write to file)
    def is_image_wanted(self):
        self.condition.acquire()
        image_required = self.waiting_for_image
        self.condition.release()
        return image_required

    # recieves an image from the main processing thread
    def set_image(self, img):
        self.condition.acquire()
        self.img = img
        self.waiting_for_image = False
        self.condition.notify()
        self.condition.release()


'''
Handles HTTP GET requests, supplying live.png from the ImageSource instead of
the file system.
'''
class GetHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    img_src = ImageSource()

    def do_GET(self):
        if "/live.png" in self.path:
            img = self.img_src.wait_for_image()
            #print("Sending live camera image")
            retval,buf = cv2.imencode(".png", img)
            buf = np.array(buf)
            length = len(buf)
            self.send_response(200)
            self.send_header("Content-type", 'image/png')
            self.send_header("Last-Modified", self.date_time_string(time.time()))
            self.end_headers()
            self.wfile.write(buf.tostring())
            return

        return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

'''
Listens on the supplied port and runs a GetHandler for the live.png requests.
'''
class LiveImageServer(threading.Thread):
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.daemon = True
        self.port = port
        self.start_time = time.time()
        self.frame = 0
        self.fps = 0
        self.start()

    def run(self):
        SocketServer.TCPServer.allow_reuse_address = True
        self.httpd = SocketServer.TCPServer(("", self.port), GetHandler)
        print "LiveImageServer serving web requests on port", self.port
        print
        self.httpd.serve_forever()

    # Call to work out if someone is waiting for an image.
    def is_image_wanted(self):
        return GetHandler.img_src.is_image_wanted()

    # Call to supply the image.
    def set_image(self, img):
        #print("setting image")
        GetHandler.img_src.set_image(img)

    # calculates the frequency of where it is called
    def track_fps(self):
        s = time.time() - self.start_time
        self.frame += 1
        self.fps = self.frame/s
        print("save fps %f" %self.fps)

# Test only code, streams images from the local camera.
if __name__ == "__main__":
    ws = LiveImageServer(PORT)
    cap = cv2.VideoCapture(-1)
    while(True):
        ret, frame = cap.read()
        if GetHandler.img_src.is_image_wanted():
            # Normally we'd write on the image here...
            # ...and then make it available to who asked for it.
            GetHandler.img_src.set_image(frame)
        else:
            time.sleep(0.01)
