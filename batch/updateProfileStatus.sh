#! /bin/bash --
#

# Set local PATH
PATH=${HOME}/code/ooi-gutils/scripts:${PATH}:/bin;
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
    $app - Update profile status JSON files for all configured deployments

SYNOPSIS
    $app [h]

DESCRIPTION
    -h
        show help message

    -c
        clobber and rewrite all profile status JSON files
";

# Default values for options

# Process options
while getopts "hxc" option
do
    case "$option" in
        "h")
            echo -e "$USAGE";
            exit 0;
            ;;
        "x")
            DEBUG=1;
            ;;
        "c")
            clobber=1;
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
    return 1;
elif [ ! -d "$OOI_GLIDER_DAC_HOME" ]
then
    echo "OOI_GLIDER_DAC_HOME set to an invalid directory" >&2;
    return 1;
fi

# Find all deployment directores under OOI_GLIDER_DAC_HOME/deployments
deployments_root="${OOI_GLIDER_DAC_HOME}/deployments";
if [ ! -d "$deployments_root" ]
then
    echo "Invalid deployments root: $deployments_root" >&2;
    return 1;
fi
deployment_dirs=$(find $deployments_root -type d -maxdepth 1 -name '*MOAS*');
if [ -z "$deployment_dirs" ]
then
    echo "No OOI glider deployments found: $deployments_root";
    return 1;
fi

# Activate the gutils virtualenv
workon gutils;

env | grep PYTHONPATH;

for d in $deployment_dirs
do
    echo "Deployment: $d";
    # Process all deployments and send new data requests if needed
    if [ -n "$DEBUG" ]
    then
        write_deployment_profile_status.py -l debug $d;
    else
        if [ -z "$clobber" ]
        then
            write_deployment_profile_status.py $d;
        else
            write_deployment_profile_status.py -c $d;
        fi
    fi
done

# Deactivate the gutils virtualenv
deactivate;
