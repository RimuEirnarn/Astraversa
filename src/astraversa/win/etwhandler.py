import ctypes
from ctypes import wintypes
import uuid
import struct
import sys

# Load required Windows DLLs
advapi32 = ctypes.WinDLL("advapi32")
kernel32 = ctypes.WinDLL("kernel32")

# Constants
WNODE_FLAG_TRACED_GUID = 0x00020000
EVENT_TRACE_REAL_TIME_MODE = 0x00000100
EVENT_TRACE_CONTROL_STOP = 1
EVENT_TRACE_CONTROL_UPDATE = 4
ERROR_SUCCESS = 0
ERROR_ALREADY_EXISTS = 183

# Kernel Process Provider GUID: {2229620d-0376-4219-9c21-c463d321d159}
ProcessProviderGuid = uuid.UUID("{2229620d-0376-4219-9c21-c463d321d159}")

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.ULONG),
        ("Data2", wintypes.USHORT),
        ("Data3", wintypes.USHORT),
        ("Data4", wintypes.BYTE * 8)
    ]

class EVENT_TRACE_PROPERTIES(ctypes.Structure):
    _fields_ = [
        ("Wnode", wintypes.BYTE * 48), # WNODE_HEADER
        ("BufferSize", wintypes.ULONG),
        ("MinimumBuffers", wintypes.ULONG),
        ("MaximumBuffers", wintypes.ULONG),
        ("MaximumFileSize", wintypes.ULONG),
        ("LogFileMode", wintypes.ULONG),
        ("FlushTimer", wintypes.ULONG),
        ("EnableFlags", wintypes.ULONG),
        ("AgeLimit", wintypes.LONG),
        ("NumberOfBuffers", wintypes.ULONG),
        ("FreeBuffers", wintypes.ULONG),
        ("EventsLost", wintypes.ULONG),
        ("BuffersWritten", wintypes.ULONG),
        ("LogBuffersLost", wintypes.ULONG),
        ("RealTimeBuffersLost", wintypes.ULONG),
        ("LoggerThreadId", wintypes.HANDLE),
        ("LogFileNameOffset", wintypes.ULONG),
        ("LoggerNameOffset", wintypes.ULONG)
    ]

class EVENT_HEADER(ctypes.Structure):
    _fields_ = [
        ("Size", wintypes.USHORT),
        ("HeaderType", wintypes.USHORT),
        ("Attributes", wintypes.USHORT),
        ("TebOffset", wintypes.USHORT),
        ("Reserved", wintypes.ULONG),
        ("ThreadId", wintypes.ULONG),
        ("ProcessId", wintypes.ULONG),
        ("TimeStamp", wintypes.LARGE_INTEGER),
        ("ProviderId", GUID),
        ("EventDescriptor", wintypes.BYTE * 16),
        ("KernelTime", wintypes.ULONG),
        ("UserTime", wintypes.ULONG),
        ("ActivityId", GUID)
    ]

class EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("EventHeader", EVENT_HEADER),
        ("BufferContext", wintypes.BYTE * 4),
        ("ExtendedDataCount", wintypes.USHORT),
        ("UserDataLength", wintypes.USHORT),
        ("ExtendedData", ctypes.c_void_p),
        ("UserData", ctypes.c_void_p),
        ("UserContext", ctypes.c_void_p)
    ]

# Event Record Callback Prototype
PEVENT_RECORD_CALLBACK = ctypes.WINFUNCTYPE(None, ctypes.POINTER(EVENT_RECORD))

@PEVENT_RECORD_CALLBACK
def process_event_callback(event_record_ptr):
    record = event_record_ptr.contents
    event_id = record.EventHeader.EventDescriptor[0]  # ID is in the first byte of EventDescriptor
    
    # Kernel Process Start Event ID is 1 (or Wnode/Start depending on tracking mask)
    # Process Start carries PID and parent PID in UserData
    if event_id == 1 and record.UserDataLength >= 16:
        # UserData layout for process start: UniqueProcessKey (8), ProcessId (4), ParentProcessId (4)...
        user_data_buffer = ctypes.cast(record.UserData, ctypes.POINTER(wintypes.BYTE * record.UserDataLength))
        data_bytes = bytes(user_data_buffer.contents)
        
        # Unpack ProcessId and ParentProcessId
        try:
            pid, ppid = struct.unpack_from("II", data_bytes, 8)
            print(f"[CTYPES ETW EVENT] Process Started -> PID: {pid}, Parent PID: {ppid}")
        except struct.error:
            pass

def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def test_etw():
    # Check for Administrator Privileges
        
    if not is_admin():
        print("Error: ETW kernel tracing requires running as Administrator.")
        sys.exit(1)

    logger_name = "PythonKernelProcessMonitor"
    
    # 1. Allocate and configure EVENT_TRACE_PROPERTIES structure
    # The structure must be large enough to hold the logger name string at the end.
    logger_name_w = logger_name + "\x00"
    prop_size = ctypes.sizeof(EVENT_TRACE_PROPERTIES) + (len(logger_name_w) * 2)
    buffer = bytearray(prop_size)
    
    properties = EVENT_TRACE_PROPERTIES.from_buffer(buffer)
    properties.Wnode[0:4] = struct.pack("I", prop_size)
    properties.Wnode[4:8] = struct.pack("I", WNODE_FLAG_TRACED_GUID)
    properties.BufferSize = 64
    properties.MinimumBuffers = 2
    properties.MaximumBuffers = 4
    properties.LogFileMode = EVENT_TRACE_REAL_TIME_MODE
    properties.LoggerNameOffset = ctypes.sizeof(EVENT_TRACE_PROPERTIES)
    
    # Copy logger name into the tail of the buffer structure
    ctypes.memmove(
        ctypes.addressof(properties) + properties.LoggerNameOffset,
        ctypes.c_wchar_p(logger_name),
        len(logger_name_w) * 2
    )

    # Stop any lingering session with the same name
    advapi32.StopTraceW(0, logger_name, ctypes.byref(properties))

    # 2. Start the Trace Session
    session_handle = wintypes.HANDLE(0)
    status = advapi32.StartTraceW(ctypes.byref(session_handle), logger_name, ctypes.byref(properties))
    
    if status != ERROR_SUCCESS:
        print(f"Failed to start ETW trace session. Error code: {status}")
        return

    # 3. Enable the Kernel Process Provider
    # Guid structure conversion
    guid_struct = GUID()
    guid_bytes = ProcessProviderGuid.bytes_le
    ctypes.memmove(ctypes.byref(guid_struct), guid_bytes, 16)
    
    # EnableFlags for process tracking (EVENT_TRACE_FLAG_PROCESS = 0x00000001)
    status = advapi32.EnableTraceEx2(
        session_handle,
        ctypes.byref(guid_struct),
        2, # EVENT_CONTROL_CODE_ENABLE_PROVIDER
        4, # TRACE_LEVEL_INFORMATION
        0x10, # MatchAnyKeyword (Process tracking flag)
        0,
        0,
        None
    )

    print(f"Listening to native ETW process events (Session: {logger_name})... Press Ctrl+C to exit.")

    # Note: Consuming real-time events via OpenTrace requires a dedicated structure setup.
    # For a minimal standalone script, process monitoring control loops typically run here.
    try:
        while True:
            ctypes.windll.kernel32.Sleep(1000)
    except KeyboardInterrupt:
        print("\nStopping trace session...")
    finally:
        advapi32.StopTraceW(session_handle, logger_name, ctypes.byref(properties))

if __name__ == "__main__":
    test_etw()