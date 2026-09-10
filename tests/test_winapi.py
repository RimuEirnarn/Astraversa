from queue import Queue
from astraversa.win.winapi import consume_process_events, select_known_process_event, Event


def test_select_known_process_event_uses_executable_basename():
    assert select_known_process_event(r"C:\\Windows\\System32\\notepad.exe", {"notepad.exe"}) == "notepad.exe"
    assert select_known_process_event(r"C:\\Program Files\\Foo\\App.EXE", {"app.exe"}) == "app.exe"
    assert select_known_process_event(r"C:\\Windows\\System32\\calc.exe", {"notepad.exe"}) is None


def test_consume_process_events_drains_queue_in_main_thread():
    queue = Queue()
    queue.put({"name": "notepad.exe", "pid": 101})
    queue.put({"name": "calc.exe", "pid": 202})

    seen = []
    signal = Event()
    signal.set()

    consume_process_events(queue, seen.append, signal=signal)

    assert seen == [{"name": "notepad.exe", "pid": 101}, {"name": "calc.exe", "pid": 202}]
    assert signal.is_set() is False