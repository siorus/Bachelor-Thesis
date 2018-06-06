#!/usr/bin/python3

#DEPENDENCIES: free

import argparse
import re
import subprocess
import sys

def script_action(script):
  """
  Run specified script.
  """
  subprocess.run(script.split(" "))

def print_output(actual_value,threshold,free_out,importance,type,script):
  """
  Prints output to stdout when threshold is reached.

  Keyword arguments:
  actual_value -- current free ram
  threshold -- defined free ram threshold
  free_out -- output of command line utility free
  importance -- given script importance
  type -- unit %/MB
  script -- script to be executed when threshol is reached
  """
  if actual_value <= threshold:
    ret_str = importance + "\n"
    ret_str = ret_str + "THRESHOLD FREE RAM: " + str(threshold) + type +"\n"
    ret_str = ret_str + "CURRENT FREE RAM: " + str(actual_value) + type +"\n"
    ret_str = ret_str + free_out + "\n"
    if script is not None:
      script_action(script)
  else :
    ret_str = ""
  return ret_str

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="ram_free_mon.py", description="Monitoring free ram utilization on machine",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  unit_type = parser.add_mutually_exclusive_group(required=True)
  unit_type.add_argument("-p","--percentage",help="threshold free ram in percentage",action="store",type=int)
  unit_type.add_argument("-m","--megabytes",help="threshold free ram in megabytes",action="store",type=int)

  args = parser.parse_args()

  free_out = subprocess.run(["free","-m"], stdout=subprocess.PIPE)
  free_out = free_out.stdout.decode("utf-8")
  total = re.search("(.*?) +(\d+) +(\d+) +(\d+) +(\d+) +(\d+)",free_out.split("\n",3)[1]).group(2)
  free = re.search("(.*?) +(\d+) +(\d+) +(\d+) +(\d+) +(\d+)",free_out.split("\n",3)[1]).group(4)
  buff = re.search("(.*?) +(\d+) +(\d+) +(\d+) +(\d+) +(\d+)",free_out.split("\n",3)[1]).group(6)
  percentage = (int(free)+int(buff))/int(total)*100
  mibibytes = int(buff)+int(free)
  
  if args.percentage is not None:
    ret_str = print_output(percentage,args.percentage,free_out,args.importance,"%",args.execute)
  else:
    ret_str = print_output(mibibytes,args.megabytes/1.0486,free_out,args.importance," MiB",args.execute)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
