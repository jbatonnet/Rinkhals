import os
import time
import sys
import json
import re
import platform

from PIL import Image, ImageDraw, ImageFont

from enum import Enum
from typing import Any
from types import FunctionType


class FontManager:
    def get_font(path: str, size: float) -> ImageFont:
        key = f'{path}|{size}'

        font = Cache.get(key)
        if font:
            return font

        font = ImageFont.truetype(path, size)
        Cache.set(key, font)
        return font

class Cache:
    items: dict[str, Any] = {}

    def get(key: str):
        return Cache.items.get(key)
    def set(key: str, item):
        Cache.items[key] = item
    def remove(key):
        Cache.items.pop(key)
    def clear():
        items = []


class Component:
    class LayoutMode(Enum):
        Relative = 0
        Absolute = 1

    parent = None
    visible: bool = True
    left: int
    width: int
    right: int
    top: int
    height: int
    bottom: int
    layout_mode: LayoutMode = LayoutMode.Relative

    _x: int
    _width: int
    _y: int
    _height: int

    def __init__(self, left: int = None, width: int = None, right: int = None, top: int = None, height: int = None, bottom: int = None, layout_mode: LayoutMode = LayoutMode.Relative):
        self.left = left
        self.width = width
        self.right = right
        self.top = top
        self.height = height
        self.bottom = bottom

    def measure(self):
        width = self.width
        height = self.height

        if width is not None:
            width = width * self.scale
        if height is not None:
            height = height * self.scale

        return (width, height)
    def layout(self):
        pass
    def draw(self, draw: ImageDraw, offset_x: int, offset_y: int):
        pass

    def on_refresh(self):
        if self.parent:
            self.parent.on_refresh()

    def on_touch_down(self, position_x: int, position_y: int):
        pass
    def on_touch_move(self, position_x: int, position_y: int):
        pass
    def on_touch_up(self, position_x: int, position_y: int):
        pass
    def on_touch_cancel(self):
        pass

class Panel(Component):
    components: list[Component]
    background_color: str
    border_color: str
    border_width: int

    _touched_component = None

    def __init__(self, components: list[Component] = [], background_color: str = None, border_color: str = None, border_width: int = 0, left: int = None, width: int = None, right: int = None, top: int = None, height: int = None, bottom: int = None, layout_mode: Component.LayoutMode = Component.LayoutMode.Relative):
        super().__init__(left=left, width=width, right=right, top=top, height=height, bottom=bottom, layout_mode=layout_mode)
        self.components = components
        self.background_color = background_color
        self.border_color = border_color
        self.border_width = border_width

    def layout(self):
        super().layout()

        if not self.components:
            return

        for component in self.components:
            component.parent = self
            component.scale = self.scale

            (width, height) = component.measure()

            scale = component.scale
            if self.layout_mode == Component.LayoutMode.Absolute:
                scale = 1

            if component.left is not None and width is not None:
                x = component.left * scale
            elif component.left is not None and component.right is not None:
                x = component.left
                width = self._width - component.right * scale - component.left * scale
            elif width is not None and component.right is not None:
                x = self._width - component.right * scale - width
            else:
                raise Exception('Two of left, width and right must be provided')

            if component.top is not None and height is not None:
                y = component.top * scale
            elif component.top is not None and component.bottom is not None:
                y = component.top * scale
                height = self._height - component.bottom * scale - component.top * scale
            elif height is not None and component.bottom is not None:
                y = self._height - component.bottom * scale - height
            else:
                raise Exception('Two of top, height and bottom must be provided')
            
            component._x = int(x)
            component._y = int(y)
            component._width = int(width)
            component._height = int(height)

            component.layout()
    def draw(self, draw: ImageDraw, offset_x: int, offset_y: int):
        if self.background_color:
            draw.rectangle([(offset_x + self._x, offset_y + self._y), (offset_x + self._x + self._width - 1, offset_y + self._y + self._height - 1)], self.background_color)
        if self.border_width > 0 and self.border_color:
            draw.line([(offset_x + self._x, offset_y + self._y), (offset_x + self._x + self._width - 1, offset_y + self._y)], self.border_color, self.border_width)
            draw.line([(offset_x + self._x, offset_y + self._y + self._height - 1), (offset_x + self._x + self._width - 1, offset_y + self._y + self._height - 1)], self.border_color, self.border_width)
            draw.line([(offset_x + self._x, offset_y + self._y), (offset_x + self._x, offset_y + self._y + self._height - 1)], self.border_color, self.border_width)
            draw.line([(offset_x + self._x + self._width - 1, offset_y + self._y), (offset_x + self._x + self._width - 1, offset_y + self._y + self._height - 1)], self.border_color, self.border_width)

        if not self.components:
            return
        for component in self.components:
            component.draw(draw, offset_x + self._x, offset_y + self._y)
            
    def on_touch_down(self, touch_x: int, touch_y: int):
        if not self.components:
            return

        if self._touched_component:
            self._touched_component.on_touch_cancel()
            self._touched_component = None

        for component in reversed(self.components):
            if touch_x >= component._x and touch_x < component._x + component._width and touch_y >= component._y and touch_y < component._y + component._height:
                component.on_touch_down(touch_x - component._x, touch_y - component._y)
                self._touched_component = component
                break
    def on_touch_move(self, touch_x: int, touch_y: int):
        if not self.components:
            return

        for component in reversed(self.components):
            if touch_x >= component._x and touch_x < component._x + component._width and touch_y >= component._y and touch_y < component._y + component._height:
                if self._touched_component and self._touched_component != component:
                    self._touched_component.on_touch_cancel()
                    self._touched_component = None
                    break

                component.on_touch_move(touch_x - component._x, touch_y - component._y)
                break
    def on_touch_up(self, touch_x: int, touch_y: int):
        if not self.components:
            return

        for component in reversed(self.components):
            if touch_x >= component._x and touch_x < component._x + component._width and touch_y >= component._y and touch_y < component._y + component._height:
                if self._touched_component and self._touched_component != component:
                    self._touched_component.on_touch_cancel()
                    self._touched_component = None
                    break

                component.on_touch_up(touch_x - component._x, touch_y - component._y)
                self._touched_component = None
                break
    def on_touch_cancel(self):
        if self._touched_component:
            self._touched_component.on_touch_cancel()
            self._touched_component = None

class Label(Component):
    text: str
    font_path: str
    font_size: float
    auto_size: bool
    text_color: str

    _font: ImageFont = None
    _measure_target: Image = None

    def __init__(self, text: str = '', font_path: str = None, font_size: float = 10, auto_size: bool = True, text_color: str = (0, 0, 0), left: int = None, width: int = None, right: int = None, top: int = None, height: int = None, bottom: int = None):
        super().__init__(left=left, width=width, right=right, top=top, height=height, bottom=bottom)
        self.text = text
        self.font_path = font_path
        self.font_size = font_size
        self.auto_size = auto_size
        self.text_color = text_color

    def measure(self):
        self._font = FontManager.get_font(self.font_path, self.font_size * self.scale)

        width = self.width
        height = self.height

        if width is not None:
            width = width * self.scale
        if height is not None:
            height = height * self.scale

        if self.auto_size:
            if not self._measure_target:
                self._measure_target = Image.new('RGBA', (10, 10))

            draw = ImageDraw.Draw(self._measure_target)
            bbox = draw.multiline_textbbox((0, 0), self.text, self._font)

            if width is None:
                width = bbox[2]
            if height is None:
                height = bbox[3]

        return (width, height)
    def draw(self, draw: ImageDraw, offset_x: int, offset_y: int):
        draw.text((offset_x + self._x + int(self._width / 2), offset_y + self._y + int(self._height / 2)), self.text, fill=self.text_color, font=self._font, anchor='mm')

class Button(Label):
    background_color: tuple[int, int, int]
    pressed_color: tuple[int, int, int]
    border_color: tuple[int, int, int]
    border_width: int
    callback: FunctionType

    _is_pressed: bool = False

    def __init__(self, text: str = '', callback: FunctionType = None, font_path: str = None, font_size: float = 10, auto_size: bool = False, pressed_color: tuple[int, int, int] = (128, 128, 128), text_color: tuple[int, int, int] = None, background_color: tuple[int, int, int] = None, border_color: tuple[int, int, int] = None, border_width: int = 0, left: int = None, width: int = None, right: int = None, top: int = None, height: int = None, bottom: int = None):
        super().__init__(text=text, font_path=font_path, font_size=font_size, auto_size=auto_size, text_color=text_color, left=left, width=width, right=right, top=top, height=height, bottom=bottom)
        self.callback = callback
        self.background_color = background_color
        self.pressed_color = pressed_color
        self.border_color = border_color
        self.border_width = border_width

    def draw(self, draw: ImageDraw, offset_x: int, offset_y: int):
        if self.background_color:
            draw.rectangle([(offset_x + self._x, offset_y + self._y), (offset_x + self._x + self._width - 1, offset_y + self._y + self._height - 1)], self.background_color)
        if self._is_pressed:
            draw.rectangle([(offset_x + self._x, offset_y + self._y), (offset_x + self._x + self._width - 1, offset_y + self._y + self._height - 1)], self.pressed_color)

        if self.border_width > 0 and self.border_color:
            draw.line([(offset_x + self._x, offset_y + self._y), (offset_x + self._x + self._width, offset_y + self._y)], self.border_color, int(self.border_width * self.scale))
            draw.line([(offset_x + self._x, offset_y + self._y + self._height - 1), (offset_x + self._x + self._width, offset_y + self._y + self._height - 1)], self.border_color, int(self.border_width * self.scale))
            draw.line([(offset_x + self._x, offset_y + self._y), (offset_x + self._x, offset_y + self._y + self._height)], self.border_color, int(self.border_width * self.scale))
            draw.line([(offset_x + self._x + self._width - 1, offset_y + self._y), (offset_x + self._x + self._width - 1, offset_y + self._y + self._height)], self.border_color, int(self.border_width * self.scale))

        super().draw(draw, offset_x, offset_y)

    def on_touch_down(self, position_x: int, position_y: int):
        self._is_pressed = True
        self.on_refresh()
    def on_touch_up(self, position_x: int, position_y: int):
        if self._is_pressed and self.callback:
            self.callback()
        self._is_pressed = False
        self.on_refresh()
    def on_touch_cancel(self):
        self._is_pressed = False
        self.on_refresh()

class StackPanel(Panel):
    class Orientation(Enum):
        Vertical = 0
        Horizontal = 1
    class Alignment(Enum):
        Start = 0
        Center = 1
        End = 2

    orientation: Orientation
    alignment: Alignment

    def __init__(self, components: list[Component] = [], background_color: str = None, border_color: str = None, border_width: int = 0, left: int = None, width: int = None, right: int = None, top: int = None, height: int = None, bottom: int = None, orientation: Orientation = Orientation.Vertical, alignment: Alignment = Alignment.Center, layout_mode: Component.LayoutMode = Component.LayoutMode.Relative):
        super().__init__(components=components, background_color=background_color, border_color=border_color, border_width=border_width, left=left, width=width, right=right, top=top, height=height, bottom=bottom, layout_mode=layout_mode)
        self.orientation = orientation
        self.alignment = alignment

    def layout(self):
        if not self.components:
            return

        last_x = 0
        last_y = 0

        for component in self.components:
            component.parent = self
            component.scale = self.scale

            (width, height) = component.measure()

            scale = component.scale
            if self.layout_mode == Component.LayoutMode.Absolute:
                scale = 1

            x = 0
            y = 0

            if component.left is not None and width is not None:
                x = component.left * scale
            elif component.left is not None and component.right is not None:
                x = component.left * scale
                width = self._width - component.right * scale - component.left * scale
            elif width is not None and component.right is not None:
                x = self._width - component.right * scale - width
            elif width is None:
                raise Exception()

            if component.top is not None and height is not None:
                y = component.top * scale
            elif component.top is not None and component.bottom is not None:
                y = component.top * scale
                height = self._height - component.bottom * scale - component.top * scale
            elif height is not None and component.bottom is not None:
                y = self._height - component.bottom * scale - height
            elif height is None:
                raise Exception()

            if self.orientation == StackPanel.Orientation.Vertical:
                if self.alignment == StackPanel.Alignment.Start:
                    x = 0
                elif self.alignment == StackPanel.Alignment.Center:
                    x = int((self._width - width) / 2)
                elif self.alignment == StackPanel.Alignment.End:
                    x = self._width - width

                if component.top is not None:
                    last_y += component.top * component.scale

                y = last_y
                last_y += height

                if component.bottom is not None:
                    last_y += component.bottom * component.scale
                
            elif self.orientation == StackPanel.Orientation.Horizontal:
                if self.alignment == StackPanel.Alignment.Start:
                    y = 0
                elif self.alignment == StackPanel.Alignment.Center:
                    y = int((self._height - height) / 2)
                elif self.alignment == StackPanel.Alignment.End:
                    y = self._height - height

                if component.left is not None:
                    last_x += component.left * component.scale

                x = last_x
                last_x += width

                if component.right is not None:
                    last_x += component.right * component.scale

            component._x = int(x)
            component._y = int(y)
            component._width = int(width)
            component._height = int(height)

            component.layout()

class Picture(Component):
    image_path: str

    _image: Image = None

    def __init__(self, image_path: str = None, left: int = None, width: int = None, right: int = None, top: int = None, height: int = None, bottom: int = None):
        super().__init__(left=left, width=width, right=right, top=top, height=height, bottom=bottom)
        self.image_path = image_path

    def measure(self):
        self._image = Cache.get(self.image_path)
        if not self._image:
            self._image = Image.open(self.image_path).convert('RGBA')
            Cache.set(self.image_path, self._image)

        width = self.width
        height = self.height

        if width is not None:
            width = width * self.scale
        if height is not None:
            height = height * self.scale

        if width is None and height is None:
            width = self._image.width
            height = self._image.height
        elif width is None:
            width = int(height * self._image.width / self._image.height)
        elif height is None:
            height = int(width * self._image.height / self._image.width)

        size = (int(width), int(height))
        self._image = self._image.resize(size)
        return size
    def draw(self, draw: ImageDraw, offset_x: int, offset_y: int):
        draw._image.alpha_composite(self._image, (offset_x + self._x, offset_y + self._y))

class Switch(Component):
    pass

class ScrollPanel(Panel):
    pass


class Screen(Panel):
    components: list[Component] = []
    scale: float = 1
    background_color: tuple[int, int, int] = (255, 255, 255)

    def layout(self):
        self._width = self.width
        self._height = self.height
        super().layout()
    def capture(self):
        return Image.new('RGBA', (self.width, self.height), (0, 0, 0))
    def run(self):
        pass

    def on_refresh(self):
        self.draw()

class TouchFramebuffer(Screen):
    class Rotation(Enum):
        Normal = 0,
        Left = 90,
        Right = 270,
        UpsideDown = 180

    framebuffer_device_name: str = None
    input_device_path: str = None
    rotation: int = 0

    # Cache
    _target: Image = None
    _target_draw: ImageDraw = None

    def __init__(self, framebuffer_device: str, input_device: str = None, width: int = None, height: int = None, rotation: int = None):
        # Framebuffer handling
        path_match = re.search('^/dev/(fb[0-9]+)$', framebuffer_device)
        device_match = re.search('^(fb[0-9]+)$', framebuffer_device)
        
        if path_match:
            self.framebuffer_device_name = path_match[1]
        elif device_match:
            self.framebuffer_device_name = path_match[1]
        else:
            raise Exception('Provide a valid framebuffer device path')

        if not os.path.exists(f'/dev/{self.framebuffer_device_name}'):
            raise Exception('The provided framebuffer doesn\'t exist')

        if width and height:
            self.width = width
            self.height = height
        else:
            with open(f'/sys/class/graphics/{self.framebuffer_device_name}/virtual_size') as f:
                resolution = f.read()

                resolution_match = re.search('^([0-9]+),([0-9]+)$')
                if not resolution_match:
                    raise Exception('Could not retrieve framebuffer size')

                self.width = resolution_match[1]
                self.height = resolution_match[2]

        if rotation:
            self.rotation = rotation
        else:
            with open(f'/sys/class/graphics/{self.framebuffer_device_name}/rotate') as f:
                rotation = f.read()

            self.rotation = int(rotation)
        
        # Input device handling
        self.input_device_path = input_device

        self.touch_device = evdev.InputDevice(input_device)
        self.touch_last_x = 0
        self.touch_last_y = 0
        self.touch_down_builder = None
        self.touch_device.grab()

        # TODO: Setup direct mmap framebuffer access
        #fbdev = open( f"/dev/{fbN}", mode='r+b') # open R/W
        #fb = mmap.mmap( fbdev.fileno(), w * h * bpp//8, mmap.MAP_SHARED, mmap.PROT_WRITE|mmap.PROT_READ)

        # Image cache
        if self.rotation % 180 == 0:
            _target = Image.new('RGBA', (self.width, self.height), self.background_color)
        else:
            _target = Image.new('RGBA', (self.height, self.width), self.background_color)

        _target_draw = ImageDraw.Draw(_target)

    def capture(self):
        framebuffer_path = f'/dev/{self.framebuffer_device_name}'
        if USING_SIMULATOR:
            framebuffer_path = f'{RINKHALS_ROOT}/opt/rinkhals/ui/framebuffer_{KOBRA_MODEL_CODE}.bin'

        with open(framebuffer_path, 'rb') as f:
            framebuffer_bytes = f.read()

        if SCREEN_ROTATION % 180 == 90:
            framebuffer = Image.frombytes('RGBA', (SCREEN_HEIGHT, SCREEN_WIDTH), framebuffer_bytes, 'raw', 'BGRA')
        else:
            framebuffer = Image.frombytes('RGBA', (SCREEN_WIDTH, SCREEN_HEIGHT), framebuffer_bytes, 'raw', 'BGRA')

        framebuffer = framebuffer.rotate(SCREEN_ROTATION, expand = True)

        return framebuffer
    def draw(self):
        _target.paste(self.background_color, [0, 0, self.width, self.height])

        if not self.components:
            return

        for component in self.components:
            component.draw(_target_draw, 0, 0)

        target_bytes = _target.rotate(-self.rotation, expand = True).tobytes('raw', 'BGRA')
        with open(f'/dev/{self.framebuffer_device_name}', 'wb') as f:
            f.write(target_bytes)
    def run(self):
        while True:
            event = self.touch_device.read_one()
            if not event:
                break

            # Touch position
            if event.type == evdev.ecodes.EV_ABS:

                # For K3 / K2P
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

                # For KS1
                if event.code == evdev.ecodes.ABS_MT_POSITION_X:
                    self.touch_last_x = (event.value - TOUCH_CALIBRATION_MIN_X) / (TOUCH_CALIBRATION_MAX_X - TOUCH_CALIBRATION_MIN_X) * SCREEN_WIDTH
                    self.touch_last_x = min(max(0, int(self.touch_last_x)), SCREEN_WIDTH)
                    if self.touch_down_builder:
                        self.touch_down_builder[0] = self.touch_last_x
                elif event.code == evdev.ecodes.ABS_MT_POSITION_Y:
                    self.touch_last_y = (event.value - TOUCH_CALIBRATION_MIN_Y) / (TOUCH_CALIBRATION_MAX_Y - TOUCH_CALIBRATION_MIN_Y) * SCREEN_HEIGHT
                    self.touch_last_y = min(max(0, int(self.touch_last_y)), SCREEN_HEIGHT)
                    if self.touch_down_builder:
                        self.touch_down_builder[1] = self.touch_last_y

                if self.touch_down_builder and self.touch_down_builder[0] >= 0 and self.touch_down_builder[1] >= 0:
                    self.on_touch_down(self.touch_down_builder[0], self.touch_down_builder[1])
                    self.touch_down_builder = None
                else:
                    self.on_touch_move(self.touch_last_x, self.touch_last_y)

            # Touch action
            elif event.code == evdev.ecodes.BTN_TOUCH: # EV_KEY
                if time.time_ns() - self.last_screen_check > 5000000000:
                    self.last_screen_check = time.time_ns()

                    if not self.is_screen_on():
                        self.turn_on_screen()
                        return

                if event.value == 1:
                    self.touch_down_builder = [-1, -1]
                elif event.value == 0:
                    self.on_touch_up(self.touch_last_x, self.touch_last_y)

            time.sleep(0.1)

class SimulatorScreen(Screen):
    window = None
    quitting = False

    _target: Image = None
    _target_draw: ImageDraw = None

    def __init__(self, title: str, width: int, height: int):
        from tkinter import Tk, Label

        self.width = width
        self.height = height

        def on_closing():
            self.window.destroy()
            self.quitting = True
        def on_mouse_down(event):
            self.on_touch_down(event.x, event.y)
        def on_mouse_move(event):
            self.on_touch_move(event.x, event.y)
        def on_mouse_up(event):
            self.on_touch_up(event.x, event.y)

        self.window = Tk()
        self.window.title(title)
        self.window.geometry(f'{width}x{height}')
        self.window.resizable(False, False)
        self.window.configure(bg='black')
        self.window.update()

        self.window_panel = Label(self.window)
        self.window_panel.pack(fill = "both", expand = "yes")

        self.window.protocol("WM_DELETE_WINDOW", on_closing)
        self.window.bind('<Button-1>', on_mouse_down)
        self.window.bind('<B1-Motion>', on_mouse_move)
        self.window.bind('<ButtonRelease-1>', on_mouse_up)
        
        # Image cache
        self._target = Image.new('RGBA', (self.width, self.height), (0, 0, 0))
        self._target_draw = ImageDraw.Draw(self._target)

    def capture(self):
        return _target.copy()
    def draw(self):
        from PIL import ImageTk
        
        self._target.paste((0, 0, 0), [0, 0, self.width, self.height])

        if not self.components:
            return

        for component in self.components:
            component.draw(self._target_draw, 0, 0)

        image_tk = ImageTk.PhotoImage(self._target)
        globals()['__image_tk'] = image_tk

        self.window_panel.config(image = image_tk)
        self.window.update()
    def run(self):
        while not self.quitting:
            self.window.update()
            time.sleep(0.1)
