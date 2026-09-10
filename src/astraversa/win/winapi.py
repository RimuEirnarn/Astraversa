import os
from collections.abc import Callable, Iterable
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any, TypedDict

import pythoncom
import win32com.client

DispatcherEvent = Event()

class EventData(TypedDict):
    name: str
    pid: int
    path: str
    source_name: str

def select_known_process_event(
    executable_path: str | None,
    known_processes: Iterable[str] | set[str],
) -> str | None:
    """Return the executable basename when it matches a known process name."""
    if not executable_path:
        return None

    basename = os.path.basename(os.fspath(executable_path)).lower()
    allowed = {name.lower() for name in known_processes}
    return basename if basename in allowed else None


def _queue_process_event(
    queue: Queue[EventData],
    known_processes: Iterable[str] | set[str],
    *,
    process_name: str,
    executable_path: str | None,
    process_id: int,
) -> None:
    selected_name = select_known_process_event(executable_path or process_name, known_processes)
    if selected_name is None:
        return

    queue.put(
        {
            "name": selected_name,
            "pid": process_id,
            "path": executable_path or process_name,
            "source_name": process_name,
        }
    )


def consume_process_events(
    event_queue: Queue[EventData],
    callback: Callable[[EventData], None],
    *,
    signal: Event | None = None,
) -> list[EventData]:
    """Drain queued process events on the main thread and hand each to a callback."""
    drained: list[EventData] = []
    while True:
        try:
            event = event_queue.get_nowait()
        except Empty:
            break

        drained.append(event)
        callback(event)

    if signal is not None:
        signal.clear()
    return drained


def spawn_process_watchdog(
    known_processes: Iterable[str] | set[str],
    *,
    event_queue: Queue[EventData] | None = None,
    signal: Event | None = None,
) -> tuple[Thread, Queue[EventData], Event]:
    """Start a watcher thread that emits only known process events to the main thread."""
    pythoncom.CoInitialize()
    DispatcherEvent.set()
    queue = event_queue or Queue()
    main_signal = signal or Event()

    def _watch_process_creation() -> None:
        pythoncom.CoInitialize()
        wmi = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        services = wmi.ConnectServer(".", "root\\cimv2")

        query = (
            "SELECT * FROM __InstanceCreationEvent WITHIN 1 "
            "WHERE TargetInstance ISA 'Win32_Process'"
        )
        watcher = services.ExecNotificationQuery(query)

        while DispatcherEvent.is_set():
            event = watcher.NextEvent()
            target = getattr(event, "TargetInstance", None)
            if target is None:
                continue

            process_name = str(getattr(target, "Name", "") or "").strip()
            process_id = int(getattr(target, "ProcessId", -1) or -1)
            executable_path = str(getattr(target, "ExecutablePath", "") or "").strip() or None

            _queue_process_event(
                queue,
                known_processes,
                process_name=process_name,
                executable_path=executable_path,
                process_id=process_id,
            )

            if not queue.empty():
                main_signal.set()

    thread = Thread(target=_watch_process_creation, daemon=True)
    thread.start()
    return thread, queue, main_signal
