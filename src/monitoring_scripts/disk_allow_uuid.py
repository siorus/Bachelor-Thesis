#!/usr/bin/python3

#DEPENDENCIES: blkid

import argparse
import re
import os
import subprocess
import sys
try:
  from packages import linmon_builtin
  stand_alone = False
except ImportError:
  stand_alone = True

def script_action(script):
  """
  Run specified script.
  """
  subprocess.run(script.split(" "))

def print_output(found_not_allowed,importance,script,blkid):
  """
  Prints output to stdout when not allowed disk found.

  Keyword arguments:
  found_not_allowed -- list of not allowed disks
  importance -- given script importance
  script -- script to be executed when threshol is reached
  """
  ret_str = importance + "\n"
  for uuid in found_not_allowed:
    ret_str = ret_str + "Found hard disk UUID, which was not set as allowed: "
    ret_str = ret_str + uuid + "\n"
    ret_str = ret_str + "Block device: " + uuid_to_block(uuid) + "\n"
    try:
      ret_str = ret_str + "Label: " + re.search("LABEL=\"(.*?)\".*" + uuid + ".*",blkid).group(1) + "\n"
    except AttributeError:
      pass
    try:
      ret_str = ret_str + "File system: " + re.search(".*" + uuid +".*TYPE=\"(.*?)\"",blkid).group(1) + "\n\n"
    except AttributeError:
      pass
  if script is not None:
      script_action(script)
  return ret_str    

def uuid_to_block(uuid):
  """
  Return name of block device according to uuid

  Keyword arguments:
  uuid -- id of partition
  """
  blkid = subprocess.run(["blkid"],stdout=subprocess.PIPE)
  blkid = blkid.stdout.decode("utf-8")
  try:
    block_dev = re.search("(.*)\:.*UUID=\"" + re.escape(uuid) + "\".*",blkid).group(1)  #filter block dev name
  except AttributeError:
    block_dev = ""
  return block_dev

def compare_allowed_disks(uuid_list,config_file):
  """
  Returns list of not allowed disks (which was not specified in conf file)

  Keyword arguments:
  uuid_list -- list of current attached hdd uuids
  config_file -- file where are allowed disks specified
  """
  forbidden_uuids = []
  match = False
  fp = open(config_file,"r")
  allowed_uuids = fp.read()
  for uuid in uuid_list:  #for every current scanned uuid number
    for line in allowed_uuids.split('\n')[:-1]:  #for every allowed uuid from config file
      if uuid == line:  #scanned uuid number is in config
        match = True
        break
      else:  #scanned uuid number is not in allowed config file
        match = False 
    if not match and uuid != "":  #current scanned uuid is not in conf file
      forbidden_uuids.append(uuid)
    match = False
  match = False
  return forbidden_uuids

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="disk_allow_uuid.py", description="Tracking allowed attached hard disks according to their UUID",\
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter,epilog="For stand-alone version config file should \
                                    contain one allowed serial number on each line, add new line at the end")
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-c","--config",help="when linmon monitoring tool is not installed, config file with allowed UUID of hard disks can be specified",type=str)
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  args = parser.parse_args()

  blkid_out = subprocess.run(["blkid"],stdout=subprocess.PIPE)
  uuid = re.findall(" UUID=\"(.*?)\".+",blkid_out.stdout.decode("utf-8"))
  if stand_alone == True:  #standalone script, linmon not installed
    if not args.config:
      print("In stand-alone script version config file has to be specified, used help to run program correctly and to see syntax of config file")
      sys.exit(1)
    elif os.path.isfile(args.config):
      config_file = args.config  #config file exist
    else:
      print("Specified config file does not exist")  #config file does not exist
      sys.exit(1)
  else:  #linomn monitoring script seems to be installed
    try:
      config_file = linmon_builtin.read_configfile_fn("config")+"disk_allow_uuid.conf"  #file, where allowed disks are specified
      open(config_file)
    except FileNotFoundError:
      print(args.importance+"\n"+"Cannot find config file with allowed serial numbers, add it (disk_allow_uuid.conf) to config directory of linmon\n")  #script was not installed, only works with linmon
      sys.exit(1)

  found_not_allowed = compare_allowed_disks(uuid,config_file)  #compare actual disks with allowed
  if found_not_allowed == []:  #only allowed hdds in machine
    ret_str = ""
  else:  #found not allowed hdd
    ret_str = print_output(found_not_allowed,args.importance,args.execute,blkid_out.stdout.decode("utf-8"))
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
