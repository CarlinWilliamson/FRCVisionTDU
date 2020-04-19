'''
Pretends to be the robot by sending and revieving data from a vision script
Use numberkeys to change cameras
Need to do:
  sudo pip install readchar
'''

import socket 
import readchar
import threading
import time
import sys

class Sender(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True # Don't wait for this thread on exit
        self.client = None
        self.start()

    def update_client(self, new):
    	print "new client"
    	self.client = new

    def run(self):
    	while True:
    	    if self.client:
                data = client.recv(size)
                print(data)
                print
            else:
                time.sleep(1)

client = 0
backlog = 5 
size = 2048
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('127.0.0.1',5801))
s.listen(backlog)
sender = Sender()

print("bound and listening")
while True:
    while not client:
        client, address = s.accept()
        sender.update_client(client)
        print("accepted")

    key = sys.stdin.readline()
    key = key[0]
    if key == "q":
        sys.exit(0)
    client.send(key)
