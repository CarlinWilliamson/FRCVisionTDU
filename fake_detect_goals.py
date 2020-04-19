#!/usr/bin/python
'''
Pretend to be the detect_goals.py script and send updates to the robot about the vision target.
Need to do:
  pip install readchar
'''

import math
import os
import readchar
import socket
import sys
import threading
import time

robot_ip = "10.31.32.99"
robot_port = 5800

class Sender(threading.Thread):
        def __init__(self, ip, port):
                threading.Thread.__init__(self)
                self.ip = ip
                self.port = port
                self.data = ""
                self.socket = None
                self.daemon = True # Don't wait for this thread on exit

        def set_send_text(self, text):
                self.data = text

        def run(self):
                while True:
                        # Don't send/reconnect too often
                        time.sleep(0.1)
                        if not self.socket:
                                self.connect()

                        # No connection? Meh, go back to the beginning.
                        if not self.socket:
                                continue

                        # Try to send some data
                        try:
                                self.socket.send(self.data)
                        except Exception, e:
                                self.socket = None

        def connect(self):
                try:
                        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.socket.connect((self.ip,self.port))
                        print("Control connection established")
                except Exception, e:
                        self.socket = None

def updateSender(sender, distance, aim):
        text = "1,%f,%f,0.01\n" % (aim, distance)
        print("Sending: %s" % text)
        sender.set_send_text(text)

UP = '\x1b[A'
DOWN = '\x1b[B'
LEFT = '\x1b[D'
RIGHT = '\x1b[C'
ESC = 27

done = False
# Try talking to the robot.
sender = Sender(robot_ip, robot_port)
sender.start()
distance = 10
pixelsOff = 0
print("Use arrow keys to change the distance and angle")
while not done:
        # Update the message to the robot.
        updateSender(sender, distance, pixelsOff)
        print("Reading a key (q to quit):")
        key = readchar.readkey()
        if key == 'q':
                done = True
        elif key == UP:
                distance += 1
        elif key == DOWN:
                distance -= 1
        elif key == LEFT:
                pixelsOff -= 2
        elif key == RIGHT:
                pixelsOff += 2
        else:
                print("Unknown key %s" % repr(key))
