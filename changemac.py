#!/usr/bin/env python3


import argparse
import ctypes
from platform import system
from os import geteuid
from random import randint
from sys import argv
from subprocess import run, CalledProcessError, DEVNULL
from re import match


def chk_root():
    if geteuid() != 0:
        print("\nPlease run the script as root and try again.\nExiting script...")
        exit(1)


def chk_admin_win():
    if ctypes.windll.shell32.IsUserAnAdmin() != 1:
        print("\nPlease run the script as admin and try again.\nExiting script...")
        exit(1)


def chk_package(command, package):
    run_command = run([command, package], stdout=DEVNULL, stderr=DEVNULL)
    if run_command.returncode != 0:
        print(f"\n{package} package does not exist. Please install it first and try again.")
        print("Exiting script ...\n")
        exit(1)


def usage():
    print('''
Usage: 
python3 macchanger -i <interface> -m <MAC>

Description: 
Change the MAC address of an interface.

Options:
    -h, --help              Show this help message and exit
    -i, --interface         Interface name
    -m, --mac               Set a MAC address manually
    -r, --random            Set a random MAC address

Examples:
python3 macchanger -i wlan0 -m 00:11:22:33:44:55
python3 machanger -i "Wireless Network Connection" -r
    ''')
    exit()


def get_args():
    arg_parser = argparse.ArgumentParser(add_help=False, usage="python3 macchanger -i <interface> -m <MAC>")
    
    arg_parser.add_argument("-h", "--help", action="store_true")
    arg_parser.add_argument("-i", "--interface", dest="interface")
    arg_parser.add_argument("-m", "--mac", dest="new_mac")
    arg_parser.add_argument("-r", "--random", action="store_true")
    
    return arg_parser


def is_valid_interface(interface):
    if system() == "Linux":
        chk_package("which", "ip")
        return run(["ip", "link", "show", interface], stdout=DEVNULL, stderr=DEVNULL).returncode == 0
    elif system() == "Windows":
        chk_package("where", "netsh")
        return run(["netsh", "interface", "show", "interface", interface], stdout=DEVNULL, stderr=DEVNULL).returncode == 0
    elif system() == "Darwin":
        chk_package("hash", "networksetup")
        return f"{interface} (Hardware Port: " in run(["networksetup", "-listallhardwareports"], stdout=DEVNULL, stderr=DEVNULL).stdout.decode().split("\n")


# Check if interface is Wi-Fi or not on macOS
# Req. due to an issue described in change_wifi_mac_macos()
def is_wifi_macos(interface):
    for line in run(["networksetup", "-listallhardwareports"], stdout=DEVNULL, stderr=DEVNULL).stdout.decode().split("\n"):
        if line.startswith(interface) and "Wi-Fi" in line:
            return True


def is_valid_mac(new_mac):
    # The second check is for detecting whether first byte (or octet) of the MAC addr is even or not.
    # If the least significant bit of the first byte
    # is even, then it's unicast, otherwise multicast.
    return match("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", new_mac) and int(new_mac.split(':')[0], 16) % 2 == 0


def gen_random_mac():
    random_new_mac = ""
    while not is_valid_mac(random_new_mac):
        random_new_mac = ":".join(["{:02x}".format(randint(0, 255)) for _ in range(6)])
        # {:02x}".format(randint(0, 255)) generates a 2-digit hexadecimal value of a random int between 0-255
        # In a MAC addr, each byte is denoted by two hexadecimal chars (or 8 bits),
        # & the range of values that can be represented in 8 bits is 0-255 (2^8 -1)

    return random_new_mac


def change_mac_lin(interface, new_mac):
    print(f"\nChanging MAC address of {interface} to {new_mac} ...")
    try:    
        run(["ip", "link", "set", interface, "down"])
        run(["ip", "link", "set", interface, "address", new_mac])
        run(["ip", "link", "set", interface, "up"])
        print("Done\n")
        run(["ip", "link", "show", interface])
    except CalledProcessError as err:
        print(f"Some error occurred performing the task.\n{err}")


def change_mac_win(interface, new_mac):
    print(f"\nChanging MAC address of {interface} to {new_mac} ...")
    try:    
        run(["netsh", "interface", "set", "interface", interface, "admin=disable"])
        run(["netsh", "interface", "set", "interface", interface, f"ethernet={new_mac}", "admin=enable"])
        print("Done\n")
        run(["getmac", "/v"])
    except CalledProcessError as err:
        print(f"Some error occurred performing the task.\n{err}")


def change_ethernet_mac_macos(interface, new_mac):
    print(f"\nChanging MAC address of {interface} to {new_mac} ...")
    try:    
        run(["networksetup", "-setairportpower", interface, "off"])
        run(["networksetup", "-setmacaddress", interface, new_mac])
        run(["networksetup", "-setairportpower", interface, "on"])
        print("Done\n")
        run(["networksetup", "-getinfo", interface])
    except CalledProcessError as err:
        print(f"Some error occurred performing the task.\n{err}")


def change_wifi_mac_macos(interface, new_mac):
    print(f"\nChanging MAC address of {interface} to {new_mac} ...")
    try:
        # Sometimes on macOS, changing MAC addr for Wi-Fi shows following infinite output:
        # ifconfig: ioctl (SIOCAIFADDR): Can't assign requested address
        # One fix is to NOT use networksetup -setairportpower en0 off
        # instead use the following:
        # /System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport "en0" -z
        run(["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", interface, "-z"])
        run(["networksetup", "-setmacaddress", interface, new_mac])
        run(["networksetup", "-setairportpower", interface, "on"])
        print("Done\n")
        run(["networksetup", "-getinfo", interface])
    except CalledProcessError as err:
        print(f"Some error occurred performing the task.\n{err}")


arguments = get_args().parse_args()

if len(argv) == 1 or arguments.help:
    usage() # Print usage if no options provided or -h/--help provided
elif not arguments.interface:
    get_args().error("No interface provided.\nTry 'macchanger -h' for more info.")
elif not arguments.new_mac and not arguments.random:
    get_args().error("No MAC address provided.\nTry 'macchanger -h' for more info.")
elif arguments.random and arguments.new_mac:
    get_args().error("You can not use -r/--random and -m/--mac options together.\nTry 'macchanger -h' for more info.")
elif arguments.new_mac and not is_valid_mac(arguments.new_mac):
    get_args().error("Not a valid unicast MAC address\nExiting script ...\n")
elif arguments.interface and not is_valid_interface(arguments.interface):
    get_args().error("Not a valid interface.\nExiting script ...\n")
elif arguments.random:
    arguments.new_mac = gen_random_mac()


if system() == "Linux":
    chk_root()
    change_mac_lin(arguments.interface, arguments.new_mac)
elif system() == "Windows":
    chk_admin_win()
    change_mac_win(arguments.interface, arguments.new_mac)
elif system() == "Darwin":
    chk_root()
    if is_wifi_macos(arguments.interface):
        change_wifi_mac_macos(arguments.interface, arguments.new_mac)
    else:
        change_ethernet_mac_macos(arguments.interface, arguments.new_mac)
else:
    print("\nUnknown OS detected. The script can't run on this OS.\nExiting script ...")
    exit(1)


exit()