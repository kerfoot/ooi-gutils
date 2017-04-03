#! /bin/bash --
#

# Set local PATH
PATH=${HOME}/code/ooi-gutils/scripts:/usr/local/opt/coreutils/libexec/gnubin:${PATH}:/bin;
# Import python virtualenvwrapper capabilities
VIRTUALENVWRAPPER_SCRIPT=/usr/local/bin/virtualenvwrapper.sh;
WORKON_HOME=/Users/kerfoot/code/venvs;
if [ ! -f "$VIRTUALENVWRAPPER_SCRIPT" ]
then
    echo "Cannot activate python virtual environment (Invalid virtualenv wrapper script: $VIRTUALENVWRAPPER_SCRIPT)" >&2;
    exit 1;
fi
# Source VIRTUALENVWRAPPER_SCRIPT
. $VIRTUALENVWRAPPER_SCRIPT;
[ "$?" -ne 0 ] && exit 1;

app=$(basename $0);

# Usage message
USAGE="
NAME
    $app - Initialize new OOI glider deployments

SYNOPSIS
    $app [h]

DESCRIPTION
    -h
        show help message

    -x
        print UFrame NetCDF files to be processed but do not process them
";

# Default values for options

# Process options
while getopts "hx" option
do
    case "$option" in
        "h")
            echo -e "$USAGE";
            exit 0;
            ;;
        "x")
            DEBUG=1;
            ;;
        "?")
            echo -e "$USAGE" >&2;
            exit 1;
            ;;
    esac
done

# Remove option from $@
shift $((OPTIND-1));

# Must have OOI_GLIDER_DAC_HOME set and pointing to a valid directory
if [ -z "$OOI_GLIDER_DAC_HOME" ]
then
    echo "OOI_GLIDER_DAC_HOME not set" >&2;
    exit 1;
elif [ ! -d "$OOI_GLIDER_DAC_HOME" ]
then
    echo "OOI_GLIDER_DAC_HOME set to an invalid directory" >&2;
    exit 1;
fi

# Create the glider deployments root name and validate it
deployments_root="${OOI_GLIDER_DAC_HOME}/deployments";
if [ ! -d "$deployments_root" ]
then
    echo "Invalid deployments root: $deployments_root" >&2;
    exit 1;
fi
deployment_dirs=$(find $deployments_root -type d -name '*MOAS*');
if [ -z "$deployment_dirs" ]
then
    echo "No configured deployments found: $deployments_root";
    exit 0;
fi

# Activate the gutils virtualenv
workon gutils;

# Process all deployments and send new data requests if needed
for d in $deployment_dirs
do
    echo "Deployment $d";

    # Find all UFrame NetCDFs to be processed
    nc_dir="${d}/nc-source";
    nc_files=$(find $nc_dir -type f -name '*.nc');
    if [ -z "$nc_files" ]
    then
        echo "No NetCDF files to process $d";
        continue
    fi

    for nc in $nc_files:
    do
        echo "UFrame NetCDF: $nc";
    done
    
    [ -n "$DEBUG" ] && continue;

    create_ioos_dac_netcdf.py --timestamping --verbosity $d;

    [ "$?" -ne 0 ] && continue;

    for nc in $nc_files
    do
        mv $nc "${nc}.pro";
    done
done

# Deactivate the gutils virtualenv
deactivate;
