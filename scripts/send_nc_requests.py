#!/usr/bin/env python

import logging
import argparse
import os
import sys
import json
import datetime
from dateutil import parser
import pytz
from m2m.UFrameClient import UFrameClient
from ooidac import (
    build_trajectory_name,
    GLIDER_INSTRUMENT_TYPES, 
    GLIDER_TELEMETRY_TYPES,
    GLIDER_INSTRUMENT_STREAMS
)

# Send new requests if at least MIN_DATASET_UPDATE_MINUTES have been added to the UFrame stream
MIN_DATASET_UPDATE_MINUTES = 60
MIN_DATASET_UPDATE_SECONDS = MIN_DATASET_UPDATE_MINUTES*60

def main(args):
    """Send OOI glider deployment asynchronous NetCDF requests for creation of U.S. 
    IOOS Glider Data Assembly Center NetCDF file creation by querying OOI UFrame asset management."""
   
    # Dummy user.  Requests are now mapped to the UI login user account
    user = os.getenv('USER') or 'anonymous'
    
    exit_status = 0
    
    # Set up the erddapfoo.lib.m2m.M2mClient logger
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(module)s:%(funcName)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    logging.basicConfig(format=log_format, level=log_level)
    
    # Deployments home directory
    deployments_root = args.root or os.getenv('OOI_GLIDER_DAC_HOME')
    if not deployments_root:
        logging.error('No deployments root specified (OOI_GLIDER_DAC_HOME not set?)')
        return 1
    if not os.path.isdir(deployments_root):
        logging.error('Invalid deployments root {:s}'.format(deployments_root))
        return 1
        # Deployment directories home
    deployments_home = os.path.join(deployments_root, 'deployments')
    if not os.path.isdir(deployments_home):
        logging.error('Invalid deployments home {:s}'.format(deployments_home))
        return 1
        
    # UFrame instance
    uframe_base_url = args.base_url or os.getenv('UFRAME_BASE_URL')
    if not uframe_base_url:
        logging.error('No base_url set/found')
        return 1

    client = UFrameClient(uframe_base_url, timeout=args.timeout, m2m=True)
    
    # Fetch all MOAS instruments
    instruments = client.search_instruments('MOAS')
    if not instruments:
        logging.warning('No MOAS instruments found {:s}'.format(client.base_url))
        return 1
    gliders = list(set('-'.join(i.split('-')[:2]) for i in instruments))
    gliders.sort()
        
    seen_deployments = []
    for glider in gliders:
        
        logging.debug('Processing glider {:s}'.format(glider))
        
        # Fetch all deployments of this instrument
        logging.debug('Fetching all deployments for {:s}'.format(glider))
        instrument_deployments = client.fetch_instrument_deployments(glider)
        if not instrument_deployments:
            logging.debug('No deployments found for {:s}'.format(glider))
            continue
        # Filter deployments by status type
        logging.debug('Filtering for {:s} deployments'.format(args.status))
        status_deployments = client.filter_deployments_by_status(instrument_deployments, status=args.status)
        if not status_deployments:
            logging.debug('No {:s} deployments for {:s}'.format(args.status, glider))
            continue
    
        for deployment in status_deployments:
            
            if deployment['referenceDesignator'].split('-')[-1] not in args.instruments:
                continue
            
            deployment_dir = '{:s}-deployment{:04.0f}-{:s}'.format(glider, deployment['deploymentNumber'], GLIDER_TELEMETRY_TYPES[args.status])
            logging.info('Checking deployment {:s}'.format(deployment_dir))
            deployment_path = os.path.join(deployments_home, deployment_dir)            
            
            if deployment_dir in seen_deployments:
                logging.warning('Deployment not configured {:s}'.format(deployment_dir))
                continue
            seen_deployments.append(deployment_dir)
                
            if not os.path.isdir(deployment_path):
                logging.warning('Deployment path not found {:s}'.format(deployment_path))
                continue
            
            # Validate required directories
            cfg_dir = os.path.join(deployment_path, 'cfg')
            nc_source_dir = os.path.join(deployment_path, 'nc-source')
            nc_archive_dir = os.path.join(deployment_path, 'nc-archive')
            deployment_status_dir = os.path.join(deployment_path, 'status')
            
            # Skip this deployment if the recovered.txt file is present
            if os.path.isfile(os.path.join(cfg_dir, 'recovered.txt')):
                logging.info('Skipping deployment: {:s} has been recovered'.format(deployment_dir))
                continue
                
            # Create trajectory name
            deployment_json_file = os.path.join(cfg_dir, 'deployment.json')
            if not os.path.isfile(deployment_json_file):
                logging.warning('Deployment configuration does not exist {:s}'.format(deployment_json_file))
                continue
                
            # Read deployment_json_file
            try:
                with open(deployment_json_file, 'r') as fid:
                    deployment_cfg = json.load(fid)
            except (OSError, ValueError) as e:
                logging.error('Error reading deployment config file: {:s} ({:s})'.format(deployment_json_file, e))
                continue
                
            if 'glider' not in deployment_cfg:
                logging.error('Missing glider in deployment configuration: {:s}'.format(deployment_json_file))
                return 1
            if 'trajectory_date' not in deployment_cfg:
                logging.error('Missing trajectory_date in deployment_configuration: {:s}'.format(deployment_json_file))
                return 1
        
            trajectory = build_trajectory_name(deployment_cfg['glider'], deployment_cfg['trajectory_date'])
            if not trajectory:
                logging.error('Error creating trajectory identifier {:s}'.format(deployment_json_file))
                continue
            logging.debug('Trajectory {:s}'.format(trajectory))
            
            # Create DAC NetCDF destination
            nc_queue_dir = os.path.join(deployment_path, trajectory)
            
            # Validate existence of the deployment configuration directory
            if not os.path.isdir(cfg_dir):
                logging.error('Missing deployment configuration directory {:s}'.format(cfg_dir))
                continue
            # Validate existence of NetCDF archive directory
            if not os.path.isdir(nc_archive_dir):
                logging.error('Missing archive NetCDF directory {:s}'.format(nc_archive_dir))
                continue
            # See if the deployment JSON file exists
            if not os.path.isfile(deployment_json_file):
                logging.error('Missing deployment configuration file {:s}'.format(deployment_json_file))
                continue    
            # Create source NetCDF file directory
            if not os.path.isdir(nc_source_dir):
                logging.error('Missing source NetCDF directory {:s}'.format(nc_source_dir))
                continue
            # Validate existence of status directory
            if not os.path.isdir(deployment_status_dir):
                logging.error('Missing deployment status directory {:s}'.format(deployment_status_dir))
                continue
                
            logging.debug('Deployment config dir {:s}'.format(cfg_dir))
            logging.debug('NetCDF Source dir {:s}'.format(nc_source_dir))
            logging.debug('NetCDF Archive dir {:s}'.format(nc_archive_dir))
            logging.debug('Deployments JSON file {:s}'.format(deployment_json_file))
            logging.debug('NetCDF Queue dir {:s}'.format(nc_queue_dir))
            logging.debug('Deployment Status dir {:s}'.format(deployment_status_dir))
            
            # Skip if there is a pending NetCDF request
            request_file = os.path.join(deployment_status_dir, '{:s}-requests.json'.format(deployment_dir))
            if os.path.isfile(request_file):
                logging.warning('Request in process - Skipping {:s}'.format(deployment_dir))
                continue
    
            # Parse/set deployment start/stop times
            if not deployment['eventStartTime']:
                logging.warning('No eventStartTime for {:s}'.format(deployment_dir))
                continue
            try:
                dt0 = datetime.datetime.utcfromtimestamp(deployment['eventStartTime']/1000).replace(tzinfo=pytz.UTC)
            except ValueError as e:
                logging.error('Error parsing deployment eventStartTime {:s}'.format(deployment['eventStartTime']))
                continue
            dt1 = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
            if deployment['eventStopTime']:
                try:
                    dt1 = datetime.datetime.utcfromtimestamp(deployment['eventStopTime']/1000).replace(tzinfo=pytz.UTC)
                except ValueError as e:
                    logging.error('Error parsing deployment eventStopTime {:s}'.format(deployment['eventStopTime']))
                    continue
                    
            nc_end_dt = None
            # Profile status file used to store information about previously created NetCDF files.  Used to set up the
            # aynchronouse NetCDF requests
            profile_status_file = os.path.join(deployment_status_dir, '{:s}-profiles.json'.format(trajectory))
            if os.path.isfile(profile_status_file):
                try:
                    with open(profile_status_file, 'r') as fid:
                        profile_status = json.load(fid)
                except (OSError, ValueError) as e:
                    logging.error('Status read error {:s} ({:s})'.format(profile_status_file, e))
                    continue
                # If there are entries in the profile_status array, get the max end time from
                # p['profile_max_time'] and add 1 second
                if profile_status:
                    try:
                        profile_max_times = [p['profile_max_time'] for p in profile_status]
                        nc_end_dt = datetime.datetime.utcfromtimestamp(max(profile_max_times)).replace(tzinfo=pytz.UTC) + datetime.timedelta(seconds=1)
                    except ValueError as e:
                        logging.error('Error parsing max_profile_time {:s}'.format(profile_status_file))
                        
            # Get the list of instruments on this glider
            glider_instruments = client.search_instruments(glider)
            async_requests = []
            for i in glider_instruments:
                instrument_class = i.split('-')[-1]
                if instrument_class not in args.instruments:
                    continue
                if instrument_class not in GLIDER_INSTRUMENT_STREAMS[args.status]:
                    logging.warning('No stream found for {:s}'.format(i))
                    continue
                stream_info = GLIDER_INSTRUMENT_STREAMS[args.status][instrument_class]
                # Fetch all streams produced by this instrument
                instrument_streams = client.fetch_instrument_streams(i)
                if not instrument_streams:
                    logging.warning('No streams found for {:s}'.format(i))
                    continue
                # Find the target stream
                target_streams = [s for s in instrument_streams if s['method'] == stream_info['method'] and s['stream'] == stream_info['stream']]
                if not target_streams:
                    logging.warning('Missing target stream {:s}-{:s}-{:s}'.format(i, stream_info['stream'], stream_info['method']))
                    continue
                elif len(target_streams) > 1:
                    logging.warning('Multiple target streams found {:s}-{:s}-{:s}'.format(i, stream_info['stream'], stream_info['method']))
                    continue
                    
                # Convenience
                target_stream = target_streams[0]
                
                # Parse the stream start and end times
                try:
                    stream_dt0 = parser.parse(target_stream['beginTime'])
                except ValueError as e:
                    logging.error('Error parsing {:s}-{:s}-{:s} beginTime {:s}'.format(i, stream_info['stream'], stream_info['method'], target_stream['beginTime']))
                    continue
                try:
                    stream_dt1 = parser.parse(target_stream['endTime'])
                except ValueError as e:
                    logging.error('Error parsing {:s}-{:s}-{:s} endTime {:s}'.format(i, stream_info['stream'], stream_info['method'], target_stream['endTime']))
                    continue
                    
                # Make sure the stream data falls within the deployment window
                if stream_dt1 < dt0:
                    logging.warning('No stream data within deployment window {:s}-{:s}-{:s}'.format(i, stream_info['stream'], stream_info['method']))
                    continue
                    
                # Figure out the start_date and end_date for the async request
                start_date = dt0
                end_date = dt1
                if nc_end_dt and nc_end_dt > start_date:
                    start_date = nc_end_dt
                if stream_dt1 < end_date:
                    end_date = stream_dt1
                    
                # Skip if start_date is after end_date as there is no new data
                #available
                if start_date >= end_date:
                    logging.debug('No update to UFrame {:s}-{:s}-{:s}'.format(i, stream_info['stream'], stream_info['method']))
                    continue
                    
                # Calculate the delta between end_date and start_date
                delta_date = end_date - start_date
                if delta_date.total_seconds() <= MIN_DATASET_UPDATE_SECONDS:
                    logging.info('No UFrame updates to {:s}-{:s}-{:s}'.format(i, stream_info['stream'], stream_info['method']))
                    continue
                    
                logging.info('UFrame dataset has been updated {:s}-{:s}-{:s}'.format(i, stream_info['stream'], stream_info['method']))
                    
                # Create the async request url
                stream_requests = client.instrument_to_query(i,
                    user,
                    stream=target_stream['stream'],
                    telemetry=target_stream['method'],
                    begin_ts=start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    end_ts=end_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    time_check=False,
                    exec_dpa=True,
                    application_type='netcdf',
                    provenance=False,
                    limit=-1)
                if not stream_requests:
                    continue
                    
                # If debugging (args.debug) print the async request url, but do not send it
                if args.debug:
                    sys.stdout.write('Request URL: {:s}\n'.format(stream_requests[0]))
                    continue
                   
                # Send the request
                logging.info('Sending request {:s}'.format(stream_requests[0])) 
                response = client.send_request(stream_requests[0])
                r = {'name' : deployment_dir,
                    'path' : deployment_path,
                    'instrument' : i,
                    'stream' : target_stream['stream'],
                    'method' : target_stream['method'],
                    'deployment_number' : deployment['deploymentNumber'],
                    'request_url' : stream_requests[0],
                    'response' : response}

                async_requests.append(r)
            
            if async_requests:
                logging.info('Writing responses {:s}'.format(request_file))
                try:    
                    with open(request_file, 'w') as fid:
                        json.dump(async_requests, fid, indent=4)
                except OSError as e:
                    logging.error('Failed to write response file {:s} ({:s})'.format(request_file, e))
                
    return exit_status

    
if __name__ == '__main__':

    arg_parser = argparse.ArgumentParser(description=main.__doc__)
    arg_parser.add_argument('-r', '--root',
        help='Root directory containing the OOI glider deployment folders and master configurations.  Taken from OOI_GLIDER_DAC_HOME if not specified')
    arg_parser.add_argument('-s', '--status',
        dest='status',
        type=str,
        default='active',
        choices=['active', 'inactive'],
        help='Specify the status of the deployment <Default=active>')
    arg_parser.add_argument('-i', '--instruments',
        help='Instrument type <Default=CTDGVM000>',
        nargs='+',
        default=['CTDGVM000'],
        choices=GLIDER_INSTRUMENT_TYPES)
    arg_parser.add_argument('-b', '--baseurl',
        dest='base_url',
        type=str,
        help='UFrame m2m base url beginning with https.  Taken from UFRAME_BASE_URL if not specified')
    arg_parser.add_argument('-l', '--loglevel',
        help='Verbosity level <Default=info>',
        type=str,
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')
    arg_parser.add_argument('-x', '--debug',
        help='Print new deployments but do not perform any intitialization',
        action='store_true')
    arg_parser.add_argument('-t', '--timeout',
        type=int,
        default=30,
        help='Request timeout, in seconds <Default=30>')

    parsed_args = arg_parser.parse_args()
    #print parsed_args
    #sys.exit(1)

    sys.exit(main(parsed_args))
