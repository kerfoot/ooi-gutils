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
        print NetCDF URLs but do not download them
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
response_files=$(find $deployments_root -type f -name '*requests.json');
if [ -z "$response_files" ]
then
    echo "No pending request files found";
    exit 0;
fi

# Activate the gutils virtualenv
workon gutils;

# Process all deployments and send new data requests if needed
for f in $response_files
do
    echo "Processing response file: $f";
    if [ -n "$DEBUG" ]
    then
        download_async_nc_files.py -x $f;
    else
        download_async_nc_files.py $f;
        # If the download was successful, copy the with appended timestamp and them remove the original
        if [ "$?" -eq 0 ]
        then
            cp $f ${f}.$(date --utc +'%Y%m%dT%H%M%SZ');
            [ "$?" -ne 0 ] && continue;
            rm $f;
        fi
    fi

done

# Deactivate the gutils virtualenv
deactivate;
