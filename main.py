import sys
import numpy as np
import psutil
import ctypes
import keyboard as kb
import argparse
import pyautogui
from icecream import ic
from PIL import ImageGrab
from time import sleep
from enum import Enum
from ultralytics import YOLO
from serial import Serial

# keeping track of game states
class GAMESTATE(Enum):
    UNKNOWN = -2
    INIT = -1
    CHARACTER = 0
    MAP = 1

# globals
arduino_port = None
state = GAMESTATE.INIT
model = YOLO("eldenring-detect.pt")
threshold = 0.3
iou_union = 0.1

def get_arduino() -> str:
    # we could read the registry here to find the number of COM ports but this creates additional work for little value,
    # instead we will step up by 1 until we find the correct COM port,
    # plus, if the user really has a COM port, say 2560000 or whatever, they will likely just input it
    com_port = 1
    while True:
        try:
            ser = Serial(f"COM{com_port}", 9600)
            ser.close()
            return com_port
        except Exception as e:
            com_port += 1
            continue

def keyboard(key: str, duration: int = 100):
    ser = Serial(arduino_port, 9600)
    ic("Sending key press", key, duration)
    ser.write(f"{key},{duration};".encode())
    resp = ser.readline().strip()
    while resp != b'1':
        sleep(0.1)
        resp = ser.readline()
    ic("Got response", resp)
    ser.close()

def mouse(change_x: int, change_y: int, duration: int = 100):
    ser = Serial(arduino_port, 9600)
    ic("Sending mouse movement", change_x, change_y, duration)
    ser.write(f"M,{change_x},{change_y},{duration};".encode())
    resp = ser.readline().strip()
    while resp != b'1':
        sleep(0.1)
        resp = ser.readline()
    ic("Got response", resp)
    ser.close()

def get_screen() -> np.ndarray:
    screenshot = ImageGrab.grab()
    return screenshot

def focus_window(window_title: str) -> None:
    handle = ctypes.windll.user32.FindWindowW(None, window_title)
    if handle != 0:
        ctypes.windll.user32.ShowWindow(handle, 9)
        ctypes.windll.user32.SetForegroundWindow(handle)
        sleep(0.1)
    else:
        print(f"Window not found: {window_title}")
        sys.exit()

def get_state() -> None:
    global state
    state = GAMESTATE.UNKNOWN
    # get current screen
    screen = get_screen()
    results = model.predict(screen, conf=threshold, iou=iou_union)
    # 0: compass, 1: grace, 2: map
    for result in results:
        objects = result.boxes.cls.tolist()
        obj_dict = {"compass": 0, "grace": 0, "map": 0}
        for obj in objects:
            for obj in objects:
                match obj:
                    case 0:
                        obj_dict["compass"] += 1
                    case 1:
                        obj_dict["grace"] += 1
                    case 2:
                        obj_dict["map"] += 1
        if (obj_dict["compass"] > 0 and obj_dict["grace"] > 0) or (obj_dict["compass"] > 0 and obj_dict["map"] > 0):
            print("multiple states detected")
            keyboard(key="w")
            return
        if obj_dict["compass"] > 0:
            state = GAMESTATE.CHARACTER
            # print("Character state detected")
            return
        elif obj_dict["grace"] > 0 or obj_dict["map"] > 0:
            state = GAMESTATE.MAP
            # print("Map state detected")
            return

    print("Unknown state, likely in game menu or loading screen. Waiting for known state.")
    state = GAMESTATE.UNKNOWN

def use_grace_marker() -> None:
    global state
    print("Using grace marker")
    if(state != GAMESTATE.MAP):
        # use G to open map
        keyboard(key="G")
        sleep(1.5)
    # use grace marker
    keyboard(key="F") # grace menu
    sleep(0.2)
    keyboard(key="E")
    sleep(0.2) # wait for men
    keyboard(key="E") # confirm
    sleep(1) 

def main():
    # argument parser
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("choice", type=int, help="Enter a number")
    args = arg_parser.parse_args()
    choice = 0
    if args.choice is not None:
        choice = args.choice

    # check choice
    if choice != 1 and choice != 2:
        choice = 1
        print("Invalid choice, defaulting to 1")
    if choice == 1:
        print("Boulder Selected!")
    if choice == 2:
        print("Ritual Sword Selected!")

    # check if elden ring is running
    if(("eldenring.exe" in (i.name() for i in psutil.process_iter())) == False):
        print("Elden Ring is not running")
        sys.exit()

    # tab into elden ring
    focus_window("Elden Ring™")
    get_state()
    use_grace_marker()

    while True:
        if kb.is_pressed("ctrl"):
            print("Exiting")
            break
        get_state()
        if state == GAMESTATE.UNKNOWN:
            sleep(1)
            continue
        if state == GAMESTATE.CHARACTER:
            # Bro I just spent 2 hours debugging why my elden ring character was jumping.
            # If you send the input as 'D' in the backend it gets simulated as Shift + d which cause you to dash.
            # So I was sending Q which locks and unlocks camera and the character was randomly jumping.
            sleep(2) # wait for load in
            get_state()
            if state != GAMESTATE.CHARACTER:  # model can hallucinate, recheck after load-in
                continue
            ic("Character state")
            ic("Starting Movement")
            ic(choice)
            if choice == 1:
                keyboard(key="q")
                keyboard(key="sd", duration=350) # turn around
                keyboard(key="q") # face camera
                sleep(0.2)
                keyboard(key="e_^") # _ activates horse
                keyboard(key="w_!", duration=5500)
                keyboard(key="wd_!", duration=150)
                keyboard(key="q")
                sleep(0.2)
                keyboard(key="w_!", duration=3300)
                keyboard(key="aw", duration=1000)
                keyboard(key="w", duration=300)
                keyboard(key="aw", duration=400)
                keyboard(key="wd", duration=500)
                keyboard(key="d_!", duration=1000)
                keyboard(key="sd", duration=600)
                keyboard(key="as", duration=700)
                ic("Movement Done")
                ic("Waiting for death of rock")
                sleep(3.5)
                keyboard(key="g")
                sleep(0.2)
                break
            elif choice == 2:
                pyautogui.moveTo(1,1)
                keyboard(key="q")
                keyboard(key="w_!", duration=1300)
                keyboard(key="aw", duration=250)
                keyboard(key="q")
                keyboard(key="w_!", duration=3000)
                keyboard(key="q")
                keyboard(key="e_$")
                sleep(6)
                keyboard(key="g")
                sleep(0.2)
        if state == GAMESTATE.MAP:
            print("Map state")
            use_grace_marker()

if __name__ == '__main__':
    main()
    # debug()
