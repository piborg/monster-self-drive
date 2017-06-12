# MonsterBorg Self-drive
Easy to understand self-driving example for [MonsterBorg](https://www.kickstarter.com/projects/frobotics/monsterborg-the-raspberry-pi-monster-robot/?ref=selfdrive).

![](track-overlay-fpi.PNG?raw=true)

This project is a simple example of how to make a Raspberry Pi based robot fully autonomous using nothing more than a camera input for making decisions.  The code is entirely written in Python and makes extensive use of OpenCV to access the camera and process the images.  It should work with any Video4Linux capable camera attached to the Pi, but we have tested it with the official Raspberry Pi Camera.

## Downloading the code
To get the code we will clone this repository to the Raspberry Pi.
In a terminal run the following commands
```bash
cd ~
git clone https://github.com/piborg/monster-self-drive.git
```

## The code structure
The code is split into four Python scripts, each responsible for a set task.
* `ThunderBorg.py` - The standard ThunderBorg library, used to control MonsterBorg's motors
* `Settings.py` - Our settings for the robot to drive with, also holds some shared data between the scripts
* `MonsterAuto.py` - The main starting script, controls all of the threads and gets things started
* `ImageProcessor.py` - The complex part, this script talks to the camera, processes the images, then decides on how much power to give the motors

In general you should be able to get everything running just by changing `Settings.py` to match your track / route so that the robot knows what to follow.  Anyone that wants to see how the processing works or to make improvements will want to look at `ImageProcessor.py` as well.

## The idea
This example attempts to follow a course marked out using a distinctive colour.  We are only using the forward facing camera fitted to the MonsterBorg, no other line or distance sensors are needed.

The track itself should be made up of a continuous line in the same colour.  Bright colours tend to work best, particularly red, green, or blue.  Avoid any colours which have too much in common with the rest of the area to help the robot stay on course.  We would recommend avoiding black in particular as it can easily be confused with shadows.  Good lighting will help, even levels of light with minimal shadows and bright spots are best.

The track can be either thin or thick depending on your needs.  The thickest width we would recommend is about 60 cm (2 ft) and the smallest about 2.5 cm (1 in), something around 30 cm (1 ft) works rather well.  With narrower tracks you will need the robot to follow the course more precisely to make sure it does not get lost.  Wider tracks can follow the course in a looser fashion, but will likely stray further from the central line of the track.

Check out [Formula Pi](https://www.formulapi.com/?ref=selfdrive) to get an idea of what a fully walled track can look like.  There are also videos of how MonsterBorgs can perform on this track from just the camera image on our [YouTube channel](https://www.youtube.com/channel/UCKyhhVOx8BjZKJWLQTuc67g).

## Getting setup
Unlike most of our examples, this code needs a bit of adjustment before it is ready to go.  The default settings are setup for following one of the red lanes on our [Formula Pi track](https://www.formulapi.com/track-1?ref=selfdrive).  You should be able to follow any nice obvious colour, but bright colours will work better.

Before starting you will want a connection to your robot where you can see graphical output, such as VNC, an actual monitor, or SSH with X11 forwarding enabled.  This will allow you to see what effect the changes have on what the robot can see.  It is best to do the setup on the MonsterBorg itself when sat on the floor so that the camera height is correct for your track.

From the Raspberry Pi begin by running the main script:
```bash
cd ~/monster-self-drive
./MonsterAuto.py
```

Your robot should start processing the camera but it will not start moving yet.

![](track-overlay-mode.PNG?raw=true)

The image shown has a few parts of interest:
* The bright areas are those which match the set colour
* The dark areas are those which do not match the set colour
* The two cyan circles are the points we have placed the center of our lane at
* The yellow line is what we are trying to follow

If everything is setup correctly for the track then you should see the correct area highlighted.  Otherwise we need to set the image up for the track.

### Setting the track colour
First end the script using `CTRL`+`C` if it is still running.  All of the settings are in `Settings.py` so open it up in your favourite text editor.

The lines you are looking for are:
```python
minHuntColour = ( 80,   0,   0)         # Minimum RGB values for our coloured line
maxHuntColour = (255, 100, 100)         # Maximum RGB values for our coloured line
erodeSize = 5                           # Size of the erosion used to remove noise, larger reduces noise further
```

The first, `minHuntColour`, is the minimum red, green, and blue levels that will be highlighted.  The second, `maxHuntColour`, are the maximums to be highlighted.  Your track colour as seen by the camera should be between these values.  A wider range will deal better with differing light levels, but a narrower range will have less trouble with mistaking the surroundings for the track.

The third value, `erodeSize`, is a little harder to explain.  With a value of `1` each pixel is highlighted based only on what is described above.  With a value of `2` each pixel looks at neighbouring pixels to decide if it is just noise (a lone spot) or really part of the track.  As you increase the number it will remove more unintended noisy points, but it will also narrow the width of the real highlighted track.

If you are struggling to see what is highlighted you can set the `overlayOriginal` setting further down to `False`.  This will show matched areas as grey and unmatched as black.

![](track-mask-mode.PNG?raw=true)

Each time you make a change save the `Settings.py` file and run `MonsterAuto.py` again to test the change.  Once the highlighted region is approximately correct we can move on to positioning the tracked points in the correct places.

### Setting the tracked points
Stay tuned ^_^
