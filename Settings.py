#!/usr/bin/env python
# coding: Latin-1

#####################################################################
# This is the settings script for the MonsterBorg self-driving code #
#####################################################################

# Power settings
voltageIn = 1.2 * 10                    # Total battery voltage to the ThunderBorg
voltageOut = 12.0 * 0.95                # Maximum motor voltage, we limit it to 95% to allow the RPi to get uninterrupted power

# Camera settings
cameraWidth  = 640                      # Camera image width
cameraHeight = 480                      # Camera image height
frameRate    = 30                       # Camera image capture frame rate
flippedImage = True                     # True if the camera needs to be rotated

# Processing settings
scaledWidth   = 160                     # Resized image width
scaledHeight  = 120                     # Resized image height
processingThreads = 4                   # Number of processing threads to run
minHuntColour = ( 80,   0,   0)         # Minimum RGB values for our coloured line
maxHuntColour = (255, 100, 100)         # Maximum RGB values for our coloured line
erodeSize = 5                           # Size of the erosion used to remove noise, larger reduces noise further
targetY1 = int(scaledHeight * 0.9)      # Y location for the closest point to track in the scaled image
targetY2 = int(scaledHeight * 0.6)      # Y location for the furthest point to track in the scaled image

# Control settings
motorSmoothing = 5                      # Number of frames to average motor output for, larger is slower to respond but drives smoother
positionP = 1.00                        # P term for control based on distance from line
positionI = 0.00                        # I term for control based on distance from line
positionD = 0.40                        # D term for control based on distance from line
changeP = 1.00                          # P term for control based on change between the points from the line
changeI = 0.00                          # I term for control based on change between the points from the line
changeD = 0.40                          # D term for control based on change between the points from the line
clipI = 100                             # Maximum limit for both integrators

# Final drive settings
steeringGain = 1.0                      # Steering range correction value
steeringClip = 1.0                      # Maximum steering value
steeringOffset = 0.0                    # Steering centre correction value

# Debugging display
fpsInterval = frameRate                 # Number of frames to average FPS over
showFps = True                          # True to display FPS readings in the terminal
testMode = True                         # True to prevent the robot moving, False will self-drive
showImages = True                       # True to show processing images
overlayOriginal = True                  # True to draw over original image, False to show a mask instead
showPerSecond = 1                       # Frames to show per second, lower has less impact on the running code
scaleFinalImage = 1.0                   # Use to resize the displayed image, 1.0 is actual size
targetLine = (0, 255, 255)              # Colour for the line between target points
targetPoints = (255, 255, 0)            # Colour for the circles around each target point
targetPointSize = 3                     # Size of the target circle around each target point

#################
# Shared values #
#################

# Control values
running = True                          # When this is set False the program will end itself
currentSpeed = 1.0                      # Speed setting used by the control loop
testModeCounter = 0                     # Tick in test mode for showing motor output in-line with FPS readings

# Shared functions
MonsterMotors = None                    # Function which runs the MonsterBorg motors

# Shared data
displayFrame = None                     # Image to show when running (if any)
frameCounter = 0                        # Shared index for each frame coming in
frameAnnounce = 0                       # Wrapping counter for FPS display
lastFrameStamp = 0                      # Time stamp used for measuring FPS

# Shared objects
frameLock = None                        # Used to prevent threading clashes
processorPool = None                    # List of available image processing threads
capture = None                          # OpenCV image capture object
controller = None                       # Motor control thread
