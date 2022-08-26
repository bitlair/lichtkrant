import serial
import logging
import sys
import crc
import struct
import calendar
import datetime
import time


# nog even naïef wbt lezen van respons, we gaan er vanuit dat alles goed gaat
# what could possibly go wrong? :)
# TODO
class Ledje:
    ser = None
    debug_output = None
    in_programming_mode = False
    password = False

    def __init__(self, devicename: str = '/dev/ttyUSB0', baudrate: int = 19200, debug_out_filename: str = None):
        self.ser = serial.Serial(devicename, baudrate, timeout=1)
        if debug_out_filename:
            self.debug_output = open(debug_out_filename, 'wb')

    def _integerToLeftPadHexAscii(self, int_in: int, left_pad: int):
        int_as_hex = str(hex(int_in))[2:].upper()
        return int_as_hex.zfill(left_pad).encode('ASCII')

    def _integerToLeftPadAscii(self, int_in: int, left_pad: int):
        int_as_hex = str(int_in)
        return int_as_hex.zfill(left_pad).encode('ASCII')


    def _serial_write(self, to_write):
        
        self.ser.write(to_write)

    def _send_command(self, addr=1, command=None):
        if isinstance(command, str):
            # encode command as ASCII
            command = command.encode('ASCII')
        # everything starts with this
        to_send_bytes = bytearray([0x15,0x15,0x03])  # for purposes of calculating the CRC
        # 'preamble', all messages must start with 0x15 0x15 0x03

        # display address
        addr_bytes = self._integerToLeftPadHexAscii(addr, 2)
        to_send_bytes += addr_bytes

        # inverted display address
        addr_string_inv = self._integerToLeftPadHexAscii(255 - addr, 2)
        to_send_bytes += addr_string_inv
        # command length
        length = self._integerToLeftPadHexAscii(len(command), 3)
        to_send_bytes += length

        # the actual command
        to_send_bytes += command

        # calculate CRC16 and send it
        crc_value = self._integerToLeftPadHexAscii(crc.crcb(to_send_bytes[3:]), 4)
        to_send_bytes += crc_value
        self._serial_write(to_send_bytes)
        #time.sleep(1)
        
        return to_send_bytes

    def start_programming_mode(self, addr=1):
        if self.in_programming_mode == True:
            raise Exception("Programming mode already enabled")
        else:
            resp = self._send_command(addr, 'P')
            self.in_programming_mode = True
            time.sleep(0.5)
            return resp
    
    def stop_programming_mode(self, addr=1):
        if self.in_programming_mode == False:
            raise Exception("Programming mode not enabled")
        else:
            resp = self._send_command(addr, 'H')
            self.in_programming_mode = False
            return resp
    
    def schedule(self, addr=1):
        #https://revspace.nl/Grote_lichtkrant#Commando_A_.28schedule.29
        #doen we voorlopig even niks mee dus
        if self.in_programming_mode == False:
            raise Exception("Programming mode not enabled")
        else:
            resp = self._send_command(addr, "A01ser     * *       *       0")
            time.sleep(0.5)
            return resp

    def strftime(self, formatspec: str):
        """converts strftime-compatible-ish formatspec to a format that the display understands and will
        substitute for current time and date
        the display is not year-aware, by the way
        supported substitutions (all with padded zero and 2 characters long unless spec'd otherwise):
        %m -> BCh BDh: month
        %b -> BFh C0h C1h: 3 character long representation of the current month
        %d -> BAh BBh: day of month
        %H -> B4h B5h: hour
        %M -> B6h B7h: minute
        %S -> B8h B9h: second
        %%: literal '%'

        %q -> F6h: a blinking ':', single character (not in the strftime spec but included for completeness sake)
        """
        formatspec = formatspec.encode('ASCII')
        formatspec = formatspec.replace(b'%%',b'%')
        formatspec = formatspec.replace(b'%m',bytes([0xBC, 0xBD]))
        formatspec = formatspec.replace(b'%b',bytes([0xBF, 0xC0, 0xC1]))
        formatspec = formatspec.replace(b'%d',bytes([0xBA, 0xBB]))
        formatspec = formatspec.replace(b'%H',bytes([0xB4, 0xB5]))
        formatspec = formatspec.replace(b'%M',bytes([0xB6, 0xB7]))
        formatspec = formatspec.replace(b'%S',bytes([0xB8, 0xB9]))
        formatspec = formatspec.replace(b'%q',bytes([0xF6]))
        
        return formatspec

    def add_slide(self, text: tuple, lines: int = 6, addr: int = 1, program_number: int = 1, page_number: int = 1, appear_effect: int = 1, disappear_effect: int = 1, display_seconds: int = 10):
        displaytext = self.tuple_to_displaytext(text, lines)
        #dispcontent = b"C01013612 " + display.tuple_to_displaytext(weer_tekstje)
        message = bytearray()
        # Voor de eerste pagina wordt commando C gebruikt, voor alle opvolgende pagina's commando B. 
        if page_number == 1:
            message.append(0x43)
        else:
            message.append(0x42)
        
        message += self._integerToLeftPadHexAscii(program_number, 2)
        message += self._integerToLeftPadHexAscii(page_number, 2)
        message += self._integerToLeftPadHexAscii(appear_effect, 1)
        message += self._integerToLeftPadHexAscii(disappear_effect, 1)
        message += self._integerToLeftPadAscii(display_seconds, 2)
        message += b' '
        message += displaytext

        resp = self._send_command(addr, message)
        return resp

        

    
    def tuple_to_displaytext(self, text: tuple, lines = 6):
        displaytext = bytearray()
        text = list(text)
        if len(text) < lines:
            amount_to_add = 7 - len(text)
            for i in range(1, amount_to_add):
                text.append('')
                pass
                
        for i, textline in enumerate(text):
            if type(textline) == str:
                textline = textline.encode('ASCII')
            if len(textline) > 45:
                raise ValueError("Text too long")
            else:
                displaytext += textline.ljust(46, b' ')
            if i != len(text) - 1:
                displaytext += b' ' # this is not shown, but is necessary otherwise the first character on the next line is cut off
        return displaytext

    def configure(self, addr: int = 1):
        curtime = datetime.datetime.now()
        message = bytearray()
        message += "U".encode("ASCII")
        message += curtime.strftime("%H%M%S")[::-1].encode("ASCII")
        message.append(0x34) # Betekenis onbekend; lijkt wel afhankelijk te zijn van datum
        message += curtime.strftime("%m%d")[::-1].encode("ASCII")
        if calendar.isleap(int(curtime.strftime("%Y"))):
            message.append(0x31)
        else:
            message.append(0x30)
        message.append(0x33) # Onbekend
        message.append(0x32) # Onbekend
        message += "        ".encode("ASCII")
        message += "00000000000000003303".encode("ASCII")
        message += "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF".encode("ASCII")
        message.append(0x34) # Onbekend
        for x in range(0,25):
            message.append(0x3F)

        resp = self._send_command(addr, message)
        time.sleep(1)
        return resp