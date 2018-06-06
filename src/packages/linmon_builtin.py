#!/usr/bin/python3

import re
import subprocess
import sys
import os
import fcntl
try:
  import unitinfo
except ImportError:
  from packages import unitinfo

version = 1.0  #version of program, could be changed

def station_info(subject_string):
  """
  Forming header of email message and body with machine info.
  """
  ret_str = "Subject:"+subject_string + "\n"
  ret_str = ret_str + "\r\n"  #delimites email header from body
  ret_str = ret_str + "Hostname: " + unitinfo.hostname_fn() + "\n"
  ret_str = ret_str + "Distribution: " + unitinfo.full_dist_name_fn() + "\n"
  ret_str = ret_str + "Kernel version: " + unitinfo.kernel_version_fn() + "\n"
  ret_str = ret_str + "Init system type: " + unitinfo.init_system_fn() + "\n"
  ret_str = ret_str + "Package manager: " + unitinfo.package_manager_fn() + "\n"
  adapter = unitinfo.adapter_ip_fn()  
  for key in adapter:
    ret_str = ret_str + "Network adapter \"UP\": " + key + " " + adapter[key]+"\n"
  return ret_str

def sendmail_notification_fn(message,path):
  """
  Creates file from string, which will be sent and send it to receipent.
  """
  sendmail_bin = read_configfile_fn("sendmail")  #load sendmail binary absolute path
  fp = open(path,"w")
  fp.write(message)
  fp.write("\n")
  fp.close()
  try:
    fp = open(path,"r",encoding="utf-8")
    subprocess.run([sendmail_bin,read_configfile_fn("email")],stdin=fp)  #send info to specified email from config file
    subprocess.Popen([sendmail_bin,"-q"])  #flush sendmail queue
    fp.close()
  except subprocess.SubprocessError or OSError:
    pass
  os.remove(path)  #remove message file from /tmp/linmon after successful send

def read_configfile_fn(search_line):
  """
  Read configuration file and return specified line value.

  Keyword arguments:
  search_line -- line to be searched within config file
  """
  fp = open("/etc/profile.d/linmon.sh","r")  #determine where is config stored
  conf_file = fp.read()
  conf_file = re.search("export LINMON_CONFIG_PATH=(.*)\n",conf_file).group(1)  #get path to config
  fp = open(conf_file,"r")
  config_file = fp.read()
  return re.search(search_line+": (.*)\n",config_file).group(1)  #return wished line

def lock_file_fn():
  """
  Lock linmon.py, only one instance can be run, protection for cron.
  """
  global file_lock
  file_lock = open("/var/run/linmon","w")
  try:
    fcntl.lockf(file_lock, fcntl.LOCK_EX|fcntl.LOCK_NB)  #linmon is not running
    file_pid = open("/var/run/linmon.pid","w")  #file for linmon process pid storage
    file_pid.write(str(os.getpid()))
    file_pid.close()
    return 0
  except IOError:
    return 1

def init_script_start():
  """
  Starts init system script for linmon.
  """
  init_system = unitinfo.init_system_fn()
  ret_fail_str = "  Init system file error(s): "
  if init_system == "systemd":
    try:
      subprocess.run(["systemctl","enable","linmon"],check=True)
      ret_str = "  Init system file enabled: OK\n"
      subprocess.run(["systemctl","start","linmon"],check=True)
      ret_str = ret_str + "  Init system file started: OK\n"
    except subprocess.SubprocessError:
      ret_str = "  Init system file enabled: FAIL\n"
      ret_str = ret_str + "  Init system file started: FAIL\n"
      ret_fail_str = ret_fail_str + "error"
  elif init_system == "init":
    try:
      subprocess.run(["service","linmon","start"],check=True)
      ret_str = "  Init system file enabled: OK\n"
      ret_str = ret_str + "  Init system file started: OK\n"
    except subprocess.SubprocessError:
      ret_str = "  Init system file enabled: FAIL\n"
      ret_str = ret_str + "  Init system file started: FAIL\n"
      ret_fail_str = ret_fail_str + "error"
  elif init_system == "upstart":
    try:
      subprocess.run(["start","linmon"],check=True)
      ret_str = "  Init system file enabled: OK\n"
      ret_str = ret_str + "  Init system file started: OK\n"
    except subprocess.SubprocessError:
      ret_str = "  Init system file enabled: FAIL\n"
      ret_str = ret_str + "  Init system file started: FAIL\n"
      ret_fail_str = ret_fail_str + "error"
  else:
    sys.stderr.write("Unknown init system, cannot ensure starting script")
    ret_str = "  Init system file enabled: FAIL\n"
    ret_str = ret_str + "  Init system file started: FAIL\n"
    ret_fail_str = ret_fail_str + "Unknown init system, cannot ensure starting script"
  ret_fail_str = ret_fail_str + "\n"
  return ret_str,ret_fail_str