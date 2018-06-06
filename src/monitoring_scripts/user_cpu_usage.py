#!/usr/bin/python3

#DEPENDENCIES: top

import argparse
import re
import subprocess
import sys

def num_of_cpucores():
  """
  Retruns number of cores in CPU
  """
  fp = open("/proc/cpuinfo")
  cpu_info = fp.read()
  num_of_cores = 0
  for core in re.findall("^processor.*$",cpu_info,flags=re.MULTILINE):
    num_of_cores = num_of_cores + 1
  return num_of_cores

def script_action(script):
  """
  Run specified script.
  """
  subprocess.run(script.split(" "))

def print_output(percentage,threshold,user,top_out,user_processes,importance,script):
  """
  Prints output to stdout when threshold is reached.

  Keyword arguments:
  percentage -- current cpu utilization by specified user
  threshold -- defined threshold value for cpu utilization by user
  user -- defined user to be monitored
  top_out -- output of command line utility top
  user_processes -- processes started by defined user
  importance -- given script importance
  script -- script to be executed when threshol is reached
  """
  if percentage >= threshold:
    ret_str = importance + "\n"
    ret_str = ret_str + "USER: \"" + user + "\" HAS EXCEEDED CPU THRESHOLD: " + str(threshold) + "%\n"
    ret_str = ret_str + "CURRENT THRESHOLD: " + str(percentage) + "%\n"
    ret_str = ret_str + top_out.split("\n",7)[6] + "\n"  #cut header of top cmd, show only processes 
    for line in user_processes:
      ret_str = ret_str + line + "\n"
    if script is not None:
      script_action(script)
  else :
    ret_str = ""
  return ret_str

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="user_cpu_usage.py", description="Monitoring cpu utilization by specified user",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("user",metavar="USER",help="user which will be monitored",action="store",type=str)
  parser.add_argument("-t","--threshold",help="threshold for user in percentage",action="store",required=True,type=int)
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  args = parser.parse_args()

  top_out = subprocess.run(["top","-n","1","-b"], stdout=subprocess.PIPE)  #show every processes, run one time
  top_out = top_out.stdout.decode("utf-8")
  user_processes = re.findall("^(?: *.*? +)(?:"+args.user+").*$",top_out.split("\n",6)[6],flags=re.MULTILINE)  #filter processes for given user
  percentage = 0.0
  try:
    for cpu_per in user_processes:
      percentage = percentage + float(re.search("( *)(.*?)( +)"+ args.user +"( +)(.*?)( +)(.*?)( +)(.*?)( +)(.*?)( +)(.*?)( +)(.*?)( +)(.*?)( +)(.*?)",cpu_per).group(17).replace(",","."))
  except AttributeError:  #given user not in top cmd output
    percentage = 0.0
  ret_str = print_output(percentage/num_of_cpucores(),args.threshold,args.user,top_out,user_processes,args.importance,args.execute)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
