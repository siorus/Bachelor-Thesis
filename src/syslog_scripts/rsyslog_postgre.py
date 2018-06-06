#!/usr/bin/python3

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

def print_output(err_lines,log_file,script,importance):
  """
  Prints output to stdout when error is found

  Keyword arguments:
  err_lines -- found lines with error
  log_file -- name of monitoring log
  script -- script to be executed when threshol is reached
  importance -- given script importance
  """
  ret_str = ""
  if err_lines != "":
    ret_str = importance + "\n"
    ret_str = ret_str + "Found Postgre error(s) in " + log_file + ":\n"
    ret_str = ret_str + err_lines
    if script is not None:
      script_action(script)
  return ret_str

def script_name():
  """
  Returns config file of script to store last line number
  """
  script_name = os.path.basename(__file__)
  script_conf = os.path.splitext(script_name)[0]
  return script_conf

def last_line():
  """
  Returns last line of monitoring log file
  """
  script_conf = script_name()
  try:
    fp = open("/tmp/linmon/"+script_conf+".conf","r")
    line = int(fp.read().rstrip())
  except FileNotFoundError:
    line = -1  #config file has not been created yet
  return line

def count_lines(log_file):
  """
  Returns number of lines in file

  Keyword arguments:
  log_file -- file to be examined
  """
  fp = open(log_file,"r")
  count = 0
  for line in fp.readlines():
    count = count + 1
  fp.close()
  return count

def store_num_of_lines(count):
  """
  Saves current new number of line of log file

  Keyword arguments:
  count -- new number of lines
  """
  script = "/tmp/linmon/" + script_name() + ".conf"
  try:
    fp = open(script,"w")
  except FileNotFoundError:
    os.makedirs("/tmp/linmon/", 0o755 )
    fp = open(script,"w")
  fp.write(str(count))
  fp.close()

def examine_new_logs(log_file,line_to_start):
  """
  Returns lines with matched pattern

  log_file -- file to be examined
  line_to_start -- line where examination will start
  """
  err_line = ""
  examing_regex = ["^.*password authentication failed for user.*$"]  #searching pattern
  fp = open(log_file,"r")
  new_lines = 0
  if count_lines(log_file) < line_to_start:  #in case log rotate, new log has less lines than saved value
    line_to_start = 0
  for line in fp.readlines()[line_to_start:]:
    new_lines = new_lines +1
    for regex in examing_regex:
      try:
        err_line = err_line + re.search(regex,line).group(0) + "\n"  #whole line
      except AttributeError:
        continue  #current line dow not contain searchinf pattern 
  store_num_of_lines(line_to_start+new_lines)  #save next search line position
  return err_line
  
def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="rsyslog_postgre.py", description="Looks for Postgre errors in syslog",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("file",metavar="FILE",help="specifies log file which will be examined",action="store",type=str)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  args = parser.parse_args()
  
  ret_str = ""
  log_file = args.file
  line_to_start = last_line()
  if line_to_start == -1:
    count = count_lines(log_file)
    store_num_of_lines(count)
  else:
    err_lines = examine_new_logs(log_file,line_to_start)
    ret_str = print_output(err_lines,log_file,args.execute,args.importance)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
    