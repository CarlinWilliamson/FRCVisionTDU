class cameraNames:
  def __init__(self):
    self.cameras={}
    self.cameraString = check_output("""/bin/sh /var/www/html/vision/camera_enumeration""", shell=True)
    self.cameraLines = self.cameraString.split("\n")
    for i in self.cameraLines:
      if i != '':
        s=i.split(' ', 1)
        self.cameras[int(s[0])] = s[1]

  def getCameras(self):
    return self.cameras

  def getCameraIndex(self, name):
    for i in self.cameras:
      if self.cameras[i].find(name) != -1:
        return i
    return -1
