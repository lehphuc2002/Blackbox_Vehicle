import time
from RFID_lib import RFIDReader, create_user_library

if __name__ == '__main__':
    user_library = create_user_library()
    reader = RFIDReader(user_library)

    try:
        while True:
            uid = reader.read_id()
            if uid is not None:
                user_info = reader.get_user_info(uid)
                if user_info is not None:
                    print(f'User Info: {user_info}')
                else:
                    print(f'UID {uid:X} not found in user library.')
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        reader.cleanup()
