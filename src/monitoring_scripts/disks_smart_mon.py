#!/usr/bin/python3

#DEPENDENCIES: blkid,smartctl(smartmontools)

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

def print_output(smart_values,importance,script):
  """
  Prints output to stdout.

  Keyword arguments:
  smart_values -- smart detail info of problem device(s)
  importance -- given script importance
  script -- script to be executed when threshol is reached
  """
  ret_str = importance + "\n"
  ret_str = ret_str + smart_values
  if script is not None:
      script_action(script)
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

def check_values(block_devs):
  """
  Returns block device which is about to fail

  Keyword arguments:
  block_devs -- all block devices in machine
  """
  ret_str = ""
  for dev in block_devs:
    smart_out = subprocess.run(["smartctl","-a",dev],stdout=subprocess.PIPE)
    smart_out = smart_out.stdout.decode("utf-8")
    try:
      smart_values = re.search("(ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE\n)([\s\S]*?\n\n)",smart_out).group(2)  #filter smart values only
    except AttributeError:
      ret_str = ret_str + "S.M.A.R.T. VALUES UNAVAILABLE FOR " + str(dev) + "\n"
      ret_str = ret_str + smart_out + "\n"
      continue
    first_time = True  #flag, that error has occured for the first time on a device
    for line in smart_values.split('\n')[:-2]:
      value = re.search(" *\d+ +.*? +.*? +(.*?) +(.*?) +(.*?) +.*", line).group(1)
      threshold = re.search(" *\d+ +.*? +.*? +(.*?) +(.*?) +(.*?) +.*", line).group(3)
      if (int(value) <= int(threshold)) and first_time:
        ret_str = ret_str + "\n" + "Block device \"" + dev + "\" status: Error \n"
        ret_str = ret_str + re.search("=== START OF INFORMATION SECTION ===([\s\S]*?\n\n)",smart_out).group(1)
        ret_str = ret_str +  "Threshold has reached its value:\n" + line + "\n"
        first_time = False
      elif (int(value) <= int(threshold)):
        ret_str = ret_str + line + "\n"
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

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="disk_smart_mon.py", description="Monitoring SMART value on every disk",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  specific_disk = parser.add_mutually_exclusive_group(required=True)
  specific_disk.add_argument("-b","--blockdev",help="disk partition identified as block device e.g. /dev/sda1",action="store",type=str)
  specific_disk.add_argument("-a","--alldevices",help="defines all block devices connected to machine",action="store_true")
  specific_disk.add_argument("-u","--uuid",help="disk partition identified with uuid",action="store",type=str)
  args = parser.parse_args()

  if args.alldevices:
    block_devs = find_block_devs()
  elif args.blockdev:
   block_devs = []
   block_devs.append(args.blockdev)
  elif args.uuid:
    block_devs = []
    block_devs.append(uuid_to_block(args.uuid))

  smart_values = check_values(block_devs)
  if smart_values == "":
    ret_str = ""
  else:
    ret_str = print_output(smart_values,args.importance,args.execute)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
