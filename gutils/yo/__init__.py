#!/usr/bin/env python

import numpy as np
import logging
import os

from gutils import (
    validate_glider_args,
    clean_dataset,
    boxcar_smooth_dataset
)

# For Readability
TIME_DIM = 0
DATA_DIM = 1


def binarize_diff(data):
    data[data <= 0] = -1
    data[data >= 0] = 1
    return data


def calculate_delta_depth(interp_data):
    delta_depth = np.diff(interp_data)
    delta_depth = binarize_diff(delta_depth)

    #delta_depth = boxcar_smooth_dataset(delta_depth, 2)
    
    #delta_depth = binarize_diff(delta_depth)

    return delta_depth


def create_profile_entry(dataset, start, end):
    time_start = dataset[start, TIME_DIM]
    time_end = dataset[end - 1, TIME_DIM]
    depth_start = dataset[start, DATA_DIM]
    depth_end = dataset[end - 1, DATA_DIM]
    return {
        'index_bounds': (start, end),
        'time_bounds': (time_start, time_end),
        'depth_bounds': (depth_start, depth_end)
    }

logger = logging.getLogger(os.path.basename(__file__))

def find_yo_extrema(timestamps, depth, tsint=10):
    """Returns the start and stop timestamps for every profile indexed from the 
    depth timeseries

    Parameters:
        time, depth

    Returns:
        A Nx2 array of the start and stop timestamps indexed from the yo

    Use filter_yo_extrema to remove invalid/incomplete profiles
    """

    validate_glider_args(timestamps, depth)

    est_data = np.column_stack((
        timestamps,
        depth
    ))

    # Set negative depth values to NaN
    est_data[est_data[:, DATA_DIM] <= 0] = float('nan')

    est_data = clean_dataset(est_data)

    # Create the fixed timestamp array from the min timestamp to the max timestamp
    # spaced by tsint intervals
    ts = np.arange(est_data[:,0].min(), est_data[:,0].max(), tsint)
    # Stretch estimated values for interpolation to span entire dataset
    interp_z = np.interp(
        ts,
        est_data[:, 0],
        est_data[:, 1],
        left=est_data[0, 1],
        right=est_data[-1, 1]
    )

    filtered_z = boxcar_smooth_dataset(interp_z, tsint/2)

    delta_depth = calculate_delta_depth(filtered_z)

    #interp_indices = np.argwhere(delta_depth == 0).flatten()

    p_inds = np.empty((0,2))
    inflections = np.where(np.diff(delta_depth) != 0)[0]

    p_inds = np.append(p_inds, [[0, inflections[0]]], axis=0)
    for p in range(len(inflections)-1):
        p_inds = np.append(p_inds,[[inflections[p], inflections[p+1]]], axis=0)
    p_inds = np.append(p_inds, [[inflections[-1], len(ts)-1]], axis=0)

    #profile_timestamps = np.empty((0,2))
    ts_window = tsint*2
    
    # Create orig GUTILS return value - lindemuth method
    # Initialize an nx3 numpy array of nans
    profiled_dataset = np.full((len(timestamps),3), np.nan)
    # Replace TIME_DIM column with the original timestamps
    profiled_dataset[:, TIME_DIM] = timestamps
    # Replace DATA_DIM column with the original depths
    profiled_dataset[:, DATA_DIM] = depth
    
    # Create Nx2 numpy array of profile start/stop times - kerfoot method
    profile_times = np.full((p_inds.shape[0], 2), np.nan)
    
    # Start profile index
    profile_ind = 0
    # Iterate through the profile start/stop indices
    for p in p_inds:
        # Profile start row
        p0 = int(p[0])
        # Profile end row
        p1 = int(p[1])
        # Find all rows in the original yo that fall between the interpolated timestamps
        profile_i = np.flatnonzero(np.logical_and(profiled_dataset[:, TIME_DIM] >= ts[p0]-ts_window,profiled_dataset[:, TIME_DIM] <= ts[p1]+ts_window))
        # Slice out the profile
        pro = profiled_dataset[profile_i]
        # Find the row index corresponding to the minimum depth
        try:
            min_i = np.nanargmin(pro[:,1])
        except ValueError as e:
            logger.warning(e)
            continue
        # Find the row index corresponding to the maximum depth
        try:
            max_i = np.nanargmax(pro[:,1])
        except ValueError as e:
            logger.warning(e)
            continue
        # Sort the min/max indices in ascending order
        sorted_i = np.sort([min_i, max_i])
        # Set the profile index 
        profiled_dataset[profile_i[sorted_i[0]]:profile_i[sorted_i[1]],2] = profile_ind
        
        # kerfoot method
        profile_times[profile_ind,:] = [timestamps[profile_i[sorted_i[0]]], timestamps[profile_i[sorted_i[1]]]]
        # Increment the profile index
        profile_ind += 1
            
        #profile_timestamps = np.append(profile_timestamps, [[est_data[profile_i[0][0],0], est_data[profile_i[0][-1],0]]], axis=0)

    #return profiled_dataset
    return profile_times
