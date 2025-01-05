from machine import UART, Pin
import time
from enum import Enum

class Error(Exception):
    pass

class InputError(Error):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class StateError(Error):
    def __init__(self, message):
        self.message = message

class Roomba:
    _baudrate = 57600
    sci_states = Enum('status', [('off', 0), ('passive', 1), ('safe', 2), ('full', 3), ('undefined', -1)])
    charging_states = Enum('status', [('not charging', 0), ('charging recovery', 1), ('charging', 2), ('trickle charging', 3), ('waiting', 4), ('charger error', 5), ('unknown', -1)])
    def __init__(self, tx_pin, rx_pin, dd_pin, uart_id=0):
        self._uart = UART(uart_id, Roomba._baudrate, Pin(tx_pin), Pin(rx_pin))
        self._uart.init(Roomba._baudrate, bits=8, parity=None, stop=1)
        self._SCI_status = Roomba.sci_states.undefined
        self._device_detect = Pin(dd_pin, Pin.OUT, Pin.OPEN_DRAIN)
        self._device_detect.off()
    
    def initialize_sci(self):
        self.send(128)
        self._SCI_status = self.sci_states.passive
        time.sleep_ms(25)

    def set_baudrate(self, baudrate):
        validBaudrates = {300: 0, 600:1, 1200: 2, 2400: 3, 4800: 4, 9600: 5, 14400: 6, 1920: 7, 28800: 8, 38400: 9, 57600: 10, 115200: 11}
        if baudrate not in validBaudrates.keys:
            raise InputError(baudrate, "Baudrate must be 300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600 or 115200, but was {baudrate}")
        else:
            translatedBaudrate = validBaudrates[baudrate]
            self.send([129, translatedBaudrate])
            time.sleep_ms(150)
            self._uart.deinit()
            self._uart.init(Roomba._baudrate, bits=8, parity=None, stop=1)
    
    def set_sci_safe(self):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        elif self._SCI_status is self.sci_states.safe:
            return
        elif self._SCI_status is self.sci_states.passive:
            self.send(130)
            time.sleep_ms(25)
            self._SCI_status = self.sci_states.safe
        elif self._SCI_status is self.sci_states.full:
            self.send(131)
            time.sleep_ms(25)
            self._SCI_status = self.sci_states.safe
        else:
            raise StateError("SCI is in an unknown state, something has gone catastrophically wrong")
        
    def set_sci_full(self):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        if self._SCI_status is self.sci_states.passive:
            self.set_sci_safe()
        elif self._SCI_status is self.sci_states.full:
            return
        elif self._SCI_status is self.sci_states.safe:
            self.send(132)
            time.sleep_ms(25)
            self._SCI_status = self.sci_states.full
        else:
            raise StateError("SCI is not in Safe mode, but in {self._SCI_status} mode. You have to explicitly traverse the states to minimize side effects.")
    
    def set_sci_passive(self):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        if(self._SCI_status is self.sci_states.full or self._SCI_status is self.sci_states.safe):
            self.send(133)
            time.sleep_ms(25)
            self._device_detect.on()
            time.sleep_ms(550)
            self._device_detect.off()
            self._SCI_status = self.sci_states.passive
        elif self._SCI_status is self.sci_states.passive:
            return
        else: 
            raise StateError("SCI is in an unknown state ({self._SCI_status}), something has gone catastrophically wrong")

    def press_power(self):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        if self._SCI_status is self.sci_states.passive:
            self.set_sci_safe()
        self.send(133)
        self._SCI_status = self.sci_states.passive
    
    def power_on(self):
        self._device_detect.on()
        time.sleep_ms(550)
        self._device_detect.off()
    
    def press_spot(self):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        if self._SCI_status is self.sci_states.passive:
            self.set_sci_safe()
        self.send(134)
        self._SCI_status = self.sci_states.passive

    def press_clean(self):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        if self._SCI_status is self.sci_states.passive:
            self.set_sci_safe()
        self.send(135)
        self._SCI_status = self.sci_states.passive

    def press_max(self):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        if self._SCI_status is self.sci_states.passive:
            self.set_sci_safe()
        self.send(136)
        self._SCI_status = self.sci_states.passive

    def set_drive_speed(self, speed, radius):
        if(radius < -2000 or radius > 2000):
            raise InputError(radius, "Radius must be between -2000 and 2000, but was {radius}!")
        if((speed < -500 or speed > 500) and speed is not 32768):
            raise InputError(speed, "Speed must be between -500 and 500 (or 32768), but was {speed}!")
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        elif self._SCI_status is self.sci_states.passive:
            self.set_sci_safe()
        elif self._SCI_status is self.sci_states.full:
            self.set_sci_safe()
        self.send((137, self._get_tc_high_byte_int16(speed), self._get_tc_low_byte_int16(speed), self._get_tc_high_byte_int16(radius), self._get_tc_low_byte_int16(radius)))
        
        
    def _get_tc_high_byte_int16(self, number):
        if number < 0:
            number = (1 << 16) + number
        number &= 0xFFFF
        high_byte = (number >> 8) & 0xFF
        return high_byte
    
    def _get_tc_low_byte_int16(self, number):
        if number < 0:
            number = (1 << 16) + number
        number &= 0xFFFF
        low_byte = number & 0xFF
        return low_byte

    def set_drive_speed_unsafe(self, speed, radius):
        if(radius < -2000 or radius > 2000):
            raise InputError(radius, "Radius must be between -2000 and 2000, but was {radius}!")
        if((speed < -500 or speed > 500) and speed is not 32768):
            raise InputError(speed, "Speed must be between -500 and 500 (or 32768), but was {speed}!")
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        elif self._SCI_status is self.sci_states.passive:
            self.set_sci_full()
        elif self._SCI_status is self.sci_states.safe:
            self.set_sci_full()
        self.send((137, self._get_tc_high_byte_int16(speed), self._get_tc_low_byte_int16(speed), self._get_tc_high_byte_int16(radius), self._get_tc_low_byte_int16(radius)))

    def set_motor_actions(self, main_brush=False, vacuum=False, side_brush=False):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        elif self._SCI_status is self.sci_states.passive:
            self.set_sci_safe()
        elif self._SCI_status is self.sci_states.full:
            self.set_sci_safe()
        self.send((138, main_brush << 2 | vacuum << 1 | side_brush << 0))

    def set_motor_unsafe(self, main_brush=False, vacuum=False, side_brush=False):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        elif self._SCI_status is self.sci_states.passive:
            self.set_sci_full()
        elif self._SCI_status is self.sci_states.safe:
            self.set_sci_full()
        self.send((138, main_brush << 2 | vacuum << 1 | side_brush << 0))

    def set_led_state(self, status_green=False, status_red=False, spot=False, clean=False, max=False, dirt_detect=False, power_color=0, power_intensity=0):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        elif self._SCI_status is self.sci_states.passive:
            self.set_sci_safe()
        elif self._SCI_status is self.sci_states.full:
            self.set_sci_safe()
        elif power_color < 0 or power_color > 255:
            raise InputError(power_color, "power_color must be between 0 and 255, but was {power_color}")
        elif power_intensity < 0 or power_intensity > 255:
            raise InputError(power_intensity, "power_intensity must be between 0 and 255, but was {power_intensity}")
        self.send((139, status_green << 5 | status_red << 4 | spot << 3 | clean << 2 | max << 1 | dirt_detect << 0, power_color, power_intensity))

    def set_led_state_unsafe(self, status_green=False, status_red=False, spot=False, clean=False, max=False, dirt_detect=False, power_color=0, power_intensity=0):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        elif self._SCI_status is self.sci_states.passive:
            self.set_sci_full()
        elif self._SCI_status is self.sci_states.safe:
            self.set_sci_full()
        elif power_color < 0 or power_color > 255:
            raise InputError(power_color, "power_color must be between 0 and 255, but was {power_color}")
        elif power_intensity < 0 or power_intensity > 255:
            raise InputError(power_intensity, "power_intensity must be between 0 and 255, but was {power_intensity}")
        self.send((139, status_green << 5 | status_red << 4 | spot << 3 | clean << 2 | max << 1 | dirt_detect << 0, power_color, power_intensity))

    def play_song(self, song_number):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        elif self._SCI_status is self.sci_states.passive:
            self.set_sci_safe()
        elif self._SCI_status is self.sci_states.full:
            self.set_sci_safe()
        elif song_number < 0 or song_number > 15:
            raise InputError(song_number, "song_number must be between 0 and 15, but was {song_number}")
        self.send((141, song_number))

    def play_song_unsafe(self, song_number):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        elif self._SCI_status is self.sci_states.passive:
            self.set_sci_full()
        elif self._SCI_status is self.sci_states.safe:
            self.set_sci_full()
        elif song_number < 0 or song_number > 15:
            raise InputError(song_number, "song_number must be between 0 and 15, but was {song_number}")
        self.send((141, song_number))

    def set_force_dock(self):
        if self._SCI_status is self.sci_states.off:
            raise StateError("SCI has not been initialized yet!")
        elif self._SCI_status is self.sci_states.safe:
            self.set_sci_passive()
        elif self._SCI_status is self.sci_states.full:
            self.set_sci_passive()
        self.send(143)


    def send(self, message):
        self._uart.write(message)
    
    def listen(self, bytes):
        if bytes is None:
            reply = self._uart.read()
        else:
            reply = self._uart.read(bytes)
        return reply
