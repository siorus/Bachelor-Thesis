#!/usr/bin/python3
import argparse
import re
import subprocess
import sys
import os
import errno
import time
import datetime
import sched
import threading
import signal
import shutil
import fcntl
from packages import unitinfo
from packages import linmon_builtin

version = 1.0  #version of program, could be changed

file_lock = None  #global var for allowing only one instance of script to be run

def append_importance(importance_list,importance):
  """
  Returns modified list with new importance

  Keyword arguments:
  importance_list -- list which will be used for append
  importance -- current new importance
  """
  if importance not in ["critical","info","warning","error"]:
    importance_list.append("info")  #first line of script is not filled with importance, default will be appended
  else:
    importance_list.append(importance)
  return importance_list
  
def highest_importance(importance_list):
  """
  Returns the highest importance in list

  Keyword arguments:
  importance_list -- list to be examined
  """
  importance_weight = {1:"critical",2:"error",3:"warning",4:"info"}
  actual_max_value = 4  #default key, the lowest weight
  for importance in importance_list:
    for weight_key,value in importance_weight.items():
      if (importance == value) and (weight_key < actual_max_value):
        actual_max_value = weight_key
  return importance_weight[actual_max_value]

def parse_cron_minutes(conf_cron):
  """
  Returns dictionary with delay time group and command to be executed

  Keyword arguments:
  conf_cron -- file where commands for execution are placed 
  """
  run_every = {}
  for line in re.findall("^(?:\d+)\ (?:.*)$",conf_cron,flags=re.MULTILINE):  #find lines with right syntax, ommit comments
    minutes = re.search("^(\d+)\ (.*)$",line,flags=re.MULTILINE).group(1)  #extract minute from line
    try:
      command = re.search("^("+minutes+")\ (\[.*?\])\ (.+)$",line,flags=re.MULTILINE).group(3).rstrip()  #group for command is defined, take command
      group = re.search("^("+minutes+")\ (\[.*?\])\ (.+)$",line,flags=re.MULTILINE).group(2).upper()  #specified group on line
    except AttributeError:
      command = re.search("^("+minutes+")\ (.*)$",line,flags=re.MULTILINE).group(2).rstrip()  #command to be executed, no group defined
      group = "[DEFAULT]"  #no group is specified, defaul tag will be used
    run_every = create_cron_cmd_dictionary(run_every,group,minutes,command)
  return run_every

def parse_cron_time(conf_cron):
  """
  Returns dictionary with time group and command to be executed

  Keyword arguments:
  conf_cron -- file where commands for execution are placed 
  """
  run_at = {}
  for line in re.findall("^(?:\d{1,2}:\d{2})\ (?:.*)$",conf_cron,flags=re.MULTILINE):  #find lines with right syntax, ommit comments
    time_set = re.search("^(\d{1,2}:\d{2})\ (.*)$",line,flags=re.MULTILINE).group(1)  #extract time from line
    try:
      command = re.search("^("+time_set+")\ (\[.*?\])\ (.+)$",line,flags=re.MULTILINE).group(3).rstrip()  #group for command is defined, take command
      group = re.search("^("+time_set+")\ (\[.*?\])\ (.+)$",line,flags=re.MULTILINE).group(2).upper()  #specified group on line
    except AttributeError:
      command = re.search("^("+time_set+")\ (.*)$",line,flags=re.MULTILINE).group(2).rstrip()  #command to be executed, no group defined
      group = "[DEFAULT]"  #no group is specified, defaul tag will be used
    if re.search("^\d{1}:\d{2}$",time_set,flags=re.MULTILINE):
      time_set = "0" + time_set
    run_at = create_cron_cmd_dictionary(run_at,group,time_set,command)
  return run_at

def create_cron_cmd_dictionary(cmd_dict,group,times,command):
  """
  Returns dictionary with uniq key(minutes/time)

  Keyword arguments:
  cmd_dict -- current dictionary with command,time and group
  group -- current appended group
  times -- current appended time of execution
  command -- current appended command 
  """
  if cmd_dict == {}:
    cmd_dict.setdefault(times,[]).append({group:[command]})  #first job for append
  elif times not in cmd_dict:
    cmd_dict.setdefault(times,[]).append({group:[command]})  #delayed times value defined for first time
  else:
    group_presents = False  #flag to know whether group is in dict
    place_to_append = ""  #dictionary element for appending command
    for value in list(cmd_dict[times]):  #loop through all groups(keys in dict) within given minute delay defined in cron conf
      if group in value:
        group_presents = True  #group in delay times dict exist
        place_to_append = value  #dict key for appending command in same group
        break  #dont loop again, group already exist
      else:
        group_presents = False  #group has not been found yet, loop again
    if group_presents:
      place_to_append[group].append(command)  #group exists in delay times, append to it
    else:
      cmd_dict.setdefault(times,[]).append({group:[command]})
  return cmd_dict

def plan_script_to_run(sc):
  """
  Returns parsed commands from linmon cron config in dictionary

  Keyword arguments:
  sc -- scheduler
  """
  fp = open(linmon_builtin.read_configfile_fn("config")+"scripts_to_run.conf","r")
  conf_cron = fp.read()
  run_every = parse_cron_minutes(conf_cron)
  for delay_minutes in run_every:  #loop every set minutes delay
    for group_key_val in run_every[delay_minutes]:  #loop through all group within specified minute delay
      group = next(iter(group_key_val))  #actual group of commands
      command_list = group_key_val[group]  #all commands in actual group
      time_flag = delay_minutes+"min"  #time flag for message subject
      actual_time = time.time()  #in case planned time gain or loose
      delay_timer(sc,command_list,int(delay_minutes),group,actual_time,time_flag,True)

  run_at = parse_cron_time(conf_cron)
  for time_to_run in run_at:
    priority = 1  #in case more commands in different group in same time, scheduler has to differentiate priority
    for group_key_val in run_at[time_to_run]:
      group = next(iter(group_key_val))  #actual group of commands
      command_list = group_key_val[group]  #all commands in actual group
      hour = int(re.search("(\d{1,2})\:(\d{2})",time_to_run).group(1))
      minutes = int(re.search("(\d{1,2})\:(\d{2})",time_to_run).group(2))
      actual_time = datetime.datetime.now()
      if (actual_time.hour*3600 + actual_time.minute*60 + actual_time.second) >= (hour*3600 + minutes*60):
        event_time = actual_time.replace(hour=hour,minute=minutes,second=0, microsecond=0) + datetime.timedelta(days=1)  #planned time elapsed, plan for newxt day
      else:
        event_time = actual_time.replace(hour=hour,minute=minutes,second=0, microsecond=0)  #planned time has not elapsed, plan for given time this day
      time_flag = re.search(".*\ (\d+:\d+)",str(event_time)).group(1)
      runat_timer(sc,command_list,event_time,group,priority,time_flag,True)
      priority = priority + 1  # next group increase priority
  fp.close()

def form_msg(script_out,script_no,command,num_of_spaces,importance_list,exc):
  """
  Returns list with flag error was found(catch error), edited importance list and output of failed script

  Keyword arguments:
  script_out -- output of monitoring script 
  script_no -- sequence number of script 
  command -- command which was executed
  num_of_spaces  -- indentation correction
  importance_list -- list with script importance withou current one
  exc -- flag exception occured executing monitoring script
  """
  catch_error = 0
  warn_output = ""
  if exc:  #exception occured executing script, script does not exist or ...
    catch_error = catch_error + 1  #script returned error
    importance_list = append_importance(importance_list,".")
    script_checklist = str(script_no) + "." + " "*(4-len(str(script_no))) + command + " "*(6+num_of_spaces-len(command)) + "ERR\n"  #correction of indentation
    warn_output = "-------------------" + importance_list[-1].upper() + " script no." + str(script_no) +"-------------------\n"
    warn_output = warn_output + "Script: " + command + "\n"
    warn_output = warn_output + "Executed time: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n"
    warn_output = warn_output + "An error has occured when executing script, it might not exists\n" + str(script_out) + "\n"
    warn_output = warn_output + "-------------------END OF " + importance_list[-1].upper() + " script no." + str(script_no) +"-------------------\n\n\n"
  elif script_out.stdout.decode("utf-8") == "":
    script_checklist = str(script_no) + "." + " "*(4-len(str(script_no))) + command + " "*(6+num_of_spaces-len(command)) +"OK" + "\n"  #no stdout output from monitoring script, everything ok
  elif script_out.stdout.decode("utf-8") != "\n":  #monitoring script has found abnormal value
    catch_error = catch_error + 1  #script returned error
    importance_list = append_importance(importance_list,script_out.stdout.decode("utf-8").split('\n', 1)[0])
    script_checklist = str(script_no) + "." + " "*(4-len(str(script_no))) + command + " "*(6+num_of_spaces-len(command)) + "ERR\n"  #correction of indentation
    warn_output = "-------------------" + importance_list[-1].upper() + " script no." + str(script_no) +"-------------------\n"
    warn_output = warn_output + "Script: " + command + "\n"
    warn_output = warn_output + "Executed time: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n"
    if (len(script_out.stdout.decode("utf-8").splitlines())) == 1:
      warn_output = warn_output + script_out.stdout.decode("utf-8").rstrip() + "\n"  #no importance print only one line of output
    else:
      warn_output = warn_output + script_out.stdout.decode("utf-8").split('\n', 1)[1].rstrip() + "\n"  #normal output with importance, omiit first line with importance
    warn_output = warn_output + "-------------------END OF " + importance_list[-1].upper() + " script no." + str(script_no) +"-------------------\n\n\n"
  else:
    script_checklist = str(script_no) + "." + " "*(4-len(str(script_no))) + command + " "*(6+num_of_spaces-len(command)) +"OK" + "\n"  #no stdout output from monitoring script, everything ok
  return [catch_error,importance_list,script_checklist,warn_output]

def runcmd_and_send(command_list,group,time_flag):
  """
  Execute commands and send info

  Keyword arguments:
  command_list -- list of commands for execution
  group -- name of group same for all commands
  time_flag -- group defined time of execution of command_list
  """
  catch_error = 0  #flag error was found
  script_no = 0  #sequence number for script
  script_checklist = ""  #string which holds status of script execution
  warn_output = ""  #string which holds monitoring script error outputs
  importance_list = []  #list which stores given importance of executing scripts
  num_of_spaces = max(len(x) for x in command_list)  #max len of scripts in list for indentation 
  script_checklist = "Executed scripts status\n" + "-"*25 + "\n"
  script_checklist = script_checklist + "No.  "+ "Script" + " "*num_of_spaces + "Status\n"
  for command in command_list:
    script_no = script_no + 1
    try:
      script_out = subprocess.run(command.split(" "),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)  #run monitoring script
      send_msg_list = form_msg(script_out,script_no,command,num_of_spaces,importance_list,False)  #try to form message
    except Exception as e:
      send_msg_list = form_msg(e,script_no,command,num_of_spaces,importance_list,True)  #message cannot be formed, script probably does not exist      
    catch_error = catch_error + int(send_msg_list[0])  #increase counter for error(script something found)
    importance_list = send_msg_list[1]  #update importance list with new modified one
    script_checklist = script_checklist + send_msg_list[2]  #add current scritp check list status
    warn_output = warn_output + send_msg_list[3]  #concat new error output
  if catch_error :  #monitoring script found abnormal value
    importance = highest_importance(importance_list)  #find highest importance
    msg_header = linmon_builtin.station_info("LINMON" + "[" + unitinfo.hostname_fn() + "][" + importance + "]" + "[" +time_flag + "]" + group)  #add subject of email message and machine info
    message = msg_header + "\n" + script_checklist + "\n" + warn_output 
    linmon_builtin.sendmail_notification_fn(message,"/tmp/linmon/sendmail"+ str(time.time()))  #send message

def runat_timer(sc,command_list,event_time,group,priority,time_flag,first_run):
  """
  Plan next event and run command from cronfile

  Keyword arguments:
  sc -- scheduler variable
  command_list -- command which will be executed
  event_time -- time of execution
  group -- name of group same for all commands
  priority -- scheduler command list priority
  actual_time -- in case planned time gain or loose
  time_flag --group defined time of execution of command_list
  first_run -- flag first run
  """
  if first_run:
    run_at = time.strptime(re.match("\d{4}-\d{2}-\d{2}\ \d{2}\:\d{2}\:\d{2}",str(event_time)).group(0),"%Y-%m-%d %H:%M:%S")  #plan next event
  else:
    event_time = event_time + datetime.timedelta(days=1)  #plan for next day
    run_at = time.strptime(re.match("\d{4}-\d{2}-\d{2}\ \d{2}\:\d{2}\:\d{2}",str(event_time)).group(0),"%Y-%m-%d %H:%M:%S")  #plan next event
  sc.enterabs(time.mktime(run_at),priority,runat_timer,(sc,command_list,event_time,group,priority,time_flag,False,))
  if not first_run:
    runcmd_and_send(command_list,group,time_flag)  #run after second plan

def delay_timer(sc,command_list,delay_minutes,group,actual_time,time_flag,first_run):
  """
  Plan next event and run command from cronfile

  Keyword arguments:
  sc -- scheduler variable
  command_list -- command which will be executed
  delay_minutes -- next event delay
  group -- name of group same for all commands
  actual_time -- in case planned time gain or loose
  time_flag --group defined time of execution of command_list
  first_run -- flag first run
  """
  actual_time = actual_time + (delay_minutes*60)  #set new delay time
  threading.Timer(actual_time - time.time(), delay_timer,[sc,command_list,delay_minutes,group,actual_time,time_flag,False]).start()  #plan next event
  if not first_run:
    runcmd_and_send(command_list,group,time_flag)  #run after second plan

def proc_kill():
  """
  Kills linmon process
  """
  pid_file = open("/var/run/linmon.pid","r")
  pid = pid_file.read()
  os.kill(int(pid), signal.SIGKILL)
  time.sleep(1)
  linmon_builtin.lock_file_fn()

def maintenance_mode(args):
  """
  Kills running linmon instance and disable monitoring 
  """
  if args.maintenance != "off":
    proc_kill()
  if args.time:  #maintenance mode will run for specified time
    msg_header = linmon_builtin.station_info("LINMON" + "[" + unitinfo.hostname_fn() + "] Maintenance mode ON")  #add subject of email message and machine info
    message = "Maintenance mode has been turned on at " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " for " + str(args.time) +" minutes\n"
    message = msg_header + "\n" + message
    linmon_builtin.sendmail_notification_fn(message,"/tmp/linmon/sendmail"+ str(time.time()))  #send message
    time.sleep(args.time*60)
    msg_header = linmon_builtin.station_info("LINMON" + "[" + unitinfo.hostname_fn() + "] Maintenance mode OFF")  #add subject of email message and machine info
    message = "Maintenance mode has been turned off at " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n"
    message = message + "System monitoring will continue\n"
    message = msg_header + "\n" + message
    linmon_builtin.sendmail_notification_fn(message,"/tmp/linmon/sendmail"+ str(time.time()))  #send message
    linmon_builtin.init_script_start()
    sys.exit(0)
  else:  #maintenance mode will run until "-m off"
    if args.maintenance == "off":
      file_lock = open("/tmp/linmon/maintenance","w")
      while True:
        try:
          fcntl.lockf(file_lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
          shutil.rmtree("/tmp/linmon")
          proc_kill() 
          linmon_builtin.init_script_start()
          sys.exit(0)
        except IOError:
          time.sleep(1)
    else:
      file_lock = open("/tmp/linmon/maintenance","w")
      try:
        fcntl.lockf(file_lock, fcntl.LOCK_EX|fcntl.LOCK_NB)  #linmon is not running
      except IOError:
        sys.exit(0)
      msg_header = linmon_builtin.station_info("LINMON" + "[" + unitinfo.hostname_fn() + "] Maintenance mode ON")  #add subject of email message and machine info
      message = "Maintenance mode has been turned on at " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n"
      message = message + "For turnining it off, run: ./linmon.py -m off\n"
      message = msg_header + "\n" + message
      linmon_builtin.sendmail_notification_fn(message,"/tmp/linmon/sendmail"+ str(time.time()))  #send message
    while True:
      ps_out = subprocess.run(["ps","-ef"],stdout=subprocess.PIPE)
      if re.search(".*linmon\.py.*-m off.*",ps_out.stdout.decode("utf-8")):
        msg_header = linmon_builtin.station_info("LINMON" + "[" + unitinfo.hostname_fn() + "] Maintenance mode OFF")  #add subject of email message and machine info
        message = "Maintenance mode has been turned off at " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n"
        message = message + "System monitoring will continue\n"
        message = msg_header + "\n" + message
        linmon_builtin.sendmail_notification_fn(message,"/tmp/linmon/sendmail"+ str(time.time()))  #send message
        sys.exit(0)
      time.sleep(1)

def update_and_run():
  """
  Read new values from conf file and run linmon again
  """
  proc_kill()
  time.sleep(1)
  msg_header = linmon_builtin.station_info("LINMON" + "[" + unitinfo.hostname_fn() + "] Configuration files were updated")  #add subject of email message and machine info
  message = "Configuration files were modified at " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n"
  message = msg_header + "\n" + message
  linmon_builtin.sendmail_notification_fn(message,"/tmp/linmon/sendmail"+ str(time.time()))  #send message
  linmon_builtin.init_script_start()
  sys.exit(0)

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="linmon.py", description="Monitoring tool for GNU/LINUX",\
                                  formatter_class=argparse.ArgumentDefaultsHelpFormatter,usage="linmon.py [-h] [-v] (-u | -m (on | off) | -t)")
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  special_run = parser.add_mutually_exclusive_group()
  special_run.add_argument("-u","--update",help="load new settings when configfile/cron was changed",action="store_true")
  special_run.add_argument("-m","--maintenance",help="temporarly disable daemon, stop monitoring, ignore syslog",action="store",choices=["on","off"])
  parser.add_argument("-t","--time",help="time in minutes for which will be maintenance mode turned on",action="store",type=int)
  args = parser.parse_args()

  if args.maintenance or args.time:
    maintenance_mode(args)
  elif args.update:
    update_and_run()
  
  if linmon_builtin.lock_file_fn():
    sys.exit(3)  #linmon is running
 
  try:
   os.makedirs("/tmp/linmon", 0o755)
  except FileExistsError:
    pass

  s = sched.scheduler(time.time,time.sleep)
  plan_script_to_run(s)
  s.run()

if __name__ == '__main__':
    main()
