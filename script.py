import random
from typing import Tuple, Optional, Union

import PySimpleGUI as sg 
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
   
import threading 
import time
import numpy as np
import serial
import json
import os
import sys
from pathlib import Path

# sg.theme('DarkAmber')    # Keep things interesting for your users

class Plotter:
    def __init__(self, dev, plot_width: int = 20, interval: float = 0.5):
        self.dev = dev
        self.plot_width = plot_width
        self.interval = interval
        
        self.canvas = sg.Canvas(key='-CANVAS-', expand_x=True, expand_y=True)
        
        self.fig = plt.figure(figsize=(5, 4))
        self.ax = self.fig.add_subplot(111)
        self.ax.xaxis.set_major_locator(plt.MultipleLocator(self.plot_width//10))
        self.ax.grid()
        
        self.lines = []
        
        self.stop_flag = False

    @staticmethod
    def draw_figure(canvas, figure):
        figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
        figure_canvas_agg.draw()
        figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
        return figure_canvas_agg
    
    def setup(self, window):
        self.fig_agg = Plotter.draw_figure(window['-CANVAS-'].TKCanvas, self.fig)
        
    def _update(self):
        self.fig_agg.draw()
        
    def start(self):
        self.thread = threading.Thread(target=self.draw_loop)
        self.thread.start()
        
    def stop(self):
        self.stop_flag = True
        self.thread.join()
        
    def draw_loop(self):
        while not self.stop_flag:
            data = self.dev.get_data(self.plot_width)
            
            if data is None:
                continue
            
            x = np.arange(data.shape[0])
            
            if not self.lines:
                self.lines.extend(self.ax.plot(x, data, linewidth=1, alpha=0.6))
                self.fig.legend(labels=list(range(data.shape[1])))
                continue

            for idx, line in enumerate(self.lines):
                line.set_data(x, data[:, idx])
                
            self.ax.relim()
            self.ax.autoscale_view(True,True,True)
                
            self._update()
                
            time.sleep(self.interval)
    

class GUI:
    def __init__(self, dev, save_dir: str = "./data", plow_width: int = 500, min_size: Tuple[int, int] = (980, 800)):
        self.active = True

        self.plotter = Plotter(dev, plot_width=plot_width)
        
        self.dev = dev
        self.save_dir = Path(save_dir)
        
        col = [
                # [sg.Text("Outputs", expand_x=True, expand_y=False), sg.Text("Logs", expand_x=True, expand_y=False)],
                [sg.Multiline(key="-OUTPUT-" + sg.WRITE_ONLY_KEY, expand_x=True, expand_y=True)],
                
            ]
        
        layout = [
                [self.plotter.canvas],
                [sg.Column(col, expand_x=True, expand_y=True)],
                # [sg.HorizontalSeparator()],
                [sg.Text(), sg.Button("Start Recording", key="-RECORD-"), sg.Exit()],
        ]
                 

        self.window = sg.Window('Serial Monitor', layout, resizable=True, finalize=True, size=min_size, location=(200, 200), font='Monospace 10')   
        self.window.set_min_size(min_size)
        
        self.plotter.setup(self.window)
    
        def print_to_output(*args, **kwargs):
            if self.active:
                self.window["-OUTPUT-" + sg.WRITE_ONLY_KEY].print(*args, **kwargs)
    
        # def print_to_log(*args, **kwargs):
        #     if self.active:
        #         self.window["-LOG-" + sg.WRITE_ONLY_KEY].print(*args, **kwargs)
        
        self.output = print_to_output
        # self.log = print_to_log
        

    def event_loop(self):
        while True:
            event, values = self.window.read()
            print(event, values)  
            
            if event == "-RECORD-":
                if self.dev.rec_state():
                    print("Stopped recording.")
                    self.window["-RECORD-"].update(text="Start Recording")
                    self.dev.rec_stop(save_dir=self.save_dir)
                else:
                    print("Started recording.")
                    self.window["-RECORD-"].update(text="Stop Recording")
                    self.dev.rec_start()
        
            if event == sg.WIN_CLOSED or event == 'Exit':
                break      

        self.active = False
        self.window.close()


class SerialDevice:
    def __init__(self, port: str, baudrate: int, max_memory: int = 1000):
        self.max_memory = max_memory
        self.port = port
        self.baudrate = baudrate
        
        self.stop_flg = False
        self.record_flg = False
        self.rec_start_idx = None
        
        self.counter = 0
        self.times = []
        self.memory = []


    def open(self) -> bool:
        try:
            self.ser = serial.Serial(self.port, self.baudrate)
            return True
        except serial.serialutil.SerialException:
            return False


    def get_data(self, n: int = -1) -> np.ndarray:
        if len(self.memory) == 0:
            return None
        
        if n < 0:
            data = np.array(self.memory)
        else:
            data = np.array(self.memory[-n:])
        return data


    def _receive(self):
        while not self.stop_flg:
            if self.ser.in_waiting:
                try:
                    recv = self.ser.readline().decode().strip()
                    vals = [float(i) for i in recv.split(",")]
                    
                    output(recv)
                    
                    self.memory.append(vals)
                    self.times.append(time.time())
                    self.counter += 1
                    
                    if len(self.memory) > self.max_memory:
                        self.memory.pop(0)
                        self.time.pop(0)
                        
                except Exception as e:
                    # log(e)
                    print(e)
                    continue
        self.ser.close()

    
    def start(self):
        self.thread = threading.Thread(target=self._receive)
        self.thread.start()


    def stop(self):
        self.stop_flg = True
        self.thread.join()
        
    def rec_start(self):
        self.record_flg = True
        self.rec_start_idx = self.counter - 1

    def rec_stop(self, save_dir: Path) -> np.array:
        self.record_flg = False
        data = np.array(self.memory[self.rec_start_idx:self.counter])
        
        if not save_dir.exists():
            print("Created directory.")
            save_dir.mkdir()
        
        save_path = save_dir / f"data{time.strftime('%Y%m%d%H%M%S')}.csv"
        print(f"Saved as {save_path}.")
        np.savetxt(save_path, data, delimiter=",")

    def rec_state(self):
        return self.record_flg

    
class DummyDevice:
    def __init__(self, max_memory: int = 100000):
        self.max_memory = max_memory
        self.port = "COM7"
        self.baudrate = 112500
        
        self.stop_flg = False
        self.counter = 0
        self.times = []
        self.memory = []


    def open(self) -> bool:
        return True


    def get_data(self, n: int = -1) -> np.ndarray:
        if n < 0:
            data = np.array(self.memory)
        else:
            data = np.array(self.memory[-n:])
        return data


    def _receive(self):
        while not self.stop_flg:
            if True:
                try:
                    recv = ",".join([str(random.randint(0, 9)) for i in range(4)])
                    if self.gui:
                        self.gui.output(recv)
                    
                    vals = [float(i) for i in recv.split(",")]
                    
                    self.memory.append(vals)
                    self.times.append(time.time())
                    self.counter += 1
                    
                    if len(self.memory) > self.max_memory:
                        self.memory.pop(0)
                        self.time.pop(0)
                        
                except Exception as e:
                    # log(e)
                    
                    continue
                
                time.sleep(0.1)

    
    def start(self):
        self.thread = threading.Thread(target=self._receive)
        self.thread.start()


    def stop(self):
        self.stop_flg = True
        self.thread.join()
    

if __name__ == "__main__":
    config_path = Path("./config.json")
    config_path.touch(exist_ok=True)
    
    try: 
        with open(config_path) as config_file:
            config = json.load(config_file)
    except json.decoder.JSONDecodeError: 
        sg.popup("Invalid JSON file.")
        sys.exit()
        
    try:
        port = config["port"]
        baudrate = config["baudrate"]
        plot_width = config["plot_width"]
    except KeyError:
        sg.popup("Some keys are missing in the config.json.")
        sys.exit()
        
    print(config)
    
    dev = SerialDevice(port=port, baudrate=baudrate)
    
    while not dev.open():
        print(f"Failed to open {dev.port}.")
        time.sleep(1)
    print(f"Opened port {dev.port}")
    
    my_gui = GUI(dev=dev, plow_width=plot_width)
    
    output = my_gui.output
    
    dev.start()
    my_gui.plotter.start()
    
    my_gui.event_loop()
    
    my_gui.plotter.stop()
    dev.stop()
    