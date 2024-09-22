# rfid_library.py

import pirc522
import time
print(pirc522.__file__)
class RFIDReader:
    def __init__(self, user_library, pin_irq=None, antenna_gain=3):
        self.reader = pirc522.RFID(pin_irq=pin_irq, antenna_gain=antenna_gain)
        self.user_library = user_library

    def read_id(self):
        return self.reader.read_id(True)

    def get_user_info(self, uid):
        return self.user_library.get(uid, None)

    def cleanup(self):
        self.reader.cleanup()

def create_user_library():
    return {
        0x91E468C: {'name': 'Le Huu Phuc', 'phone': '123-456-7890'},
        0x81E468C: {'name': 'Le The Hoan', 'phone': '987-654-3210'},

    }
