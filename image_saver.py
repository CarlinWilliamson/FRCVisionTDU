'''
Write sample images to disk.

As the robot will sometimes sit on the field for up to 20 minutes before
the match starts we need to be careful how many images we keep.

We are currently saving one image per second.

Hence we write files of the format saved.0/capture_goal_%d.png where
%d is a number from 0 to 300, will give us five minutes before it
starts overwriting the first images.

This way we only keep the last five minutes of images, so we shouldn't
loose anything if we get to the robot within two minutes of the match
finishing and turn it off.

Then to prevent the next boot up from overwriting them again, on
startup we move the "saved.0" directory to saved.1, but before we do
that we move saved.1 to saved.2 and so on for 5 directories.

This way we can wait for four starts before losing images. Ideally
we would copy images off after every match.

Even better would be to write them to a USB key, but this didn't happen
in time for Sydney

'''

import cv2
import numpy as np
import os
import threading
import time
import shutil



MIN_TO_SAVE = 5
IMAGES_PER_SEC = 60
NUM_DIRS_TO_KEEP = 30 # Number of restarts to keep files around.
NUM_FILES_TO_KEEP = MIN_TO_SAVE * IMAGES_PER_SEC

class ImageSaver(threading.Thread):
    def __init__(self, save_dir, present):
        threading.Thread.__init__(self)
        self.condition = threading.Condition()
        self.daemon = True
        self.save_dir = save_dir
        self.image = None
        self.capture_timestamp = 0
        self.written_timestamp = 0
        self.file_number = 0
        self.rename_directories()
        if present: self.start()

    # called by the main processing thread to give it images
    def give_image(self, image, capture_timestamp):
        if not capture_timestamp - IMAGES_PER_SEC/60 > self.written_timestamp:
            return
        self.condition.acquire()
        self.image = np.copy(image)
        self.capture_timestamp = capture_timestamp
        self.condition.notify()
        self.condition.release()

    # Saves image to a specified directory making sure they are at least 1 second appart
    def maybe_write_image(self):
        self.condition.acquire()
        # block until we are given a new image
        self.condition.wait()
        image = self.image
        self.written_timestamp = self.capture_timestamp
        self.condition.release()
        
        filename = os.path.join(self.get_dir_path(0), "capture_goal_%03d.png" % self.file_number)
        cv2.imwrite(filename, image)
        self.file_number += 1
        self.file_number %= NUM_FILES_TO_KEEP

    def run(self):
        while True:
                self.maybe_write_image()

    def get_dir_path(self, dir_num):
        return os.path.join(self.save_dir, "saved.%d" % dir_num)

    """
    Rename saved.(N) to saved.(N+1) while only keeping NUM_DIRS_TO_KEEP.
    If NUM_DIRS_TO_KEEP=5, the first directory is saved.0 and the last directory
     is saved.4
    """
    def rename_directories(self):
        # Remove the oldest.
        try:
            shutil.rmtree(self.get_dir_path(NUM_DIRS_TO_KEEP - 1))
        except OSError, e:
            # This is likely fine.
            print("Possibly expected error when deleting old directory: %s" % e)
        # Move everyone else up a directory.
        dir_num = NUM_DIRS_TO_KEEP - 1
        while dir_num > 0:
            source = self.get_dir_path(dir_num - 1)
            destination = self.get_dir_path(dir_num)
            print("Renaming directory %s to %s" % (source, destination))
            dir_num -= 1
            try:
                shutil.move(source, destination)
            except IOError, e:
                print("Possibly expected error when renaming directory: %s" % e)
                # Try the next directory
        print
        # Make the first directory
        os.mkdir(self.get_dir_path(0))
