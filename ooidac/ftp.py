#!/usr/bin/env python

import os
import logging
import ftputil
import sys
import argparse

logger = logging.getLogger(os.path.basename(__file__))

def main(args):
    """FTP one or more U.S. IOOS DAC NetCDF files to the U.S. IOOS Glider Data
    assembly center FTP server"""
    
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(module)s:%(funcName)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    if args.timestamping:
        log_format = '%(asctime)s:%(funcName)s:%(module)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    logging.basicConfig(format=log_format, level=log_level)
    
    if not args.host:
        logging.error('No FTP host specified')
        return 1
        
    if not args.user:
        logging.error('No FTP username specified')
        return 1
        
    if not args.password:
        logging.error('No FTP password specified')
        return 1
        
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

    
        
def ftp_trajectory_nc_to_dac(host, user, pw, trajectory, nc_files, update=True):
    """FTP one or more U.S. IOOS DAC NetCDF files to the U.S. IOOS Glider Data
    assembly center FTP server
    
    Arguments:
        host: host URL without ftp://
        user: FTP account user name
        pw: FTP account password
        trajectory: remote directory identifying the deployment/trajectory
        nc_files: list of local NetCDF files to transfer
        update (optional): Set to True <default> to re-transfer existing NetCDF files
            if the local file is newer than the remote file
    """
    
    ftp_files = []
    
    if not nc_files:
        logger.info('No local NetCDF files specified')
        return ftp_files
    if type(nc_files) != list:
        logger.warning('Local files must be a list')
        return ftp_files
    
    # Connect to the FTP server
    try:
        ftp_host = ftputil.FTPHost(host, user, pw)
        # Synchronize times between host and local machines
        ftp_host.synchronize_times()
    except ftputil.FTPError as e:
        logging.error('ftputil {:s}'.format(e))
        return 1
    
    # Get the list of trajectory directories on the server
    ftp_trajectories = ftp_host.listdir('.')
    if trajectory not in ftp_trajectories:
        logging.warning('Deployment has not been registered {:s}'.format(trajectory))
        ftp_host.close()
        return 1
        
    # Change to the remote trajectory directory
    ftp_host.chdir(trajectory)
    
    # Get the list of remote files
    remote_files = ftp_host.listdir('.')
        
    for nc_file in nc_files:
        if not nc_file.endswith('.nc'):
            logger.warning('Specified file is not NetCDF {:s}'.format(nc_file))
            continue
        try:
            if update:
                ftp_host.upload_if_newer(nc_file, '.')
            else:
                if os.path.basename(nc_file) in remote_files:
                    continue
                ftp_host.upload(nc_file, '.')
            logger.info('File uploaded {:s}'.format(nc_file))
            ftp_files.append(nc_file)
        except ftputil.FTPError as e:
            logging.error('Error uploading {:s} ({:s})'.format(nc_file, e))
            continue
            
    return ftp_files
    
if __name__ == '__main__':
    
    arg_parser = argparse.create_arg_parser(description=main.__doc__)
    
    arg_parser.add_argument('nc_files',
        help='One or more NetCDF files',
        nargs='+')
    
    arg_parser.add_argument('-h', '--host',
        help='FTP host url')
        
    arg_parser.add_argument('-u', '--user',
        help='User name')
        
    arg_parser.add_argument('-p', '--password',
        help='Password')
        
    arg_parser.add_argument('--update',
        help='Re-transfer file if the local file is newer than the remote file',
        action='store_true')
        
    arg_parser.add_argument('-l', '--loglevel',
        help='Python logging level <Default=info>',
        type=str,
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')
        
    args = arg_parser.parse_args()
    
    sys.exit(main(args))