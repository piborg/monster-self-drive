#!/usr/bin/env python
# coding: Latin-1

#################################################################
# This is the main script for the MonsterBorg self-driving code #
#################################################################

# Load all the library functions we want
import time
import os
import sys
import threading
import cv2
import numpy
import ThunderBorg
import Settings
import ImageProcessor
print 'Libraries loaded'

# Derive some settings from the main settings
if Settings.voltageOut > Settings.voltageIn:
    maxPower = 1.0
else:
    maxPower = Settings.voltageOut / float(Settings.voltageIn)

showFrameDelay = 1.0 / Settings.showPerSecond
waitKeyDelay = int(showFrameDelay * 1000)

# Change the current directory to where this script is
scriptDir = os.path.dirname(sys.argv[0])
os.chdir(scriptDir)
print 'Running script in directory "%s"' % (scriptDir)

if Settings.testMode:
    print 'TEST MODE: Skipping board setup'
else:
    # Setup the ThunderBorg
    global TB
    TB = ThunderBorg.ThunderBorg()
    #TB.i2cAddress = 0x15                  # Uncomment and change the value if you have changed the board address
    TB.Init()
    if not TB.foundChip:
        boards = ThunderBorg.ScanForThunderBorg()
        if len(boards) == 0:
            print 'No ThunderBorg found, check you are attached :)'
        else:
            print 'No ThunderBorg at address %02X, but we did find boards:' % (TB.i2cAddress)
            for board in boards:
                print '    %02X (%d)' % (board, board)
            print 'If you need to change the I²C address change the setup line so it is correct, e.g.'
            print 'TB.i2cAddress = 0x%02X' % (boards[0])
        sys.exit()
    TB.SetCommsFailsafe(False)

    # Blink the LEDs in white to indicate startup
    TB.SetLedShowBattery(False)
    for i in range(3):
        TB.SetLeds(0,0,0)
        time.sleep(0.5)
        TB.SetLeds(1,1,1)
        time.sleep(0.5)
    TB.SetLedShowBattery(True)

# Function used by the processing to control the MonsterBorg
def MonsterMotors(driveLeft, driveRight):
    global TB
    TB.SetMotor1(driveRight * maxPower) # Right side motors
    TB.SetMotor2(driveLeft  * maxPower) # Left side motors

# Function used by the processing for motor output in test mode
def TestModeMotors(driveLeft, driveRight):
    # Convert to percentages
    driveLeft *= 100.0
    driveRight *= 100.0
    # Display at FPS update rate
    Settings.testModeCounter += 1
    if Settings.testModeCounter >= Settings.fpsInterval:
        Settings.testModeCounter = 0
        print 'MOTORS: %+07.2f %% left, %+07.2f %% right' % (driveLeft, driveRight)

# Push the appropriate motor function into the settings module
if Settings.testMode:
    Settings.MonsterMotors = TestModeMotors
else:
    Settings.MonsterMotors = MonsterMotors

# Startup sequence
print 'Setup camera input'
os.system('sudo modprobe bcm2835-v4l2')
Settings.capture = cv2.VideoCapture(0) 
Settings.capture.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, Settings.cameraWidth);
Settings.capture.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, Settings.cameraHeight);
Settings.capture.set(cv2.cv.CV_CAP_PROP_FPS, Settings.frameRate);
if not Settings.capture.isOpened():
    Settings.capture.open()
    if not Settings.capture.isOpened():
        print 'Failed to open the camera'
        sys.exit()

print 'Setup stream processor threads'
Settings.frameLock = threading.Lock()
Settings.processorPool = [ImageProcessor.StreamProcessor(i+1) for i in range(Settings.processingThreads)]
allProcessors = Settings.processorPool[:]

print 'Setup control loop'
Settings.controller = ImageProcessor.ControlLoop()

print 'Wait ...'
time.sleep(2)
captureThread = ImageProcessor.ImageCapture()

try:
    print 'Press CTRL+C to quit'
    Settings.MonsterMotors(0, 0)
    # Create a window to show images if we need one
    if Settings.showImages:
        cv2.namedWindow('Monster view', cv2.WINDOW_NORMAL)
    # Loop indefinitely
    while Settings.running:
        # See if there is a frame to show, wait either way
        monsterView = Settings.displayFrame
        if monsterView != None:
            if Settings.scaleFinalImage != 1.0:
                size = (int(monsterView.shape[1] * Settings.scaleFinalImage), 
                        int(monsterView.shape[0] * Settings.scaleFinalImage))
                monsterView = cv2.resize(monsterView, size, interpolation = cv2.INTER_CUBIC)
            cv2.imshow('Monster view', monsterView)
            cv2.waitKey(waitKeyDelay)
        else:
            # Wait for the interval period
            time.sleep(showFrameDelay)
    # Disable all drives
    Settings.MonsterMotors(0, 0)
except KeyboardInterrupt:
    # CTRL+C exit, disable all drives
    print '\nUser shutdown'
    Settings.MonsterMotors(0, 0)
except:
    # Unexpected error, shut down!
    e = sys.exc_info()
    print
    print e
    print '\nUnexpected error, shutting down!'
    Settings.MonsterMotors(0, 0)
# Tell each thread to stop, and wait for them to end
Settings.running = False
while allProcessors:
    with Settings.frameLock:
        processor = allProcessors.pop()
    processor.terminated = True
    processor.event.set()
    processor.join()
Settings.controller.terminated = True
Settings.controller.join()
captureThread.join()
Settings.capture.release()
del Settings.capture
Settings.MonsterMotors(0, 0)
if not Settings.testMode:
    # Turn the LEDs off to indicate we are done
    TB.SetLedShowBattery(False)
    TB.SetLeds(0,0,0)
print 'Program terminated.'
