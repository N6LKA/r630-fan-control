# r630-fan-control

![Version](https://img.shields.io/badge/version-1.0.3-blue)

Dynamic fan speed control for LCARS-01, a Dell R630 running Proxmox. Works around iDRAC pinning fans at an elevated baseline speed when it can't get thermal telemetry from a non-Dell NVMe adapter, while still protecting against overheating if load actually increases.

## What it does

- Puts the BMC's fan control into manual mode at a quiet, fixed speed via IPMI raw commands
- Polls CPU temperature on an interval
- Reverts to iDRAC's automatic fan curve if CPU temp crosses a high-water threshold
- Resumes the quiet manual speed once temps have stayed low for a sustained period (avoids flapping)
- Falls back to automatic control if it can't read temps, or if the service stops/crashes for any reason

## Files

- `r630-fan-control.py` — the control script
- `r630-fan-control.service` — systemd unit

## Requirements

- `git` and `ipmitool` installed, with local IPMI access working (`ipmitool sdr type fan` should return sensor data)
- Python 3

On a bare Proxmox host, `git` usually isn't installed yet:

```bash
apt update && apt install -y git
```

## Manual install

Clone the repo onto the host (public repo, no credentials needed):

```bash
git clone https://github.com/N6LKA/r630-fan-control.git /opt/r630-fan-control
```

Install the script and service:

```bash
cp /opt/r630-fan-control/r630-fan-control.py /usr/local/bin/
cp /opt/r630-fan-control/r630-fan-control.service /etc/systemd/system/
chmod +x /usr/local/bin/r630-fan-control.py

systemctl daemon-reload
systemctl enable --now r630-fan-control.service
```

## Check status / logs

```bash
systemctl status r630-fan-control.service
journalctl -u r630-fan-control.service -f
```

## Checking fan speeds and temps

Useful for a manual spot-check any time, independent of the service:

```bash
ipmitool sdr type fan
ipmitool sdr type temperature
```

To track a trend over several checks, prefix with a timestamp:

```bash
date; ipmitool sdr type fan; ipmitool sdr type temperature
```

## Disable and revert fans to automatic

```bash
systemctl disable --now r630-fan-control.service
ipmitool raw 0x30 0x30 0x01 0x01
```

## Updating

```bash
cd /opt/r630-fan-control
git pull
cp r630-fan-control.py /usr/local/bin/
cp r630-fan-control.service /etc/systemd/system/
systemctl daemon-reload
systemctl restart r630-fan-control.service
```

## Tuning

Edit the constants at the top of `r630-fan-control.py` before installing (or after, followed by a service restart):

| Constant | Meaning |
|---|---|
| `MANUAL_SPEED_HEX` | Fan duty cycle when quiet (hex, `0x00`-`0x64` = 0-100%) |
| `TEMP_HIGH_C` | CPU temp that triggers reverting to automatic |
| `TEMP_RESUME_C` | CPU temp that must be sustained before resuming manual |
| `RESUME_SUSTAIN_POLLS` | Consecutive low readings required before resuming |
| `POLL_INTERVAL_SEC` | How often to check temps |
