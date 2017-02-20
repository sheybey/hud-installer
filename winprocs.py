import ctypes

DWORD = ctypes.c_ulong
DWORD_256 = DWORD * 256
DWORD_SIZE = ctypes.sizeof(DWORD)
HANDLE = ctypes.c_void_p
LPWSTR = ctypes.c_wchar_p

PROCESS_QUERY_LIMITED_INFORMATION = DWORD(0x1000)

EnumProcesses = ctypes.windll.psapi.EnumProcesses
EnumProcesses.restype = ctypes.c_int

OpenProcess = ctypes.windll.kernel32.OpenProcess
OpenProcess.restype = HANDLE

QueryFullProcessImageNameW = ctypes.windll.kernel32.QueryFullProcessImageNameW
QueryFullProcessImageNameW.restype = ctypes.c_int

CloseHandle = ctypes.windll.kernel32.CloseHandle
CloseHandle.restype = ctypes.c_int

def all_pids():
    pids = DWORD_256()
    returned = DWORD()
    r = EnumProcesses(pids, DWORD(256 * DWORD_SIZE), ctypes.byref(returned))
    if r == 0:
        raise RuntimeError("EnumProcesses failed")
    for i in range(returned.value // DWORD_SIZE):
        yield pids[i]

def process_exe(pid):
    process = OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION,
        ctypes.c_int(0),
        DWORD(pid)
    )
    # if process.value is None:
    #     raise RuntimeError("OpenProcess failed")

    size = DWORD(260)
    path = ctypes.create_unicode_buffer(size.value)
    r = QueryFullProcessImageNameW(
        process,
        DWORD(0),
        path,
        ctypes.byref(size)
    )

    CloseHandle(process)

    if r == 0:
        raise RuntimeError("QueryFullProcessImageNameW failed")

    return path.value