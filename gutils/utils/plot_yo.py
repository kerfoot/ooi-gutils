#!/usr/bin/env python

import argparse
import os
import sys
import numpy as np
from gutils.readers.nc import *
from gutils.readers.dba import *
from gutils.readers import stream_to_yo
from gutils.yo import find_yo_extrema
from gutils.yo.filters import default_profiles_filter
from gutils.yo.plot import plot_yo
import logging

# m2m NetCDF file
#nc_file = '/Users/kerfoot/code/ooi-gutils/resources/nc/deployment0003_CE05MOAS-GL326-05-CTDGVM000-telemetered-ctdgv_m_glider_instrument_20160423T060422.620360-20160423T144220.654020.nc'

logger = logging.getLogger(os.path.basename(__file__))

def main(args):
    """Parse the Slocum glider data file, index and plot the profiles"""

    sys.stdout.write('main\n')
    # Parse and create the stream
    if args.filetype == 'dba':
        sys.stdout.write('parsing dba')
        if not args.depth:
            args.depth = 'sci_water_pressure'
        dataset = bd_to_stream(args.filename, timesensor=args.time)
    elif args.filetype == 'm2m':
        if not args.depth:
            args.depth = 'sci_water_pressure_dbar'
        dataset = m2m_nc_to_gutils_stream(nc_file)
        
    # Create the depth timeseries to index profiles
    yo = stream_to_yo(dataset['stream'], args.depth, timesensor=args.time)
    # Index the profiles
    profile_times = find_yo_extrema(yo[:,0], yo[:,1])
    # Filter out bad profiles
    profile_times = default_profiles_filter(yo, profile_times)

    sys.stdout.write('plotting yo')
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
        help="Set time parameter to use for profile recognition <Default=timestamp>",
        default="timestamp"
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
