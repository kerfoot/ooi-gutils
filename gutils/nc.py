#!/usr/bin/env python

# GLIDER_NETCDF_WRITER - Creates a file like object into which
#   glider binary data readers can insert data.
#
# Depends on the glider_binary_data_reader library:
# https://github.com/USF-COT/glider_binary_data_reader
#
# By: Michael Lindemuth
# University of South Florida
# College of Marine Science
# Ocean Technology Group
#
# Much of the code below is derived from John Kerfoot's ioos_template_example.py  # NOQA
# https://github.com/IOOSProfilingGliders/Real-Time-File-Format/blob/master/util/ioos_template_example.py#L136  # NOQA

import os
import sys
import json
from datetime import datetime
from dateutil import parser

import numpy as np
from netCDF4 import Dataset, stringtoarr
from netCDF4 import default_fillvals as NC_FILL_VALUES

from gutils.ctd import calculate_practical_salinity, calculate_density

import logging
logger = logging.getLogger(__name__)

#DEFAULT_GLIDER_BASE = os.path.join(os.path.dirname(__file__), 'datatypes')

GLIDER_QC = {
    "no_qc_performed": 0,
    "good_data": 1,
    "probably_good_data": 2,
    "bad_data_that_are_potentially_correctable": 3,
    "bad_data": 4,
    "value_changed": 5,
    "interpolated_value": 8,
    "missing_value": 9
}

GLIDER_UV_DATATYPE_KEYS = (
    'time_uv',
    'm_water_vx',
    'm_water_vy',
    'lon_uv',
    'lat_uv'
)

def open_glider_netcdf(output_path, config_path, mode=None, COMP_LEVEL=None,
                       DEBUG=False):

    mode = mode or 'w'
    COMP_LEVEL = COMP_LEVEL or 1
    return GliderNetCDFWriter(output_path, config_path, mode, COMP_LEVEL, DEBUG)


class GliderNetCDFWriter(object):
    """Writes a NetCDF file for glider datasets

    """

    def __init__(self, output_path, config_path, mode=None, COMP_LEVEL=None,
                 DEBUG=False):
        """Initializes a Glider NetCDF Writer
        NOTE: Does not open the file.

        Input:
        - output_path: Path to new or existing NetCDF file.
        - mode: 'w' to create or overwrite a NetCDF file.
                'a' to append to an existing NetCDF file.
                Default: 'w'
        - COMP_LEVEL: NetCDF compression level.
        """

        self.nc = None
        self.output_path = output_path
        self.mode = mode or 'w'
        self.COMP_LEVEL = COMP_LEVEL or 1
        self.config_path = config_path
        self.DEBUG = DEBUG
        self.datatypes = {}
        
        #self.__create_netcdf()

    def __setup_qaqc(self):
        """ Internal function for qaqc variable setup
        """

        # Create array of unsigned 8-bit integers to use for _qc flag values
        self.QC_FLAGS = np.array(range(0, 10), 'int8')
        # Meanings of QC_FLAGS
        self.QC_FLAG_MEANINGS = "no_qc_performed good_data probably_good_data bad_data_that_are_potentially_correctable bad_data value_changed not_used not_used interpolated_value missing_value"  # NOQA

        self.qaqc_methods = {}

    def __load_datatypes(self):
        """ Internal function to setup known datatypes

            Adds variables from base_variables.json
        """

        datatypes_path = os.path.join(
            self.config_path,
            'datatypes.json'
        )
        #if not os.path.isfile(datatypes_path):
        #    # Fall back to the included datatypes.json
        #    datatypes_path = os.path.join(
        #        DEFAULT_GLIDER_BASE,
        #        'datatypes.json'
        #    )

        with open(datatypes_path, 'r') as f:
            contents = f.read()
        self.datatypes = json.loads(contents)

    def __update_history(self):
        """ Updates the history, date_created, date_modified
        and date_issued file attributes
        """

        # Get timestamp for this access
        # Cannot use datetime.isoformat()
        # does not append Z at end of string
        now_time = datetime.utcnow()
        time_string = now_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        history_string = "%s: %s\n" % (time_string, os.path.realpath(sys.argv[0]))

        if 'history' not in self.nc.ncattrs():
            self.nc.setncattr("history", history_string)
            self.nc.setncattr("date_created", time_string)
        else:
            self.nc.history += history_string

        self.nc.setncattr("date_modified", time_string)
        self.nc.setncattr("date_issued", time_string)

    def __get_time_len(self):
        if 'time' in self.nc.variables:
            return len(self.nc.variables['time'])
        else:
            return 0
            
    def __enter__(self):
        """ Opens the NetCDF file. Sets up QAQC and time variables.
        Updates global history variables.
        Called at beginning of Python with block.
        """

        self.nc = Dataset(
            self.output_path, self.mode,
            format='NETCDF4_CLASSIC'
        )

        self.__setup_qaqc()
        self.__load_datatypes()

        self.__update_history()
        self.stream_index = self.__get_time_len()

        return self

    def __exit__(self, type, value, tb):
        """ Updates bounds and closes file.  Called at end of "with" block
        """

        if self.__get_time_len() > 0:
            self.update_bounds()

        self.nc.close()
        self.nc = None

    def __create_netcdf(self):
        """ Opens the NetCDF file. Sets up QAQC and time variables.
        Updates global history variables.
        Called at beginning of Python with block.
        """

        self.nc = Dataset(
            self.output_path, self.mode,
            format='NETCDF4_CLASSIC'
        )

        #self.__setup_qaqc()
        self.__load_datatypes()

        self.__update_history()
        self.stream_index = self.__get_time_len()

        #return self


    def set_global_attributes(self, global_attributes):
        """ Sets a dictionary of values as global attributes

        Warning!
        Each file must have different values for the following parameters:
        date_created, date_issued, date_modified
        geospatial_
            lat_max
            lat_min
            lat_resolution
            lat_units
            lon_max
            lon_min
            lon_resolution
            lon_units
            vertical_max
            vertical_min
            vertical_positive
            vertical_resolution
            vertical_units
        history
        id
        time_coverage_end
        time_coverage_resolution
        time_coverage_start
        """

        for key, value in sorted(global_attributes.items()):
            self.nc.setncattr(key, value)

    def set_trajectory_id(self, glider, deployment_date):
        """ Sets the trajectory dimension and variable for the dataset and the
        global id attribute

        Input:
            - glider: Name of the glider deployed.
            - deployment_date: String or DateTime of when glider was
                first deployed.
        """

        if(type(deployment_date) is datetime):
            deployment_date = deployment_date.strftime("%Y%m%dT%H%M%SZ")
        elif type(deployment_date) is str or type(deployment_date) is unicode:
            # Parse deployment date string to UTC datetime
            try:
                if not deployment_date.endswith('Z'):
                    deployment_date = '{:s}Z'.format(deployment_date)
                dt = parser.parse(deployment_date)
                deployment_date = dt.strftime("%Y%m%dT%H%M%SZ")
            except ValueError as e:
                logger.error('Invalid deployment date specified {:s} ({:s})'.format(deployment_date, e))
                return

        traj_str = "%s-%s" % (glider, deployment_date)

        if 'trajectory' not in self.nc.variables:
            # Setup Trajectory Dimension
            self.nc.createDimension('traj_strlen', len(traj_str))

            # Setup Trajectory Variable
            trajectory_var = self.nc.createVariable(
                'trajectory',
                'S1',
                ('traj_strlen',),
                zlib=True,
                complevel=self.COMP_LEVEL
            )

            attrs = {
                'cf_role': 'trajectory_id',
                'long_name': 'Trajectory/Deployment Name',  # NOQA
                'comment': 'A trajectory is a single deployment of a glider and may span multiple data files.'  # NOQA
            }
            for key, value in sorted(attrs.items()):
                trajectory_var.setncattr(key, value)
        else:
            trajectory_var = self.nc.variables['trajectory']

        trajectory_var[:] = stringtoarr(traj_str, len(traj_str))
        self.nc.id = traj_str  # Global id variable

    def check_datatype_exists(self, key):
        if key not in self.datatypes:
            raise KeyError('Unknown datatype %s cannot '
                           'be inserted to NetCDF' % key)

        datatype = self.datatypes[key]
        if datatype['name'] not in self.nc.variables:
            self.set_datatype(key, datatype)

        return datatype

    def get_status_flag_name(self, name):
        return name + "_qc"

    def set_datatype(self, key, desc):
        """ Sets up a datatype description for the dataset
        """
        
        if 'is_dimension' in desc and desc['is_dimension']:
            self.nc.createDimension(desc['name'], desc['dimension_length'])

        if len(desc) == 0:
            return  # Skip empty configurations

        if desc['name'] in self.nc.variables:
            return  # This variable already exists

        if desc['dimension'] is None:
            dimension = ()
        else:
            dimension = (desc['dimension'],)

        datatype = self.nc.createVariable(
            desc['name'],
            desc['type'],
            dimensions=dimension,
            zlib=True,
            complevel=self.COMP_LEVEL,
            fill_value=NC_FILL_VALUES[desc['type']]
        )

        # Add an attribute to note the variable name used in the source data file
        desc['attrs']['source_variable'] = key
        for k, v in sorted(desc['attrs'].items()):
            datatype.setncattr(k, v)

        if 'status_flag' in desc:
            status_flag = desc['status_flag']
            status_flag_name = self.get_status_flag_name(desc['name'])
            datatype.setncattr('ancillary_variables', status_flag_name)
            status_flag_var = self.nc.createVariable(
                status_flag_name,
                'i1',
                dimension,
                zlib=True,
                complevel=self.COMP_LEVEL,
                fill_value=NC_FILL_VALUES['i1']
            )
            # Append defaults
            sf_standard_name = desc['attrs']['standard_name'] + ' status_flag'
            status_flag['attrs'].update({
                'standard_name': sf_standard_name,
                'flag_meanings': self.QC_FLAG_MEANINGS,
                'valid_min': self.QC_FLAGS[0],
                'valid_max': self.QC_FLAGS[-1],
                'flag_values': self.QC_FLAGS
            })
            for key, value in sorted(status_flag['attrs'].items()):
                status_flag_var.setncattr(key, value)
        
    def perform_qaqc(self, key, value):
        if key in self.qaqc_methods:
            flag = self.qaqc_methods[key](value)
        elif value == NC_FILL_VALUES['f8']:
            flag = GLIDER_QC["missing_value"]
        else:
            flag = GLIDER_QC['no_qc_performed']

        return flag
        
    def set_scalar(self, key, value=None):
        datatype = self.check_datatype_exists(key)

        # Set None or NaN values to _FillValue
        if value is None or np.isnan(value):
            value = NC_FILL_VALUES[datatype['type']]

        self.nc.variables[datatype['name']].assignValue(value)

        if "status_flag" in datatype:
            status_flag_name = self.get_status_flag_name(datatype['name'])
            flag = self.perform_qaqc(key, value)
            self.nc.variables[status_flag_name].assignValue(flag)

    def set_array_value(self, key, index, value=None):
        datatype = self.check_datatype_exists(key)

        # Set None or NaN values to _FillValue
        if value is None or np.isnan(value):
            value = NC_FILL_VALUES[datatype['type']]

        self.nc.variables[datatype['name']][index] = value

        if "status_flag" in datatype:
            status_flag_name = self.get_status_flag_name(datatype['name'])
            flag = self.perform_qaqc(key, value)
            self.nc.variables[status_flag_name][index] = flag

    def set_array(self, key, values):
        datatype = self.check_datatype_exists(key)

        self.nc.variables[datatype['name']][:] = values
        if "status_flag" in datatype:
            status_flag_name = self.get_status_flag_name(datatype['name'])
            for i, value in enumerate(values):
                flag = self.perform_qaqc(key, value)
                self.nc.variables[status_flag_name][i] = flag

    def set_segment_id(self, segment_id):
        """ Sets the segment ID as a variable

        SEGMENT_ID
        segment_id: 2 byte integer
        kerfoot@marine.rutgers.edu: explicitly specify fill_value when creating
        variable so that it shows up as a variable attribute.  Use the default
        fill_value based on the data type
        """

        self.set_scalar('segment_id', segment_id)

    def set_profile_id(self, profile_id):
        """ Sets Profile ID in NetCDF File

        """

        self.set_scalar('profile_id', profile_id)

    def set_platform(self, platform_attrs):
        """ Creates a variable that describes the glider
        """

        self.set_scalar('platform')
        for key, value in sorted(platform_attrs.items()):
            self.nc.variables['platform'].setncattr(key, value)

    def set_instrument(self, name, var_type, attrs):
        """ Adds a description for a single instrument
        """

        if name not in self.nc.variables:
            self.nc.createVariable(
                name,
                var_type,
                fill_value=NC_FILL_VALUES[var_type]
            )

        for key, value in sorted(attrs.items()):
            self.nc.variables[name].setncattr(key, value)

    def set_instruments(self, instruments_array):
        """ Adds a list of instrument descriptions to the dataset
        """

        for description in instruments_array:
            self.set_instrument(
                description['name'],
                description['type'],
                description['attrs']
            )

    def fill_uv_vars(self, line):
        self.set_scalar('time_uv', line['m_present_time-timestamp'])
        self.set_scalar('lat_uv', line['m_gps_lat-lat'])
        self.set_scalar('lon_uv', line['m_gps_lon-lon'])
        
    def stream_dict_insert(self, line, qaqc_methods={}):
        """ Adds a data point glider_binary_data_reader library to NetCDF

        Input:
        - line: A dictionary of values where the key is a given
                <value name>-<units> pair that matches a description
                in the datatypes.json file.
        """

        if 'timestamp' not in line:
            raise ValueError('No timestamp found for line')

        self.set_array_value('timestamp', self.stream_index, line['timestamp'])

        for name, value in line.items():
            if name == 'timestamp':
                continue  # Skip timestamp, inserted above

            try:
                datatype = self.check_datatype_exists(name)
            except KeyError:
                if self.DEBUG:
                    logger.exception("Datatype {} does not exist".format(name))
                continue

            datatype = self.datatypes[name]
            if datatype['dimension'] == 'time':
                self.set_array_value(name, self.stream_index, value)
            else:
                self.set_scalar(name, value)
                if name == "m_water_vx-m/s":
                    self.fill_uv_vars(line)

        self.stream_index += 1
        
    def contains(self, datatype_key):
        if datatype_key in self.datatypes:
            field_name = self.datatypes[datatype_key]['name']
            return field_name in self.nc.variables
        else:
            return False

    def get_scalar(self, datatype_key):
        if self.contains(datatype_key):
            field_name = self.datatypes[datatype_key]['name']
            return self.nc.variables[field_name].getValue()

    def copy_field(self, src_glider_nc, datatype_key):
        datatype = self.check_datatype_exists(datatype_key)
        field_name = datatype['name']

        if src_glider_nc.contains(field_name):
            src_variable = src_glider_nc.nc.variables[field_name]

            if 'time' in src_variable.dimensions:
                self.set_array(datatype_key, src_variable[:])
            else:
                self.set_scalar(datatype_key, src_variable.getValue())

        else:
            raise KeyError(
                'Field not found in source glider NetCDF: %s' % field_name
            )

    def copy_glider_datatypes(self, src_glider_nc, datatype_keys):
        for datatype_key in datatype_keys:
            try:
                self.copy_field(src_glider_nc, datatype_key)
            except KeyError:
                logger.exception("Copy field failed")

    def __netcdf_to_np_op(self, variable_data, operation):
        array = np.array(variable_data)
        array[array == NC_FILL_VALUES['f8']] = float('nan')

        result = operation(array)
        if result == np.nan:
            result = NC_FILL_VALUES['f8']
        return result

    def update_profile_vars(self):
        """ Internal function that updates all profile variables
        before closing a file
        """

        if 'time' in self.nc.variables:
            profile_time = self.__netcdf_to_np_op(
                self.nc.variables['time'][:],
                np.nanmin
            )
            self.set_scalar('profile_time', profile_time)

        if 'lon' in self.nc.variables:
            profile_lon = self.__netcdf_to_np_op(
                self.nc.variables['lon'][:],
                np.average
            )
            self.set_scalar('profile_lon', profile_lon)

        if 'lat' in self.nc.variables:
            profile_lat = self.__netcdf_to_np_op(
                self.nc.variables['lat'][:],
                np.average
            )
            self.set_scalar('profile_lat', profile_lat)
            
    def update_global_title(self, glider):
        
        if 'time' in self.nc.variables:
            profile_time = self.__netcdf_to_np_op(
                self.nc.variables['time'][:],
                np.nanmin
            )
            dt = datetime.utcfromtimestamp(profile_time)
            self.nc.title = '{:s}-{:s}'.format(glider, dt.strftime('%Y%m%dT%H%M'))

    def update_bounds(self):
        """ Internal function that updates all global attribute bounds
        before closing a file.
        """

        for key, desc in self.datatypes.items():
            if 'global_bound' in desc:
                prefix = desc['global_bound']
                dataset = self.nc.variables[desc['name']][:]
                self.nc.setncattr(
                    prefix + '_min',
                    self.__netcdf_to_np_op(
                        dataset,
                        np.nanmin
                    )
                )
                self.nc.setncattr(
                    prefix + '_max',
                    self.__netcdf_to_np_op(
                        dataset,
                        np.nanmax
                    )
                )
                self.nc.setncattr(
                    prefix + '_units',
                    desc['attrs']['units']
                )
                self.nc.setncattr(
                    prefix + '_resolution',
                    desc['attrs']['resolution']
                )
                self.nc.setncattr(
                    prefix + '_accuracy',
                    desc['attrs']['accuracy']
                )
                self.nc.setncattr(
                    prefix + '_precision',
                    desc['attrs']['precision']
                )

    def calculate_salinity(self):
        if self.__get_time_len() == 0:
            raise TypeError('Cannot calculate salinity: time array empty')

        required_params = ('time', 'conductivity', 'temperature', 'pressure')
        for param in required_params:
            if param not in self.nc.variables:
                raise TypeError('Cannot calculate salinity: '
                                'missing %s' % param)

        salinity = calculate_practical_salinity(
            np.array(self.nc.variables["time"][:]),
            np.array(self.nc.variables["conductivity"][:]),
            np.array(self.nc.variables["temperature"][:]),
            np.array(self.nc.variables["pressure"][:])
        )

        salinity[np.isnan(salinity)] = NC_FILL_VALUES['f8']
        self.set_array('salinity-psu', salinity)

    def calculate_density(self):
        if self.__get_time_len() == 0:
            raise TypeError('Cannot calculate salinity: time array empty')

        required_params = (
            'time', 'conductivity', 'temperature', 'pressure',
            'salinity', 'lat', 'lon'
        )
        for param in required_params:
            if param not in self.nc.variables:
                raise TypeError('Cannot calculate salinity: '
                                'missing %s' % param)

        density = calculate_density(
            np.array(self.nc.variables["time"][:]),
            np.array(self.nc.variables["temperature"][:]),
            np.array(self.nc.variables["pressure"][:]),
            np.array(self.nc.variables["salinity"][:]),
            np.array(self.nc.variables["lat"][:]),
            np.array(self.nc.variables["lon"][:])
        )

        density[np.isnan(density)] = NC_FILL_VALUES['f8']
        self.set_array('density-kg/m^3', density)
