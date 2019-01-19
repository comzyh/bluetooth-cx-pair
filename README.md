# bluetooth-cx-pair
Bluetooth device cross-platform pairing tool

This tool can help export bluetooth pair infomation from your os,

supported platform:
- Linux (Tested on Ubuntu 18.04)
- Windows (Tested on Windows 10)

This tool can export `CSRK`, `IRK`, `LTK`, `EDIV`, `ERand` from your system, or export `LinkKey` for old device

With configs above, you can share bluetooth device connection between Linux and Windows on same computer.

## Windows

Administrator privileges is required. But Administrator privileges is ××not enough×× to access Windows Registry， so you need `PsExec`

Requiement:

- Python 3
- PsExec

You can get PsExec from [here](https://docs.microsoft.com/en-us/sysinternals/downloads/psexec)

Then run

> PsExec64.exe -s python3 blcx-pair.py


## Linux

Requirement:

- Python 3
- sudo

> python3 blcx-pair.py

## Typical Usage

1. Pair your device (keyboard or mouse) in linux first
2. Reboot and pair it in windows, and run this tool, backup device config you need
3. Reboot to Linux, run this tool and get the controller's MAC address and device's MAC address
4. Edit `/var/lib/bluetooth/<controller>/<device>/info` (sudo required)

If you are using old device, replace `Key` under `[LinkKey]` with `LinkKey`

If you are using newer device, replace fields as folowing

- `Key` under`[IdentityResolvingKey]`: `IRK`
- `Key` under`[LongTermKey]`: `LTK`
- `EDiv` under`[LongTermKey]`: `EDIV`
- `Rand` under`[LongTermKey]`: `ERand`

And then restart your bluetooth service

> sudo service bluetooth restart

Enjoy ~
