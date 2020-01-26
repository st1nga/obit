#!/usr/bin/env python
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Remote OBIT
#===========================================================================
# Modifications
#---------------------------------------------------------------------------

import configparser
import sys
import MySQLdb
import time
import datetime

import platform
import signal
import requests
import configparser
import logging
from optparse import OptionParser

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Stops nasty message going to stdout :-) Unrequired prettyfication
#---------------------------------------------------------------------------
def signal_handler(sig, frame):
  print("Exiting due to control-c")
  sys.exit(0)

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#---------------------------------------------------------------------------
def custom_logger(name, logger_level, config, log_to_screen):
    '''Custom logging module'''

    logger_level = logger_level.upper()

    formatter = logging.Formatter(fmt='%(asctime)s %(name)s:%(process)-5d %(levelname)-8s %(lineno)-4d: %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    handler = logging.FileHandler(config.get("obit", "log_file"), mode='a')
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.getLevelName(logger_level))
    logger.addHandler(handler)

    if log_to_screen == True:
      screen_handler = logging.StreamHandler(stream=sys.stdout)
      screen_handler.setFormatter(formatter)
      logger.addHandler(screen_handler)

    return logger

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Send a command to RadioDJ
#---------------------------------------------------------------------------
def send_command_to_rdj(url, params, logger):
  logger.debug("Sending %s%s" % (url, params))

  r = requests.get(url = url, params = params)
  if r.status_code  != 200:
    logger.debug("Response status = %s" % r.status_code)
    sys.exit(1)
  else:
    logger.debug("Yay!! success")

  return r.status_code

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#MAIN Main main
#---------------------------------------------------------------------------
def main():

#+
#Catch control-c
#-
  signal.signal(signal.SIGINT, signal_handler)

#+
#Parse the options passed
#-
  parser = OptionParser()
  parser.add_option("", "--logger-level", dest="logger_level",
    help="Log level: ERROR, WARNING, INFO, DEBUG [Default=%default]", default="DEBUG")

  parser.add_option("", "--config", dest="config_file",
    help="Config file [Default=%default]", default="/etc/obit.conf")

  parser.add_option("", "--log-to-screen", action="store_true", dest="log_to_screen",
    help="Output log message to screen [Default=%default]")

  (options, args) = parser.parse_args()

#+
#Load the config file
#-
  config = configparser.ConfigParser()
  config.read(options.config_file)

#+
#Setup custom logging
#-
  logger = custom_logger(config.get('obit', 'logger_name'), options.logger_level, config, options.log_to_screen)
  logger.info("Hello world! Python version = '%s'" % platform.python_version())

  curr_datetime = datetime.datetime.now()
  now_past_hour_s = (curr_datetime.minute * 60) + curr_datetime.second
  logger.debug(now_past_hour_s)
  if now_past_hour_s >= int(config.get('obit', 'end_s')) or now_past_hour_s <= int(config.get('obit', 'start_s')):
    logger.info("Can't run now we are close to the news")
    sys.exit(1)

#+
#Connect to database
#-
  try:
    db = MySQLdb.connect(host = config.get("sql", "host"), user = config.get("sql", "username"), passwd = config.get("sql", "password"), db = config.get("sql", "database"))
  except MySQLdb.Error as err:
    logger.error("Error %d: %s" % (err.args[0], err.args[1]))
    sys.exit(1)

  c = db.cursor()

#+
#Get the OBIT playlist ID
#-
  sql = "select id from playlists where name = 'obit'"
  try:
    c.execute(sql)
  except MySQLdb.Error as err:
    logger.error("Error %d: %s" % (err.args[0], err.args[1]))
    logger.error("sql = '%s'" % sql)
    sys.exit(1)

  if c.rowcount:
    obit_playlist_id = c.fetchone()[0]
  else:
    logger.error("'%s' playlist not found in database" % config.get('obit', 'playlist'))

  url = "http://%s:%s/opt" % (config.get('obit', 'radiodj_host'), config.get('obit', 'port'))

  status = send_command_to_rdj(url, {'auth':config.get('obit', 'radiodj_passwd'), 'command':'EnableEvents', 'arg':0}, logger)
  status = send_command_to_rdj(url, {'auth':config.get('obit', 'radiodj_passwd'), 'command':'EnableAutoDJ', 'arg':0}, logger)
  status = send_command_to_rdj(url, {'auth':config.get('obit', 'radiodj_passwd'), 'command':'ClearPlaylist'}, logger)
  status = send_command_to_rdj(url, {'auth':config.get('obit', 'radiodj_passwd'), 'command':'EnableAssisted', 'arg':0}, logger)
  status = send_command_to_rdj(url, {'auth':config.get('obit', 'radiodj_passwd'), 'command':'StopPlayer'}, logger)
  time.sleep(int(config.get('obit', 'wait_before_play_s')))
  status = send_command_to_rdj(url, {'auth':config.get('obit', 'radiodj_passwd'), 'command':'LoadPlaylist', 'arg':obit_playlist_id}, logger)
  time.sleep(1)
  status = send_command_to_rdj(url, {'auth':config.get('obit', 'radiodj_passwd'), 'command':'PlayPlaylistTrack', 'arg':0}, logger)

#sleep x seconds
#LoadPlaylist 'Playlist ID as argument
#PlayFromIntro
##+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#---------------------------------------------------------------------------
if __name__ == "__main__":
#    exit()
    main()
