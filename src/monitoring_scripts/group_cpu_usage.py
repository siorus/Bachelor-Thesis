#!/usr/bin/python3

#DEPENDENCIES: top

import argparse
import re
import subprocess
import sys

def num_of_cpucores():
  """
  Returns number of cores in CPU
  """
  fp = open("/proc/cpuinfo")
  cpu_info = fp.read()
  num_of_cores = 0
  for core in re.findall("^processor.*$",cpu_info,flags=re.MULTILINE):
    num_of_cores = num_of_cores + 1
  return num_of_cores

def parse_users(group):
  """
  Returns users belonging in specified group

  Keyword arguments:
  group -- group of user to be monitored
  """
  fp = open("/etc/group","r")
  group_file = fp.read()
  try:
    users = (re.search("^(" + group + ")\:(.+)\:(.+)\:(.+)$",group_file,flags=re.MULTILINE).group(4)).split(",")
  except AttributeError:
    users = ""
  return users

def script_action(script):
  """
  Run specified script.
  """
  subprocess.run(script.split(" "))

def print_output(percentage,threshold,group,top_out,user_processes,importance,script):
  """
  Prints output to stdout when threshold is reached.

  Keyword arguments:
  percentage -- current cpu utilization
  threshold -- threshold cpu utilization value
  group -- specified group of user
  top_out -- output of commandline utility top
  user_processes -- filtered processes
  importance -- given script importance
  script -- script to be executed when threshol is reached
  """
  if percentage >= threshold:
    ret_str = importance + "\n"
    ret_str = ret_str + "GROUP: \"" + group + "\" HAS EXCEEDED CPU THRESHOLD: " + str(threshold) + "%\n"  #subject for email message
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
  parser = argparse.ArgumentParser(prog="group_cpu_usage.py", description="Monitoring cpu utilization by specified group of users",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("group",metavar="GROUP",help="group which will be monitored",action="store",type=str)
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-t","--threshold",help="threshold for group in percentage",action="store",required=True,type=int)
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  args = parser.parse_args()

  users = parse_users(args.group)
  top_out = subprocess.run(["top","-n","1","-b"], stdout=subprocess.PIPE)  #show every processes, run one time
  top_out = top_out.stdout.decode("utf-8")
  user_processes = []
  for user in users:
    user_processes = user_processes + re.findall("^(?: *.*? +)(?:"+str(user)+").*$",top_out.split("\n",6)[6],flags=re.MULTILINE)  #filter processes for given user
  percentage = 0.0
  try:
    for cpu_per in user_processes:
      percentage = percentage + float(re.search("( *)(.*?)( +)(.*?)( +)(.*?)( +)(.*?)( +)(.*?)( +)(.*?)( +)(.*?)( +)(.*?)( +)(.*?)( +)(.*?)",cpu_per).group(18).replace(",","."))
  except AttributeError:  #given user not in top cmd output
    percentage = 0.0
  ret_str = print_output(percentage/num_of_cpucores(),args.threshold,args.group,top_out,user_processes,args.importance,args.execute)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
