import cv2
import os
from screen_handler import *
from process_image import *
from control_connection import *
from camera_interfaces import *
from image_saver import *
from live_image_server import LiveImageServer
import time
import optparse
import sys

class Parser:
    def parse(self):
        parser = optparse.OptionParser()
        parser.add_option("-s", "--use_screen", action = "store_true", dest = "use_screen", default = False, help = "run with a screens") 
        parser.add_option("-r", "--dis_con_to_robot", action = "store_false", dest = "con_to_robot", default = True, help = "stop the script from trying to connect to the robot") 
        parser.add_option("-l", "--use_local_file", action = "store_true", dest = "use_local_file", default = False, help = "use a local images instead") 
        parser.add_option("-w", "--dis_write_image", action = "store_false", dest = "write_file", default = True, help = "disable writing images") 
        parser.add_option("-d", "--use_debug", action = "store_true", dest = "use_debug", default = False, help = "show mask, all goals found and disables writing. script will try to connect to a local server instead") 
        parser.add_option("-v", "--verbose", action = "store_true", dest = "verbose", default = False, help = "be verbose") 
        parser.add_option("-c", "--use_single_camera", action = "store_true", dest = "use_single_camera", default = False, help = "use only one camera")

        (options, args) = parser.parse_args()
        use_screen = options.use_screen
        con_to_robot = options.con_to_robot
        use_local_file = options.use_local_file
        write_file = options.write_file
        use_debug = options.use_debug
        verbose = options.verbose
        use_single_camera = options.use_single_camera
        print options
        return use_screen, con_to_robot, use_local_file, write_file, use_debug, verbose, use_single_camera

IMAGE_NAME = "boiler.png"
IMAGE_NAME_2 = "lift_peg.png"
ERROR_IMAGE_NAME = "error_image.png"
SAVE_DIR = "output"
RIO_PORT = 5801
IMAGE_SERVER_PORT = 5802


GOAL_AREA_THRESHOLD = 200
GOAL_FULLNESS_THRESHOLD_LOWER = .1
GOAL_FULLNESS_THRESHOLD_UPPER = 1
GOAL_ASPECT_THRESHOLD_LOWER = 2
GOAL_ASPECT_THRESHOLD_UPPER = 14
GOAL_TARGET_ASPECT_THRESHOLD_LOWER = 1
GOAL_TARGET_ASPECT_THRESHOLD_UPPER = 3
GOAL_TARGET_DISTANCE_FACTOR = 20000
   
GOAL_SELECTION_VALUES = [GOAL_AREA_THRESHOLD,\
                        GOAL_FULLNESS_THRESHOLD_LOWER,\
                        GOAL_FULLNESS_THRESHOLD_UPPER,\
                        GOAL_ASPECT_THRESHOLD_LOWER,\
                        GOAL_ASPECT_THRESHOLD_UPPER,\
                        GOAL_TARGET_ASPECT_THRESHOLD_LOWER,\
                        GOAL_TARGET_ASPECT_THRESHOLD_UPPER,\
                        GOAL_TARGET_DISTANCE_FACTOR]

GEAR_AREA_THRESHOLD = 200
GEAR_FULLNESS_THRESHOLD_LOWER = .6
GEAR_FULLNESS_THRESHOLD_UPPER = 1.4
GEAR_ASPECT_THRESHOLD_LOWER = 0
GEAR_ASPECT_THRESHOLD_UPPER = 2
GEAR_TARGET_ASPECT_THRESHOLD_LOWER = 1.5
GEAR_TARGET_ASPECT_THRESHOLD_UPPER = 2.5
GEAR_TARGET_DISTANCE_FACTOR = 3403
   
GEAR_SELECTION_VALUES = [GEAR_AREA_THRESHOLD,\
                        GEAR_FULLNESS_THRESHOLD_LOWER,\
                        GEAR_FULLNESS_THRESHOLD_UPPER,\
                        GEAR_ASPECT_THRESHOLD_LOWER,\
                        GEAR_ASPECT_THRESHOLD_UPPER,\
                        GEAR_TARGET_ASPECT_THRESHOLD_LOWER,\
                        GEAR_TARGET_ASPECT_THRESHOLD_UPPER,\
                        GEAR_TARGET_DISTANCE_FACTOR]

def main():
    # create SAVE_DIR if it is missing
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    mask_values = [32,209,66,115,255,255]
    parser = Parser()
    use_screen, con_to_robot, use_local_file, write_file, use_debug,\
        verbose, use_single_camera = parser.parse()
    goal = Goal()
    goal_history = GoalHistory()
    live_image_server = LiveImageServer(IMAGE_SERVER_PORT)
    screen = ScreenHandler(mask_values, use_screen)
    image_saver = ImageSaver(SAVE_DIR, write_file)

    camera_1 = camera_2 = None

    # create camera interface classes
    if use_local_file:
        camera_1 = LocalFileCameraInterface(IMAGE_NAME)
        camera_2 = LocalFileCameraInterface(IMAGE_NAME_2)
    elif use_single_camera:
        camera_1 = camera_2 = UsbCameraInterface(0)
    else:
        camera_1 = UsbCameraInterface(1)
        camera_2 = UsbCameraInterface(0)

    # create a class for managing a socket conneciton between the robot and the jetson
    if use_debug:
        ip_address = "127.0.0.1"
    else:
        ip_address = "roborio-3132-frc.local"
    connection = ControlConnection(ip_address, RIO_PORT, con_to_robot)

    time.sleep(2) # wait a moment to allow the camera interfaces to find some images
    camera_1.test_camera() # These set flags as to if the camera is returning images or should be given up on
    camera_2.test_camera()

    print "\n________Finished setting up________\n"


    capture_timestamp = 1
    data = "0,0,0,0\n"

    while True:
        #try:
            # decide if we want to draw all information on the image
            # if the live image server and we are not trying to debug we
            # only draw a dot at the center of each goal and fps/data on the image
            # this also improves performace
            draw_extra = live_image_server.is_image_wanted() or use_debug
            mask_values = screen.update_mask_values(mask_values)
           
            # use the camera the robot needs and the corresponting selection values
            connection.updateDesiredCameraID()

            if connection.wantedCameraID() == "b" and not camera_1.is_broken():
                print "searching for a boiler"
                camera_2.disable()
                camera_1.enable()

                image, capture_timestamp = camera_1.get_image(capture_timestamp)
                image_mask = mask_image(image, mask_values)
                data, image = goal.find_goal(image, image_mask, goal_history,\
                    capture_timestamp, use_screen, draw_extra, verbose, False, GOAL_SELECTION_VALUES)
            
            elif connection.wantedCameraID() == "g" and not camera_2.is_broken():
                print "searching for a gear lift"
                camera_1.disable()
                camera_2.enable()

                image, capture_timestamp = camera_2.get_image(capture_timestamp)
                image_mask = mask_image(image, mask_values)
                data, image = goal.find_goal(image, image_mask, goal_history,\
                    capture_timestamp, use_screen, draw_extra, verbose, True, GEAR_SELECTION_VALUES)
            
            else:
                print "couldn't use a camera by the id of " + connection.wantedCameraID()
                time.sleep(1)
                # the chosen camera is broken or doesn't exist
                # thus send a fail whale to the driverstation and default data to the Rio
                image = image_mask = cv2.imread(ERROR_IMAGE_NAME, 1)
                data = "0,0,0,0\n"                

            if image is None:
                print "null image, continuing"
                time.sleep(1)
                continue

            screen.display_image(image, image_mask, use_debug)
            connection.send(data)
            
            # if we have drawn extra on the image send it to the live image server
            # we reduce the images resolution and convert it to grayscale due to the
            # low badwidth over the fms
            if draw_extra:
                image = resize_gray_image(image, 0.4)
                live_image_server.set_image(image)
                # print(ret) # print out if we were succesfull in writing an image
            else:
                image_saver.give_image(image, capture_timestamp)
                # make sure the image doesn't have any extra drawing on it
                # we want clean images to be able to rerun the script after a match
            sys.stdout.flush()

       # except Exception, e:
       #     print("error in detect_goals.py")
       #     print(e)

if __name__ == "__main__":
    main()
