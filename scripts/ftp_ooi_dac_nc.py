#!/usr/bin/env python

import os
import logging
import argparse
import sys
import glob
import json
import pytz
import shutil
from ooidac.ftp import ftp_trajectory_nc_to_dac
from dateutil import parser

def main(args):
    """FTP NetCDF files contained in the specified directory to the U.S IOOS
    National Data Assembly Center.  Default behavior is to transfer only files
    that do not exist on the remote server"""
    
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(module)s:%(funcName)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    if args.timestamping:
        log_format = '%(asctime)s:%(funcName)s:%(module)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    logging.basicConfig(format=log_format, level=log_level)
    
    # Set up and validate the FTP host, user and password arguments
    args.host = args.host or os.getenv('OOI_GLIDER_DAC_FTP_HOST')
    args.user = args.user or os.getenv('OOI_GLIDER_DAC_USER')
    args.password = args.password or os.getenv('OOI_GLIDER_DAC_PASSWORD')
    
    if not args.host:
        logging.error('No FTP host specified')
        return 1
        
    if not args.user:
        logging.error('No FTP username specified')
        return 1
        
    if not args.password:
        logging.error('No FTP password specified')
        return 1
        
    if not args.glider_deployment_path:
        logging.error('No glider deployment path specified')
        return 1
    if not os.path.isdir(args.glider_deployment_path):
        logging.error('Invalid glider deployment path specified {:s}'.format(args.glider_deployment_path))
        return 1
        
    # Create and validate the deployment config path
    deployment_cfg_path = os.path.join(args.glider_deployment_path, 'cfg')
    if not os.path.isdir(deployment_cfg_path):
        logging.error('Deployment configuration directory does not exist {:s}'.format(deployment_cfg_path))
        return 1
    # Create, validate and load the deployment.json file
    deployment_cfg_file = os.path.join(deployment_cfg_path, 'deployment.json')
    if not os.path.isfile(deployment_cfg_file):
        logging.warning('Invalid deployment configuration file {:s}'.format(deployment_cfg_file))
        return 1
    try:
        with open(deployment_cfg_file, 'r') as fid:
            deployment = json.load(fid)
    except OSError as e:
        logging.error('Error loading deployment configuration file {:s}'.format(deployment_cfg_file))
        return 1
            
    if 'trajectory_date' not in deployment:
        logging.warning('Deployment is missing trajectory_date {:s}'.format(deployment_cfg_file))
        return 1
    if 'glider' not in deployment:
        logging.warning('Deployment is missing glider name {:s}'.format(deployment_cfg_file))
        return
        
    # Create the DAC NetCDF trajectory name
    try:
        traj_dt = parser.parse(deployment['trajectory_date']).replace(tzinfo=pytz.UTC)
    except ValueError as e:
        logging.error('Error parsing deployment trajectory_date: {:s}'.format(deployment['trajectory_date']))
        return 1
    trajectory = '{:s}-{:s}'.format(deployment['glider'], traj_dt.strftime('%Y%m%dT%H%M'))
    # Location of local NetCDF files to be ftp'd
    nc_source_dir = os.path.join(args.glider_deployment_path, trajectory)
    logging.info('Local NetCDF source directory: {:s}'.format(nc_source_dir))
    if not os.path.isdir(nc_source_dir):
        logging.warning('Local NetCDF directory does not exist: {:s}'.format(nc_source_dir))
        return 1
    nc_archive_dir = os.path.join(args.glider_deployment_path, 'nc-archive')
    logging.info('Local NetCDF archive directory: {:s}'.format(nc_archive_dir))
    if not os.path.isdir(nc_archive_dir):
        logging.info('Creating archive {:s}'.format(nc_archive_dir))
        try:
            os.mkdir(nc_archive_dir)
        except OSError as e:
            logging.error('Error creating archive: {:s} ({:s})'.format(nc_archive_dir, 3))
            continue
        
    nc_files = glob.glob(os.path.join(nc_source_dir, '*.nc'))
    if not nc_files:
        logging.info('No local NetCDF files found {:s}'.format(args.deployment_nc_path))
        return 0
        
    # FTP the files
    ftp_files = ftp_trajectory_nc_to_dac(args.host,
        args.user,
        args.password,
        trajectory,
        nc_files,
        update=args.update)
    for nc_file in ftp_files:
        logging.info('Archiving file to {:s}'.format(nc_archive_dir))
        try:
            shutil.move(nc_file, nc_archive_dir)
            if args.verbose:
                sys.stdout.write('{:s}\n'.format(nc_file))
        except OSError as e:
            logging.warning('Error archiving file {:s} ({:s})'.format(nc_file, e))
            
    if len(ftp_files) == len(nc_files):
        return 0
    else:
        return 1

    
if __name__ == '__main__':
    
    arg_parser = argparse.create_arg_parser(description=main.__doc__)
    
    arg_parser.add_argument('glider_deployment_path',
        help='Path to glider deployment configuration information')
    
    arg_parser.add_argument('-h', '--host',
        help='FTP host url')
        
    arg_parser.add_argument('-u', '--user',
        help='User name')
        
    arg_parser.add_argument('-p', '--password',
        help='Password')
        
    arg_parser.add_argument('-u', '--update',
        help='Re-transfer file if a newer version exists locally',
        action='store_true')
        
    arg_parser.add_argument('-a', '--all',
        help='Transfer all files regardless of whether they exist on the remote',
        action='store_true')
        
    arg_parser.add_argument('-v', '--verbose',
        help='Print the list of successfully transferred files to STDOUT',
        action='store_true')
        
    arg_parser.add_argument('-l', '--loglevel',
        help='Python logging level <Default=info>',
        type=str,
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')
        
    args = arg_parser.parse_args()
    
    sys.exit(main(args))