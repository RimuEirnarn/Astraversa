from sys import path
from os.path import realpath
from queue import Queue
from threading import Event
from time import sleep

path.insert(0, realpath(__file__+'/../../'))

from astraversa.win.winapi import spawn_process_watchdog, EventData, consume_process_events, DispatcherEvent

known = {"notepad.exe", "python.exe"}
events: Queue[EventData] = Queue()
signal = Event()

watchdog, event_queue, main_signal = spawn_process_watchdog(known, event_queue=events, signal=signal)

def on_process(event: EventData):
    print(f"Main thread saw: {event['name']} (PID {event['pid']})")

if __name__ == '__main__':
    try:
        while True:
            if main_signal.is_set():
                consume_process_events(events, on_process, signal=main_signal)
            sleep(0.0625)
    except KeyboardInterrupt:
        pass

    DispatcherEvent.clear()