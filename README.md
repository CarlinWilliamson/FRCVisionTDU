# FRCVisionTDU
Framework for using a camera to detect vision targets

## What is this?
FIRST Robotics Competition is an anual robotics competition where high school students with help from industry mentors design, build and program 2 m^3, 55 kg robots.
Typically the game will involve shooting some sort of object into a goal around which is ususally some retro-reflective tape (similar to what is found on hi-vis vests)
This system is designed to run on seperate hardware (like a raspberry pi).
To detect the goals we place an LED ring around the camera and lower the exposure down such that only the goal shows up on an otherwise black image.
It's location on the image can be converted into distance and horizonal angle the goal relative to the camera. With this information we can aim and shoot at the goal

## Features
Seperate threads for capturing images, saving images for debugging, serving images over the web, communication with other devices and the main processing of images/localiation
Selects goals based upon their area, squareness and aspect ratio
Ability to run and switch between multiple cameras with different goal selection parameters
Runs at approximately 20fps on a raspberry pi 3

## Running this code
detect_goals.py is the main entry point
There are also systemd files wihch can be used to run this as a service on external hardware
