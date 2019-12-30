#!/usr/bin/env python3
"""Cross platform bluetooth pair tookit"""
import re
import sys
import argparse
import configparser
import os
import os.path
import json

_mac_pattern = re.compile(r'([0-9a-fA-f]{2}:){5}[0-9a-fA-f]{2}')  # 00:af:12:34:56:78
_win_mac_pattern = re.compile(r'([0-9a-fA-f]{2}){6}')  # 00af12345678
_win_disp_mac_pattern = re.compile(r'([0-9a-fA-f]{2}-){5}[0-9a-fA-f]{2}')  # 00-af-12-34-56-78


def pick_mac(macs, mac_type="controler"):
    if len(macs) == 1:
        selected = 0
    else:
        print('{} are:'.format(mac_type))
        for index, name in enumerate(macs):
            print('{:3}\t{}'.format(index, name))
        selected = input(
            'which {} you want to use? [{}-{}]:'.format(mac_type, 0, len(macs) - 1))
        selected = int(selected, 10)
    print('using BT {}: {}'.format(mac_type, macs[selected]))
    return macs[selected]


def to_local_mac(mac, pattern):
    if not _mac_pattern.match(mac) and not _win_mac_pattern.match(mac) and not _win_disp_mac_pattern.match(mac):
        raise Exception("Invalid maca address \"{}\"".format(mac))
    mac = mac.replace(":", "")
    mac = mac.replace("-", "")

    if pattern == 'linux':  # linux
        return "{}:{}:{}:{}:{}:{}".format(*[mac[i*2:i*2+2] for i in range(6)]).upper()
    else:
        return "{}-{}-{}-{}-{}-{}".format(*[mac[i*2:i*2+2] for i in range(6)]).lower()


def linux(args):
    base_dir = '/var/lib/bluetooth'
    controler = []
    for name in os.listdir(base_dir):
        if _mac_pattern.match(name):
            controler.append(name)

    if args.controler and args.controler in controler:
        controler = args.controler
    else:
        controler = pick_mac(controler)
    base_dir = os.path.join(base_dir, controler)
    devices = []
    if not args.device:
        try:
            for name in os.listdir(base_dir):
                if _mac_pattern.match(name):
                    devices.append(name)
        except PermissionError:
            print('ERROR, you are lack of permission, try using sudo')
            return

    if args.update:  # update local config
        device = to_local_mac(args.device, 'linux')
        info_file = os.path.join(base_dir, device, 'info')
        config = configparser.ConfigParser()
        config.read(info_file)
        print("device name: {}".format(config['General']['Name']))
        lcfg = json.loads(sys.stdin.read())  # loaded config
        print(lcfg)

        if 'LinkKey' in lcfg:
            config['LinkKey']['Key'] = lcfg['LinkKey']
        else:
            config['IdentityResolvingKey']['Key'] = lcfg['IRK']
            config['LongTermKey']['Key'] = lcfg['LTK']
            config['LongTermKey']['EDiv'] = str(lcfg['EDIV'])
            config['LongTermKey']['Rand'] = str(lcfg['ERand'])
            config['LocalSignatureKey']['Key'] = lcfg['CSRK']
        with open(info_file, 'w') as configfile:
            config.write(configfile)

        return

    # output configs
    configs = {}
    print('paired devices are:')
    for index, device in enumerate(devices):
        info_file = os.path.join(base_dir, device, 'info')
        config = configparser.ConfigParser()
        config.read(info_file)
        if 'LinkKey' in config:
            configs[device] = {'LinkKey': config['LinkKey']['Key']}
        elif 'LongTermKey' in config:
            # TODO: CSRK parser for linux
            configs[device] = {
                'IRK': config['IdentityResolvingKey']['Key'],
                'LTK': config['LongTermKey']['Key'],
                'CSRK': config['LocalSignatureKey']['Key'],
                'EDIV': config['LongTermKey']['EDiv'],
                'ERand': config['LongTermKey']['Rand']
            }
        else:
            continue
        print('{mac:18} {name}'.format(mac=device, name=config['General']['Name']))
        print(json.dumps(configs[device], indent=' '))


def windows(args):
    import winreg
    # HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters\Keys
    base_sub_key = r'SYSTEM\CurrentControlSet\Services\BTHPORT\Parameters'
    try:
        keys = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "{}\\Keys".format(base_sub_key))
    except PermissionError:
        print('ERROR, you are lack of permission, try using PsExec -s')
        return
    controler = []
    for index in range(winreg.QueryInfoKey(keys)[0]):
        key = winreg.EnumKey(keys, index)
        if _win_mac_pattern.match(key):
            controler.append(key)

    if args.controler and args.controler in controler:
        controler = args.controler
    else:
        controler = pick_mac(controler)
    keys.Close()

    # list devices in keys
    devices = []
    configs = {}
    keys = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "{}\\Keys\\{}".format(base_sub_key, controler))
    num_keys, num_values, last_modified = winreg.QueryInfoKey(keys)
    for index in range(num_values):  # Simple
        record = winreg.EnumValue(keys, index)
        if _win_mac_pattern.match(record[0]):
            devices.append(record[0])
            configs[record[0]] = {"LinkKey": record[1].hex()}
    for index in range(num_keys):  # Complex
        device = winreg.EnumKey(keys, index)
        if not _win_mac_pattern.match(record[0]):
            continue
        devices.append(device)
        device_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "{}\\Keys\\{}\\{}".format(base_sub_key, controler, device))
        config = {}
        for value_name in ['CSRK', 'IRK', 'LTK', 'EDIV', 'ERand']:
            try:
                value, _ = winreg.QueryValueEx(device_key, value_name)
                if isinstance(value, bytes):
                    value = value.hex()
                config[value_name] = value
            except Exception:
                pass
            configs[device] = config
    keys.Close()

    for index, device in enumerate(devices):
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "{}\\Devices\\{}".format(base_sub_key, device))
        except Exception as e:
            print('Exception when open key: {}: {}'.format(device, e))
            continue
        try:
            name, _ = winreg.QueryValueEx(key, 'Name')
        except Exception as e:
            print('Exception when reading name: {}: {}'.format(device, e))
            continue
        print('{mac:18} {name}'.format(mac=device, name=name.decode()))
        print(json.dumps(configs[device], indent=' '))


def main():
    parser = argparse.ArgumentParser(description='Cross platform bluetooth pair tookit')
    parser.add_argument('--controler', type=str, default='',
                        help='bluetooth controler MAC address')
    parser.add_argument('--device', type=str, default='',
                        help='bluetooth device MAC address')
    # parser.add_argument('-o', '--output', type=str,
    #                     default='', help='output file for device')
    parser.add_argument('--update', action='store_true', help="import from stdin")
    args = parser.parse_args()
    if os.name == 'posix':  # linux
        linux(args)
    elif os.name == 'nt':  # Windows
        windows(args)


if __name__ == '__main__':
    main()
