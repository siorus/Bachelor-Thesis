#!/usr/bin/python3

#DEPENDENCIES: blkid,df

import argparse
import re
import subprocess
import sys

def label_to_block(label):
  """
  Return name of block device according to label

  Keyword arguments:
  label -- disk label
  """
  blkid = subprocess.run(["blkid"],stdout=subprocess.PIPE)
  blkid = blkid.stdout.decode("utf-8")
  try:
    block_dev = re.search("(.*)\:.*LABEL=\"" + re.escape(label) + "\".*",blkid).group(1)  #filter block dev name
  except AttributeError:
    block_dev = ""
  return block_dev

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

def block_to_uuid_label(block_dev):
  """
  Returns uuid and label of block device

  Keyword arguments:
  block_dev -- name of partiton 
  """
  blkid = subprocess.run(["blkid"],stdout=subprocess.PIPE)
  blkid = blkid.stdout.decode("utf-8")
  try:
    label = re.search(re.escape(block_dev) + ": LABEL=\"(.*)\" UUID=\"(.*?)\"",blkid).group(1)
    uuid = re.search(re.escape(block_dev) + ": LABEL=\"(.*)\" UUID=\"(.*?)\"",blkid).group(2)
  except AttributeError:
    label = ""
    uuid = ""
  return label,uuid

def script_action(script):
  """
  Run specified script.
  """
  subprocess.run(script.split(" "))

def print_output(free_memory,threshold,args,disk_free,block_dev,unit,script):
  """
  Prints output to stdout when threshold is reached.

  Keyword arguments:
  free_memory -- current free disk space
  threshold -- set free space threshold
  args -- commandline args 
  disk_free --  output from command line utility df
  block_dev -- specific block device
  unit -- disk space unit %/GB
  script -- script to be executed when threshol is reached
  """
  if free_memory <= threshold:
    date = subprocess.run(["date"],stdout=subprocess.PIPE)
    label,uuid = block_to_uuid_label(block_dev)
    ret_str = args.importance + "\n"
    ret_str =  ret_str + "Execution time: " + date.stdout.decode("utf-8")  #script executed time
    ret_str = ret_str + "BLOCK DEVICE: " + block_dev + "\nLABEL: " + label + "\nUUID: " + uuid + "\n"
    ret_str = ret_str + "THRESHOLD FREE DISK PARTITION SPACE: " + str(threshold) + unit +"\n"  #subject for email message
    ret_str = ret_str + "CURRENT FREE DISK PARTITION SPACE: " + str(free_memory) + unit +"\n"
    ret_str = ret_str + disk_free 
    if script is not None:
      script_action(script) 
  else:
    ret_str = ""
  return ret_str

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="disk_usage.py", description="Monitoring free space on specified partition",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  specific_disk = parser.add_mutually_exclusive_group(required=True)
  specific_disk.add_argument("-b","--blockdev",help="disk partition identified as block device e.g. /dev/sda1",action="store",type=str,default="")
  specific_disk.add_argument("-l","--label",help="disk partition identified with label e.g. backup-disk",action="store",type=str,default="")
  specific_disk.add_argument("-u","--uuid",help="disk partition identified with uuid",action="store",type=str)
  free_units = parser.add_mutually_exclusive_group(required=True)
  free_units.add_argument("-p","--percentage",help="free space in percentage",action="store",type=int)
  free_units.add_argument("-g","--gigabytes",help="free disk space in gigabytes",action="store",type=int)
  args = parser.parse_args()

  if args.label:
    block_dev = label_to_block(args.label)
  elif args.uuid:
    block_dev = uuid_to_block(args.uuid)
  elif args.blockdev:
    block_dev = args.blockdev
  
  if block_dev == "":
    print("Partition not found, blockdevice/label/uuid does not exist")
    sys.exit(0)
  
  disk_free = subprocess.run(["df","-h",block_dev],stdout=subprocess.PIPE)
  if disk_free.returncode == 1:
    print("Block device does not exist")
    exit(2)
  disk_free = disk_free.stdout.decode("utf-8")
  ret_str = ""
  
  if args.percentage :
    free_perc = 100 - int(re.search(".*\n.+ (\d+)%.*",disk_free).group(1))
    ret_str = print_output(free_perc,args.percentage,args,disk_free,block_dev,"%",args.execute)
  elif args.gigabytes:
    free_giga = int(re.search(".*\n.+ (\d+)G.*",disk_free).group(1))
    ret_str = print_output(free_giga,args.gigabytes,args,disk_free,block_dev,"GB",args.execute) 
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)