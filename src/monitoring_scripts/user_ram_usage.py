#!/usr/bin/python3

#DEPENDENCIES: smem

import argparse
import re
import subprocess
import sys

def script_action(script):
  """
  Run specified script.
  """
  subprocess.run(script.split(" "))

def print_output(value,threshold,user,importance,type,script):
  """
  Prints output to stdout when threshold is reached.

  Keyword arguments:
  value -- current user ram utilization
  threshold -- defined user ram utilization threshold
  user -- specified user ram utilization to be monitored
  importance -- given script importance
  type -- unit %/MB
  script -- script to be executed when threshol is reached
  """
  if value >= threshold:
    ret_str = importance + "\n"
    ret_str = ret_str + "USER: \"" + user + "\" HAS EXCEEDED RAM THRESHOLD: " + str(threshold) + type +"\n"
    ret_str = ret_str + "CURRENT THRESHOLD: " + str(value) + type +"\n"
    smem_out = subprocess.run(["smem","--userfilter="+user,"-s","pid"],stdout=subprocess.PIPE)
    ret_str = ret_str + smem_out.stdout.decode("utf-8")
    if script is not None:
      script_action(script)
  else :
    ret_str = ""
  return ret_str

def actual_value(user,percent):
  if percent:
    smem_out = subprocess.run(["smem","-u","--userfilter="+user,"-p"], stdout=subprocess.PIPE)  #show ram usage by user in %
    regex = "(" + user + ")( +)(\d+)( +)(.+?)( +)(.+?)( +)(.+?)%( +)(.+)"
  else:
    smem_out = subprocess.run(["smem","-u","--userfilter="+user], stdout=subprocess.PIPE)  #show ram usage by user in KB
    regex = "(" + user + ")( +)(\d+)( +)(.+?)( +)(.+?)( +)(.+?)( +)(.+)"
  smem_out = smem_out.stdout.decode("utf-8").split("\n",2)[1]  #line without head
  try:
    ret = float(re.search(regex,smem_out).group(9))  #PSS column
  except AttributeError:
    ret = 0  #user not found
  return ret 

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="user_ram_usage.py", description="Monitoring ram utilization by specified user",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("user",metavar="USER",help="user which will be monitored",action="store",type=str)
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  threshold = parser.add_mutually_exclusive_group(required=True)
  threshold.add_argument("-p","--percentage",help="threshold value for user in percentage",action="store",type=int)
  threshold.add_argument("-m","--megabytes",help="threshold value for user in megabytes",action="store",type=int)
  args = parser.parse_args()

  #user_processes = re.findall("^(?: *.*? +)(?:"+args.user+").*$",top_out.split("\n",6)[6],flags=re.MULTILINE)  #filter processes for given user
  if args.percentage is not None:
    percentage = actual_value(args.user,1)
    ret_str = print_output(percentage,args.percentage,args.user,args.importance,"%",args.execute)
  else:
    memory = actual_value(args.user,0)/1000
    ret_str = print_output(memory,args.megabytes,args.user,args.importance,"MB",args.execute)
  
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)