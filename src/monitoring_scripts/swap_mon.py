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
  actual_value -- current free swap
  threshold -- defined free swap threshold
  free_out -- output of command line utility free
  importance -- given script importance
  type -- units %/MB
  script -- script to be executed when threshol is reached
  """
  if actual_value <= threshold:
    ret_str = importance + "\n"
    ret_str = ret_str + "THRESHOLD FREE SWAP: " + str(threshold) + type +"\n"
    ret_str = ret_str + "CURRENT FREE SWAP: " + str(actual_value) + type +"\n"
    ret_str = ret_str + free_out + "\n"
    if script is not None:
      script_action(script)
  else :
    ret_str = ""
  return ret_str

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="swap_mon.py", description="Monitoring free swap utilization on machine",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  unit_type = parser.add_mutually_exclusive_group(required=True)
  unit_type.add_argument("-p","--percentage",help="threshold free swap in percentage",action="store",type=int)
  unit_type.add_argument("-m","--megabytes",help="threshold free swap in megabytes",action="store",type=int)

  args = parser.parse_args()

  free_out = subprocess.run(["free","-m"], stdout=subprocess.PIPE)  #show ram utilization
  free_out = free_out.stdout.decode("utf-8")
  swap_line = re.search("Swap.*",free_out).group(0)
  total = re.search("(.*?) +(\d+) +(\d+) +(\d+)",swap_line).group(2)  #total ram
  free = re.search("(.*?) +(\d+) +(\d+) +(\d+)",swap_line).group(4)  #free ram
  percentage = int(free)/int(total)*100
  mibibytes = int(free)
  
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

