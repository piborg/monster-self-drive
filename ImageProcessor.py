#!/usr/bin/env python
# coding: Latin-1

# Load library functions we want
import time
import datetime
import threading
import cv2
import numpy
import math
import random
import Settings

def rgb2bgr((r, g, b)):
    return b, g, r

# PID processing thread
class ControlLoop(threading.Thread):
    def __init__(self):
        super(ControlLoop, self).__init__()
        self.event = threading.Event()
        self.lock = threading.Lock()
        self.terminated = False
        self.eventWait = 2.0 / Settings.frameRate
        self.Reset()
        print 'Control loop thread started with idle time of %.2fs' % (self.eventWait)
        self.start()

    def run(self):
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            self.event.wait(self.eventWait)
            if self.event.isSet():
                if self.terminated:
                    break
                try:
                    # Read the next set of values
                    sample = self.nextSample
                    self.RunLoop(sample)
                finally:
                    # Reset the event trigger
                    self.event.clear()
        print 'Control loop thread terminated'

    def Reset(self):
        with self.lock:
            self.__Reset__()

    def __Reset__(self):
        # Set everything to a clean starting state
        self.moving = False
        self.positionI = 0.0
        self.changeI = 0.0
        self.clipIMax = Settings.clipI
        self.clipIMin = -Settings.clipI
        self.firTaps = Settings.motorSmoothing
        self.firHistorySpeed = []
        self.firHistorySteering = []
        self.lastSteering = 0.0
        self.lastSpeed = 0.0
        self.lastPosition = 0.0
        self.lastChange = 0.0
        self.SetDrive(0.0, 0.0)
    
    def SetDrive(self, speed, steering):
        # Make sure speed and steering are within limits
        if steering < -1.0:
            steering = -1.0
        elif steering > 1.0:
            steering = 1.0
        if speed < -1.0:
            speed = -1.0
        elif speed > 1.0:
            speed = 1.0
        # Final steering corrections
        steering *= Settings.steeringGain
        steering += Settings.steeringOffset
        if steering < -Settings.steeringClip:
            steering = -Settings.steeringClip
        elif steering > Settings.steeringClip:
            steering = Settings.steeringClip
        # Determine the individual drive power levels
        driveLeft  = speed
        driveRight = speed
        if steering < -0.01:
            # Turning left
            driveLeft *= 1.0 + steering
        elif steering > 0.01:
            # Turning right
            driveRight *= 1.0 - steering
        # Set the motors to the new speeds
        Settings.MonsterMotors(driveLeft, driveRight)
    
    def FirFilter(self, speed, steering):
        # Filtering for speed and steering
        self.firHistorySpeed.append(speed)
        self.firHistorySteering.append(steering)
        self.firHistorySpeed = self.firHistorySpeed[-self.firTaps:]
        self.firHistorySteering = self.firHistorySteering[-self.firTaps:]
        filteredSpeed = numpy.mean(self.firHistorySpeed)
        filteredSteering = numpy.mean(self.firHistorySteering)
        self.SetDrive(filteredSpeed, filteredSteering)

    def RunLoop(self, (isGood, position, change)):
        with self.lock:
            if isGood:
                # Position offset loop
                self.positionP = Settings.positionP * position
                self.positionI += Settings.positionI * position
                if self.positionI > self.clipIMax:
                    self.positionI = self.clipIMax
                elif self.positionI < self.clipIMin:
                    self.positionI = self.clipIMin
                self.positionD = Settings.positionD * (position - self.lastPosition)
                self.lastPosition = position
                self.positionPID = self.positionP + self.positionI + self.positionD
                # Position change loop
                self.changeP = Settings.changeP * change
                self.changeI += Settings.changeI * change
                if self.changeI > self.clipIMax:
                    self.changeI = self.clipIMax
                elif self.changeI < self.clipIMin:
                    self.changeI = self.clipIMin
                self.changeD = Settings.changeD * (change - self.lastChange)
                self.lastChange = change
                self.changePID = self.changeP + self.changeI + self.changeD
                # Speed and steering values
                speed = Settings.currentSpeed
                steering = self.positionPID + self.changePID
            else:
                # Cannot find line, keep same steering but slow down
                # This calculation produces a smooth curve that reaches about 20% after 31 times
                speed = self.lastSpeed * 0.95
                if speed < 0.2:
                    speed = 0.0
                steering = self.lastSteering
            # Set the final drive
            self.FirFilter(speed, steering)
            self.lastSpeed = speed
            self.lastSteering = steering
    

# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self, name):
        super(StreamProcessor, self).__init__()
        self.event = threading.Event()
        self.terminated = False
        self.name = str(name)
        self.eventWait = (2.0 * Settings.processingThreads) / Settings.frameRate
        if Settings.cameraWidth != Settings.scaledWidth or Settings.cameraHeight != Settings.scaledHeight:
            self.resize = True
        else:
            self.resize = False
        print 'Processor thread %s started with idle time of %.2fs' % (self.name, self.eventWait)
        self.start()

    def run(self):
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            self.event.wait(self.eventWait)
            if self.event.isSet():
                if self.terminated:
                    break
                try:
                    # grab the image and do some processing on it
                    if Settings.flippedImage:
                        image = cv2.flip(self.nextFrame, -1)
                    else:
                        image = self.nextFrame
                    self.ProcessImage(image)
                finally:
                    # Reset the event
                    self.nextFrame = None
                    self.event.clear()
                    # Return ourselves to the pool at the back
                    with Settings.frameLock:
                        Settings.processorPool.insert(0, self)
        print 'Processor thread %s terminated' % (self.name)
    
    # Find sections in a boolean image
    # Returns a list of size and location pairs sorted by largest first
    def SweepLine(self, image, Y):
        # Grab the line of interest
        line = image[Y, :]
        width = len(line)
        # Work out where the changes are
        changed = numpy.where(line[:-1] != line[1:])[0]
        # Set an initial state with an edge at the start of the line
        current = line.item(0)
        previousPosition = 0
        sectionsFound = []
        # Sweep over the list of changes
        for i in changed:
            # Filter out changes at the edge of the image
            # These can be messy from the camera
            if i < 2:
                pass
            elif i > (width - 3):
                pass
            elif current:
                # End of high section - add to list
                size = i - previousPosition
                location = int(size / 2) + previousPosition
                sectionsFound.append([size, location])
                previousPosition = i
            else:
                # End of low section, mark the next start point
                previousPosition = i
            current = not current
        # If we finished on a high section generate a final section for it
        # This includes the whole line being active!
        if current:
            size = width - previousPosition
            location = int(size / 2) + previousPosition
            sectionsFound.append([size, location])
        # Finally sort by size and return
        sectionsFound.sort()
        sectionsFound.reverse()
        return sectionsFound

    # Image processing function
    def ProcessImage(self, image):
        # Frame rate counter
        with Settings.frameLock:
            self.frame = Settings.frameCounter
            Settings.frameAnnounce += 1
            Settings.frameCounter += 1
            if Settings.frameAnnounce == Settings.fpsInterval:
                frameStamp = time.time()
                if Settings.showFps:
                    fps = Settings.fpsInterval / (frameStamp - Settings.lastFrameStamp)
                    fps = '%.1f FPS' % (fps)
                    print fps
                Settings.frameAnnounce = 0
                Settings.lastFrameStamp = frameStamp
        # Resize if needed
        if self.resize:
            image = cv2.resize(image, (Settings.scaledWidth, Settings.scaledHeight), interpolation = cv2.INTER_NEAREST)
        # Process image to get a lineMask image (boolean)
        minBGR = numpy.array((Settings.minHuntColour[2], Settings.minHuntColour[1], Settings.minHuntColour[0]))
        maxBGR = numpy.array((Settings.maxHuntColour[2], Settings.maxHuntColour[1], Settings.maxHuntColour[0]))
        lineMask = cv2.inRange(image, minBGR, maxBGR)
        # Erode the mask to remove noise
        if Settings.erodeSize > 1:
            erodeKernel = numpy.ones((Settings.erodeSize, Settings.erodeSize), numpy.uint8)
            lineMask   = cv2.erode(lineMask, erodeKernel)
        # Find the line sections in our two locations
        sectionsY1 = self.SweepLine(lineMask, Settings.targetY1)
        sectionsY2 = self.SweepLine(lineMask, Settings.targetY2)
        # Pick the largest sections and take their center positions
        if len(sectionsY1) > 0:
            X1 = sectionsY1[0][1]
        else:
            X1 = None
        if len(sectionsY2) > 0:
            X2 = sectionsY2[0][1]
        else:
            X2 = None
        # Generate the display image
        if Settings.showImages:
            if Settings.overlayOriginal:
                displayImage = image.copy()
                # Darken areas not matching the mask
                blue, green, red = cv2.split(displayImage)
                red  [lineMask == 0] /= 3
                green[lineMask == 0] /= 3
                blue [lineMask == 0] /= 3
                displayImage = cv2.merge([blue, green, red])
            else:
                # Generate grey image from mask
                displayImage = cv2.merge([lineMask, lineMask, lineMask])
                displayImage /= 2
            # Draw line between points
            if (X1 != None) and (X2 != None):
                cv2.line(displayImage, (X1, Settings.targetY1), (X2, Settings.targetY2), Settings.targetLine, 1, lineType = cv2.CV_AA)
            # Draw circles around points
            if X1 != None:
                cv2.circle(displayImage, (X1, Settings.targetY1), Settings.targetPointSize, Settings.targetPoints, 1, lineType = cv2.CV_AA) 
            if X2 != None:
                cv2.circle(displayImage, (X2, Settings.targetY2), Settings.targetPointSize, Settings.targetPoints, 1, lineType = cv2.CV_AA) 
            Settings.displayFrame = displayImage
        # Pass the results to the control loop
        # Offset is most important, but ideally we need both
        if (X1 == None) and (X2 == None):
            # No line found
            isGood = False
            offset = 0.0
            change = 0.0
        elif X1 == None:
            # We only have a far point
            # Not great, but we will use it
            isGood = True
            offset = ((2.0 * X2) / Settings.scaledWidth) - 1.0
            change = 0.0
        elif X2 == None:
            # We only have a near point
            # We loose the change, but offset will be good
            isGood = True
            offset = ((2.0 * X1) / Settings.scaledWidth) - 1.0
            change = 0.0
        else:
            # We have both points :)
            isGood = True
            offset = ((2.0 * X1) / Settings.scaledWidth) - 1.0
            change = (2.0 * (X2 - X1)) / Settings.scaledWidth
        Settings.controller.nextSample = (isGood, offset, change)
        Settings.controller.event.set()


# Image capture thread
class ImageCapture(threading.Thread):
    def __init__(self):
        super(ImageCapture, self).__init__()
        self.start()

    # Stream delegation loop
    def run(self):
        while Settings.running:
            # Grab the oldest unused processor thread
            with Settings.frameLock:
                if Settings.processorPool:
                    processor = Settings.processorPool.pop()
                else:
                    processor = None
            if processor:
                # Grab the next frame and send it to the processor
                ret, frame = Settings.capture.read()
                if ret:
                    processor.nextFrame = frame.copy()
                    processor.event.set()
                else:
                    print 'Capture stream lost...'
                    Settings.running = False
                    break
            else:
                # When the pool is starved we wait a while to allow a processor to finish
                time.sleep(0.01)
        print 'Streaming terminated.'
