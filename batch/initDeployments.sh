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
    $app - Initialize new OOI glider deployments

SYNOPSIS
    $app [h]

DESCRIPTION
    -h
        show help message

    -x
        print new deployments but do not initialize
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
    return 1;
elif [ ! -d "$OOI_GLIDER_DAC_HOME" ]
then
    echo "OOI_GLIDER_DAC_HOME set to an invalid directory" >&2;
    return 1;
fi

# Activate the gutils virtualenv
workon gutils;

# Process all deployments and send new data requests if needed
if [ -n "$DEBUG" ]
then
    init_deployments.py -x;
else
    init_deployments.py;
fi

# Deactivate the gutils virtualenv
deactivate;
