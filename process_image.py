import cv2
import numpy as np
import math
import time


"""""""""""""""""""""
IMAGE PROCESSING
"""""""""""""""""""""

# returns the height and width of an image
def cal_image_size(image):
    height, width, channels = image.shape
    return (width,height)

# applies a hsv mask to an image 
def mask_image(image, mask_values):
    if image is None:
        print("Trying to convert a null image")
    image_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lc = np.array([mask_values[0], mask_values[1], mask_values[2]])
    hc = np.array([mask_values[3], mask_values[4], mask_values[5]])
    image_mask = cv2.inRange(image_hsv, lc, hc)
    return image_mask
    
# changes the resolution of an image and converts it to grayscale
# used to improve framerate when streaming back to the driver station
def resize_gray_image(image, factor):
    image = cv2.resize(image, (0,0), fx=factor, fy=factor)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image

"""""""""""""""""""""
GOAL HISTORY
"""""""""""""""""""""
# This class remembers information from previous goals and allows for
# the averaging of dist, aim, age, lock and thresholding of lock.

AVERAGE_DIST_OVER = 1 # Currently don't do any averaging
AVERAGE_AIM_OVER = 1 # Currently don't do any averaging
AVERAGE_LOCK_OVER = 1 # Currently don't do any averaging
AVERAGE_AGE_OVER = 1 # Currently don't do any averaging
AVERAGE_SKEW_OVER = 1 # Currently don't do any averaging
LOCK_THRESHOLD = 50 # as a percentage 0-100

class GoalHistory():
    def __init__(self):
        self.frame_num = 0
        self.start_time = time.time()
        self.oldest = 0

        self.lock_history = [0]*AVERAGE_LOCK_OVER
        self.lock_index = 0
        self.aim_history = [0]*AVERAGE_AIM_OVER
        self.aim_index = 0
        self.dist_history = [0]*AVERAGE_DIST_OVER
        self.dist_index = 0
        self.age_history = [0]*AVERAGE_AGE_OVER
        self.age_index = 0
        self.skew_history = [0]*AVERAGE_SKEW_OVER
        self.skew_index = 0

    # calculates the:
    # age: how long since the image was taken
    # fps: the frequency at which we are processing images
    # oldest: the slowest time to process an image this run of the script (used for debug)
    def cal_goal_history(self, capture_timestamp):
        current_timestamp = time.time()
        age = round(current_timestamp - capture_timestamp, 10)
        self.frame_num = self.frame_num + 1
        fps = self.frame_num/(current_timestamp - self.start_time)
        if age > self.oldest:
            self.oldest = age
        return age, fps, self.oldest

    def cal_data(self, lock, aim, dist, age, skew):
        l = 0
        if lock: l = 100

        self.lock_history[self.lock_index] = l
        self.aim_history[self.aim_index] = aim
        self.dist_history[self.dist_index] = dist
        self.age_history[self.age_index] = age
        self.skew_history[self.skew_index] = skew

        self.lock_index += 1
        self.aim_index += 1
        self.dist_index += 1
        self.age_index += 1
        self.skew_index += 1
        
        self.lock_index %= AVERAGE_LOCK_OVER
        self.aim_index %= AVERAGE_AIM_OVER
        self.dist_index %= AVERAGE_DIST_OVER
        self.age_index %= AVERAGE_AGE_OVER
        self.skew_index %= AVERAGE_SKEW_OVER

        data_lock = 0
        data_aim = 0
        data_dist = 0
        data_skew = 0 
        if (sum(self.lock_history) / AVERAGE_LOCK_OVER > LOCK_THRESHOLD):
            data_lock = 1
            data_aim = sum(self.aim_history) / AVERAGE_AIM_OVER
            data_dist = sum(self.dist_history) / AVERAGE_DIST_OVER
            data_skew = sum(self.skew_history) / AVERAGE_SKEW_OVER
        data_age = sum(self.age_history) / AVERAGE_AGE_OVER
        return "%d,%f,%f,%f,%f\n" % (data_lock, data_aim, data_dist, data_skew, data_age)

# Tracks score and xy coordinate
class Corner():
    def __init__(self):
        self.xy = []
        self.score = -10000
    def update_score(self, X, Y, score):
        if score > self.score:
            self.xy = [X,Y]
            self.score = score


"""""""""""""""""""""
GOAL PROCESSING
"""""""""""""""""""""
# finds vision targets in masked image

VIRTICAL_FOV_LIFECAM = 33.58
HORIZONTAL_FOV_LIFECAM = 59.7
GOAL_HEIGHT_RELATIVE = 84 - 19.4 # virtical distance between the camera and the goal
CAMERA_ANGLE_OF_ELEVATION = 30 * (math.pi / 180)
PIXELS_PER_DEGREE = 0.171/1.8
AIM_CORRECTION_DEGREES = 0 # 7 # The camera maybe off-centred with the robot

class Goal():
    def find_goal(self, image, image_mask, goal_history, capture_timestamp,\
    	    use_screen, draw_extra, verbose, duel_target, selection_values):
        self.area1 = 0
        self.area2 = 0
        self.corners1 = [[0,0],[0,0],[0,0],[0,0]]
        self.corners2 = [[0,0],[0,0],[0,0],[0,0]]

        lock = False
        data = '0,0,0,0\n'
        aim = 0
        distance = 0
        skew = 0

        image_size = cal_image_size(image)

        # find any contours (edges between the white and black on the masked image)
        contours = find_contours(image_mask)
        for contour in contours:

            # If the contour is too small then ignore it
            area = cal_contour_area(contour)
            if area < selection_values[0]:
            	if verbose:
                    print("bad size %.1f" %area)
                continue

            # If there isn't a significant portion of the area of the contour's corners then it cant be a U shape
            corners = cal_corners(contour) # narrows down a contour to a the coordinates of four corners
            corner_area = cal_corner_area(corners)
            
            # make sure corner_area is not 0 to avoid a division by zero error
            if (corner_area == 0):
                if verbose:
                    print("corner_area == 0")
                continue    

            if area/corner_area < selection_values[1] or area/corner_area > selection_values[2]:
                if verbose:
                    print "bad fullness %.1f" %(area/corner_area)
                continue

            # If it has a completly incorrect aspect ratio then ignore it
            avg_width, avg_height = cal_avg_height_width(corners)
            aspect_ratio = cal_aspect_ratio(avg_width, avg_height)
            if aspect_ratio < selection_values[3] or aspect_ratio > selection_values[4]:
                if verbose:
                    print("bad aspect ratio %.1f" %aspect_ratio)
                continue


            # Save the two largest vision targets found
            if area > self.area1:
                self.area1 = self.area2
                self.corners1 = self.corners2
                self.area2 = area
                self.corners2 = corners
            elif area > self.area2:
                self.area2 = area
                self.corners2 = corners

            goal_center = cal_goal_center(corners[0], avg_width, avg_height)
            draw_goal_center(image, goal_center) # we draw the centers of all goals so we can see which ones we found after the match (on the saved images)
            if draw_extra == True: # draw more information if this image will be sent back to the driverstation
                draw_areas(image, contour, area, corner_area, corners)
                draw_aspect_ratio(image, aspect_ratio, goal_center)

        age, fps, oldest = goal_history.cal_goal_history(capture_timestamp)
        draw_age_fps(image, age, fps, oldest)

        if draw_extra: draw_image_center(image, image_size) # we usually don't want to draw too much information on the images otherwise they become unusable as debug after a match

        # If we have found two correctly sized vision targets combine them and find useful data to send back to te robot
        if self.area1 > 0 and self.area2 > 0 and duel_target:
            # combine the two contours
            target_contour = np.array([[self.corners1[0]],[self.corners1[1]],[self.corners1[2]],[self.corners1[3]],\
                [self.corners2[0]],[self.corners2[1]],[self.corners2[2]],[self.corners2[3]]])
            # run cal_corners again to find the four outermost corners of the target
            target_corners = cal_corners(target_contour)

            target_avg_width, target_avg_height = cal_avg_height_width(target_corners)
            target_aspect_ratio = cal_aspect_ratio(target_avg_width, target_avg_height)
            # If it has a completly incorrect aspect ratio then ignore it
            if target_aspect_ratio > selection_values[5] and target_aspect_ratio < selection_values[6]:
                
                target_goal_center = cal_goal_center(target_corners[0], target_avg_width, target_avg_height)
                aim = cal_aim(image_size, target_goal_center)
                
                if (selection_values[7] > 0):
                    distance = cal_distance(target_avg_height, selection_values[7])
                    skew = cal_goal_skew(target_corners, distance, selection_values[7])
                else:
                    distance = cal_distance_position(image_size, target_goal_center)
                
                if draw_extra: draw_rectangle_offset(image, target_corners, 5) # we usually don't want to draw too much information on the images otherwise they become unusable as debug after a match

                draw_goal_center(image, target_goal_center, (0,255,255), 15)
                draw_aim_distance(image, aim, distance)
                lock = True
            elif verbose: print("bad target aspect ratio %.1f" %target_aspect_ratio)

        # For singular targets
        if (self.area1 > 0 or self.area2 > 0) and not duel_target:
            distance = cal_distance(avg_width, selection_values[7])
            aim = cal_aim(image_size, goal_center)
            if draw_extra: draw_rectangle_offset(image, corners, 5) # we usually don't want to draw too much information on the images otherwise they become unusable as debug after a match
            draw_goal_center(image, goal_center, (0,255,255), 15)
            draw_aim_distance(image, aim, distance)
            lock = True

        data = goal_history.cal_data(lock, aim, distance, age, skew)    
        if verbose:
            print(data)

        print("fps: %.1f" %fps)
        return data, image

# Finds outermost contours (edges between black and white on a masked image)
def find_contours(image_mask):
    ret, thresh = cv2.threshold(image_mask, 0, 255, 0)
    _, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Change cv2.RETR_EXTERNAL to cv2.RETR_TREE to find all contours
    return contours

# takes a contour and finds the four outermost corners
# returns their coordinates in an array
def cal_corners(contour):
    TL_corner = Corner()
    TR_corner = Corner()
    BL_corner = Corner()
    BR_corner = Corner()
    # go through each point and see if it is a better corner then the last
    for point in contour:
        x = point[0][0] # +ve is more right.
        y = point[0][1] # +ve is more down
        TL_corner.update_score(x, y, -x -y)
        TR_corner.update_score(x, y, +x -y)
        BL_corner.update_score(x, y, -x +y)
        BR_corner.update_score(x, y, +x +y)
    TL = TL_corner.xy
    TR = TR_corner.xy
    BL = BL_corner.xy
    BR = BR_corner.xy
    return [TL, TR, BL, BR]

# calculates the area inside a contour
def cal_contour_area(contour):
    area = cv2.contourArea(contour)
    return area

# calculates the area inside of four corners
def cal_corner_area(corners):
    TL = corners[0]
    TR = corners[1]
    BL = corners[2]
    BR = corners[3]
    corner_contour = np.array([[corners[0], corners[2], corners[3], corners[1]]])
    corner_area = cv2.contourArea(corner_contour)
    return corner_area

# calculates the distance between two points using Pythagoras' Theorm
def cal_point_distance(p, q):
    c = math.sqrt((p[0] - q[0])**2 + (p[1] - q[1])**2)
    return c

# calculates the skew of the target (left_height/right_height)
def cal_goal_skew(corners, center_distance, distance_factor):
    HALF_WIDTH_GEAR_TARGET = 5.125 # IRL in inches

    TL = corners[0]
    TR = corners[1]
    BL = corners[2]
    BR = corners[3]
    left_side_length = cal_point_distance(TL, BL)
    right_side_length = cal_point_distance(TR, BR)

    left_side_distance = cal_distance(left_side_length, distance_factor)
    left_acute_angle = cal_cosine_rule_deg(center_distance, HALF_WIDTH_GEAR_TARGET, left_side_distance)

    right_side_distance = cal_distance(left_side_length, distance_factor)
    right_acute_angle = cal_cosine_rule_deg(center_distance, HALF_WIDTH_GEAR_TARGET, right_side_distance)
    avg_angle = (left_acute_angle + (180 - right_acute_angle))/2
    return 90 - avg_angle

# calculates the angle in a triangle of known lengths
# adj1 and adj2 are the adjacent sides to the angle
# opposite is the opposite angle to the the desired angle
def cal_cosine_rule_deg(adj1,adj2,opposite):
    adj1_sqrd = math.pow(adj1, 2)
    adj2_sqrd = math.pow(adj2, 2)
    opposite_sqrd = math.pow(opposite, 2)
    if (abs((adj1_sqrd + adj2_sqrd - opposite_sqrd)/(2*adj1*adj2)) >1 ):
        #print "error in cal_cosine_rule_deg() opposite_sqd = %f" %opposite_sqrd
        return 0
    return math.degrees(math.acos((adj1_sqrd + adj2_sqrd - opposite_sqrd)/(2*adj1*adj2)))


# calculates the length of each side then the average width and height
def cal_avg_height_width(corners):
    TL = corners[0]
    TR = corners[1]
    BL = corners[2]
    BR = corners[3]
    top_side_length = cal_point_distance(TL, TR)
    bot_side_length = cal_point_distance(BL, BR)
    left_side_length = cal_point_distance(TL, BL)
    right_side_length = cal_point_distance(TR, BR)
    avg_height = (left_side_length + right_side_length)/2
    avg_width = (top_side_length + bot_side_length)/2
    return avg_width, avg_height

# calculates the center of the goal assuming it is a rectangle
def cal_goal_center(TL, avg_width, avg_height):
    goal_center = (TL[0] + int(avg_width / 2), TL[1] + int(avg_height / 2))
    return goal_center

# calculates the aspect ratio (width/height)
def cal_aspect_ratio(avg_width, avg_height):
    aspect_ratio = avg_width/avg_height
    return aspect_ratio

# Calculates distance to the goal based on the pixel height and real height
def cal_distance(dependent_var, factor):
    """Use this code to calibrate factor
    1.Change "DISTANCE" to the camera's current distance away from the goal
    2.Run program and average the first ten console outputs
        
    DISTANCE = 82
    FACTOR = DISTANCE*dependent_var
    print "%d" %FACTOR
    """    
    distance = round((factor/dependent_var), 1)
    #print(distance)
    return distance

# calculates the angle between the camera and the target
def cal_distance_position(image_size, goal_center):
    image_center = image_size[1]/2
    image_height = image_size[1]
    
    degrees_per_pixel = VIRTICAL_FOV_LIFECAM/image_height
    pixel_height = image_size[1] - goal_center[1]

    elevation_angle = (degrees_per_pixel * pixel_height - (VIRTICAL_FOV_LIFECAM/2)) * (math.pi/180) + CAMERA_ANGLE_OF_ELEVATION
    horizontal_distance = (GOAL_HEIGHT_RELATIVE * math.sin(math.pi/2 - elevation_angle))/math.sin(elevation_angle)
    
    # linear correction
    """
    Use Spreadsheet to calculate gradient and intercept
    1) Reset the current magic values to 0 and comment out the Pythagorus's theorm calculation just before the return
    2) Take readings of what the vision thinks the distance is and the real horizontal distance
    3) Input these into the following spreadsheet:
    https://docs.google.com/spreadsheets/d/1dRjTlxUB827p9uOyVD0SimTnsq3S977NRUhrfPGv-64/edit?usp=sharing
    """
    CORRECTION_GRADIENT = 0.431
    CORRECTION_INTERCEPT = -23.807
    horizontal_distance += horizontal_distance*CORRECTION_GRADIENT
    horizontal_distance += CORRECTION_INTERCEPT

    # Use pythagorus's theorm to find the distance between the camera and the goal
    distance = cal_point_distance((horizontal_distance, GOAL_HEIGHT_RELATIVE),(0,0))
    print(horizontal_distance, distance);
    return distance

# calculates the angle between the camera and the target
def cal_aim(image_size, goal_center):
    image_center = image_size[0]/2
    image_width = image_size[0]
    aim = (HORIZONTAL_FOV_LIFECAM/image_width * (goal_center[0] - image_center)) - AIM_CORRECTION_DEGREES # the camera may not be centered on the robot
    return aim

# draws a rectangle from four specified points applying an offset of 5 pixels
def draw_rectangle_offset(image, corners, offset):
    TL = corners[0]
    TR = corners[1]
    BL = corners[2]
    BR = corners[3]
    cv2.line(image, (TL[0]-offset,TL[1]-offset), (TR[0]+offset,TR[1]-offset), (0,0,255), 2)
    cv2.line(image, (TR[0]+offset,TR[1]-offset), (BR[0]+offset,BR[1]+offset), (0,0,255), 2)
    cv2.line(image, (BR[0]+offset,BR[1]+offset), (BL[0]-offset,BL[1]+offset), (0,0,255), 2)
    cv2.line(image, (BL[0]-offset,BL[1]+offset), (TL[0]-offset,TL[1]-offset), (0,0,255), 2)

# draws the area, corner area and their values
def draw_areas(image, contour, area, corner_area, corners):
    cv2.drawContours(image, [contour], 0, (255,255,255), 2)
    draw_rectangle_offset(image, corners, 5)
    draw_text(image, str(area), corners[2], (0,150,0))
    draw_text(image, str(corner_area), corners[1], (0,0,150))

# draws a dot at specified coordinates
def draw_goal_center(image, goal_center, colour = (255,0,255), size = 8):
    cv2.line(image, goal_center, goal_center, colour, size)

# draws a virtical line taking into account for aim correction
def draw_image_center(image, image_size):
    x = int(image_size[0]/2 + AIM_CORRECTION_DEGREES/PIXELS_PER_DEGREE)
    cv2.line(image, (x,0), (x, image_size[1]), (0,255,255), 2)

# draws a label for the aspect ratio at goal_center
def draw_aspect_ratio(image, aspect_ratio, goal_center):
    draw_text(image, str(round(aspect_ratio,3)), goal_center, (255,0,255))

# draws text showing information on where the target is relative to the robot
def draw_aim_distance(image, aim, distance):
    text = "Distance: ~" + "%02.1f" %distance + "  Aim: ~" + "%02.1f" %aim
    draw_text(image, text, (0,25), (255,255,255))

# draws information on how quickly the script is running
def draw_age_fps(image, age, fps, oldest):
    text = "Age: ~" + "%01.2f" %age + "  Fps: ~" + "%02.1f" %fps + \
        "  Oldest: ~" + "%01.2f" %oldest
    cv2.putText(image, text, (0,50), cv2.FONT_HERSHEY_SIMPLEX, .75, (255,255,255), 2)

# draws text (called by other draw functions)
def draw_text(image, text, xy, colour=(0,0,255)):
    cv2.putText(image, text, (xy[0],xy[1]), cv2.FONT_HERSHEY_SIMPLEX, .75, colour, 2)
