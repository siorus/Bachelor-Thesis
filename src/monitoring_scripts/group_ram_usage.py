#!/usr/bin/python3

#DEPENDENCIES: smem

import argparse
import re
import subprocess
import sys

def user_to_regex(user_list):
  """
  Returns regex with users according to specified group
  """
  user_str = ""
  for user in user_list:
      user_str = user_str + "("+ user +")|"
  return user_str[:-1]  

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

def print_output(value,threshold,group,user_regex,importance,type,script):
  """
  Prints output to stdout when threshold is reached.

  Keyword arguments:
  value -- curent used ram by group
  threshold -- threshold used value for group
  group -- specified group to be monitored
  user_regex -- regex for smem of all users in group
  importance -- given script importance
  type -- unit of used ram %/MB
  script -- script to be executed when threshol is reached
  """
  if value >= threshold:
    ret_str = importance + "\n"
    ret_str = ret_str + "GROUP: \"" + group + "\" HAS EXCEEDED RAM THRESHOLD: " + str(threshold) + type +"\n"
    ret_str = ret_str + "CURRENT THRESHOLD: " + str(value) + type +"\n"
    smem_out = subprocess.run(["smem","--userfilter="+user_regex,"-s","pid"],stdout=subprocess.PIPE)
    ret_str = ret_str + smem_out.stdout.decode("utf-8")
    if script is not None:
      script_action(script)
  else :
    ret_str = ""
  return ret_str

def actual_value(users,user_regex,percent):
  """
  Returns current used ram by group

  Keyword arguments:
  users -- users to be monitored
  user_regex -- regex for smem of all users in group
  percent -- flag for unit %/MB
  """
  ret = 0
  if percent:
    smem_out = subprocess.run(["smem","-u","--userfilter="+user_regex,"-p","-H"], stdout=subprocess.PIPE)  #show ram usage by user in %
    regex = "( +)(\d+)( +)(.+?)( +)(.+?)( +)(.+?)%( +)(.+)"
  else:
    smem_out = subprocess.run(["smem","-u","--userfilter="+user_regex,"-H"], stdout=subprocess.PIPE)  #show ram usage by user in KB
    regex = "( +)(\d+)( +)(.+?)( +)(.+?)( +)(.+?)( +)(.+)"
  smem_out = smem_out.stdout.decode("utf-8")  #line without head
  try:
    for user in users:
      ret = ret + float(re.search("(" + user + ")" + regex,smem_out,flags=re.MULTILINE).group(9))  #PSS column
  except AttributeError:
    ret = 0  #user not found
  return ret 

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="group_ram_usage.py", description="Monitoring used ram by specified group",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("group",metavar="GROUP",help="group which will be monitored",action="store",type=str)
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  threshold = parser.add_mutually_exclusive_group(required=True)
  threshold.add_argument("-p","--percentage",help="threshold value for group in percentage",action="store",type=int)
  threshold.add_argument("-m","--megabytes",help="threshold value for group in megabytes",action="store",type=int)
  args = parser.parse_args()

  users = parse_users(args.group)
  user_regex = user_to_regex(users)
  #user_processes = re.findall("^(?: *.*? +)(?:"+args.user+").*$",top_out.split("\n",6)[6],flags=re.MULTILINE)  #filter processes for given user
  if args.percentage is not None:
    percentage = actual_value(users,user_regex,1)
    ret_str = print_output(percentage,args.percentage,args.group,user_regex,args.importance,"%",args.execute)
  else:
    memory = actual_value(users,user_regex,0)/1000
    ret_str = print_output(memory,args.megabytes,args.group,user_regex,args.importance,"MB",args.execute)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
