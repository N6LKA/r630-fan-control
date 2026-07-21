#!/usr/bin/env python3
"""Dynamic fan control for LCARS-01 (Dell R630).
Keeps fans at a quiet manual speed when temps are low, hands control
back to iDRAC's automatic curve if CPU temps cross a safety threshold.
"""

import re
import subprocess
import syslog
import time

MANUAL_SPEED_HEX = "0x0a"   # fan duty cycle when quiet (hex, 0x00-0x64 = 0-100%)
TEMP_HIGH_C = 65            # revert to automatic at/above this CPU temp
TEMP_RESUME_C = 55          # must drop back below this before resuming manual
RESUME_SUSTAIN_POLLS = 5    # consecutive low readings required before resuming
POLL_INTERVAL_SEC = 30

CPU_TEMP_RE = re.compile(r"^Temp\s+\|\s+\w+\s+\|\s+ok\s+\|\s+[\d.]+\s+\|\s+(\d+)\s+degrees C", re.M)


def run_ipmi(args):
    return subprocess.run(["ipmitool"] + args, capture_output=True, text=True, timeout=10)


def set_manual(speed_hex):
    run_ipmi(["raw", "0x30", "0x30", "0x01", "0x00"])
    run_ipmi(["raw", "0x30", "0x30", "0x02", "0xff", speed_hex])


def set_automatic():
    run_ipmi(["raw", "0x30", "0x30", "0x01", "0x01"])


def read_max_cpu_temp():
    result = run_ipmi(["sdr", "type", "temperature"])
    temps = [int(t) for t in CPU_TEMP_RE.findall(result.stdout)]
    return max(temps) if temps else None


def main():
    syslog.openlog("r630-fan-control")
    manual_active = True
    low_streak = 0

    set_manual(MANUAL_SPEED_HEX)
    syslog.syslog(f"Startup: manual mode set to {MANUAL_SPEED_HEX}")

    try:
        while True:
            temp = read_max_cpu_temp()

            if temp is None:
                syslog.syslog(syslog.LOG_WARNING, "Could not read temps - reverting to automatic for safety")
                set_automatic()
                manual_active, low_streak = False, 0

            elif manual_active and temp >= TEMP_HIGH_C:
                syslog.syslog(syslog.LOG_WARNING, f"CPU temp {temp}C >= {TEMP_HIGH_C}C - reverting to automatic")
                set_automatic()
                manual_active, low_streak = False, 0

            elif not manual_active:
                if temp < TEMP_RESUME_C:
                    low_streak += 1
                    if low_streak >= RESUME_SUSTAIN_POLLS:
                        syslog.syslog(f"CPU temp {temp}C stable below {TEMP_RESUME_C}C - resuming manual {MANUAL_SPEED_HEX}")
                        set_manual(MANUAL_SPEED_HEX)
                        manual_active, low_streak = True, 0
                else:
                    low_streak = 0

            time.sleep(POLL_INTERVAL_SEC)
    finally:
        set_automatic()
        syslog.syslog("Shutting down - reverted to automatic fan control")


if __name__ == "__main__":
    main()
