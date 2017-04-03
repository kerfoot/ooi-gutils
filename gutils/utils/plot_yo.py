#!/usr/bin/env python

import argparse
import os
import sys
import numpy as np
from gutils.readers.nc import m2m_nc_to_gutils_stream
from gutils.readers.dba import dba_to_stream
from gutils.readers import stream_to_yo
from gutils.yo import find_yo_extrema
from gutils.yo.filters import default_profiles_filter
from gutils.yo.plot import plot_yo
import logging

# m2m NetCDF file
#nc_file = '/Users/kerfoot/code/ooi-gutils/resources/nc/deployment0003_CE05MOAS-GL326-05-CTDGVM000-telemetered-ctdgv_m_glider_instrument_20160423T060422.620360-20160423T144220.654020.nc'

def main(args):
    """Parse the Slocum glider data file, index and plot the profiles"""

    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(module)s:%(funcName)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    logging.basicConfig(format=log_format, level=log_level)
    
    # Parse and create the stream
    if args.filetype == 'dba':
        if not args.depth:
            args.depth = 'sci_water_pressure'
        dataset = dba_to_stream(args.filename, timesensor=args.time)
    elif args.filetype == 'm2m':
        args.time = args.time or None
        if not args.depth:
            args.depth = 'sci_water_pressure_dbar'
        dataset = m2m_nc_to_gutils_stream(args.filename)
        
    # Create the depth timeseries to index profiles
    yo = stream_to_yo(dataset['stream'], args.depth, timesensor=args.time)
    if not len(yo) == 0:
        logging.warning('No depth/pressure time-series (yo) created {:s}'.format(args.filename))
        return 1
        
    # Index the profiles
    profile_times = find_yo_extrema(yo[:,0], yo[:,1])
    # Filter out bad profiles
    profile_times = default_profiles_filter(yo, profile_times)

    plot_yo(yo, profile_times)

if __name__ == '__main__':

    arg_parser = argparse.ArgumentParser(description=main.__doc__)
    arg_parser.add_argument('filename',
        type=str,
        help='Glider data file containing timestamps and depth/pressure readings')
        
    arg_parser.add_argument(
        '-f', '--filetype',
        help='Type of source filename <Default=dba>',
        choices=['dba', 'm2m', 'erddap'],
        default='dba'
    )
    
    arg_parser.add_argument(
        '-t', '--time',
        help="Set time parameter to use for profile recognition"
    )

    arg_parser.add_argument(
        '-d', '--depth',
        help="Set depth parameter to use for profile recognition <Default=sci_water_pressure_dbar>",
    )
    
    arg_parser.add_argument('-l', '--loglevel',
        help='Verbosity level <Default=info>',
        type=str,
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')

    parsed_args = arg_parser.parse_args()

    sys.exit(main(parsed_args))
