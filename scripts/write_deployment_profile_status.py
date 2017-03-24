#!/usr/bin/env python

import os
import logging
import argparse
import sys
from ooidac import write_dataset_status_file

def main(args):
    """Write the profile status file summarizing all DAC NetCDF files written for
    the deployment  Profile status for new NetCDF files are appended to the file,
    if it exists."""
    
    # Configure logging
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(module)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    logging.basicConfig(format=log_format, level=log_level)
    
    if not os.path.isdir(args.glider_deployment_path):
        logging.error('Invalid deployment directory specified {:s}'.format(args.glider_deployment_path))
        return 1
        
    profile_status_file = write_dataset_status_file(args.glider_deployment_path, clobber=args.clobber)
    
    if not profile_status_file:
        return 1
        
    return 0
    
if __name__ == '__main__':
    
    arg_parser = argparse.ArgumentParser(description=main.__doc__)
    
    arg_parser.add_argument('glider_deployment_path',
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
    