#!/usr/bin/python3

#DEPENDENCIES: top

import argparse
import re
import subprocess
import sys

def script_action(script):
  """
  Run specified script.
  """
  subprocess.run(script.split(" "))

def print_output(percentage,threshold,top_out,out_str,importance,script):
  """
  Prints output to stdout when threshold is reached.

  Keyword arguments:
  percentage -- actual percentage utilization
  threshold -- set percentage threshold
  top_out -- output from cmd utility top
  out_str -- string according to type of cpu utilization (TOTAL/SYSTEM/USER)
  importance -- given script importance
  script -- script to be executed when threshold is reached
  """
  if percentage >= threshold:
    ret_str = importance + "\n"
    ret_str = ret_str + out_str + str(threshold) + "%\n"  #string with type of utilization
    ret_str = ret_str + "CURRENT UTILIZATION: " + str(percentage) + "%\n"
    ret_str = ret_str + re.search("top[\s\S]*(top - [\s\S]*)",top_out).group(1) + "\n"  #cut header of top cmd, show only processes
    if script is not None:  #action script was specified
      script_action(script) 
  else :
    ret_str = ""
  return ret_str

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="cpu_mon.py", description="Monitoring cpu utilization on machine",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument("-t","--total",help="total cpu utilziation is more or equal",action="store",type=int)
  group.add_argument("-u","--user",help="all users cpu utilization is more or equal",action="store",type=int)
  group.add_argument("-s","--system",help="system cpu utilization is more or equal",action="store",type=int)
  args = parser.parse_args()

  top_out = subprocess.run(["top","-n","2","-b"], stdout=subprocess.PIPE)  #show every processes
  top_out = top_out.stdout.decode("utf-8")
  top_head = re.findall(".* +(?:\d+,\d+) id.*",top_out)
  if args.total is not None:
    idle = re.search(".* +(\d+,\d+) id.*",top_head[1]).group(1).replace(",",".")  #filter total cpu utilization
    ret_str = print_output(100.0-float(idle),args.total,top_out,"THRESHOLD TOTAL CPU UTILIZATION: ",args.importance,args.execute)
  elif args.user is not None:
    user = re.search(".* +(\d+,\d+) us.*",top_head[1]).group(1).replace(",",".")  #filter user cpu utilization
    ret_str = print_output(float(user),args.user,top_out,"THRESHOLD USER CPU UTILIZATION: ",args.importance,args.execute)
  else:
    system = re.search(".* +(\d+,\d+) sy.*",top_head[1]).group(1).replace(",",".")  #filter system cpu utilization
    ret_str = print_output(float(system),args.system,top_out,"THRESHOLD SYSTEM CPU UTILIZATION: ",args.importance,args.execute)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
