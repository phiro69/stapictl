#!/usr/bin/env python
import argparse
import logging.config
import json
import yaml
import requests
import sys
import os
import errno
import time


# create a new account
# ./stapictl.py --create <accountname>

parser = argparse.ArgumentParser(
    prog="stapictl",
    usage="./stapictl --create <accountname>",
    description="SpadeTraders API ctl",
    allow_abbrev=False,
)

# top level exclusive commands
parser.add_argument(
    "--create",
    action="store",
    help="Creates a new account for SpaceTraders. Requires an account name as an argument. ",
)

# spit out the full help if no args are passed
if len(sys.argv) == 1:
    parser.print_help()
    # parser.print_usage() # for just the usage line
    parser.exit()

# now parse the args!
args = parser.parse_args()

def main():
    # time start for reporting at the end
    start_time = time.time()

    # get logging config
    logging_filename = "logging.yaml"
    logging_conf = {}
    try:
        logging_conf = yaml.load(open(logging_filename), Loader=yaml.FullLoader)
        logging.config.dictConfig(logging_conf)
    except os.error as err:
        if abs(err.errno) == errno.ENOENT:
            print(f"Error: Logging configuration file {logging_filename} not found, exiting!")
            sys.exit()
    # set logger
    logger = logging.getLogger("default")

    # load config
    stapi_conf = load_config(logger, "stapictl.yaml")

    # logging the start of the run with the running options:
    cli = ""
    for arg in sys.argv:
        if len(cli) == 0:
            cli = arg
        else:
            cli = cli + " " + arg
    logger.info(f"Starting with the following cli: \'{cli}\'")
    exit_text = ""
    status = False

    if args.create:
        status, result = stapi_register(logger=logger, stapi_conf=stapi_conf, register_name=args.create, register_faction='COSMIC')
        if not status:
            logger.error(f"Error creating account: {result}.")
        else:
            logger.info(f"Account \"{args.create}\" successfully created!")
            logger.info(f"token: {result.get('data').get('token')}")
            logger.info(f"accountId: {result.get('data').get('agent').get('accountId')}")
            logger.info(f"symbol: {result.get('data').get('agent').get('symbol')}")
    else:
        logger.warning(f"No operation detected.")
    logger.info(f"Elapsed time: {int(time.time() - start_time)} seconds.")


def stapi_register(logger=None, stapi_conf=None, register_name=None, register_faction=None):
    session = requests.Session()
    session.headers = {'Content-type': 'application/json'}
    register_url = stapi_conf['stapi_url'] + 'v2/register'

    # set data payload up
    dict_data = {'symbol': register_name, 'faction': register_faction}
    json_data = json.dumps(dict_data)

    try:
        r = session.post(register_url, data=json_data, timeout=30)
        # print(f"debug - r.status_code {r.status_code}")
    except requests.exceptions.RequestException as e:
        return_text = f"Error in stapi_register: {e}"
        return False, return_text
    try:
        result = r.json()
    except:
        return_text = f"Error in converting request to json"
        return False, return_text

    # print(f"debug - result.json(): {result}")

    # quantify the return code:
    if r.status_code == 404:
        return_text = f"Error in stapi_register: {r.text}"
        return False, return_text
    elif r.status_code == 422:
        error_payload = result.get('error').get('data')
        # print(f"debug error_payload {error_payload}")
        if not error_payload:
            error_payload = result
        return_text = f"Missing/incorrect data in request: Error in stapi_register: {error_payload}"
        return False, return_text
    elif r.status_code == 200:
        return_text = f"Return code 200 but expected a 201"
        return False, return_text
    elif r.status_code == 201:
        return True, result
    else:
        return_text = f"Unhandled r.status code in stapi_register: {r.status_code}"
        return False, return_text

def load_config(logger, config_filename):
    filename = config_filename
    config = {}
    try:
        config = yaml.load(open(filename), Loader=yaml.FullLoader)
    except os.error as err:
        if abs(err.errno) == errno.ENOENT:
            logger.error(f"Config file {filename} not found, exiting.")
            sys.exit()
    return config

if __name__ == "__main__":
    main()


