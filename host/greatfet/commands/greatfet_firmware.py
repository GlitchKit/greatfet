#!/usr/bin/env python
#
# This file is part of GreatFET
#
"""
    Utility for flashing the onboard SPI flash on GreatFET boards.
"""

from __future__ import print_function

import sys
import errno
import argparse

from greatfet import GreatFET
from greatfet.errors import DeviceNotFoundError
from greatfet.utils import log_silent, log_verbose


# Maximum length to allow, for now.
MAX_FLASH_LENGTH = 0x100000

def spi_flash_read(device, filename, address, length, log_function=log_silent):
    """Reads the data from the device's SPI flash to a file. """

    def print_progress(bytes_read, bytes_total):
        log_function("Read {} bytes of {}.".format(bytes_read, bytes_total), end='\r')

    # Read the data from the board's SPI flash to a file.
    with open(filename, 'wb') as f:
        flash_data = device.onboard_flash.read(address, length,
                                               progress_callback=print_progress)
        flash_data.tofile(f)
    log_function('')


def spi_flash_write(device, filename, address, log_function=log_silent):
    """Writes the data from a given file to the SPI flash."""

    def print_progress(bytes_written, bytes_total):
        log_function("Written {} bytes of {}.".format(bytes_written, bytes_total), end='\r')

    # Read the data from the board's SPI flash to a file.
    with open(filename, 'rb') as f:
        flash_data = f.read()
        device.onboard_flash.write(flash_data, address,
                                   erase_first=True,
                                   progress_callback=print_progress)
    log_function('')


def main():
    # Set up a simple argument parser.
    parser = argparse.ArgumentParser(
        description="Utility for flashing the GreatFET's onboard SPI flash")
    parser.add_argument('-a', '--address', metavar='<n>', type=int,
                        help="starting address (default: 0)", default=0)
    parser.add_argument('-l', '--length', metavar='<n>', type=int,
                        help="number of bytes to read (default: {})".format(MAX_FLASH_LENGTH),
                        default=MAX_FLASH_LENGTH)
    parser.add_argument('-r', '--read', dest='read', metavar='<filename>', type=str,
                        help="Read data into file", default='')
    parser.add_argument('-w', '--write', dest='write', metavar='<filename>', type=str,
                        help="Write data from file", default='')
    parser.add_argument('-s', '--serial', dest='serial', metavar='<serialnumber>', type=str,
                        help="Serial number of device, if multiple devices", default=None)
    parser.add_argument('-q', '--quiet', dest='quiet', action='store_true',
                        help="Suppress messages to stdout")
    parser.add_argument('-R', '--reset', dest='reset', action='store_true',
                        help="Reset GreatFET after performing other operations.")
    args = parser.parse_args()

    # Validate our options.

    # If we don't have an option, print our usage.
    if not any((args.read, args.write, args.reset,)):
        parser.print_help()
        sys.exit(0)

    # Determine whether we're going to log to the stdout, or not at all.
    log_function = log_silent if args.quiet else log_verbose

    # Create our GreatFET connection.
    try:
        log_function("Trying to find a GreatFET device...")
        device = GreatFET(serial_number=args.serial)
        log_function("{} found. (Serial number: {})".format(device.board_name(), device.serial_number()))
    except DeviceNotFoundError:
        if args.serial:
            print("No GreatFET board found matching serial '{}'.".format(args.serial), file=sys.stderr)
        else:
            print("No GreatFET board found!", file=sys.stderr)
        sys.exit(errno.ENODEV)

    # Ensure that the device supports an onboard SPI flash.
    try:
        device.onboard_flash
    except AttributeError:
        print("The attached GreatFET ({}) doesn't appear to have an SPI flash to program!".format(device.board_name()), file=sys.stderr)
        sys.exit(errno.ENOSYS)

    # If we have a write command, write first, to match the behavior of hackrf_spiflash.
    if args.write:
        log_function("Writing data to SPI flash...")
        spi_flash_write(device, args.write, args.address, log_function)
        log_function("Write complete!")
        if not args.reset:
            log_function("Reset not specified; new firmware will not start until next reset.")

    # Handle any read commands.
    if args.read:
        log_function("Reading data from SPI flash...")
        spi_flash_read(device, args.read, args.address, args.length, log_function)
        log_function("Read complete!")

    # Finally, reset the target
    if args.reset:
        log_function("Resetting GreatFET...")
        device.reset()
        log_function("Reset complete!")

if __name__ == '__main__':
    main()
