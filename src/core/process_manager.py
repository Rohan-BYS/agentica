import atexit
import os
import signal
import sys
import psutil
from typing import Set

class ProcessManager:
    """
    Ensures zero orphaned Chromium processes.
    """
    def __init__(self):
        self.pids: Set[int] = set()
        self._setup_atexit()
        self._win32_job = None
        if sys.platform == "win32":
            self._setup_win32_job()

    def _setup_win32_job(self):
        try:
            import ctypes
            from ctypes.wintypes import HANDLE, DWORD, LPVOID, BOOL
            
            # Define structures
            class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                            ("PerJobUserTimeLimit", ctypes.c_int64),
                            ("LimitFlags", DWORD),
                            ("MinimumWorkingSetSize", ctypes.c_size_t),
                            ("MaximumWorkingSetSize", ctypes.c_size_t),
                            ("ActiveProcessLimit", DWORD),
                            ("Affinity", ctypes.c_size_t),
                            ("PriorityClass", DWORD),
                            ("SchedulingClass", DWORD)]
                            
            class IO_COUNTERS(ctypes.Structure):
                _fields_ = [("ReadOperationCount", ctypes.c_uint64),
                            ("WriteOperationCount", ctypes.c_uint64),
                            ("OtherOperationCount", ctypes.c_uint64),
                            ("ReadTransferCount", ctypes.c_uint64),
                            ("WriteTransferCount", ctypes.c_uint64),
                            ("OtherTransferCount", ctypes.c_uint64)]
                            
            class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                            ("IoInfo", IO_COUNTERS),
                            ("ProcessMemoryLimit", ctypes.c_size_t),
                            ("JobMemoryLimit", ctypes.c_size_t),
                            ("PeakProcessMemoryUsed", ctypes.c_size_t),
                            ("PeakJobMemoryUsed", ctypes.c_size_t)]
            
            # Constants
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
            JobObjectExtendedLimitInformation = 9
            
            # Create job
            job = ctypes.windll.kernel32.CreateJobObjectW(None, None)
            if job:
                limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
                limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                
                res = ctypes.windll.kernel32.SetInformationJobObject(
                    job, 
                    JobObjectExtendedLimitInformation,
                    ctypes.byref(limits),
                    ctypes.sizeof(limits)
                )
                if res:
                    # Assign current process to job
                    ctypes.windll.kernel32.AssignProcessToJobObject(
                        job, ctypes.windll.kernel32.GetCurrentProcess()
                    )
                    self._win32_job = job
        except Exception as e:
            print(f"[ProcessManager] Failed to setup Win32 Job Object: {e}")

    def _setup_atexit(self):
        atexit.register(self.kill_all)
        if sys.platform != "win32":
            try:
                os.setpgrp()
            except Exception:
                pass

    def track_pid(self, pid: int) -> None:
        self.pids.add(pid)

    def untrack_pid(self, pid: int) -> None:
        self.pids.discard(pid)

    def kill_all(self) -> None:
        """Kill all tracked processes."""
        for pid in list(self.pids):
            try:
                p = psutil.Process(pid)
                p.terminate()
            except psutil.NoSuchProcess:
                pass
        self.pids.clear()
        
        if sys.platform != "win32":
            try:
                os.killpg(0, signal.SIGKILL)
            except Exception:
                pass

    def periodic_zombie_audit(self) -> None:
        """Audit tracked processes and remove dead ones."""
        for pid in list(self.pids):
            try:
                p = psutil.Process(pid)
                if p.status() == psutil.STATUS_ZOMBIE:
                    self.untrack_pid(pid)
            except psutil.NoSuchProcess:
                self.untrack_pid(pid)
