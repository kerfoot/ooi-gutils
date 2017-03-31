#!/usr/bin/env python

# create_glider_netcdf.py - A command line script for generating NetCDF files
# from a subset of glider binary data files.
#
# By: Michael Lindemuth <mlindemu@usf.edu>
# University of South Florida
# College of Marine Science
# Ocean Technology Group

import os
import sys
import json
import shutil
import argparse
import tempfile
import glob
import sys
from datetime import datetime

import numpy as np

from gutils.yo import find_yo_extrema
from gutils.gps import interpolate_gps
from gutils.yo.filters import default_profiles_filter

from gutils.nc import open_glider_netcdf, GLIDER_UV_DATATYPE_KEYS
#from gutils.nc import open_glider_netcdf

from gutils.readers.nc import *
from gutils.readers import stream_to_yo, stream_to_profiles

REQUIRED_CFG_FILES = ['datatypes.json',
    'global_attributes.json',
    'deployment.json',
    'instruments.json']
    
import logging
logger = logging.getLogger('gutils.nc')


def create_reader(nc_file, nc_type):
    
    if nc_type == 'm2m':
        dataset = m2m_nc_to_gutils_stream(nc_file)
    elif nc_type == 'erddap':
        dataset = erddap_nc_to_gutils_stream(nc_file)
    else:
        logger.error('Invalid NetCDF source file type {:s}'.format(nc_type))
        return
        
    if not dataset:
        logger.warning('No dataset parsed {:s}'.format(nc_file))
        return
        
    return dataset


def find_profiles(stream, timesensor='timestamp', depthsensor='sci_water_pressure_dbar'):
        
    # Create the yo
    yo = stream_to_yo(stream, depthsensor, timesensor=timesensor)
    if yo.shape[0] == 0:
        return
        
    # Index the profiles
    profile_times = find_yo_extrema(yo[:,0], yo[:,1])
    # Filter indexed profiles
    profile_times = default_profiles_filter(yo, profile_times)
    if profile_times.shape[0] == 0:
        logger.warning('No valid profiles found {:s}'.format(nc_file))
        return
        
    # Break the dataset['stream'] into arrays of profiles
    #return stream_to_profiles(yo[:,0], profile_times)

    return profile_times

#def get_file_set_gps(flight_path, science_path, time_name, gps_prefix):
#    gps_values = []
#    reader = create_reader(flight_path, science_path)
#    lat_name = gps_prefix + 'lat-lat'
#    lon_name = gps_prefix + 'lon-lon'
#    for line in reader:
#        if lat_name in line:
#            gps_values.append(
#                [line[time_name], line[lat_name], line[lon_name]]
#            )
#        else:
#            gps_values.append([line[time_name], np.nan, np.nan])
#
#    if not gps_values:
#        raise ValueError('Not enough gps posistions found')
#
#    try:
#        gps_values = np.array(gps_values)
#        timestamps = gps_values[:, 0]
#        latitudes = gps_values[:, 1]
#        longitudes = gps_values[:, 2]
#    except IndexError:
#        raise ValueError('Not enough timestamps, latitudes, or longitudes found')
#    else:
#        gps_values[:, 1], gps_values[:, 2] = interpolate_gps(
#            timestamps, latitudes, longitudes
#        )
#
#    return gps_values
#
#
#def fill_gps(line, interp_gps, time_name, gps_prefix):
#    lat_name = gps_prefix + 'lat-lat'
#    lon_name = gps_prefix + 'lon-lon'
#    if lat_name not in line:
#        timestamp = line[time_name]
#        line[lat_name] = interp_gps[interp_gps[:, 0] == timestamp, 1][0]
#        line[lon_name] = interp_gps[interp_gps[:, 0] == timestamp, 2][0]
#
#    return line


def init_netcdf(file_path, config_path, attrs, profile_id):
    with open_glider_netcdf(file_path, config_path, mode='w') as glider_nc:
        # Set global attributes
        glider_nc.set_global_attributes(attrs['global'])

        # Set Trajectory
        glider_nc.set_trajectory_id(
            attrs['deployment']['glider'],
            attrs['deployment']['trajectory_date']
        )

        # Set Platform
        glider_nc.set_platform(attrs['deployment']['platform'])

        # Set Instruments
        glider_nc.set_instruments(attrs['instruments'])

        # Set Segment ID
        #glider_nc.set_segment_id(segment_id)

        # Set Profile ID
        glider_nc.set_profile_id(profile_id)


#def find_segment_id(flight_path, science_path):
#    if flight_path is None:
#        filename = science_path
#    else:
#        filename = flight_path
#
#    details = parse_glider_filename(filename)
#    return details['segment']


def fill_uv_variables(dst_glider_nc, uv_values):
    for key, value in uv_values.items():
        dst_glider_nc.set_scalar(key, value)


def backfill_uv_variables(src_glider_nc, empty_uv_processed_paths):
    uv_values = {}
    for key_name in GLIDER_UV_DATATYPE_KEYS:
        uv_values[key_name] = src_glider_nc.get_scalar(key_name)

    for file_path in empty_uv_processed_paths:
        with open_glider_netcdf(file_path, 'a') as dst_glider_nc:
            fill_uv_variables(dst_glider_nc, uv_values)

    return uv_values


def create_arg_parser():
    parser = argparse.ArgumentParser(
        description=main.__doc__
    )

    parser.add_argument(
        'glider_deployment_path',
        help='Path to glider deployment configuration information'
    )

    parser.add_argument(
        'output_path',
        help='Written NetCDF file parent directory. A directory named after the deployment will be created here <Default=glider_deployment_path>.',
        nargs='?'
    )
    
    parser.add_argument('--timestamping',
        help='Timestamp log entries',
        action='store_true')
        
    parser.add_argument(
        '-v', '--verbosity',
        help='Print created NetCDF filenames to STDOUT',
        action='store_true'
    )

    parser.add_argument(
        '-m', '--mode',
        help="Set the mode for the file naming convention (rt|delayed) <Default=rt>",
        default="rt"
    )
    
    parser.add_argument(
        '--nctype',
        help='Type of source NetCDF file(s) to process <Default=m2m>',
        choices=['m2m', 'erddap'],
        default='m2m'
    )
    
    parser.add_argument(
        '-p', '--profilestart',
        help='Number specifying the starting profile id <Default=1>',
        type=int,
        default=1
    )

    parser.add_argument(
        '-t', '--time',
        help="Set time parameter to use for profile recognition <Default=timestamp>",
        default="timestamp"
    )

    parser.add_argument(
        '-d', '--depth',
        help="Set depth parameter to use for profile recognition <Default=sci_water_pressure_dbar>",
        default="sci_water_pressure_dbar"
    )
    
    parser.add_argument('-l', '--loglevel',
        help='Python logging level <Default=info>',
        type=str,
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')

    return parser


def read_attrs(glider_config_path):
    # Load in configurations
    attrs = {}

    def cfg_file(name):
        return os.path.join(
            glider_config_path,
            name
        )

    # Load institute global attributes
    global_attrs_path = cfg_file("global_attributes.json")
    with open(global_attrs_path, 'r') as f:
        attrs['global'] = json.load(f)

    # Load deployment attributes (including global attributes)
    deployment_attrs_path = cfg_file("deployment.json")
    try:
        with open(deployment_attrs_path, 'r') as f:
            attrs['deployment'] = json.load(f)
    except (OSError, ValueError) as e:
        logger.error('Error in {:s} - {:s}'.format(deployment_attrs_path, e))
        return

    # Load instruments
    instruments_attrs_path = cfg_file("instruments.json")
    with open(instruments_attrs_path, 'r') as f:
        attrs['instruments'] = json.load(f)

    # Fill in global attributes
    attrs['global'].update(attrs['deployment']['global_attributes'])

    return attrs


def process_ooi_dataset(args):

    glider_deployment_path = args.glider_deployment_path
    logger.debug('Deployment directory {:s}'.format(glider_deployment_path))
    if not os.path.isdir(glider_deployment_path):
        logger.error('Invalid deployment location {:s}'.format(args.glider_deployment_path))
        return 1
        
    # Create path to glider deployment configuration files
    cfg_path = os.path.join(glider_deployment_path, 'cfg')
    logger.debug('Deployment configuration directory {:s}'.format(cfg_path))
    if not os.path.isdir(cfg_path):
        logger.error('Deployment configuration path does not exist {:s}'.format(cfg_path))
        return 1
    # Make sure required config file exist
    cfg_status = True
    for f in REQUIRED_CFG_FILES:
        cfg_file = os.path.join(cfg_path, f)
        if not os.path.isfile(cfg_file):
            logger.error('Missing required config file {:s}'.format(cfg_file))
            cfg_status = False
    if not cfg_status:
        return 1
    
        
    # Create path to glider deployment status files
    status_path  = os.path.join(glider_deployment_path, 'status')
    logger.debug('Deployment status directory {:s}'.format(status_path))
    if not os.path.isdir(status_path):
        logger.error('Deployment status path does not exist {:s}'.format(status_path))
        return 1
        
    # Search for source NetCDF files
    nc_source_dir = os.path.join(glider_deployment_path, 'nc-source')
    logger.debug('Source NetCDF location {:s}'.format(nc_source_dir))
    if not os.path.isdir(nc_source_dir):
        logger.error('Invalid source NetCDF directory {:s}'.format(nc_source_dir))
        return 1
    nc_files = glob.glob(os.path.join(nc_source_dir, '*.nc'))
    if not nc_files:
        logger.info('No deployment source NetCDF files found {:s}'.format(nc_source_dir))
        return 1
    
    # Read deployment configuration files
    attrs = read_attrs(cfg_path)

    glider_name = attrs['deployment']['glider']
    deployment_name = '{}-{}'.format(
        glider_name,
        attrs['deployment']['trajectory_date']
    )

    # Profile id counter
    profile_status_file = os.path.join(status_path, '{:s}-profiles.json'.format(deployment_name))
    profile_id = 1
    if os.path.isfile(profile_status_file):
        try:
            with open(profile_status_file, 'r') as fid:
                profile_status = json.load(fid)
        except (OSError, ValueError) as e:
            logging.error('Status read error {:s} ({:s})'.format(profile_status_file, e))
            return 1
        # If there are entries in the profile_status array, get the max end time from
        # p['profile_max_time']
        if profile_status:
            # Find the max profile_id and increment it by one
            profile_id = max([p['profile_id'] for p in profile_status]) + 1
            
    #profile_id = args.profilestart
    
    # Process each input NetCDF file
    for nc_file in nc_files:
        
        # Create the NC_GLOBAL:history with the name of the source UFrame NetCDF file
        history = '{:s}: Data Source {:s}'.format(datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), nc_file)
        attrs['global']['history'] = '{:s}\n'.format(history)
        
        try:
           
            logger.info('Reading {:s}'.format(nc_file))
            dataset = create_reader(nc_file, args.nctype)
            logger.info('{:s} read complete'.format(nc_file))
            if not dataset:
                logger.warning('Skipping invalid NetCDF {:s}'.format(nc_file))
                continue
                
            stream = dataset['stream']
                
            # Find profile breaks
            profile_times = find_profiles(stream, depthsensor=args.depth, timesensor=args.time)
    
        except ValueError as e:
            logger.error('{} - Skipping'.format(e))
            return 1
            
        if profile_times.shape[0] == 0:
            logger.info('No profiles indexed {:s}'.format(nc_file))
            continue
        
        uv_values = None
        movepairs = []
#        uv_values = []
        empty_uv_processed_paths = []
    
        # Tempdirectory
        tmpdir = tempfile.mkdtemp()
    
        # All timestamps from stream
        ts = [r[args.time] for r in stream]
        
        # Create a new NetCDF file for each profile
        for profile in profile_times:

            # Profile start time
            p0 = profile[0]
            # Profile end time
            p1 = profile[-1]
            # Find all rows in ts that are between p0 & p1
            p_inds = np.flatnonzero(np.logical_and(ts >= p0, ts <= p1))
            profile_stream = stream[p_inds[0]:p_inds[-1]]
        
            # Path to hold file while we create it
            _, tmp_path = tempfile.mkstemp(dir=tmpdir, suffix='.nc', prefix='gutils')

            # Open new NetCDF
            begin_time = datetime.utcfromtimestamp(np.mean(profile))
            filename = "%s-%s_%s.nc" % (
                glider_name,
                begin_time.strftime("%Y%m%dT%H%M%SZ"),
                args.mode
            )

            file_path = os.path.join(
                args.output_path,
                deployment_name,
                filename
            )

            logger.debug('tmp_path={:s}'.format(tmp_path))
            #init the NetCDF output file
            init_netcdf(tmp_path, cfg_path, attrs, profile_id)
            
            with open_glider_netcdf(tmp_path, cfg_path, mode='a') as glider_nc:
                for line in profile_stream:
                    
                    #Append the row to the NetCDF file
                    glider_nc.stream_dict_insert(line)
    
                # Handle UV Variables
                if glider_nc.contains('time_uv'):
                    uv_values = backfill_uv_variables(
                        glider_nc, empty_uv_processed_paths
                    )
                elif uv_values is not None:
                    fill_uv_variables(glider_nc, uv_values)
                    del empty_uv_processed_paths[:]
                else:
                    empty_uv_processed_paths.append(tmp_path)
    
                # Update the scalar profile variables
                glider_nc.update_profile_vars()
                glider_nc.update_bounds()
                
                # Update the global title attribute with the glider name and
                # formatted self.nc.variables['profile_time']:
                # glider-YYYYmmddTHHMM
                glider_nc.update_global_title(glider_name)
    
            movepairs.append((tmp_path, file_path))
    
            profile_id += 1
    
        # Set move_status to False if any NetCDF move fails so that the temporary
        # directory is not removed.
        move_status = True
        for tp, fp in movepairs:
            dest_dir = os.path.dirname(fp)
            if not os.path.isdir(dest_dir):
                try:
                    logger.debug('Creating NetCDF destination {:s}'.format(dest_dir))
                    os.makedirs(dest_dir)
                except OSError as e:
                    logger.error('Failed to create {:s} ({:s})'.format(dest_dir, e))
                    continue
            # Move the file from the temporary directory to the destination
            if args.verbosity:
                sys.stdout.write('{:s}\n'.format(fp))
            try:
                shutil.move(tp, fp)
            except OSError as e:
                logger.error('Failed to move NetCDF {:s} ({:s})'.format(tp, e))
                move_status = False
                continue
        
        # Remove the temporary directory if all NetCDF moves succeeded        
        if move_status:
            shutil.rmtree(tmpdir)

    return 0


def main():
    """Write U.S. IOOS National Glider Data Assembly Center compliant NetCDF
    files from one or more OOI/UFrame glider NetCDF files.  
    """

    parser = create_arg_parser()
    args = parser.parse_args()

    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(module)s:%(funcName)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    if args.timestamping:
        log_format = '%(asctime)s:%(funcName)s:%(module)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    logging.basicConfig(format=log_format, level=log_level)
    
    # Check args
    if not args.output_path:
        args.output_path = args.glider_deployment_path

    return process_ooi_dataset(args)


if __name__ == '__main__':
    sys.exit(main())
