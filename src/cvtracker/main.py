import json
import sys
import numpy as np
import cv2
import json
import queue
import paho.mqtt.client as mqtt
import threading
import requests

class GlobalState:
    jobQueue = queue.Queue()

class Image:
    def __init__(self, width, height, ndims=3):
        self.image = np.zeros((height,width,3), np.uint8)
        self.prevPosition = None
    def save(self, path):
        cv2.imwrite(path, self.image)
    def add(self, coords, color=(255,255,0), size=10):
        position = (int(coords[0]), int(coords[1]))
        if self.prevPosition is not None:
            cv2.line(self.image, self.prevPosition, position, color, size*2)
        cv2.circle(self.image, position, size, color, -1)
        self.prevPosition = position
    def get(self):
        return self.image
    def resetPrevious(self):
        self.prevPosition = None

class Artistry:
    def __init__(self):
        self.fgbg = cv2.createBackgroundSubtractorMOG2()
        self.kernel = np.ones((100,100),np.uint8)

    def mask_color(self, image, ranges):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        clmask = cv2.inRange(hsv, ranges[0], ranges[1])
        masked_hsv = cv2.bitwise_and(
            hsv, hsv, mask=clmask)
        masked_color = cv2.cvtColor(masked_hsv, cv2.COLOR_HSV2BGR)
        return masked_color

    def mask_background(self, image):
        fgmask = self.fgbg.apply(image)
        masked_background = cv2.bitwise_and(image, image, mask=fgmask)
        return masked_background

    def thresh_image(self, image):
        cimg = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        thresh = cv2.morphologyEx(cimg, cv2.MORPH_CLOSE, self.kernel)
        return thresh

    def find_thresh_positions(self, image):
        results = []
        img, contours, hierarchy = cv2.findContours(
            image,
            cv2.RETR_TREE,
            cv2.CHAIN_APPROX_SIMPLE
        )
        # There is likely a better way to do this.
        if len(contours) > 0:
            for i in contours:
                k = i.sum(axis=1)
                x = 0
                y = 0
                for j in k:
                    x += j[0]
                    y += j[1]
                x = x/len(k)
                y = y/len(k)
                results.append((len(i), (x, y)))

        return results

def artUI(video_input, width, height, ranges):
    global GlobalState
    lower_range = np.array(ranges['lower'])
    upper_range = np.array(ranges['upper'])
    cap = cv2.VideoCapture(video_input)
    cap.set(3, width)
    cap.set(4, height)

    img = Image(width, height)
    art = Artistry()
    current_color = (255, 255, 0)
    brushDown = False
    while(True):
        # Check the queue
        try:
            job = GlobalState.jobQueue.get_nowait()
            print(job)
            if job['command'] == 'brushUp':
                img.resetPrevious()
                brushDown = False
            elif  job['command'] == 'brushDown':
                brushDown = True
            elif job['command'] == 'colour':
                img.resetPrevious()
                r = eval('0x'+job['data'][0:2])
                g = eval('0x'+job['data'][2:4])
                b = eval('0x'+job['data'][4:6])
                current_color = (b, g, r)
            elif job['command'] == 'done':
                # save it.
                pass
            elif job['command'] == 'reset':
                img = Image(width, height)
        except queue.Empty:
            pass
        # Capture frame-by-frame
        ret, frame = cap.read()
        # Mask out the background
        masked_background = art.mask_background(frame)
        # Pick out a color.
        masked_color = art.mask_color(
            masked_background, (lower_range, upper_range))
        # Build a mesh for the object.
        thresh = art.thresh_image(masked_color)
        positions = art.find_thresh_positions(thresh)
        # Display the best position
        try:
            _, coords = sorted(positions)[0]
            if brushDown:
                img.add(coords, color=current_color)
        except IndexError:
            pass
        # Our UI
        overlay = cv2.add(frame, img.get())
        output = np.hstack(
            (
                cv2.flip(masked_color, 1),
                cv2.flip(overlay, 1),
                cv2.flip(img.get(), 1)
            )
        )
        cv2.imshow('frame', output)
        # User input
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    # When everything done, release the capture
    cap.release()
    cv2.destroyAllWindows()

class MqttClient:
    def __init__(self, config):
        self.client = mqtt.Client()
        self.client.on_connect = MqttClient.on_connect
        self.client.on_message = MqttClient.on_message
        self.config = config

    def start(self):
        self.client.connect(
            self.config['host'],
            self.config['port'],
            60
        )
        self.client.loop_forever()

    @staticmethod
    def on_connect(client, userdaat, flags, rc):
        client.subscribe("HackShef/bobro")

    @staticmethod
    def on_message(client, userdata, msg):
        global GlobalState
        raw = json.loads(msg.payload)
        GlobalState.jobQueue.put(raw)

if __name__ == "__main__":
    if len(sys.argv) < 1:
        exit()
    with open(sys.argv[1]) as config_file:
        config = json.load(config_file)
        threading.Thread(
            target=artUI,
            args=(
                config['video_input'],
                config['width'],
                config['height'],
                config['ranges']
            )
        ).start()
        mqtt_c = MqttClient(config['mqtt'])
        threading.Thread(
            target=mqtt_c.start
        ).start()
