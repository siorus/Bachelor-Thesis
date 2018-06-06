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

def print_output(value,threshold,process,importance,type,script):
  """
  Prints output to stdout when threshold is reached.

  Keyword arguments:
  value -- current used RAM by process
  threshold -- threshold RAM value 
  process -- process to be monitored 
  importance -- given script importance
  type -- unit %/MB
  script -- script to be executed when threshol is reached
  """
  if value >= threshold:
    ret_str = importance + "\n"
    ret_str = ret_str + "PROCESS: \"" + process + "\" HAS EXCEEDED RAM THRESHOLD: " + str(threshold) + type +"\n"
    ret_str = ret_str + "CURRENT THRESHOLD: " + str(value) + type +"\n"
    smem_out = subprocess.run(["smem","--processfilter="+process,"-s","pid"],stdout=subprocess.PIPE)
    ret_str = ret_str + smem_out.stdout.decode("utf-8")
    if script is not None:
      script_action(script)
  else :
    ret_str = ""
  return ret_str

def actual_value(process,percent):
  """
  Returns current used ram by process

  Keyword arguments:
  users -- process to be monitored
  percent -- flag for unit %/MB
  """
  ret = 0
  if percent:
    smem_out = subprocess.run(["smem","-u","--processfilter="+process,"-p","-H"], stdout=subprocess.PIPE)  #show ram usage by process in %
    regex_all = "(?:.*)(?: +)(?:\d+\.\d+)%(?: +)(?:\d+\.\d+%).*"
    regex_group = "(.*)( +)(\d+\.\d+)%( +)(\d+\.\d+%).*"
  else:
    smem_out = subprocess.run(["smem","-u","--processfilter="+process,"-H"], stdout=subprocess.PIPE)  #show ram usage by process in KB
    regex_all = "(?:.*)(?: +)(?:\d+)(?: +)(?:\d+).*"
    regex_group = "(.*)( +)(\d+)( +)(\d+).*"
  smem_out = smem_out.stdout.decode("utf-8")  #line without head
  try:
    for pss in re.findall(regex_all,smem_out):
      ret = ret + float(re.search(regex_group,pss).group(3))  #PSS column
  except AttributeError:
    ret = 0  #process not found
  return ret

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="proc_ram_mon.py", description="Monitoring ram utilization by specified process",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("process",metavar="PROCESS",help="proces which will be monitored",action="store",type=str)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  threshold = parser.add_mutually_exclusive_group(required=True)
  threshold.add_argument("-p","--percentage",help="threshold value for process in percentage",action="store",type=int)
  threshold.add_argument("-m","--megabytes",help="threshold value for process in megabytes",action="store",type=int)
  args = parser.parse_args()

  if args.percentage is not None:
    percentage = actual_value(args.process,1)
    ret_str = print_output(percentage,args.percentage,args.process,args.importance,"%",args.execute)
  else:
    memory = actual_value(args.process,0)/1000
    ret_str = print_output(memory,args.megabytes,args.process,args.importance,"MB",args.execute)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
