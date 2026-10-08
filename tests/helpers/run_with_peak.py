"""Run csv_summary's main() and print the process peak memory on stderr.

Usage: PYTHONPATH=src python run_with_peak.py <csv>
The last stderr line is ``PEAK_BYTES=<n>``. The exit code is main()'s.
"""

from __future__ import annotations

import sys


def _peak_windows() -> int:
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    func = kernel32.K32GetProcessMemoryInfo
    func.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    func.restype = wintypes.BOOL
    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    if not func(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise OSError("GetProcessMemoryInfo failed")
    return int(counters.PeakWorkingSetSize)


def peak_bytes() -> int:
    """Peak resident memory of this process in bytes."""
    if sys.platform == "win32":
        return _peak_windows()
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def main() -> int:
    from csv_summary.cli import main as cli_main

    code = cli_main(sys.argv[1:])
    sys.stderr.write(f"PEAK_BYTES={peak_bytes()}\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
