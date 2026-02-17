"""System monitoring utilities (Windows-focused).

Provides lightweight CPU/RAM usage without external dependencies.
GPU usage is best-effort:
- NVIDIA: uses nvidia-smi if available
- Otherwise: tries Windows performance counter via PowerShell Get-Counter
"""

from __future__ import annotations

import ctypes
import subprocess
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class SystemStats:
    cpu_percent: Optional[float] = None
    ram_percent: Optional[float] = None
    gpu_percent: Optional[float] = None
    gpu_encode_percent: Optional[float] = None
    gpu_decode_percent: Optional[float] = None
    cpu_source: str = ""
    gpu_source: str = ""


class _FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]


def _filetime_to_int(ft: _FILETIME) -> int:
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_uint32),
        ("dwMemoryLoad", ctypes.c_uint32),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


class SystemMonitor:
    def __init__(self) -> None:
        self._last_idle = None
        self._last_kernel = None
        self._last_user = None
        self._last_t = 0.0

    def cpu_percent(self) -> tuple[Optional[float], str]:
        """Return total CPU utilization percentage (Windows).

        Prefers Windows perf counter (matches Task Manager better), falls back to GetSystemTimes.
        """
        v = self._cpu_percent_windows_counter()
        if v is not None:
            return v, "Get-Counter"

        v = self._cpu_percent_getsystemtimes()
        return v, "GetSystemTimes" if v is not None else ""

    def _cpu_percent_getsystemtimes(self) -> Optional[float]:
        """CPU utilization via GetSystemTimes delta."""
        try:
            idle = _FILETIME()
            kernel = _FILETIME()
            user = _FILETIME()
            ok = ctypes.windll.kernel32.GetSystemTimes(  # type: ignore[attr-defined]
                ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
            )
            if not ok:
                return None

            idle_i = _filetime_to_int(idle)
            kernel_i = _filetime_to_int(kernel)
            user_i = _filetime_to_int(user)

            if self._last_idle is None:
                self._last_idle, self._last_kernel, self._last_user = idle_i, kernel_i, user_i
                return None

            idle_delta = idle_i - self._last_idle
            kernel_delta = kernel_i - (self._last_kernel or 0)
            user_delta = user_i - (self._last_user or 0)

            self._last_idle, self._last_kernel, self._last_user = idle_i, kernel_i, user_i

            total = kernel_delta + user_delta
            if total <= 0:
                return 0.0
            busy = total - idle_delta
            return max(0.0, min(100.0, (busy / total) * 100.0))
        except Exception:
            return None

    @staticmethod
    def _cpu_percent_windows_counter() -> Optional[float]:
        ps = (
            "try { "
            "$v=(Get-Counter -Counter '\\Processor(_Total)\\% Processor Time' -SampleInterval 1 -MaxSamples 1).CounterSamples[0].CookedValue; "
            "if ($null -ne $v) { [math]::Round($v,1) } "
            "} catch { }"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2.5,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                return None
            out = (result.stdout or "").strip()
            if not out:
                return None
            return float(out)
        except Exception:
            return None

    def ram_percent(self) -> Optional[float]:
        """Return RAM usage percentage (Windows)."""
        try:
            ms = _MEMORYSTATUSEX()
            ms.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
            ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))  # type: ignore[attr-defined]
            if not ok:
                return None
            return float(ms.dwMemoryLoad)
        except Exception:
            return None

    def gpu_percent(self) -> tuple[Optional[float], Optional[float], Optional[float], str]:
        """Return GPU utilization percentage (best-effort).

        Returns: (overall, encode, decode, source)
        """
        g, enc, dec = self._gpu_percent_nvidia_smi()
        if g is not None or enc is not None or dec is not None:
            overall = max([x for x in [g, enc, dec] if x is not None], default=None)
            return overall, enc, dec, "nvidia-smi"

        overall, enc, dec = self._gpu_percent_windows_counter_parts()
        if overall is not None or enc is not None or dec is not None:
            overall2 = max([x for x in [overall, enc, dec] if x is not None], default=None)
            return overall2, enc, dec, "Get-Counter"

        return None, None, None, ""

    def snapshot(self) -> SystemStats:
        cpu, cpu_src = self.cpu_percent()
        ram = self.ram_percent()
        gpu, enc, dec, gpu_src = self.gpu_percent()
        return SystemStats(
            cpu_percent=cpu,
            ram_percent=ram,
            gpu_percent=gpu,
            gpu_encode_percent=enc,
            gpu_decode_percent=dec,
            cpu_source=cpu_src,
            gpu_source=gpu_src,
        )

    @staticmethod
    def _gpu_percent_nvidia_smi() -> tuple[Optional[float], Optional[float], Optional[float]]:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,utilization.encoder,utilization.decoder",
                    "--format=csv,noheader,nounits",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=1.5,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                return None, None, None
            lines = (result.stdout or "").strip().splitlines()
            if not lines:
                return None, None, None

            # If multiple GPUs, use max across them.
            gpu_vals = []
            enc_vals = []
            dec_vals = []
            for ln in lines:
                parts = [p.strip() for p in ln.split(",")]
                if len(parts) >= 1 and parts[0]:
                    gpu_vals.append(float(parts[0]))
                if len(parts) >= 2 and parts[1]:
                    enc_vals.append(float(parts[1]))
                if len(parts) >= 3 and parts[2]:
                    dec_vals.append(float(parts[2]))

            g = max(gpu_vals) if gpu_vals else None
            e = max(enc_vals) if enc_vals else None
            d = max(dec_vals) if dec_vals else None
            return g, e, d
        except Exception:
            return None, None, None

    @staticmethod
    def _gpu_percent_windows_counter_parts() -> tuple[Optional[float], Optional[float], Optional[float]]:
        """Estimate GPU utilization using Windows perf counter.

        Returns max(all engines), max(video encode), max(video decode).
        """
        ps = (
            "try { "
            "$s=(Get-Counter -Counter '\\GPU Engine(*)\\Utilization Percentage' -SampleInterval 1 -MaxSamples 1).CounterSamples; "
            "$all=($s | Measure-Object -Property CookedValue -Maximum).Maximum; "
            "$enc=($s | Where-Object { $_.InstanceName -match 'engtype_VideoEncode' } | Measure-Object -Property CookedValue -Maximum).Maximum; "
            "$dec=($s | Where-Object { $_.InstanceName -match 'engtype_VideoDecode' } | Measure-Object -Property CookedValue -Maximum).Maximum; "
            "'{0},{1},{2}' -f $all,$enc,$dec "
            "} catch { }"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3.5,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                return None, None, None
            out = (result.stdout or "").strip()
            if not out:
                return None, None, None
            parts = [p.strip() for p in out.split(",")]
            def _p(i: int) -> Optional[float]:
                if i >= len(parts):
                    return None
                if parts[i] == "" or parts[i].lower() == "nan":
                    return None
                try:
                    v = float(parts[i])
                    return max(0.0, min(100.0, v))
                except Exception:
                    return None
            return _p(0), _p(1), _p(2)
        except Exception:
            return None, None, None
