#!/usr/bin/python3

#DEPENDENCIES: lsblk,smartctl

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

def print_output(found_not_allowed,importance,script):
  """
  Prints output to stdout when not allowed disk found.

  Keyword arguments:
  found_not_allowed -- list of not allowed disks
  importance -- given script importance
  script -- script to be executed when threshol is reached
  """
  ret_str = importance + "\n"
  for hdd in found_not_allowed:
    ret_str = ret_str + "Found hard disk, which was not set as allowed: \n"
    ret_str = ret_str + hdd
  if script is not None:
      script_action(script)
  return ret_str  

def compare_allowed_disks(hdd_serial_out,config_file):
  """
  Returns list of not allowed disks (which was not specified in conf file)

  Keyword arguments:
  hdd_serial_out -- list of current attached hdd serials
  config_file -- file where are allowed disks specified
  """
  forbidden_hdd_serial = []  #dict to store changes
  match = False
  fp = open(config_file,"r")
  allowed_serials = fp.read()
  for serial in hdd_serial_out.split('\n')[:-1]:  #for every current scanned serial number
    for line in allowed_serials.split('\n')[:-1]:  #for every allowed serial from config file
      if serial == line:  #scanned serial number is in config
        match = True
        break
      else:  #scanned serial number is not in allowed config file
        match = False 
    if not match and serial != "":  #current scanned serial is not in conf file
      block_dev = subprocess.run(["lsblk","-o","serial,name","--nodeps"],stdout=subprocess.PIPE)  #store block dev with serial no.
      try:
        block_dev = re.search(serial+" *(.*)",block_dev.stdout.decode("utf-8")).group(1)  #filter only specific block dev
      except AttributeError:
        pass
      disk_info = subprocess.run(["smartctl","-a","/dev/"+block_dev],stdout=subprocess.PIPE)  #SMART has further info about device
      try:
        disk_info = re.search("=== START OF INFORMATION SECTION ===([\s\S]*?\n\n)",disk_info.stdout.decode("utf-8")).group(1)  #filter info about disks, serial number, name....
      except AttributeError:
        disk_info = ""
      forbidden_hdd_serial.append(disk_info)
    match = False
  match = False
  return forbidden_hdd_serial

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="disk_allow_serial.py", description="Tracking allowed attached hard disks according to their serial number",\
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter,epilog="For stand-alone version config file should \
                                    contain one allowed serial number on each line, add new line at the end")
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-c","--config",help="when linmon monitoring tool is not installed, config file with allowed serial numbers of hard disks can be specified",type=str)
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  args = parser.parse_args()

  hdd_serial_out = subprocess.run(["lsblk","--nodeps","-o","serial","-n"], stdout=subprocess.PIPE)  #show serials of atteched disks
  hdd_serial_out = hdd_serial_out.stdout.decode("utf-8")
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
      config_file = linmon_builtin.read_configfile_fn("config")+"disk_allow_serial.conf"  #file, where allowed disks are specified
      open(config_file)
    except FileNotFoundError:
      print(args.importance+"\n"+"Cannot find config file with allowed serial numbers, add it (disk_allow_serial.conf) to config directory of linmon\n")  #script was not installed, only works with linmon
      sys.exit(1)
  
  found_not_allowed = compare_allowed_disks(hdd_serial_out,config_file)  #compare actual disks with allowed
  if found_not_allowed == []:  #only allowed hdds in machine
    ret_str = ""
  else:  #found not allowed hdd
    ret_str = print_output(found_not_allowed,args.importance,args.execute)
  print(ret_str)
  
if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
