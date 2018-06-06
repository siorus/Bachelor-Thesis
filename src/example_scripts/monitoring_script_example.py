#!/usr/bin/python3

"""
-----------------------------------------------------------------------
GUIDE
It is recommended to add info about script dependencies at the begining
-----------------------------------------------------------------------
"""
#DEPENDENCIES: top

"""
-------------------------------------------
GUIDE
These modules are required in every scripts
-------------------------------------------
"""
import argparse
import subprocess  #when argument -e is not used this import can be omitted
import sys

"""
---------------------------------------------------------
GUIDE
When argument -e is not used this function can be omitted
---------------------------------------------------------
"""
def script_action(script):
  """
  Run specified script.
  """
  subprocess.run(script.split(" "))

def print_output(value,threshold,output,importance,script):
  """
  Prints output to stdout when threshold is reached.

  Keyword arguments:
  value -- actual percentage utilization
  threshold -- set percentage threshold
  importance -- given script importance
  output -- output which will be sent to Linmon
  script -- script to be executed when threshold is reached
  """
  if value >= threshold:
    """
    ----------------------------------------------------------
    GUIDE
    First line should contain importance, when importance 
    is not set or argument with importance is not in argparse,
    implicit importance "info" will be used.
    ----------------------------------------------------------
    """
    ret_str = importance + "\n"
    ret_str = ret_str + "MY OUPUT\n"
    """
    -----------------------------------------------------------
    GUIDE
    When argument -e is not used these two line can be omittted
    -----------------------------------------------------------
    """
    if script is not None:  #action script was specified
      script_action(script) 
  else :
    """
    -----------------------------------------------------------------
    GUIDE
    Abnormal value or threshold was not reached, return empty string.
    -----------------------------------------------------------------
    """
    ret_str = ""
  return ret_str

def main():
  version = 1.0
  """
  --------------------------------------
  GUIDE
  These argparse arguments are minimal 
  for proper use of Linmon, you can also
  omit them and hard-code importance 
  and script which will be executed.
  --------------------------------------
  """
  parser = argparse.ArgumentParser(prog="monitoring_script_example.py.py", description="Monitoring script example",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  #add own arguments
  args = parser.parse_args()

  """
  -------------------------
  GUIDE
  Do some stuff, run checks
  -------------------------
  """
  
  
  """
  -------------------------------------------------
  GUIDE
  Store empty string when threshold did not reach
  value or when abnormal value was not found.
  -------------------------------------------------
  """
  ret_str = ""


  """
  ---------------------------------------------
  GUIDE
  Call print output or print wished string
  when threshold reaches value or when abnormal
  value was found.
  ---------------------------------------------
  """
  ret_str = print_output(value,threshold,output,args.importance,args.execute)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
