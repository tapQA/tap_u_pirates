#!/usr/bin/python2.7


import requests
import json
import StringIO
import subprocess
import os
import time

from datetime import datetime
from PIL import Image


# Motion detection settings:
# Threshold (how much a pixel has to change by to be marked as "changed")
# Sensitivity (how many changed pixels before capturing an image)
# ForceCapture (whether to force an image to be captured every forceCaptureTime seconds)
threshold = 30
sensitivity = 500
forceCapture = False
forceCaptureTime = 5 # Once 5 seconds
#forceCaptureTime = 60 * 60 # Once an hour

# File settings
saveWidth = 1280
saveHeight = 960
diskSpaceToReserve = 18897856102.4 # Keep 9.25 mb free on disk. 

# Capture a small test image (for motion detection)
def captureTestImage():
    command = "raspistill -w %s -h %s -t 1000 -p '100,100,256,256' -e bmp -o -" % (100, 75)
    imageData = StringIO.StringIO()
    imageData.write(subprocess.check_output(command, shell=True))
    imageData.seek(0)
    im = Image.open(imageData)
    buffer = im.load()
    imageData.close()
    return im, buffer

# Save a full size image to disk
def saveImage(width, height, diskSpaceToReserve):
    keepDiskSpaceFree(diskSpaceToReserve)
    time = datetime.now()
    filename = "image1.jpg"
    #filename = "capture-%04d%02d%02d-%02d%02d%02d.jpg" % (time.year, time.month, time.day, time.hour, time.minute, time.second)
    subprocess.call("raspistill -w 1296 -h 972 -t 1000 -e jpg -q 15 -p '300,300,256,256' -o %s" % filename, shell=True)
    print "Captured %s" % filename

# Keep free space above given level
def keepDiskSpaceFree(bytesToReserve):
    if (getFreeSpace() < bytesToReserve):
        for filename in sorted(os.listdir(".")):
            if filename.startswith("capture") and filename.endswith(".jpg"):
                os.remove(filename)
                print "Deleted %s to avoid filling disk" % filename
                if (getFreeSpace() > bytesToReserve):
                    return

# Get available disk space
def getFreeSpace():
    st = os.statvfs(".")
    du = st.f_bavail * st.f_frsize
    print du
    return du
        
# Get first imageF
image1, buffer1 = captureTestImage()

# Reset last capture time
lastCapture = time.time()

# Presence check
getpresence = 'https://slack.com/api/users.getPresence'
user = {'token' : 'token', 'user' : 'user', 'pretty':1}

# Attempt at error handling 
while (True):
	try:
		p = requests.get(getpresence, params=user)
		print p.json()
	except requests.exceptions.ConnectionError:
		pass
	
	if p.json().get('presence') == "away":
	
		# Get comparison image
		t0=time.time()
		image2, buffer2 = captureTestImage()

		# Count changed pixels
		changedPixels = 0
		
		for x in xrange(0, 100):
			for y in xrange(0, 75):
				# Just check green channel as it's the highest quality channel
				pixdiff = abs(buffer1[x,y][1] - buffer2[x,y][1])
				if pixdiff > threshold:
					changedPixels += 1
		t1=time.time()
		# Check force capture
		if forceCapture:
			if time.time() - lastCapture > forceCaptureTime:
				changedPixels = sensitivity + 1
					
		# Save an image if pixels changed
		if changedPixels > sensitivity:
			lastCapture = time.time()
			saveImage(saveWidth, saveHeight, diskSpaceToReserve)
		
		# Swap comparison buffers
		image1 = image2
		buffer1 = buffer2

		print changedPixels, (t1-t0)
		time.sleep(30)
		
		# File upload API call

		if changedPixels > sensitivity:
			upload = 'https://slack.com/api/files.upload'
			image = {'file': open('image1.jpg', 'rb')}
			id = {'token':'token', 'channels': '#tap_u_pirates', 'pretty': 1}
			r = requests.post(upload, params=id, files=image,)
	
			print r.json()
	# How often presence is checked
	else:
		time.sleep(5)
