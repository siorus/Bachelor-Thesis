#!/usr/bin/python3

#DEPENDENCIES: blkid,smartctl(smartmontools)

import argparse
import re
import subprocess
import sys

def script_action(script):
  """
  Run specified script.
  """
  subprocess.run(script.split(" "))

def print_output(temp,threshold,dev,smart_out,importance,print_head,script):
  """
  Prints output to stdout when threshold is reached.

  Keyword arguments:
  temp -- current block device temp
  threshold -- temperature shreshold
  dev -- block device
  smart_out -- output of smartctl
  importance -- given script importance
  print_head -- flag whether print importance
  script -- script to be executed when threshol is reached
  """
  ret_str = ""
  if (temp == "Unknown") or (int(temp) >= threshold):
    if print_head:
      ret_str = importance + "\n"
    ret_str = ret_str + "BLOCK DEVICE " + dev + " THRESHOLD: " + str(threshold) + "°C\n"  #subject for email message
    ret_str = ret_str + "CURRENT " + dev + " TEMPERATURE: " + str(temp) + "°C\n"
    try:
      ret_str = ret_str + re.search("=== START OF INFORMATION SECTION ===([\s\S]*?\n\n)",smart_out).group(1) + "\n"  #show smart basic info
    except AttributeError:
      ret_str = ret_str + "Specified block device \"" + dev + "\" does not exist or has no S.M.A.R.T info\n"
    if script is not None:
      script_action(script)
  else:
    ret_str = ""
  return ret_str

def find_block_devs():
  """
  Returns block devices in machine
  """
  blkid = subprocess.run(["blkid"],stdout=subprocess.PIPE)
  blkid = blkid.stdout.decode("utf-8")
  uniq_devs = []
  for line in blkid.split('\n')[:-1]:
    try:
      dev = re.search("(.*)\d+:.*",line).group(1)  #filter only blockdevs
    except AttributeError:
      dev = re.search("(.*):.*",line).group(1)  #filter only blockdevs
    if dev not in uniq_devs:
      uniq_devs.append(dev)  #append dev only if it is not in list
  return uniq_devs

def temp_of_disk(dev):
  """
  Returns output of smartctl of specified dev and its temperature

  Keyword arguments:
  dev -- device to be scanned
  """
  smart_out = subprocess.run(["smartctl","-a",dev], stdout=subprocess.PIPE)  #show smart info of disk
  smart_out = smart_out.stdout.decode("utf-8")
  try:
    temp = re.search("\d+ Temperature.* +-  +(\d+) *",smart_out).group(1)  #filter disk temp
  except AttributeError:
    temp = "Unknown"
  return smart_out,temp

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="disk_temp.py", description="Monitoring block device(s) temperature",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-t","--temperature",help="max temperature, after reaching it notificate user",action="store",type=int,required=True)
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  disks = parser.add_mutually_exclusive_group(required=True)
  disks.add_argument("-b","--blockdevice",help="defines one block device to be monitored",action="store",type=str)
  disks.add_argument("-a","--alldevices",help="defines all block devices connected to machine",action="store_true")
  
  args = parser.parse_args()
  ret_str = ""
  if args.blockdevice:  #one block device was specified
    smart_out,temp = temp_of_disk(args.blockdevice)
    ret_str = print_output(temp,args.temperature,args.blockdevice,smart_out,args.importance,True,args.execute)
  elif args.alldevices:  #scan all devices
    block_devs = find_block_devs()
    print_head = True  #flag to print head(importance) only once
    for dev in block_devs:
      smart_out,temp = temp_of_disk(dev)
      ret_str = ret_str + print_output(temp,args.temperature,dev,smart_out,args.importance,print_head,args.execute)
      print_head = False
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)