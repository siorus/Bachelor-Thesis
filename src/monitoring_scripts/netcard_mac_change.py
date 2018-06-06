#!/usr/bin/python3

#DEPENDENCIES: ip

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

def print_output(modified_adapters,importance,script):
  """
  Prints output to stdout.

  Keyword arguments:
  modified_adapters -- dictionary with adapter changes
  importance -- given script importance
  script -- script to be executed when threshol is reached
  """
  ret_str = importance + "\n"
  for key,value in modified_adapters.items():
    if modified_adapters[key][0] == "":  #no previous record of this adapter, it is new
      ret_str = ret_str + "NEW ADAPTER ADDED: " + key + " MAC ADDRESS: " + modified_adapters[key][1] + "\n"
    elif modified_adapters[key][1] == "":  #adapter from conf file not in current scan, it was deleted
      ret_str = ret_str + "ADAPTER: " + key + " WAS DELETED MAC ADDRESS: " + modified_adapters[key][0] + "\n"
    else:  #adapter mac address was modified
      ret_str = ret_str + "ADAPTER MODIFIED: " + key + " OLD MAC ADDRESS: " + modified_adapters[key][0] + " NEW MAC ADDRESS: " + modified_adapters[key][1] + "\n"
  if script is not None:
      script_action(script)
  return ret_str  

def store_adapters(adapter_mac,config_file):
  """
  Save adapter ip addresses

  Keyword arguments:
  adapter_ip -- dictionary with adapter name and ip
  config_file -- file to store info
  """
  fp = open(config_file,"w")
  for key,value in adapter_mac.items():
    fp.write(key+": "+value+"\n")  # format eth0: 2001::1/64
  fp.close()

def compare_actual_adapters(adapter_mac,config_file):
  """
  Returns dictionary with new and deleted adapters

  Keyword arguments:
  adapter_ip -- dictionary with adapter name and ip
  config_file -- file to store info
  """
  adapter_modified = {}  #dict to store changes
  match = False
  fp = open(config_file,"r+")
  stored_adapters = fp.read()
  #modified or new adapters
  for key,value in adapter_mac.items():  #for every current adapter mac addresses
    for line in stored_adapters.split('\n')[:-1]:  #for every adapter from config file
      if (key+": "+value) == line:  #create same format string from current adapter settings as it is in config file and compare them
        match = True
        break
      else:
        match = False 
    if not match:  #current adapter or its settings is not in conf file
      try:
        old_ip = re.search(str(key)+"\: (.*)",stored_adapters).group(1)  #store old mac address
        adapter_modified[key] = [old_ip,value]  #mac address modified from one to another
      except AttributeError:
        adapter_modified[key] = ["",value]  #adapter is new, no old mac address
    match = False
  match = False
  #deleted adapters, adapter from config file not in current scan
  for line in stored_adapters.split('\n')[:-1]:  #for every adapter from config file
    for key,value in adapter_mac.items():  #for every current adapter mac addresses
      adapter = re.search("(.*)\: .*",line).group(1)
      if adapter == key:  #adapter from config file is in current scan
        match = True
        break
      else:  #adapter from config file is not in current scan, it was deleted or disabled
        match = False
    if not match:
      ip = re.search("(.*)\: (.*)",line).group(2)
      adapter_modified[adapter] = [ip,""]  #[old mac from conf file, no new mac], adapter deleted
  return adapter_modified

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="netcard_mac_change.py", description="Monitoring MAC address on interfaces, address change, new adapters, deleted adpaters",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-c","--config",help="config path has to be specified, when linmon monitoring tool is not installed, do not copy linmon_builtin module",type=str)
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  args = parser.parse_args()

  ip_out = subprocess.run(["ip","addr"], stdout=subprocess.PIPE)  #show adapters
  ip_out = ip_out.stdout.decode("utf-8")
  adapters = re.findall(".* (.*?): .*",ip_out)  #first line of every adapter with name
  adapter_mac = {}
  for adapter in adapters:
    try:
      adapter_mac[adapter] = re.search(".* "+adapter+": .*\n(?: *link\/.*?) +(.*?) .*",ip_out).group(1)  #filter mac address
    except AttributeError:
      adapter_mac[adapter] = "N/A"  #no address specified
  if stand_alone == True:  #standalone script, linmon not installed
    if not args.config:
      print("In stand-alone script version config path has to be specified, used help to run program correctly")
      sys.exit(1)
    elif os.path.isdir(args.config):
      config_file = args.config + "/netcard_mac_change.conf"  #config file exist
    else:
      print("Specified config path does not exist, create it and try it again")  #config file does not exist
      sys.exit(1)
  else:  #linomn monitoring script seems to be installed
    try:
      config_file = linmon_builtin.read_configfile_fn("config")+"netcard_mac_change.conf"  #file, where adapter mac addresses are stored
    except FileNotFoundError:
      print(args.importance+"\n"+"Cannot find config path, cannot compare recent and historical netcard values\n")  #script was not installed, only works with linmon
      sys.exit(1)
  if os.path.isfile(config_file):  #config file exist, there is something to compare
    modified_adapters = compare_actual_adapters(adapter_mac,config_file)  #compare actual mac addresses with last found mac
    if modified_adapters == {}:  #nothing has changed from previous scan
      ret_str = ""
    else:  #change found
      ret_str = print_output(modified_adapters,args.importance,args.execute)
      store_adapters(adapter_mac,config_file)  #store actual new mac addresses to comparing file
  else:  #first run of script, only create config, no comparison
    store_adapters(adapter_mac,config_file)
    ret_str = ""
  print(ret_str)
  
if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)