#!/usr/bin/python3

#DEPENDENCIES: lspci

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

def print_output(new_pci,deleted_pci,importance,script):
  """
  Prints output to stdout when pci devices change.

  Keyword arguments:
  new_pci -- list of new pci devices
  deleted_pci -- list of removed pci devices
  importance -- given script importance
  script -- script to be executed when pci device is changed
  """
  ret_str = importance + "\n"
  if new_pci != []:
    ret_str = ret_str + "New pci device(s): \n"
    for pci in new_pci:
      ret_str = ret_str + pci + "\n"
  if deleted_pci != []:
    ret_str = ret_str + "Removed pci device(s): \n"
    for pci in deleted_pci:
      ret_str = ret_str + pci + "\n"
  if script is not None:
      script_action(script)
  return ret_str  

def store_pci(pci_dev,config_file):
  """
  Save current pci devices to file

  Keyword arguments:
  dev_pci -- list of current pci devices
  config_file -- file where devices will be stored
  """
  fp = open(config_file,"w")
  fp.write(pci_dev)
  fp.close()

def compare_previous_pci(pci_out,config_file):
  """
  Compares current pci devices with stored devices in file

  Keyword arguments:
  pci_out -- list of current pci devices
  config_file -- file where devices will be stored
  """
  new_pci = []  #dict to store changes
  deleted_pci = []  #dict to store deleted devices
  match = False  #flag, device is in config file
  fp = open(config_file,"r")
  pci_file = fp.read()
  for pci_line in pci_out.split('\n')[:-1]:  #for every current scanned pci dev
    for pci_file_line in pci_file.split('\n')[:-1]:  #for every pci dev from config file
      if pci_line == pci_file_line:  #scanned pci dev is in config
        match = True
        break
      else:  #scanned pci dev is not in config file
        match = False 
    if not match:  #current pci dev is not in conf file
      new_pci.append(pci_line)
    match = False
  match = False

  for pci_file_line in pci_file.split('\n')[:-1]:  #for every pci dev from config file
    for pci_line in pci_out.split('\n')[:-1]:  #for every current scanned pci dev
      if pci_line == pci_file_line:  #scanned pci dev is in config
        match = True
        break
      else:  #scanned pci dev is not in config file
        match = False 
    if not match:  #current pci dev is not in conf file
      deleted_pci.append(pci_file_line)
    match = False
  match = False
  return new_pci,deleted_pci

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="dev_pci_change.py", description="Monitoring new attached or removed pci devices",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-c","--config",help="config path has to be specified, when linmon monitoring tool is not installed, do not copy linmon_builtin module",type=str)
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  args = parser.parse_args()

  pci_out = subprocess.run(["lspci"],stdout=subprocess.PIPE)
  pci_out = pci_out.stdout.decode("utf-8")

  if stand_alone == True:  #standalone script, linmon not installed
    if not args.config:
      print("In stand-alone script version config path has to be specified, used help to run program correctly")
      sys.exit(1)
    elif os.path.isdir(args.config):
      config_file = args.config + "/dev_pci_change.conf"  #config file exist
    else:
      print("Specified config path does not exist, create it and try it again")  #config file does not exist
      sys.exit(1)
  else:  #linomn monitoring script seems to be installed
    try:
      config_file = linmon_builtin.read_configfile_fn("config")+"/dev_pci_change.conf"   
    except FileNotFoundError:
      print(args.importance+"\n"+"Cannot find config path, cannot compare recent and historical pci devices\n")
      sys.exit(1)
  if os.path.isfile(config_file):
    new_pci,deleted_pci = compare_previous_pci(pci_out,config_file)  #compare current devices with stored in file
    if (new_pci == []) and (deleted_pci == []):
      ret_str = ""  #no new devices found
    else:
      ret_str = print_output(new_pci,deleted_pci,args.importance,args.execute)
      store_pci(pci_out,config_file)
  else:
    store_pci(pci_out,config_file)
    ret_str = ""
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
