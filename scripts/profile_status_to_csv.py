#!/usr/bin/env python

import os
import logging
import argparse
import json
import csv
import sys

def main(args):
    
    # Set up the  logger
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(module)s:%(funcName)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    logging.basicConfig(format=log_format, level=log_level)
    
    if not os.path.isfile(args.profile_json_file):
        logging.error('Invalid profile status json file: {:s}'.format(args.profile_json_file))
        return 1
        
    try:
        with open(args.profile_json_file, 'r') as fid:
            profiles = json.load(fid)
    except (OSError, ValueError) as e:
        logging.error('Erroring loading file {:s} ({:s})'.format(args.profile_json_file, e))
        return 1
        
    if not profiles:
        logging.warning('Status file contains no profile information: {:s}'.format(args.profile_json_file))
        return 0
        
    csv_writer = csv.writer(sys.stdout)
    
    cols = profiles[0].keys()
    csv_writer.writerow(cols)
    for p in profiles:
        row = []
        for c in cols:
            if c == 'filename':
                row.append(os.path.basename(p[c]))
            else:
                row.append(p[c])
                
        csv_writer.writerow(row)
        
    return 0
    
if __name__ == '__main__':

    arg_parser = argparse.ArgumentParser(description=main.__doc__)
    
    arg_parser.add_argument('profile_json_file',
        help='Profile status json file to parse')
    
    arg_parser.add_argument('-l', '--loglevel',
        help='Verbosity level <Default=info>',
        type=str,
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')
        
    args = arg_parser.parse_args()
    
    sys.exit(main(args))
    