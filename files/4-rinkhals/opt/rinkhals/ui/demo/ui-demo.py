import os
import time

from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

DEBUG = os.getenv('DEBUG')
DEBUG = not not DEBUG
DEBUG = True

CWD = os.path.dirname(os.path.realpath(__file__))

SCREEN_WIDTH = 272
SCREEN_HEIGHT = 480

RUNNING_ON_PRINTER = False
if os.path.exists('/dev/fb0'):
    RUNNING_ON_PRINTER = True

TOUCH_CALIBRATION_MIN_X = 235
TOUCH_CALIBRATION_MAX_X = 25
TOUCH_CALIBRATION_MIN_Y = 460
TOUCH_CALIBRATION_MAX_Y = 25

COLOR_TEXT = (255, 255, 255)
COLOR_BACKGROUND = (0, 0, 0)


if RUNNING_ON_PRINTER:
    import evdev
else:
    from tkinter import Tk, Label
    from PIL import ImageTk



def log(message):
    print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + message, flush = True)



class Program:

    # State
    redraw = True
    touch_down = None

    # Assets
    font = None

    def __init__(self):
        
        if RUNNING_ON_PRINTER:
            self.touch_device = evdev.InputDevice('/dev/input/event0')
            self.touch_last_x = 0
            self.touch_last_y = 0
            self.touch_down_builder = None

        else:
            def on_closing():
                self.window.destroy()
                self.quit()
            def on_mouse_down(event):
                self.on_touch_down(event.x, event.y)
            def on_mouse_up(event):
                self.on_touch_up(event.x, event.y)
            def on_mouse_move(event):
                self.on_touch_move(event.x, event.y)

            self.window = Tk()
            self.window.title('Kobra display')
            self.window.geometry(f'{SCREEN_WIDTH}x{SCREEN_HEIGHT}')
            self.window.resizable(False, False)
            self.window.configure(bg='black')
            self.window.update()

            self.window_panel = Label(self.window)
            self.window_panel.pack(fill = "both", expand = "yes")

            self.window.protocol("WM_DELETE_WINDOW", on_closing)
            self.window.bind('<Button-1>', on_mouse_down)
            self.window.bind('<ButtonRelease-1>', on_mouse_up)
            self.window.bind('<B1-Motion>', on_mouse_move)

        self.font = ImageFont.truetype(CWD + '/AlibabaSans-Regular.ttf', 16)

    def loop(self):

        while True:
            if not self.redraw:
                self.process_events(250)
                continue

            self.redraw = False

            buffer = Image.new('RGBA', (SCREEN_WIDTH, SCREEN_HEIGHT), COLOR_BACKGROUND)
            draw = ImageDraw.Draw(buffer)

            draw.text((SCREEN_WIDTH / 2, 64), 'Touch UI demo!', fill = COLOR_TEXT, font = self.font, anchor = 'mm')

            if self.touch_down:
                radius = 32
                draw.rounded_rectangle((self.touch_down[0] - radius, self.touch_down[1] - radius, self.touch_down[0] + radius, self.touch_down[1] + radius), radius, fill = (255, 0, 0))

            self.display(buffer)

        quit()
    
    def display(self, image):
        if DEBUG:
            log('Displayed image')

        if RUNNING_ON_PRINTER:
            image_bytes = image.rotate(-90, expand = True).tobytes('raw', 'BGRA')
            with open('/dev/fb0', 'wb') as fb:
                fb.write(image_bytes)
        else:
            imageTk = ImageTk.PhotoImage(image)
            globals()['__imageTk'] = imageTk

            self.window_panel.config(image = imageTk)
            self.window.update()

    def quit(self):
        log('Exiting...')
        self.redraw = False
        os.kill(os.getpid(), 9)

    def on_touch_move(self, x, y):
        if DEBUG:
            log(f'on_touch_move({x}, {y})')

        self.touch_down = [x, y]
        self.redraw = True

    def on_touch_down(self, x, y):
        if DEBUG:
            log(f'on_touch_down({x}, {y})')

        self.touch_down = [x, y]
        self.redraw = True

    def on_touch_up(self, x, y):
        if DEBUG:
            log(f'on_touch_up({x}, {y})')

        self.touch_down = None
        self.redraw = True

    def process_events(self, duration):
        stop = time.time_ns() + duration * 1000000

        while time.time_ns() < stop:

            if RUNNING_ON_PRINTER:
                while time.time_ns() < stop:
                    event = self.touch_device.read_one()
                    if not event:
                        break

                    # Touch position
                    if event.type == evdev.ecodes.EV_ABS:
                        if event.code == evdev.ecodes.ABS_X:
                            self.touch_last_y = (event.value - TOUCH_CALIBRATION_MIN_Y) / (TOUCH_CALIBRATION_MAX_Y - TOUCH_CALIBRATION_MIN_Y) * SCREEN_HEIGHT
                            self.touch_last_y = min(max(0, int(self.touch_last_y)), SCREEN_HEIGHT)
                            if self.touch_down_builder:
                                self.touch_down_builder[1] = self.touch_last_y
                        elif event.code == evdev.ecodes.ABS_Y:
                            self.touch_last_x = (event.value - TOUCH_CALIBRATION_MIN_X) / (TOUCH_CALIBRATION_MAX_X - TOUCH_CALIBRATION_MIN_X) * SCREEN_WIDTH
                            self.touch_last_x = min(max(0, int(self.touch_last_x)), SCREEN_WIDTH)
                            if self.touch_down_builder:
                                self.touch_down_builder[0] = self.touch_last_x

                        if self.touch_down_builder and self.touch_down_builder[0] >= 0 and self.touch_down_builder[1] >= 0:
                            self.on_touch_down(self.touch_down_builder[0], self.touch_down_builder[1])
                            self.touch_down_builder = None
                        else:
                            self.on_touch_move(self.touch_last_x, self.touch_last_y)

                    # Touch action
                    elif event.code == evdev.ecodes.BTN_TOUCH: # EV_KEY
                        if event.value == 1:
                            self.touch_down_builder = [-1, -1]
                        elif event.value == 0:
                            self.on_touch_up(self.touch_last_x, self.touch_last_y)

            else:
                self.window.update()

            time.sleep(0.1)
            if self.redraw:
                break



if __name__ == "__main__":
    program = Program()
    program.loop()
