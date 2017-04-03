#!/usr/bin/env python

import os
import logging
import argparse
import sys
import json
import csv

def main(args):
    """Write the profile status file summarizing all DAC NetCDF files written for
    the deployment  Profile status for new NetCDF files are appended to the file,
    if it exists."""
    
    # Configure logging
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(module)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    logging.basicConfig(format=log_format, level=log_level)
    
    if not os.path.isfile(args.profile_status_file):
        logging.error('Invalid profile status file specified {:s}'.format(args.profile_status_file))
        return 1
        
    try:
        with open(args.profile_status_file, 'r') as fid:
            profile_status = json.load(fid)
    except ValueError as e:
        logging.error('Error loading {:s} ({:s})'.format(args.profile_status_file))
        return 1
    
    if not profile_status:
        return 0
        
    cols = profile_status[0].keys()
    csv_writer = csv.writer(sys.stdout)
    csv_writer.writerow(cols)
    for p in profile_status:
        csv_writer.writerow([p[col] for col in cols])
        
    return 0
    
if __name__ == '__main__':
    
    arg_parser = argparse.ArgumentParser(description=main.__doc__)
    
    arg_parser.add_argument('profile_status_file',
        help='Glider deployment directory')
        
    arg_parser.add_argument('-c', '--clobber',
        help='Clobber the existing profile status file',
        action='store_true')
        
    arg_parser.add_argument('-l', '--loglevel',
        help='Verbosity level <Default=info>',
        type=str,
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')
        
    args = arg_parser.parse_args()
    
    sys.exit(main(args))
    