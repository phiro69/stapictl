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

parser = argparse.ArgumentParser(prog="stapictl",
                                 usage="./stapictl --create <accountname>",
                                 description="SpadeTraders API ctl",
                                 allow_abbrev=False,)

# top level commands
parser.add_argument('--create', action='store', help='Creates a new account for SpaceTraders. Requires an account name as an argument.')
parser.add_argument('--info', action='store_true', help='Returns player info based on the token in the config.', default=False)

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
    elif args.info:
        status, result = account_info(logger=logger, stapi_conf=stapi_conf)
        if not status:
            logger.error(f"Error querying account: {result}.")
    else:
        logger.warning(f"No operation detected.")
    logger.info(f"Elapsed time: {int(time.time() - start_time)} seconds.")

def account_info(logger=None, stapi_conf=None):
    # todo: use a player class to hold all of this?

    status, result_data = stapi_my_agent(logger=logger, stapi_conf=stapi_conf)
    if not status:
        return False, f"Account lookup failed: {result_data}"
    player_accountid = result_data.get('accountId')
    player_symbol = result_data.get('symbol')
    player_headquarters = result_data.get('headquarters')
    player_credits = result_data.get('credits')

    # X1-DF55-20250Z = sector-system-location
    # X1 is the sector,
    # X1-DF55 is the system,
    # and X1-DF55-20250Z is the waypoint.
    player_headquarters_list = player_headquarters.split('-')
    system_symbol = f"{player_headquarters_list[0]}-{player_headquarters_list[1]}"
    waypoint_symbol = f"{player_headquarters_list[0]}-{player_headquarters_list[1]}-{player_headquarters_list[2]}"

    status, result_data = stapi_systems(logger=logger, stapi_conf=stapi_conf, system_symbol=system_symbol, waypoint_symbol=waypoint_symbol)
    if not status:
        return False, f"Account location failed: {result_data}"

    system_symbol = result_data.get('symbol')
    system_type = result_data.get('type')
    system_orbital_count = len(result_data.get('orbitals'))
    system_traits = []
    for traits in result_data.get('traits'):
        system_traits.append(traits.get('name'))
    # system_traits = result_data.get('xxx')


    # print report
    logger.info(f"player_accountId {player_accountid}")
    logger.info(f"player_symbol {player_symbol}")
    logger.info(f"player_headquarters {player_headquarters}")
    logger.info(f"player_credits {player_credits}")

    logger.info(f"Location: {system_symbol}")
    logger.info(f"system_type: {system_type}")
    logger.info(f"system_orbital_count: {system_orbital_count}")
    logger.info(f"system_traits: {system_traits}")
    return True, ""


def stapi_my_agent(logger=None, stapi_conf=None):
    # curl 'https://api.spacetraders.io/v2/my/agent' --header 'Authorization: Bearer INSERT_TOKEN_HERE'
    session = requests.Session()
    session.headers = {'Content-type': 'application/json', 'Authorization': 'Bearer ' + stapi_conf['account_token']}
    url = stapi_conf['stapi_url'] + 'v2/my/agent'

    try:
        r = session.get(url, timeout=30)
    except requests.exceptions.RequestException as e:
        return_text = f"Error in account_info: {e}"
        return False, return_text
    try:
        result = r.json()
        result_data = result.get('data')
    except:
        return_text = f"Error in converting request to json"
        return False, return_text

    # quantify the return code:
    if r.status_code == 404:
        return_text = f"Error in account_info: {r.text}"
        return False, return_text
    elif r.status_code == 422:
        error_payload = result.get('error').get('data')
        if not error_payload:
            error_payload = result
        return_text = f"Missing/incorrect data in request: Error in stapi_my_agent: {error_payload}"
        return False, return_text
    elif r.status_code == 200:
        return True, result_data
    else:
        return_text = f"Unhandled r.status code in stapi_my_agent: {r.status_code}"
        return False, return_text


def stapi_systems(logger=None, stapi_conf=None, system_symbol=None, waypoint_symbol=None):
    # curl 'https://api.spacetraders.io/v2/systems/:systemSymbol/waypoints/:waypointSymbol' --header 'Authorization: Bearer INSERT_TOKEN_HERE'
    session = requests.Session()
    session.headers = {'Content-type': 'application/json', 'Authorization': 'Bearer ' + stapi_conf['account_token']}
    url = stapi_conf['stapi_url'] + f'v2/systems/{system_symbol}/waypoints/{waypoint_symbol}'

    try:
        r = session.get(url, timeout=30)
        # print(f"debug - r.status_code {r.status_code}")
    except requests.exceptions.RequestException as e:
        return_text = f"Error in account_info: {e}"
        return False, return_text
    try:
        result = r.json()
        result_data = result.get('data')
    except:
        return_text = f"Error in converting request to json"
        return False, return_text

    # print(f"debug - result.json(): {json.dumps(result, indent=1)}")

    # quantify the return code:
    if r.status_code == 404:
        return_text = f"Error in stapi_systems: {r.text}"
        return False, return_text
    elif r.status_code == 422:
        error_payload = result.get('error').get('data')
        if not error_payload:
            error_payload = result
        return_text = f"Missing/incorrect data in request: Error in stapi_systems: {error_payload}"
        return False, return_text
    elif r.status_code == 200:
        return True, result_data
    else:
        return_text = f"Unhandled r.status code in stapi_systems: {r.status_code}"
        return False, return_text


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


