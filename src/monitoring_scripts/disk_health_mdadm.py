#!/usr/bin/python3

#DEPENDENCIES: mdadm

import argparse
import re
import subprocess
import sys
import os

def script_action(script):
  """
  Run specified script.
  """
  subprocess.run(script.split(" "))

def print_output(mdadm_stat,importance,script):
  """
  Prints output to stdout when threshold is reached.

  Keyword arguments:
  importance -- given script importance
  script -- script to be executed when threshol is reached
  """
  if mdadm_stat != "":
    ret_str = importance + "\n"
    ret_str = ret_str + mdadm_stat
    if script is not None:
      script_action(script)
  else:
    ret_str = ""
  return ret_str 

def get_all_devices():
  """
  Returns list of RAID arrays formed by mdadm
  """
  devices = []
  cat_out = subprocess.run(["cat","/proc/mdstat"],stdout=subprocess.PIPE)
  cat_out = cat_out.stdout.decode("utf-8")
  for line in cat_out.split("\n")[1:]:
   try:
    device = re.search("(.+) :",line).group(1)  #name of array dev
   except AttributeError:
     continue
   devices.append(device)
  return devices

def check_dev_status(dev):
  """
  Returns device status

  Keyword arguments:
  dev -- current scanned RAID device
  """
  mdadm_out = subprocess.run(["mdadm","--detail",dev],stdout=subprocess.PIPE)
  mdadm_out = mdadm_out.stdout.decode("utf-8")
  try:
    state = re.search("State *:.*(degraded|FAILED).*",mdadm_out).group(1)  #check wheter device is no t OK
    ret_str = "Raid device \"" + dev + "\" status: " + state + "\n"
    ret_str = ret_str + "Failed block device(s): " + str(re.findall(".* faulty +(.*)",mdadm_out)) + "\n"
    ret_str = ret_str + "Detail of \"" + dev + "\":\n"
    ret_str = ret_str + mdadm_out.split("\n",1)[1]
  except AttributeError:
    ret_str = ""
  return ret_str
  
def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="disk_health_mdadm.py", description="Monitoring software raid devices formed by mdadm", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  disks = parser.add_mutually_exclusive_group(required=True)
  disks.add_argument("-m","--mddevice",help="defines one software raid device",action="store",type=str)
  disks.add_argument("-a","--allmddevices",help="defines all software raid devices",action="store_true")
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  args = parser.parse_args()

  ret_str = ""
  if args.allmddevices:
    devices = get_all_devices()  #list all RAID devices
    if devices == []:  #no raid dev found
      print("No raid device formed by mdadm found")
      sys.exit(1)
    mdadm_stat = ""
    for dev in devices:
      mdadm_stat = mdadm_stat + check_dev_status("/dev/"+dev)  #check status of every RAID device
    ret_str = print_output(mdadm_stat,args.importance,args.execute)
  elif args.mddevice:  #one device was specified
    mdadm_stat = check_dev_status(args.mddevice)  #check status of specified RAID device
    ret_str = print_output(mdadm_stat,args.importance,args.execute)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)