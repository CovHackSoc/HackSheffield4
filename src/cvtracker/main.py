import json
import sys
import numpy as np
import cv2
import json
import queue
import paho.mqtt.client as mqtt
import threading
import requests
import os
import binascii
import random

class GlobalState:
    jobQueue = queue.Queue()

class Image:
    def __init__(self, width, height, ndims=3):
        self.image = np.zeros((height,width,ndims), np.uint8)
        self.prevPosition = None

    def save(self, path):
        cv2.imwrite(path, self.image)

    def add(self, coords, color=(255,255,255), size=10):
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

class ArtUI:
    def __init__(self, config):
        self.config = config
        self.img = Image(config['width'], config['height'])
        self.lower_range = np.array(config['ranges']['lower'])
        self.upper_range = np.array(config['ranges']['upper'])
        self.current_color = (255,255,0)
        self.brushDown = False
        self.assets = {}
        self.assets['bob_ross_hair'] = cv2.imread('assets/bob_ross_hair.png')
        self.select_episode()

    def start(self):
        art = Artistry()

        cap = cv2.VideoCapture(self.config['video_input'])
        cap.set(3, self.config['width'])
        cap.set(4, self.config['height'])


        while True:
            # Check if we have anything new in our queue.
            ret, frame = cap.read()
            try:
                job = GlobalState.jobQueue.get_nowait()
                self.perform_job(job, frame)
            except queue.Empty:
                pass

            ret, frame = cap.read()
            # Mask out the background
            masked_background = art.mask_background(frame)
            # Pick out a color.
            masked_color = art.mask_color(
                masked_background, (self.lower_range, self.upper_range))
            # Build a mesh for the object.
            thresh = art.thresh_image(masked_color)
            positions = art.find_thresh_positions(thresh)
            # Display the best position
            try:
                _, coords = sorted(positions)[0]
                if self.brushDown:
                    self.img.add(coords, color=self.current_color)
            except IndexError:
                pass
            # Our UI
            overlay = cv2.add(frame, self.img.get())

            if config.get('bob_ross_hair', False):
                overlay = cv2.addWeighted(
                    self.assets['bob_ross_hair'], 1,
                    overlay, 1, 0)


            if config.get('developer', False):
                output = np.hstack(
                    (
                        cv2.flip(masked_color, 1),
                        cv2.flip(overlay, 1),
                        cv2.flip(self.img.get(), 1)
                    )
                )
            else:
                output = np.hstack(
                    (
                        cv2.flip(self.screenshot, 1),
                        cv2.flip(overlay, 1)
                    )
                )

            if config.get('fullscreen', False):
                cv2.namedWindow('window', cv2.WND_PROP_FULLSCREEN)
                cv2.setWindowProperty(
                    'window',cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
            cv2.imshow('window', output)

            # User input
            key = cv2.waitKey(1)
            if key == ord('q'): break
            elif key == ord('r'):
                self._reset_image()
            elif key == ord('s'):
                self._backup_image(frame)
                self._reset_image()
            elif key == ord('d'):
                self.brushDown = not(self.brushDown)


        cap.release()
        cv2.destroyAllWindows()

    def select_episode(self):
        self.episode = random.choice(self.config['episodes'])
        self.screenshot = cv2.imread(self.episode['file'])

    def _set_color(self, job):
        r = eval('0x'+job['data'][0:2])
        g = eval('0x'+job['data'][2:4])
        b = eval('0x'+job['data'][4:6])
        self.current_color = (b, g, r)
        self.img.resetPrevious()

    def _reset_image(self):
        self.select_episode()
        self.img = Image(self.config['width'], self.config['height'])

    def perform_job(self, job, frame):
        global GlobalState
        if job['command'] == 'brushUp':
            self.img.resetPrevious()
            self.brushDown = False
        elif  job['command'] == 'brushDown':
            self.brushDown = True
        elif job['command'] == 'colour':
            self._set_color(job)
        elif job['command'] == 'save':
            # Push to the website.
            self._backup_image(frame)
        elif job['command'] == 'reset':
            self._reset_image()

    def _backup_image(self, frame):
        # save it to /tmp/
        image_id = binascii.hexlify(os.urandom(16)).decode('ascii')+'.jpg'
        image_path = '/tmp/{}'.format(image_id)
        self.img.image = cv2.add(self.img.image, frame)
        self.img.save(image_path)
        # Now we can go post it to the form.
        print(self.episode)
        r = requests.post(
            self.config['form']['host'],
            files={
                'file': open(image_path, 'rb')
            },
            data={
                'episode': self.episode['name']
            }
        )
        self._reset_image()

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
        art_c = ArtUI(config)
        threading.Thread(
            target=art_c.start
        ).start()
        mqtt_c = MqttClient(config['mqtt'])
        threading.Thread(
            target=mqtt_c.start
        ).start()
