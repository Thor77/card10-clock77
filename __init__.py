import os
import display as mod_display
import utime
import leds
import bme680
import color
import buttons


# TODO: read this from config
ENABLE_LED = True
BRIGHTNESS = 200

DIGITS = [
    (True, True, True, True, True, True, False),
    (False, True, True, False, False, False, False),
    (True, True, False, True, True, False, True),
    (True, True, True, True, False, False, True),
    (False, True, True, False, False, True, True),
    (True, False, True, True, False, True, True),
    (True, False, True, True, True, True, True),
    (True, True, True, False, False, False, False),
    (True, True, True, True, True, True, True),
    (True, True, True, True, False, True, True)
]

MONTH_STRING = [
    'Jan', 'Feb', 'Mar', 'Apr', 'Mai', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
]

BATTERY_COLOR_GOOD = [0, 230, 0]
BATTERY_COLOR_OK = [255, 215, 0]
BATTERY_COLOR_BAD = [255, 0, 0]

# structure: (start, end, buildup, teardown)
events = [
    ((2019, 8, 21), (2019, 8, 25), 5, 5),
    ((2019, 12, 27), (2019, 12, 30), 5, 5)
]


def get_ccc_day():
    '''
    Return day of current CCC event
    '''
    (year, month, day, hour, minute, seconds, weekday, _yday) = \
        utime.localtime()
    for start, end, buildup, teardown in events:
        start_year, end_year = start[0], end[0]
        start_month, end_month = start[1], end[1]
        start_day, end_day = start[2], end[2]
        if year in range(start_year, end_year + 1) \
           and month in range(start_month, end_month + 1) \
           and day in range(start_day - buildup, end_day + 1 + teardown):
            color = (255, 0, 0) \
                if day < start_day or day > end_day else (0, 255, 0)
            return day - (start_day - 1), color


def get_battery_color(voltage):
    if voltage > 3.8:
        return BATTERY_COLOR_GOOD
    if voltage > 3.6:
        return BATTERY_COLOR_OK
    return BATTERY_COLOR_BAD


class Rainbow:
    '''
    Forked from https://badge.team/projects/rainbowrunnerng
    '''
    SMTH = 260
    LED_COUNT = 10 + 1  # add one for convenience
    # Calculate the HSV color steps for the 11 LEDs
    STEP = int(SMTH / LED_COUNT)

    def __init__(self):
        leds.clear()
        self.states = []
        self.setup()

    def setup(self):
        # prepare the initial color for each of the 11 LEDs
        for i in range(0, self.LED_COUNT):
            self.states.append(int(self.STEP * i))

    def step(self):
        # set every LED to its current color value
        for i in range(0, self.LED_COUNT):
            leds.prep_hsv(i, [self.states[i], 1, 0.5])
        leds.update()
        leds.dim_top(3)
        # wait a certain amount of time
        utime.sleep(0.1)
        # prepare the next color for each LED
        for i in range(0, self.LED_COUNT):
            self.states[i] = (self.states[i] + self.STEP) % self.SMTH

    def stop(self):
        leds.clear()


class Clock:
    '''
    Forked from https://badge.team/projects/yet_another_digital_clock
    '''
    def loop(self):
        rainbow = Rainbow()
        bme680.init()
        led_enabled = ENABLE_LED
        with mod_display.open() as display:
            display.backlight(25)
            while True:
                self.update_clock(display)
                if buttons.read(buttons.BOTTOM_RIGHT):
                    print('button pressed')
                    led_enabled = not led_enabled
                    if not led_enabled:
                        # turn off leds
                        rainbow.stop()
                for _ in range(5):
                    if led_enabled:
                        rainbow.step()
                    utime.sleep(0.1)

    def render_battery(self, display, voltage):
        color = get_battery_color(voltage)
        xe = 160
        if voltage < 3.6:
            xe = 120
        elif voltage < 3.8:
            xe = 140
        elif voltage < 4.0:
            xe = 160
        display.rect(0, 52, xe, 57, filled=True, col=color)

    def render_date(self, display, date, fg):
        display.print(date, fg=fg, posx=0, posy=60)

    def render_temperature(self, display, temperature):
        display.print(
            '{:2.0f}C'.format(temperature),
            posx=115, posy=60, fg=color.WHITE
        )

    def ceilDiv(self, a, b):
            return (a + (b - 1)) // b

    def tipHeight(self, w):
            return self.ceilDiv(w, 2) - 1

    def drawTip(self, d, x, y, w, c, invert=False, swapAxes=False):
        h = self.tipHeight(w)
        for dy in range(h):
            for dx in range(dy + 1, w - 1 - dy):
                px = x + dx
                py = y + dy if not invert else y + h - 1 - dy
                if swapAxes:
                    px, py = py, px
                d.pixel(px, py, col=c)

    def drawSeg(self, d, x, y, w, h, c, swapAxes=False):
        tip_h = self.tipHeight(w)
        body_h = h - 2 * tip_h

        self.drawTip(d, x, y, w, c, invert=True, swapAxes=swapAxes)

        px1, px2 = x, x + w
        py1, py2 = y + tip_h, y + tip_h + body_h
        if swapAxes:
            px1, px2, py1, py2 = py1, py2, px1, px2
        d.rect(px1, py1, px2, py2, col=c)

        self.drawTip(d, x, y + tip_h + body_h, w, c, invert=False, swapAxes=swapAxes)

    def drawGridSeg(self, d, x, y, w, l, c, swapAxes=False):
        sw = w - 2
        tip_h = self.tipHeight(sw)

        x = x * w
        y = y * w
        l = (l - 1) * w
        self.drawSeg(d, x + 1, y + tip_h + 3, sw, l - 3, c, swapAxes=swapAxes)

    def drawGridVSeg(self, d, x, y, w, l, c):
        self.drawGridSeg(d, x, y, w, l, c)

    def drawGridHSeg(self, d, x, y, w, l, c):
        self.drawGridSeg(d, y, x, w, l, c, swapAxes=True)

    def drawGrid7Seg(self, d, x, y, w, segs, c):
        if segs[0]:
            self.drawGridHSeg(d, x, y, w, 4, c)
        if segs[1]:
            self.drawGridVSeg(d, x + 3, y, w, 4, c)
        if segs[2]:
            self.drawGridVSeg(d, x + 3, y + 3, w, 4, c)
        if segs[3]:
            self.drawGridHSeg(d, x, y + 6, w, 4, c)
        if segs[4]:
            self.drawGridVSeg(d, x, y + 3, w, 4, c)
        if segs[5]:
            self.drawGridVSeg(d, x, y, w, 4, c)
        if segs[6]:
            self.drawGridHSeg(d, x, y + 3, w, 4, c)

    def renderNum(self, d, num, x, c):
        self.drawGrid7Seg(d, x, 0, 7, DIGITS[num // 10], c)
        self.drawGrid7Seg(d, x + 5, 0, 7, DIGITS[num % 10], c)

    def renderColon(self, d, c):
        self.drawGridVSeg(d, 11, 2, 7, 2, c)
        self.drawGridVSeg(d, 11, 4, 7, 2, c)

    def update_clock(self, display):
        fgcol = (55 * BRIGHTNESS, 55 * BRIGHTNESS, 55 * BRIGHTNESS)
        display.clear()
        (year, month, day, hour, minute, seconds, weekday, _yday) = utime.localtime()
        self.renderNum(display, hour, 1, fgcol)
        self.renderNum(display, minute, 13, fgcol)
        self.renderColon(display, fgcol)
        self.render_battery(display, os.read_battery())
        temperature, humidity, pressure, resistance = bme680.get_data()
        self.render_temperature(display, temperature)
        ccc_day = get_ccc_day()
        if ccc_day:
            date = 'Day {}'.format(ccc_day[0])
            date_color = ccc_day[1]
        else:
            date = '{}.{}'.format(day, MONTH_STRING[month - 1])
            date_color = (255, 255, 255)
        self.render_date(display, date, date_color)
        display.update()


clock = Clock()
clock.loop()
