from machine import UART, Pin
from time import sleep
from enum import Enum

class Roomba:
    BAUDRATE = 57600
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
        self.uart = UART(uart_id, Roomba.BAUDRATE, Pin(tx_pin), Pin(rx_pin))
        self.uart.init(Roomba.BAUDRATE, bits=8, parity=None, stop=1)
        self.SCIStatus = Roomba.sci_states.undefined
        self.device_detect = Pin(dd_pin, Pin.OUT)
        self.device_detect.on()
    
    def send(self, message):
        """
        Send a message over UART.
        
        :param message: The string message to send
        """
        self.uart.write(message)
    
    def listen(self, bytes):
        """
        Listen for a reply on UART.
        
        :param timeout: Time in seconds to wait for a response
        :return: The received message or None if timed out
        """
        if bytes is None:
            reply = self.uart.read()
        else:
            reply = self.uart.read(bytes)
        return reply
