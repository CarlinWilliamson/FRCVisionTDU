import cv2
import numpy as np
import math
import time


class ScreenHandler():
    def __init__(self, mask_values, present):
        self.present = present
        if present:
            cv2.namedWindow('Image', cv2.WINDOW_NORMAL)
            cv2.resizeWindow('Image', 640, 480)
            self.create_trackbars(mask_values)


    # Creates windows and trackbars allowing for tuning mask values
    def create_trackbars(self, mask_values):
        cv2.namedWindow('Trackbars', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Trackbars', 640, 480)

        cv2.createTrackbar('H1', 'Trackbars', mask_values[0], 255, self.nothing)
        cv2.createTrackbar('S1', 'Trackbars', mask_values[1], 255, self.nothing)
        cv2.createTrackbar('V1', 'Trackbars', mask_values[2], 255, self.nothing)
        cv2.createTrackbar('H2', 'Trackbars', mask_values[3], 255, self.nothing)
        cv2.createTrackbar('S2', 'Trackbars', mask_values[4], 255, self.nothing)
        cv2.createTrackbar('V2', 'Trackbars', mask_values[5], 255, self.nothing)

    #For trackbars. Don't ask. Don't worry
    def nothing(self, x):
        pass

    # Gets positions of trackbars and changes the mask values
    def update_mask_values(self, mask_values):
        if self.present:
            mask_values[0] = cv2.getTrackbarPos('H1', 'Trackbars')
            mask_values[1] = cv2.getTrackbarPos('S1', 'Trackbars')
            mask_values[2] = cv2.getTrackbarPos('V1', 'Trackbars')
            mask_values[3] = cv2.getTrackbarPos('H2', 'Trackbars')
            mask_values[4] = cv2.getTrackbarPos('S2', 'Trackbars')
            mask_values[5] = cv2.getTrackbarPos('V2', 'Trackbars')
        return mask_values

    def display_image(self, image, image_mask, use_debug):
        if self.present:
            cv2.imshow('Image', image)
            if use_debug:
                cv2.imshow('Mask', image_mask)
            cv2.waitKey(10)