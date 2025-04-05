import os
import time
import re
import subprocess
import threading
import logging

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

    tag = None
    parent = None
    visible: bool = True
    left: int
    width: int
    right: int
    top: int
    height: int
    bottom: int
    layout_mode: LayoutMode = LayoutMode.Relative
    scale: int = 1

    _laid_out: bool = False
    _x: int = None
    _width: int = None
    _y: int = None
    _height: int = None

    def __init__(self, left: int = None, width: int = None, right: int = None, top: int = None, height: int = None, bottom: int = None, layout_mode: LayoutMode = LayoutMode.Relative, tag=None, **kwargs):
        self.left = left
        self.width = width
        self.right = right
        self.top = top
        self.height = height
        self.bottom = bottom
        self.layout_mode = layout_mode
        self.tag = tag

    def measure(self):
        width = self.width
        height = self.height

        scale = self.scale
        if self.layout_mode == Component.LayoutMode.Absolute:
            scale = 1

        if width is not None:
            width = width * scale
        if height is not None:
            height = height * scale

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
    border_radius: int
    touch_callback: FunctionType

    _touched_component = None

    def __init__(self, components: list[Component] = [], background_color: str = None, border_color: str = None, border_width: int = 0, border_radius=0, layout_mode: Component.LayoutMode = Component.LayoutMode.Relative, touch_callback=None, **kwargs):
        super().__init__(layout_mode=layout_mode, **kwargs)
        self.components = components
        self.background_color = background_color
        self.border_color = border_color
        self.border_width = border_width
        self.border_radius = border_radius
        self.touch_callback = touch_callback

    def layout(self):
        super().layout()

        if not self.components:
            return

        for component in self.components:
            if not component.visible:
                continue

            component.parent = self
            component.scale = self.scale

            (width, height) = component.measure()

            scale = component.scale
            if self.layout_mode == Component.LayoutMode.Absolute:
                scale = 1

            if component.left is not None and width is not None:
                x = component.left * scale
            elif component.left is not None and component.right is not None:
                x = component.left * scale
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
            component._laid_out = True

            component.layout()
    def draw(self, draw: ImageDraw, offset_x: int, offset_y: int):
        if self._width == 0 or self._height == 0:
            return

        if self.background_color:
            if len(self.background_color) == 4:
                buffer = Image.new('RGBA', (self._width, self._height), self.background_color)
                draw._image.alpha_composite(buffer, (offset_x + self._x, offset_y + self._y))
            else:
                draw.rectangle([(offset_x + self._x, offset_y + self._y), (offset_x + self._x + self._width - 1, offset_y + self._y + self._height - 1)], self.background_color)

        if self.border_width > 0 and self.border_color:
            draw.line([(offset_x + self._x, offset_y + self._y), (offset_x + self._x + self._width - 1, offset_y + self._y)], self.border_color, self.border_width)
            draw.line([(offset_x + self._x, offset_y + self._y + self._height - 1), (offset_x + self._x + self._width - 1, offset_y + self._y + self._height - 1)], self.border_color, self.border_width)
            draw.line([(offset_x + self._x, offset_y + self._y), (offset_x + self._x, offset_y + self._y + self._height - 1)], self.border_color, self.border_width)
            draw.line([(offset_x + self._x + self._width - 1, offset_y + self._y), (offset_x + self._x + self._width - 1, offset_y + self._y + self._height - 1)], self.border_color, self.border_width)

        if not self.components:
            return
        for component in self.components:
            if not component.visible or not component._laid_out:
                continue
            component.draw(draw, offset_x + self._x, offset_y + self._y)
            
    def on_touch_down(self, touch_x: int, touch_y: int):
        if not self.components:
            return

        self.on_touch_cancel()

        for component in reversed(self.components):
            if not component.visible or not component._laid_out:
                continue
            if touch_x >= component._x and touch_x < component._x + component._width and touch_y >= component._y and touch_y < component._y + component._height:
                component.on_touch_down(touch_x - component._x, touch_y - component._y)
                self._touched_component = component
                return

        if self.touch_callback:
            self.touch_callback()
    def on_touch_move(self, touch_x: int, touch_y: int):
        if not self.components:
            return

        for component in reversed(self.components):
            if not component.visible or not component._laid_out:
                continue
            if touch_x >= component._x and touch_x < component._x + component._width and touch_y >= component._y and touch_y < component._y + component._height:
                if self._touched_component and self._touched_component != component:
                    self._touched_component.on_touch_cancel()
                    self._touched_component = None
                    return

                component.on_touch_move(touch_x - component._x, touch_y - component._y)
                return

        self.on_touch_cancel()
    def on_touch_up(self, touch_x: int, touch_y: int):
        if not self.components:
            return

        for component in reversed(self.components):
            if not component.visible or not component._laid_out:
                continue
            if touch_x >= component._x and touch_x < component._x + component._width and touch_y >= component._y and touch_y < component._y + component._height:
                if self._touched_component and self._touched_component != component:
                    self._touched_component.on_touch_cancel()
                    self._touched_component = None
                    return

                component.on_touch_up(touch_x - component._x, touch_y - component._y)
                self._touched_component = None
                return

        self.on_touch_cancel()
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
    text_align: str
    text_padding: int

    _font: ImageFont = None
    _measure_target: Image = None

    def __init__(self, text='', font_path=None, font_size=10, auto_size=True, text_color=(0, 0, 0), text_align='mm', text_padding=0, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.font_path = font_path
        self.font_size = font_size
        self.auto_size = auto_size
        self.text_color = text_color
        self.text_align = text_align
        self.text_padding = text_padding

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
        align = 'center'

        if self.text_align and self.text_align[0] == 'l':
            x = offset_x + self._x + self.text_padding * self.scale
            align = 'left'
        elif self.text_align and self.text_align[0] == 'r':
            x = offset_x + self._x + self._width - self.text_padding * self.scale
            align = 'right'
        else:
            x = offset_x + self._x + int(self._width / 2)

        if self.text_align and self.text_align[1] == 't':
            y = offset_y + self._y + self.text_padding * self.scale
        elif self.text_align and self.text_align[1] == 'b':
            y = offset_y + self._y + self._height - self.text_padding * self.scale
        else:
            y = offset_y + self._y + int(self._height / 2)

        if '\n' in self.text:
            draw.multiline_text((x, y), self.text, fill=self.text_color, font=self._font, anchor=self.text_align, align=align)
        else:
            draw.text((x, y), self.text, fill=self.text_color, font=self._font, anchor=self.text_align)

class Button(Label):
    background_color: tuple[int, int, int]
    pressed_color: tuple[int, int, int]
    disabled_text_color: tuple[int, int, int]
    border_color: tuple[int, int, int]
    border_width: int
    border_radius: int
    disabled: bool
    callback: FunctionType

    _text_color: tuple[int, int, int]
    _is_pressed: bool = False

    def __init__(self, text='', callback=None, auto_size=False, background_color=None, pressed_color=(128, 128, 128), disabled_text_color=(64, 64, 64), text_color=(0, 0, 0), border_color=None, border_width=0, border_radius=0, disabled=False, **kwargs):
        super().__init__(text=text, auto_size=auto_size, **kwargs)
        self.callback = callback
        self.background_color = background_color
        self.pressed_color = pressed_color
        self.disabled_text_color = disabled_text_color
        self._text_color = text_color
        self.border_color = border_color
        self.border_width = border_width
        self.border_radius = border_radius
        self.disabled = disabled

    def layout(self):
        self.text_color = self.disabled_text_color if self.disabled else self._text_color
    def draw(self, draw: ImageDraw, offset_x: int, offset_y: int):
        xy = [(offset_x + self._x, offset_y + self._y), (offset_x + self._x + self._width - 1, offset_y + self._y + self._height - 1)]
        radius = self.border_radius or 0
        fill = self.pressed_color if self._is_pressed else self.background_color

        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=self.border_color, width=self.border_width)
        super().draw(draw, offset_x, offset_y)

    def on_touch_down(self, position_x: int, position_y: int):
        if self.disabled:
            return
        self._is_pressed = True
        self.on_refresh()
    def on_touch_up(self, position_x: int, position_y: int):
        if self._is_pressed:
            self.on_clicked()
        self._is_pressed = False
        self.on_refresh()
    def on_touch_cancel(self):
        self._is_pressed = False
        self.on_refresh()

    def on_clicked(self):
        if self.callback:
            self.callback()

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
    auto_size: bool

    def __init__(self, components=[], orientation=Orientation.Vertical, alignment=Alignment.Center, layout_mode=Component.LayoutMode.Relative, auto_size=False, **kwargs):
        super().__init__(components=components, layout_mode=layout_mode, **kwargs)
        self.orientation = orientation
        self.alignment = alignment
        self.auto_size = auto_size

    def measure(self):
        if self.auto_size:
            scale = self.scale
            if self.parent.layout_mode == Component.LayoutMode.Absolute:
                scale = 1

            if self.width is not None:
                self._width = self.width * scale
            elif self.left is not None and self.right is not None:
                self._width = self.parent._width - self.right * scale - self.left * scale
            else:
                self._width = None

            if self.height is not None:
                self._height = self.height * scale
            elif self.top is not None and self.bottom is not None:
                self._height = self.parent._height - self.bottom * scale - self.top * scale
            else:
                self._height = None

            self.layout()
            max_x = 0
            max_y = 0

            for component in self.components:
                if not component.visible or not component._laid_out:
                    continue
                max_x = max(max_x, component._x + component._width + (component.right or 0) * component.scale)
                max_y = max(max_y, component._y + component._height + (component.bottom or 0) * component.scale)
            
            if self._width is not None:
                max_x = max(self._width, max_x)
            if self._height is not None:
                max_y = max(self._height, max_y)
            
            return (max_x, max_y)
        else:
            return super().measure()
    def layout(self):
        if not self.components:
            return

        last_x = 0
        last_y = 0

        for component in self.components:
            if not component.visible:
                continue

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
                    last_y += component.top * scale

                y = last_y
                last_y += height

                if component.bottom is not None:
                    last_y += component.bottom * scale
                
            elif self.orientation == StackPanel.Orientation.Horizontal:
                if self.alignment == StackPanel.Alignment.Start:
                    y = 0
                elif self.alignment == StackPanel.Alignment.Center:
                    y = int((self._height - height) / 2)
                elif self.alignment == StackPanel.Alignment.End:
                    y = self._height - height

                if component.left is not None:
                    last_x += component.left * scale

                x = last_x
                last_x += width

                if component.right is not None:
                    last_x += component.right * scale

            component._x = int(x)
            component._y = int(y)
            component._width = int(width)
            component._height = int(height)
            component._laid_out = True

            component.layout()

class Picture(Component):
    image: Image = None

    _image: Image = None

    def __init__(self, image_path: str = None, image: Image = None, left: int = None, width: int = None, right: int = None, top: int = None, height: int = None, bottom: int = None):
        super().__init__(left=left, width=width, right=right, top=top, height=height, bottom=bottom)
        
        if image:
            self.image = image
        elif image_path:
            image = Cache.get(image_path)
            if not image:
                image = Image.open(image_path).convert('RGBA')
                Cache.set(image_path, image)
            self.image = image

    def measure(self):
        if not self.image:
            return (0, 0)

        width = self.width
        height = self.height

        if width is not None:
            width = width * self.scale
        if height is not None:
            height = height * self.scale

        if width is None and height is None:
            width = self.image.width
            height = self.image.height
        elif width is None:
            width = int(height * self.image.width / self.image.height)
        elif height is None:
            height = int(width * self.image.height / self.image.width)

        size = (int(width), int(height))
        self._image = self.image.resize(size)
        return size
    def draw(self, draw: ImageDraw, offset_x: int, offset_y: int):
        if self._image:
            draw._image.alpha_composite(self._image, (offset_x + self._x, offset_y + self._y))

class CheckBox(Button):
    checked: bool
    check_symbol: str
    callback: FunctionType

    def __init__(self, callback=None, checked=False, check_symbol='×', *args, **kwargs):
        super().__init__(*args, text='', **kwargs)
        self.checked = checked
        self.check_symbol = check_symbol
        self.callback = callback

    def layout(self):
        self.text = self.check_symbol if self.checked else ''

    def on_clicked(self):
        self.checked = not self.checked
        if self.callback:
            self.callback(self.checked)
        self.layout()
        self.on_refresh()

class ScrollPanel(Panel):
    class Orientation(Enum):
        Vertical = 0
        Horizontal = 1

    inner_panel = None
    components = None
    orientation = None
    scroll_x = 0
    scroll_y = 0
    distance_threshold: int

    _scroll_start = None
    _touch_down = None

    def __init__(self, orientation=Orientation.Vertical, distance_threshold=16, **kwargs):
        super().__init__(**kwargs)
        self.inner_panel = StackPanel(auto_size=True, orientation=StackPanel.Orientation(orientation.value), **kwargs)
        self.orientation = orientation
        self.distance_threshold = distance_threshold
        self.components = self.inner_panel.components

    def layout(self):
        self.scroll_x = 0
        self.scroll_y = 0

        self.inner_panel.parent = self
        self.inner_panel.scale = self.scale

        if self.orientation == ScrollPanel.Orientation.Vertical:
            self.inner_panel._width = self._width
        elif self.orientation == ScrollPanel.Orientation.Horizontal:
            self.inner_panel._height = self._height

        (width, height) = self.inner_panel.measure()
        
        self.inner_panel._x = 0
        self.inner_panel._y = 0

        if self.orientation == ScrollPanel.Orientation.Vertical:
            self.inner_panel._height = int(height)
        elif self.orientation == ScrollPanel.Orientation.Horizontal:
            self.inner_panel._width = int(width)
        
        self.inner_panel.layout()
    def draw(self, draw: ImageDraw, offset_x: int, offset_y: int):
        self.inner_panel.draw(draw, offset_x + self._x - self.scroll_x, offset_y + self._y - self.scroll_y)

    def on_touch_down(self, position_x: int, position_y: int):
        self._touch_down = (position_x, position_y)
        self._scroll_start = None
        self.inner_panel.on_touch_down(position_x + self.scroll_x, position_y + self.scroll_y)
    def on_touch_move(self, touch_x: int, touch_y: int):
        if not self._touch_down:
            return

        if self._scroll_start is None and self.inner_panel._height > self._height:
            distance = pow(pow(touch_x - self._touch_down[0], 2) + pow(touch_y - self._touch_down[1], 2), 0.5)
            if distance > self.distance_threshold * self.scale:
                logging.debug('Start scrolling')
                if self.orientation == ScrollPanel.Orientation.Vertical:
                    self._scroll_start = self.scroll_y
                elif self.orientation == ScrollPanel.Orientation.Horizontal:
                    self._scroll_start = self.scroll_x

        if self._scroll_start is not None:
            if self.orientation == ScrollPanel.Orientation.Vertical:
                self.scroll_y = self._scroll_start + self._touch_down[1] - touch_y
                self.scroll_y = max(0, self.scroll_y)
                self.scroll_y = min(self.scroll_y, self.inner_panel._height - self._height)
            elif self.orientation == ScrollPanel.Orientation.Horizontal:
                self.scroll_x = self._scroll_start + self._touch_down[0] - touch_x
                self.scroll_x = max(0, self.scroll_x)
                self.scroll_x = min(self.scroll_x, self.inner_panel._width - self._width)

            self.parent.on_refresh()
        else:
            self.inner_panel.on_touch_move(touch_x + self.scroll_x, touch_y + self.scroll_y)
    def on_touch_up(self, position_x: int, position_y: int):
        if not self._touch_down:
            return
        
        if self._scroll_start is not None:
            self._scroll_start = None
            self.inner_panel.on_touch_cancel()
        else:
            self.inner_panel.on_touch_up(position_x + self.scroll_x, position_y + self.scroll_y)
    def on_touch_cancel(self):
        self._touch_down = None
        self._scroll_start = None
        self.inner_panel.on_touch_cancel()

class CallbackComponent(Component):
    draw_callback = None

    def __init__(self, draw_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.draw_callback = draw_callback

    def draw(self, draw: ImageDraw, offset_x: int, offset_y: int):
        if self.draw_callback:
            self.draw_callback(draw, offset_x, offset_y)


class Screen(Panel):
    components: list[Component] = []
    scale: float = 1
    background_color: tuple[int, int, int] = None
    draw_lock = threading.Lock()

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
    touch_calibration: int = 0

    # Cache
    _target: Image = None
    _target_draw: ImageDraw = None
    _last_screen_check: int = 0
    _dirty = True

    def __init__(self, framebuffer_device: str, input_device: str = None, width: int = None, height: int = None, rotation: int = None, touch_calibration: tuple[int, int, int, int] = None):
        import evdev

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

                resolution_match = re.search('^([0-9]+),([0-9]+)$', resolution)
                if not resolution_match:
                    raise Exception('Could not retrieve framebuffer size')

                self.width = int(resolution_match[1])
                self.height = int(resolution_match[2])

        if rotation:
            self.rotation = rotation
        else:
            with open(f'/sys/class/graphics/{self.framebuffer_device_name}/rotate') as f:
                rotation = f.read()

            self.rotation = int(rotation)

        if self.rotation % 180 == 90:
            (self.width, self.height) = (self.height, self.width)
        
        # Input device handling
        self.input_device_path = input_device

        self.touch_device = evdev.InputDevice(input_device)
        self.touch_last_x = 0
        self.touch_last_y = 0
        self.touch_down_builder = None
        self.touch_device.grab()

        self.touch_calibration = touch_calibration or (0, 0, self.width, self.height)

        # TODO: Setup direct mmap framebuffer access
        #fbdev = open( f"/dev/{fbN}", mode='r+b') # open R/W
        #fb = mmap.mmap( fbdev.fileno(), w * h * bpp//8, mmap.MAP_SHARED, mmap.PROT_WRITE|mmap.PROT_READ)

        # Image cache
        self._target = Image.new('RGBA', (self.width, self.height), self.background_color)
        self._target_draw = ImageDraw.Draw(self._target, 'RGBA')

    def capture(self):
        framebuffer_path = f'/dev/{self.framebuffer_device_name}'
        with open(framebuffer_path, 'rb') as f:
            framebuffer_bytes = f.read()

        if self.rotation % 180 == 90:
            framebuffer = Image.frombytes('RGBA', (self.height, self.width), framebuffer_bytes, 'raw', 'BGRA')
        else:
            framebuffer = Image.frombytes('RGBA', (self.width, self.height), framebuffer_bytes, 'raw', 'BGRA')

        framebuffer = framebuffer.rotate(self.rotation, expand = True)
        return framebuffer
    def draw(self):
        self._dirty = True
    def run(self):
        import evdev

        pending_touch_up = None
        pending_touch_up_expiration = 0
        is_touch_down = False

        while True:
            now = time.time() * 1000
            event = self.touch_device.read_one()

            if not event:
                if pending_touch_up and now > pending_touch_up_expiration:
                    logging.debug(f'-- TOUCH_UP ({pending_touch_up[0]}, {pending_touch_up[1]})')
                    is_touch_down = False
                    with self.draw_lock:
                        self.on_touch_up(pending_touch_up[0], pending_touch_up[1])
                    pending_touch_up = None

                if self._dirty:
                    self._dirty = False
                    self.force_draw()
                else:
                    time.sleep(0.1)
                continue

            # Touch position
            if event.type == evdev.ecodes.EV_ABS:

                # Swap X and Y if the screen is sideways
                if self.rotation % 180 == 90:
                    if event.code == evdev.ecodes.ABS_X:
                        event.code = evdev.ecodes.ABS_Y
                    elif event.code == evdev.ecodes.ABS_Y:
                        event.code = evdev.ecodes.ABS_X

                # Single touch
                if event.code == evdev.ecodes.ABS_X or event.code == evdev.ecodes.ABS_MT_POSITION_X:
                    self.touch_last_x = (event.value - self.touch_calibration[0]) / (self.touch_calibration[2] - self.touch_calibration[0]) * self.width
                    self.touch_last_x = min(max(0, int(self.touch_last_x)), self.width)
                    if self.touch_down_builder:
                        self.touch_down_builder[0] = self.touch_last_x
                elif event.code == evdev.ecodes.ABS_Y or event.code == evdev.ecodes.ABS_MT_POSITION_Y:
                    self.touch_last_y = (event.value - self.touch_calibration[1]) / (self.touch_calibration[3] - self.touch_calibration[1]) * self.height
                    self.touch_last_y = min(max(0, int(self.touch_last_y)), self.height)
                    if self.touch_down_builder:
                        self.touch_down_builder[1] = self.touch_last_y

                if self.touch_down_builder and self.touch_down_builder[0] >= 0 and self.touch_down_builder[1] >= 0:
                    #logging.debug(f'{now} {event} > TOUCH_DOWN temporary')
                    if not pending_touch_up:
                        logging.debug(f'-- TOUCH_DOWN ({self.touch_down_builder[0]}, {self.touch_down_builder[1]})')
                        is_touch_down = True
                        with self.draw_lock:
                            self.on_touch_down(self.touch_down_builder[0], self.touch_down_builder[1])
                    pending_touch_up = None
                    self.touch_down_builder = None
                else:
                    if is_touch_down:
                        with self.draw_lock:
                            self.on_touch_move(self.touch_last_x, self.touch_last_y)

            # Touch action
            elif event.code == evdev.ecodes.BTN_TOUCH: # EV_KEY
                if time.time_ns() - self._last_screen_check > 5000000000:
                    self._last_screen_check = time.time_ns()

                    if not self.is_screen_on():
                        self.turn_on_screen()
                        return

                if event.value == 1:
                    self.touch_down_builder = [-1, -1]
                elif event.value == 0:
                    #logging.debug(f'{now} {event} > TOUCH_UP temporary')
                    pending_touch_up_expiration = now + 100
                    pending_touch_up = (self.touch_last_x, self.touch_last_y)

    def force_draw(self):
        if self.background_color is not None:
            self._target.paste(self.background_color, [0, 0, self.width, self.height])

        if not self.components:
            return

        for component in self.components:
            if not component.visible or not component._laid_out:
                continue
            with self.draw_lock:
                component.draw(self._target_draw, 0, 0)

        target_bytes = self._target.rotate(-self.rotation, expand = True).tobytes('raw', 'BGRA')
        with open(f'/dev/{self.framebuffer_device_name}', 'wb') as f:
            f.write(target_bytes)

        logging.debug('Draw completed')

    def shell(self, command):
        result = subprocess.check_output(['sh', '-c', command])
        result = result.decode('utf-8').strip()
        logging.info(f'Shell "{command}" => "{result}"')
        return result
    def is_screen_on(self):
        brightness = self.shell('cat /sys/class/backlight/backlight/brightness')
        return brightness != '0'
    def turn_on_screen(self):
        self.shell('echo 255 > /sys/class/backlight/backlight/brightness')
    def turn_off_screen(self):
        self.shell('echo 0 > /sys/class/backlight/backlight/brightness')

class SimulatorScreen(Screen):
    window = None
    quitting = False

    _target: Image = None
    _target_draw: ImageDraw = None
    _dirty = True

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
        self._target_draw = ImageDraw.Draw(self._target, 'RGBA')

    def capture(self):
        return self._target.copy()
    def draw(self):
        self._dirty = True
    def run(self):
        while not self.quitting:
            self.window.update()
            if self._dirty:
                self.force_draw()
                self._dirty = False
            else:
                time.sleep(0.05)

    def force_draw(self):
        from PIL import ImageTk
        
        if self.background_color is not None:
            self._target.paste(self.background_color, [0, 0, self.width, self.height])

        if not self.components:
            return

        for component in self.components:
            if not component.visible or not component._laid_out:
                continue
            component.draw(self._target_draw, 0, 0)

        image_tk = ImageTk.PhotoImage(self._target)
        globals()['__image_tk'] = image_tk

        self.window_panel.config(image = image_tk)
        self.window.update()

        logging.debug('Draw completed')
