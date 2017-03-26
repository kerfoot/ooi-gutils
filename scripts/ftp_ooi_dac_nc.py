#!/usr/bin/env python

import os
import logging
import argparse
import ftputil
import sys
import glob

def main(args):
    """FTP NetCDF files contained in the specified directory to the U.S IOOS
    National Data Assembly Center.  Default behavior is to transfer only files
    that do not exist on the remote server"""
    
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(module)s:%(funcName)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    if args.timestamping:
        log_format = '%(asctime)s:%(funcName)s:%(module)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    logging.basicConfig(format=log_format, level=log_level)
    
    if not args.deployment_nc_path:
        logging.error('No glider deployment path specified')
        return 1
    if not os.path.isdir(args.deployment_nc_path):
        logging.error('Invalid glider deployment path specified {:s}'.format(args.deployment_nc_path))
        return 1
        
    nc_files = glob.glob(os.path.join(args.deployment_nc_path, '*.nc'))
    if not nc_files:
        logging.info('No local NetCDF files found {:s}'.format(args.deployment_nc_path))
        return 0
        
    # Set up the FTP host, user and password arguments
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
        
    # Connect to the FTP server
    try:
        ftp_host = ftputil.FTPHost(args.host, args.user, args.password)
        # Synchronize times between host and local machines
        ftp_host.synchronize_times()
    except ftputil.FTPError as e:
        logging.error('ftputil {:s}'.format(e))
        
    trajectory = os.path.basename(args.deployment_nc_path)
    
    # Get the list of trajectory directories on the server
    ftp_trajectories = ftp_host.listdir('.')
    if trajectory not in ftp_trajectories:
        logging.warning('Deployment has not been registered {:s}'.format(trajectory))
        ftp_host.close()
        return 1
        
    # Change to the remote trajectory directory
    ftp_host.chdir(trajectory)
    
    if not args.all:
        remote_files = ftp_host.listdir('.')
        
    exit_status = 0
    for nc_file in nc_files:
        try:
            if args.all:
                ftp_host.upload(nc_file, '.')
            elif args.update:
                ftp_host.upload_if_newer(nc_file, '.')
            else:
                if os.path.basename(nc_file) in remote_files:
                    continue
                ftp_host.upload(nc_file, '.')
                
            logging.debug('File uploaded {:s}'.format(nc_file))
        except ftputil.FTPError as e:
            logging.error('Error uploading {:s} ({:s})'.format(nc_file, e))
            exit_status = 1
            continue
            
    return exit_status
    
if __name__ == '__main__':
    
    arg_parser = argparse.create_arg_parser(description=main.__doc__)
    
    arg_parser.add_argument('deployment_nc_path',
        help='Location of NetCDF files to be uploaded')
    
    arg_parser.add_argument('-h', '--host',
        help='FTP host url')
        
    arg_parser.add_argument('-u', '--user',
        help='User name')
        
    arg_parser.add_argument('-p', '--password',
        help='Password')
        
    arg_parser.add_argument('--update',
        help='Re-transfer file if a newer version exists locally',
        action='store_true')
        
    arg_parser.add_argument('-a', '--all',
        help='Transfer all files regardless of whether they exist on the remote',
        action='store_true')
        
    arg_parser.add_argument('-l', '--loglevel',
        help='Python logging level <Default=info>',
        type=str,
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')
        
    args = arg_parser.parse_args()
    
    sys.exit(main(args))