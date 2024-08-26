import cv2  # type: ignore
import sys
import os
import numpy as np
import psutil
import ctypes
import pygetwindow as gw  # type: ignore
import keyboard as kb  # type: ignore
import argparse
import pyautogui  # type: ignore
import asyncio
import PIL
from ctypes import wintypes
from icecream import ic  # type: ignore
from datetime import datetime
from PIL import ImageGrab, Image
from time import sleep
from enum import Enum
from pathlib import Path
from ultralytics import YOLO  # type: ignore
from serial import Serial # type: ignore 
from textual.app import App, ComposeResult
from textual.widgets import Footer, Static, Button, RadioButton, RadioSet, Label, Markdown, DataTable, Tab, TabbedContent, TabPane, Tabs, Rule, Input
from textual.containers import Container, ScrollableContainer, Vertical, Horizontal
from textual.binding import Binding
from textual.reactive import Reactive
from textual.widget import Widget
from textual.worker import Worker
from textual import work

# * STRUCTURES
class GAMESTATE(Enum):
    UNKNOWN = -2
    INIT = -1
    CHARACTER = 0
    MAP = 1

# * CONSTANTS
RITUAL_SWORD = """\
# Ritual Sword Farming Instructions
"""

BOULDER = """\
# Boulder Farming Instructions
1. Go to settings, and change the following: Auto-Camera Rotation: Off
2. Go to the boulder spot.
3. Hit the boulder.
4. Collect the loot.   
"""

# * GLOBALS
# state = GAMESTATE.INIT
# model = YOLO("eldenring-detect.pt")
# threshold = 0.3
# iou_union = 0.1

# * WIDGETS
class InstructionBox(Widget):
    """A widget that changes instructions based on the selected choice."""
    def __init__(self) -> None:
        super().__init__()
        self.id = "InstructionBox"

    def on_mount(self) -> None:
        self.query_one(Tabs).focus()

    def compose(self) -> ComposeResult:
        with Vertical():
            with TabbedContent(initial="ritual_sword"):
                with TabPane("Ritual Sword", id="ritual_sword"):
                    yield Markdown(RITUAL_SWORD)
                with TabPane("Boulder", id="boulder"):
                    yield Markdown(BOULDER)
                with TabPane("Settings", id="settings_tab"):
                    with Horizontal():
                        yield Label("COM Port (COMX)")
                        yield Input()
                        yield Button("Submit") # TODO: write functionality to check if COM port is valid and act accordingly
                        

class StatusBox(Widget):
    """A widget that displays the current status of the farming bot."""
    def __init__(self) -> None:
        super().__init__()
        self.id = "StatusBox"

    status = Reactive("Not Ready :red_circle:")
    eldenring_status = Reactive("Searching :yellow_circle:")
    startstop_button = Reactive("Start")
    total_runes = Reactive("Unknown")
    arduino_status = Reactive("Unknown")

    def on_mount(self) -> None:
        pass

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(classes="statusbox-horizontal"):
                yield Label(f"Status: {self.status}")
            with Horizontal():
                yield Label(f"Elden Ring: {self.eldenring_status}")
            with Horizontal():
                yield Label(f"Total Runes: {self.total_runes} :yen:")
            with Horizontal():
                yield Label(f"Arduino: {self.arduino_status} :vertical_traffic_light:")
            with Horizontal():
                yield Button(label=self.startstop_button, variant="primary")
            with Horizontal():
                yield Button(label="Debug", id="debug")


class StatusTable(Widget):
    """A widget that displays a table of actions from the farming bot."""
    def __init__(self) -> None:
        super().__init__()
        self.id = "StatusTable"

    def compose(self) -> ComposeResult:
        with Vertical():
            yield DataTable()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Step", "Action", "Time")
        table.show_cursor = False
        table.cursor_type = "none"
        table.zebra_stripes = True
        table.scroll_visible = False  # type: ignore # this disables scrolling in general, not stated in docs
        # table.fixed_columns = 3
        # table.fixed_rows = 10

class MainApp(App):
    CSS_PATH = "main.tcss"
    BINDINGS = [
        Binding(key="d", action="toggle_dark", description="Toggle dark mode"),
    ]

    # * APP VARS
    arduino_port = Reactive(None)
    state = Reactive(GAMESTATE.INIT)
    model = YOLO("eldenring-detect.pt")
    threshold = 0.3
    iou_union = 0.1

    # * HELPER FUNCTIONS
    def keyboard(self, key: str, order_pos: int, order_max: int, custom_message: str = "", duration: int = 100):
        table = self.query_one(DataTable)
        message = f"Keyboard: {key}, Duration: {duration} (ms)" if custom_message == "" else custom_message
        table.add_row(f"{order_pos}/{order_max}", message, self.get_current_time_formatted())
        ser = Serial(self.arduino_port, 9600)
        ser.write(f"{key},{duration};".encode())
        resp = ser.readline().strip()
        while resp != b"1":
            sleep(0.1)
            resp = ser.readline()
        ser.close()

    def use_grace_marker(self) -> None:
        if self.state != GAMESTATE.MAP:
            # use G to open map
            self.keyboard(key="G", order_pos=1, order_max=4)
            sleep(1.5)
        # use grace marker
        self.keyboard(key="F", order_pos=2, order_max=4)  # grace menu
        sleep(0.2)
        self.keyboard(key="E", order_pos=3, order_max=4)
        sleep(0.2)  # wait for menu
        self.keyboard(key="E", order_pos=4, order_max=4)  # confirm
        sleep(1)

    def get_state(self) -> None:
        self.state = GAMESTATE.UNKNOWN
        # get current screen
        screen = self.get_computer_screen()
        results = self.model.predict(screen, conf=self.threshold, iou=self.iou_union)
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
                self.keyboard(key="w", order_pos=1, order_max=1, custom_message="Moving forward, multiple states detected. Rechecking state.")
                return
            if obj_dict["compass"] > 0:
                self.state = GAMESTATE.CHARACTER
                # print("Character state detected")
                return
            elif obj_dict["grace"] > 0 or obj_dict["map"] > 0:
                self.state = GAMESTATE.MAP
                # print("Map state detected")
                return

    def get_current_time_formatted(self):
        return datetime.now().time().strftime("%H:%M:%S")

    def get_computer_screen(self) -> Image.Image:
        screenshot = ImageGrab.grab()
        return screenshot

    def focus_window(self, window_title: str) -> None:
        handle = ctypes.windll.user32.FindWindowW(None, window_title)
        if handle != 0:
            ctypes.windll.user32.ShowWindow(handle, 9)
            ctypes.windll.user32.SetForegroundWindow(handle)
            sleep(0.1)
        else:
            sys.exit()

    def on_mount(self) -> None:
        # start workers after content is loaded
        # self.call_later(callback=self.get_arduino) # for some reason, this doesn't return a response, but the below one does, idk and idc
        # self.call_later(callback=self.get_eldenring)
        self.arduino_timer = self.set_interval(interval=5, callback=self.get_arduino, repeat=15)
        self.eldenring_timer = self.set_interval(interval=15, callback=self.get_eldenring, repeat=10)
        self.log(f"ARDUINO_CALL: {self.arduino_timer}, ELDENRING_CALL: {self.eldenring_timer}")

    def compose(self) -> ComposeResult:
        yield Footer()
        with Horizontal():
            yield InstructionBox()
            yield Rule(orientation="vertical", line_style="double")
            yield StatusBox()
            yield Rule(orientation="vertical", line_style="double")
            yield StatusTable()

    # * EVENTS
    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        match button_id:
            case "debug":
                datatable = self.query_one(DataTable)
                datatable.add_row("1/1", "Test", "00:00:00")
                self.get_arduino()

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        worker_name = event.worker.name
        worker_state = str(event.state).split(".")[1] # * use event state, NOT worker.state
        table = self.query_one(DataTable)
        self.log(f"{event.state}")
        # TODO: write handling to pause timers when success
        match worker_name:
            case "get_arduino":
                match worker_state:
                    case "PENDING":
                        pass
                    case "RUNNING":
                        table.add_row(
                            "1/2",
                            "Searching for Arduino",
                            self.get_current_time_formatted(),
                        )
                        self.query_one(StatusBox).arduino_status = "Searching"
                        self.query_one(StatusBox).refresh(recompose=True)
                    case "CANCELLED":
                        pass
                    case "ERROR":
                        self.log(
                            "worker be like :3"
                        )  # this doesn't matter cause textual will error out anyways :3
                    case "SUCCESS":
                        self.log(self.query_one(StatusBox).arduino_status)
                        self.query_one(StatusBox).refresh(
                            recompose=True
                        )  # * done because of a bug, see https://github.com/Textualize/textual/pull/4661
                        # handle not found
                        if self.query_one(StatusBox).arduino_status == "Not Found":
                            table.add_row(
                                "2/2",
                                "Arduino not found!",
                                self.get_current_time_formatted(),
                            )
                        else:
                            table.add_row(
                                "2/2",
                                "Arduino found!",
                                self.get_current_time_formatted(),
                            )
                            self.arduino_timer.stop()

            case "get_eldenring":
                match worker_state:
                    case "PENDING":
                        pass
                    case "RUNNING":
                        table.add_row(
                            "1/2",
                            "Searching for Elden Ring executable",
                            self.get_current_time_formatted(),
                        )
                        self.query_one(StatusBox).arduino_status = "Searching"
                        self.query_one(StatusBox).refresh(recompose=True)
                    case "CANCELLED":
                        pass
                    case "ERROR":
                        self.log("worker be like :3")
                    case "SUCCESS":
                        if(self.query_one(StatusBox).eldenring_status == "Not Found :red_circle:"):
                            table.add_row(
                                "2/2",
                                "Elden Ring Not Found!",
                                self.get_current_time_formatted(),
                            )
                        else:
                            table.add_row(
                                "2/2",
                                "Elden Ring Found!",
                                self.get_current_time_formatted(),
                            )
                        self.eldenring_timer.stop()
            case "boulder_runner":
                match worker_state:
                    case "PENDING":
                        pass
                    case "RUNNING":
                        table.add_row("1/18", "Running Boulder Routine", self.get_current_time_formatted())
                    case "CANCELLED":
                        pass
                    case "ERROR":
                        self.log("worker be like :3")
                    case "SUCCESS":
                        table.add_row("18/18", "Finished Boulder Routine", self.get_current_time_formatted())
            case "ritual_runner":
                match worker_state:
                    case "PENDING":
                        pass
                    case "RUNNING":
                        table.add_row("1/10", "Running Ritual Routine", self.get_current_time_formatted())
                    case "CANCELLED":
                        pass
                    case "ERROR":
                        self.log("worker be like :3")
                    case "SUCCESS":
                        table.add_row("10/10", "Finished Ritual Routine", self.get_current_time_formatted())

    @work(exclusive=True, name="get_arduino", thread=True)
    def get_arduino(self) -> None:
        self.log("ENTERED DEEZ")
        # we could read the registry here to find the number of COM ports but this creates additional work,
        # instead we will step up by 1 until we find the correct COM port,
        # plus, if the user really has a COM port, say 2560000 or whatever, they will likely just input it
        # we start at COM2 because COM1 is usually reserved for the system
        # also yes, this function is blocking, that is okay
        def try_open_serial(com_port):
            ser = Serial(f"COM{com_port}", 9600) # all serial statements within this file could probably be rewritten with a context manager
            ser.close()

        com_port = 2
        statusBox = self.query_one(StatusBox)
        while True:
            try:
                self.log(f"CHECKING PORT: {com_port}")
                # if com_port is over 100 fail, no point just wasting resources 99% users will not have issues and we can account for the 1% with other means
                if com_port > 100:
                    statusBox.arduino_status = "Not Found"
                    break
                # Run the serial connection attempt in an executor to avoid blocking
                try_open_serial(com_port=com_port)
                statusBox.arduino_status = f"COM{com_port}" # type: ignore # reactives
                # self.arduino_port = "TEST"  # type: ignore # reactives
                break
            except Exception as e:
                com_port += 1

    @work(exclusive=True, name="get_eldenring", thread=True)
    def get_eldenring(self) -> None:
        if(("eldenring.exe" in (i.name() for i in psutil.process_iter())) == False):
            self.query_one(StatusBox).eldenring_status = "Not Found :red_circle:"
            self.query_one(StatusBox).refresh(recompose=True)
        else:
            self.query_one(StatusBox).eldenring_status = "Found :green_circle:"
            self.query_one(StatusBox).refresh(recompose=True)

    @work(exclusive=True, thread=True, name="boulder_runner")
    async def run_boulder(self) -> None:
        loop = asyncio.get_event_loop()
        self.run_setup()
        await loop.run_in_executor(None, self.run_arduino_command, "boulder")

    @work(exclusive=True, thread=True, name="ritual_runner")
    async def run_ritual(self) -> None:
        loop = asyncio.get_event_loop()
        self.run_setup()
        await loop.run_in_executor(None, self.run_arduino_command, "ritual")

    def run_arduino_command(self, choice) -> None:
        table = self.query_one(DataTable)
        if kb.is_pressed("ctrl"):
            self.exit("Exiting")
        self.get_state()
        if self.state == GAMESTATE.UNKNOWN:
            sleep(1)
        if self.state == GAMESTATE.CHARACTER:
            # Bro I just spent 2 hours debugging why my elden ring character was jumping.
            # If you send the input as 'D' in the backend it gets simulated as Shift + d which cause you to dash.
            # So I was sending Q which locks and unlocks camera and the character was randomly jumping.
            sleep(2)  # wait for load in
            self.get_state()
            if (self.state != GAMESTATE.CHARACTER):  # model can hallucinate, recheck after load-in
                self.log("Character state")
                self.log("Starting Movement")
                self.log(f"choice: {choice}")
                if choice == "boulder":
                    self.keyboard(key="q", order_pos=2, order_max=18)
                    self.keyboard(key="sd", duration=350, order_pos=3, order_max=18)  # turn around
                    self.keyboard(key="q", order_pos=4, order_max=18)  # face camera
                    sleep(0.2)
                    self.keyboard(key="e_^", order_pos=5, order_max=18)  # _ activates horse
                    self.keyboard(key="w_!", duration=5500, order_pos=6, order_max=18)
                    self.keyboard(key="wd_!", duration=150, order_pos=7, order_max=18)
                    self.keyboard(key="q", order_pos=8, order_max=18)
                    sleep(0.2)
                    self.keyboard(key="w_!", duration=3300, order_pos=9, order_max=18)
                    self.keyboard(key="aw", duration=1000, order_pos=10, order_max=18)
                    self.keyboard(key="w", duration=300, order_pos=11, order_max=18)
                    self.keyboard(key="aw", duration=400, order_pos=12, order_max=18)
                    self.keyboard(key="wd", duration=500, order_pos=13, order_max=18)
                    self.keyboard(key="d_!", duration=1000, order_pos=14, order_max=18)
                    self.keyboard(key="sd", duration=600, order_pos=15, order_max=18)
                    self.keyboard(key="as", duration=700, order_pos=16, order_max=18)
                    self.log("Movement Done")
                    self.log("Waiting for death of rock")
                    sleep(3.5)
                    self.keyboard(key="g", order_pos=17, order_max=18)
                    sleep(0.2)
                    self.use_grace_marker()  # possibly could end up jumping into a state too quickly here
                elif choice == "ritual":
                    pyautogui.moveTo(1, 1)
                    self.keyboard(key="q", order_pos=2, order_max=10)
                    self.keyboard(key="w_!", duration=1300, order_pos=3, order_max=10)
                    self.keyboard(key="aw", duration=250, order_pos=4, order_max=10)
                    self.keyboard(key="q", order_pos=5, order_max=10)
                    self.keyboard(key="w_!", duration=3000, order_pos=6, order_max=10)
                    self.keyboard(key="q", order_pos=7, order_max=10)
                    self.keyboard(key="e_$", order_pos=8, order_max=10)
                    sleep(6)
                    self.keyboard(key="g", order_pos=9, order_max=10)
                    sleep(0.2)
                    self.use_grace_marker() # possibly could end up jumping into a state too quickly here
        if(self.state == GAMESTATE.MAP):
            self.use_grace_marker()
            sleep(2)
            self.run_arduino_command(choice)

    @work(exclusive=True, thread=True)
    async def run_setup(self) -> None:
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self.focus_window, "Elden Ring™")
            await loop.run_in_executor(None, self.get_state)
            await loop.run_in_executor(None, self.use_grace_marker)
        except Exception as e:
            self.log(f"SETUP ERROR: {e}")

if __name__ == "__main__":
    app = MainApp()
    app.run()
