"""
This class handles the connection between the jetson/pi and the roborio.
It runs its own thread to restart the socket connection if it fails
"""

import threading
import socket
import threading
import time

class ControlConnection(threading.Thread):
    def __init__(self, robot_ip, robot_port, present):
        threading.Thread.__init__(self)
        self.daemon = True
        self.socket = None
        self.robot_ip = robot_ip
        self.robot_port = robot_port
        self.camera_id = "b" # "b" or "g" or "l"
        if present: self.start() # we sometimes don't want to start the thread (-r parser flag)

    # Opens a socket with the robot (currently the laptop running the script)
    def open_connection(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((self.robot_ip, self.robot_port))
            s.settimeout(5)
            # Don't wait for a complete packet before sending.
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.socket = s
            print("Control connection established with: " + self.robot_ip)
        except Exception, e:
	    self.socket = None
            print("Unable to connect to robot: " + self.robot_ip)
            print(e)

    # Sends data to the robot via a socket
    def send(self, data):
        if not self.socket: return
        try:
            self.socket.send(data)
            #print("Sent: " + data)
        except Exception, e:
            print("Error sending data: " + str(e))
            self.socket = None

    # Recieves data from the robot via a socket
    # To switch cameras the robot passes a string to the script through the socket
    def updateDesiredCameraID(self):
        try:
            if not self.socket: return
            # Check for any messages received
            self.socket.settimeout(0)
            new_camera_id = self.socket.recv(10, socket.MSG_DONTWAIT)
            self.socket.settimeout(None)
            print("recieved: %s" % new_camera_id)
            if new_camera_id:
                new_camera_id = new_camera_id[-1]
                if new_camera_id == "b" or new_camera_id == "g":
                    if new_camera_id != self.camera_id:
                        print("Changing to camera %s" % new_camera_id)
                        self.camera_id = new_camera_id
                else:
                    print("unsupported camera id %s" % new_camera_id)
        except Exception, e:
            # A "[Errno 11] Resource temporarily unavailable"
            # is expected here if there is nothing to read.
            # print("Error reading data from control socket: " + str(e))
            pass

    # returns which camera should be used
    def wantedCameraID(self):
        return self.camera_id

    def run(self):
        while True:
            if not self.socket:
                self.open_connection()
            time.sleep(1)
