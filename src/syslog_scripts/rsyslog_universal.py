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
    ret_str = ret_str + "Found error(s) in " + log_file + ":\n"
    ret_str = ret_str + err_lines
    if script is not None:
      script_action(script)
  return ret_str

def script_name(regex):
  """
  Returns escaped regex used for conf file
  """
  regex = regex.replace("/","\/")
  regex = regex.replace(" ","\ ")
  regex = regex.replace("|","\|")
  return regex

def last_line(regex):
  """
  Returns last line of monitoring log file
  
  Keyword arguments:
  regex -- escaped regex which forms log conf file for last line record
  """
  script_path = os.path.basename(__file__)
  script_conf = os.path.splitext(script_path)[0]
  try:
    fp = open("/tmp/linmon/"+script_conf+script_name(regex),"r")
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

def store_num_of_lines(count,regex):
  """
  Saves current new number of line of log file

  Keyword arguments:
  count -- new number of lines
  regex -- escaped regex which forms log conf file for last line record
  """
  script_path = os.path.basename(__file__)
  script_conf = os.path.splitext(script_path)[0]
  script = "/tmp/linmon/" + script_conf+script_name(regex)
  try:
    fp = open(script,"w")
  except FileNotFoundError:
    os.makedirs("/tmp/linmon/", 0o755 )
    fp = open(script,"w")
  fp.write(str(count))
  fp.close()

def examine_line(line,regex):
  """
  Returns matched line in log file

  Keyword arguments:
  line -- current line in syslog
  regex -- regular expression which matches wished line
  """
  if re.search(regex,line) != None:
    if re.search(".*"+re.escape(os.path.basename(__file__))+".*",line) == None:
      ret_str = line
    else:
      ret_str = ""  #in case searching in auth.log and script would match itself, eg. rsyslog_universal run with sudo
  else:
    ret_str = ""  #given pattern not in this line
  return ret_str

def examine_new_logs(log_file,line_to_start,regex):
  """
  Returns lines with matched pattern

  log_file -- file to be examined
  line_to_start -- line where examination will start
  regex -- regular expression which matches wished line
  """
  err_line = ""
  fp = open(log_file,"r")
  new_lines = 0
  if count_lines(log_file) < line_to_start:  #in case log rotate, new log has less lines than saved value
    line_to_start = 0
  for line in fp.readlines()[line_to_start:]:
    new_lines = new_lines +1
    matched_line = examine_line(line,regex)
    if matched_line != "":  #given pattern found in log file
      err_line = err_line + matched_line
    else:
      continue
  store_num_of_lines(line_to_start+new_lines,regex)  #save next search line position
  return err_line
  
def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="rsyslog_universal.py", description="Looks for specified pattern in syslog file",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("file",metavar="FILE",help="specifies file which will be examined",action="store",type=str)
  parser.add_argument("regex",metavar="REGEX",help="regex for matching wanted log record",action="store",type=str)
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  args = parser.parse_args()
  
  ret_str = ""
  line_to_start = last_line(args.regex)
  if line_to_start == -1:
    count = count_lines(args.file)
    store_num_of_lines(count,args.regex)
  else:
    err_lines = examine_new_logs(args.file,line_to_start,args.regex)
    ret_str = print_output(err_lines,args.file,args.execute,args.importance)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
