#!/usr/bin/env python

import json
import logging
import os
import sys
import argparse
from ooidac.download import *
    
def main(args):
    """Download UFrame asynchronous request NetCDF files contained in the response_file.
    Downloaded files are written to the deployment's source-nc directory"""
    
    exit_status = 0
    
    # Set up the erddapfoo.lib.m2m.M2mClient logger
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(module)s:%(funcName)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    logging.basicConfig(format=log_format, level=log_level)        
    
    # Validate the specified response file exists
    if not os.path.isfile(args.response_file):
        logging.error('Invalid response file {:s}'.format(args.response_file))
        return 1
        
    # Read in the responses
    try:
        with open(args.response_file, 'r') as fid:
            responses = json.load(fid)
    except ValueError as e:
        logging.error('Error loading JSON {:s} ({:s})'.format(args.response_file, e))
        return 1
        
    response_count = -1
    # Process each response separately
    for response in responses:
        # Create the destination directory
        try:
            download_path = os.path.join(response['path'], 'nc-source')
        except KeyError as e:
            logging.error('Invalid response file {:s} ({:s})'.format(args.response_file, e))
            continue
            
        if not os.path.isdir(download_path):
            logging.warning('Invalid NetCDF destination {:s} in response [{:0.0f}]'.format(download_path, response_count))
            exit_status = 1
            continue
            
        logging.debug('Parsing response [{:0.0f}]'.format(response_count))
        nc_urls = parse_response_nc_urls(response, timeout=args.timeout)
        if not nc_urls:
            continue
        
        for url in nc_urls:
            # If args.debug is True display the URL but do not download it
            if args.debug:
                sys.stdout.write('DEBUG MODE: Skipping download of NetCDF URL: {:s}\n'.format(url))
                continue
                
            # Download the file
            nc_path = download_nc(url, download_path=download_path, timeout=30)
            if not nc_path:
                exit_status = 1
                continue
                
            if args.quiet:
                continue
                
            sys.stdout.write('{:s}\n'.format(nc_path))
            
    return exit_status
    
    
if __name__ == '__main__':

    arg_parser = argparse.ArgumentParser(description=main.__doc__)
    arg_parser.add_argument('response_file',
        help='Request file to process')
    #arg_parser.add_argument('-d', '--destination',
    #    help='Download destination directory')
    arg_parser.add_argument('-l', '--loglevel',
        help='Verbosity level <Default=info>',
        type=str,
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')
    arg_parser.add_argument('-q', '--quiet',
        help='Do not print downloaded file paths to STDOUT',
        action='store_true')
    #args_parser.add_argument('-s', '--status',
    #    help='Check on the status of the request but do not download NetCDF files',
    #    action='store_true')
    arg_parser.add_argument('-x', '--debug',
        help='Print file URLs but do not download them',
        action='store_true')
    arg_parser.add_argument('-t', '--timeout',
        type=int,
        default=30,
        help='Request timeout, in seconds <Default=30>')

    parsed_args = arg_parser.parse_args()
    #print parsed_args
    #sys.exit(1)

    sys.exit(main(parsed_args))
