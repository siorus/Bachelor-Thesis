#!/usr/bin/python3

#DEPENDENCIES: top,sytemd|upstart|sysv,ps

import argparse
import re
import subprocess
import sys
from packages import unitinfo

def check_service_run(service,action):
  """
  Checking whether service is running, if not it tries to start/stop it.

  Keyword arguments:
  service -- defined linux service
  action -- start/stop
  """
  service_stat = subprocess.run(["top","-b","-n","1"], stdout=subprocess.PIPE)  #VYSKUSAJ nefunfuje na devuan sysv
  #service_stat = subprocess.run(["ps","-ef"], stdout=subprocess.PIPE)  #VYSKUSAJ nefunguje na systemd
  service_stat = service_stat.stdout.decode("utf-8")
  if ((not re.search(service,service_stat)) and (action == "start")) or (re.search(service,service_stat) and (action == "stop")):
    ret = 1  #service started/stopped successfuly
    if unitinfo.init_system_fn() == "systemd":
      try:
        subprocess.run(['systemctl',action,service],check=True)
      except subprocess.SubprocessError or PermissionError or OSError:
        ret = 2  #cannot start/stop service
    elif unitinfo.init_system_fn() == "init":
      try:
        subprocess.run(['service',service,action],check=True)
      except (subprocess.TimeoutExpired,subprocess.CalledProcessError,PermissionError):
        ret = 2  #cannot start/stop service
    elif unitinfo.init_system_fn == "upstart":
      try:
        subprocess.run([action,service],check=True)
      except (subprocess.TimeoutExpired,subprocess.CalledProcessError,PermissionError):
        ret = 2  #cannot start/stop service
    else:
      ret = 3  #cannot start/stop service, unknown init system
  else:
    ret = 0  #service is ok running or stopped according to wished action
  return ret

def script_action(script):
  """
  Run specified script.
  """
  subprocess.run(script.split(" "))

def print_output(service,service_status,importance,action,script):
  """
  Prints output to stdout when threshold is reached.

  Keyword arguments:
  service -- service to be monitored
  service_status -- actual status running/stoppped/unable to run/stop
  importance -- given script importance
  actio -- start/stop service
  script -- script to be executed when threshol is reached
  """
  if service_status == 1:
    ret_str = importance + "\n"
    if action == "always_on":
      ret_str = ret_str + "SERVICE: \"" + service + "\" WAS NOT RUNNING, BUT NOW IT HAS STARTED\n"
    else:
      ret_str = ret_str + "SERVICE: \"" + service + "\" WAS RUNNING, BUT NOW IT HAS STOPPED\n" 
    if script is not None:
      script_action(script)     
  elif service_status == 2:
    ret_str = importance + "\n"
    if action == "always_on":
      ret_str = ret_str + "SERVICE: \"" + service + "\" WAS NOT RUNNING, UNABLE TO START IT\n"
    else:
      ret_str = ret_str + "SERVICE: \"" + service + "\" WAS RUNNING, UNABLE TO STOP IT\n"
    if script is not None:
      script_action(script)      
  elif service_status == 3:
    ret_str = importance + "\n"
    ret_str = ret_str + "CANNOT DETERMINE SERVICE: \"" + service + "\" IS RUNNING, UNKNOWN INIT SYSTEM\n"
    if script is not None:
      script_action(script)
  else:
    ret_str = ""
  return ret_str

def service_operation(service,activity):
  """
  Returns status of monitored service

  service -- service to be monitored
  activity -- start/stop service
  """
  if activity == "always_on":
    ret = check_service_run(service,"start")
  else:
    ret = check_service_run(service,"stop")
  return ret


def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="service_alive_stat.py", description="Monitoring specifed service status",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("service",metavar="SERVICE",help="specifies service",action="store",type=str)
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  status = parser.add_mutually_exclusive_group(required=True)
  status.add_argument("-a","--active",help="monitor whether service is active, if it is passive, start it and notify admin ",action="store_true")
  status.add_argument("-p","--passive",help="monitor whether service is passive, if it is active, start it and notify admin ",action="store_true")

  args = parser.parse_args()
  if args.active:
    service_status = service_operation(args.service,"always_on")
    ret_str = print_output(args.service,service_status,args.importance,"always_on",args.execute)
  else:
    service_status = service_operation(args.service,"always_off")  
    ret_str = print_output(args.service,service_status,args.importance,"always_off",args.execute)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
