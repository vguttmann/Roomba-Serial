from machine import UART, Pin
import time
from enum import Enum


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class InputError(Error):
    """Exception raised for errors in the input.

    Attributes:
        `expression`:
            input expression in which the error occurred
        
        `message`:
            explanation of the error
    """
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class StateError(Error):
    """Exception raised for errors in the input.

    Attributes:
        `expression`:
            input expression in which the error occurred
        
        `message`:
            explanation of the error
    """
    def __init__(self, message):
        self.message = message

class Roomba:
    _baudrate = 57600
    sci_states = Enum('status', [('off', 0), ('passive', 1), ('safe', 2), ('full', 3), ('undefined', -1)])
    charging_states = Enum('status', [('not charging', 0), ('charging recovery', 1), ('charging', 2), ('trickle charging', 3), ('waiting', 4), ('charger error', 5), ('unknown', -1)])
    def __init__(self, tx_pin, rx_pin, dd_pin, uart_id=0):
        """
        Initialize UART communication.
        
        :param int tx_pin: Pin used for UART TX
        :param int rx_pin: Pin used for UART RX
        :param int dd_pin: Pin used for Device Detect
        :param int uart_id: UART peripheral ID (e.g., 0, 1, or 2 depending on the board)
        """
        self._uart = UART(uart_id, Roomba._baudrate, Pin(tx_pin), Pin(rx_pin))
        self._uart.init(Roomba._baudrate, bits=8, parity=None, stop=1)
        self._SCI_status = Roomba.sci_states.undefined
        self._device_detect = Pin(dd_pin, Pin.OUT)
        self._device_detect.on()
    
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
        elif self._SCI_status is self.sci_states.full:
            self.send(131)
        else:
            raise StateError("SCI is in an unknown state, something has gone catastrophically wrong")

    def send(self, message):
        """
        Send a message over UART.
        
        :param message: The message to send
        """
        self._uart.write(message)
    
    def listen(self, bytes):
        """
        Listen for a reply on UART.
        
        :param timeout: Time in seconds to wait for a response
        :return: The received message or None if timed out
        """
        if bytes is None:
            reply = self._uart.read()
        else:
            reply = self._uart.read(bytes)
        return reply
