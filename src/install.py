#!/usr/bin/python3

import argparse
import re
import subprocess
import sys
import os
import errno
import shutil
import glob
import fcntl
import time
from packages import unitinfo
from packages import linmon_builtin

version = 1.0  #version of program, could be changed

file_lock = None  #global var for allowing only one instance of script to be run

def store_install_report(report_output):
  """
  Keep installation checklist in file.
  """
  fp = open(linmon_builtin.read_configfile_fn("config")+"instalation_report","w")
  fp.write(report_output)
  fp.close

def check_sendmail_run_fn():
  """
  Checking whether sendmail is running, if not it tries to start it.
  """
  #sendmail_stat = subprocess.run(["top","-b","-n","1"], stdout=subprocess.PIPE)
  sendmail_stat = subprocess.run(["ps","-ef"], stdout=subprocess.PIPE)
  sendmail_stat = sendmail_stat.stdout.decode("utf-8")
  ret_fail_str = "  Sendmail error: "
  if re.search(".*sendmail.*",sendmail_stat) == None:
    if unitinfo.init_system_fn() == "systemd":
      try:
        subprocess.run(['systemctl','start','sendmail'],check=True)
        ret_str = "  Sendmail running: OK\n"
      except subprocess.SubprocessError or PermissionError or OSError:
        ret_str = "  Sendmail running: FAIL\n"
        ret_fail_str = ret_fail_str + "cannot start sendmail"
    elif (unitinfo.init_system_fn() == "init") or (unitinfo.init_system_fn() == "upstart"):
      try:
        subprocess.run(['service','sendmail','start'],check=True)
        ret_str = "  Sendmail running: OK\n"
      except (subprocess.TimeoutExpired,subprocess.CalledProcessError,PermissionError):
        ret_str = "  Sendmail running: FAIL\n"
        ret_fail_str = ret_fail_str + "cannot start sendmail"
    else:
      ret_str = "  Sendmail running: FAIL\n"
      ret_fail_str = ret_fail_str + "unknown init system, cannot guarantee sendmail is running"
  else:
    ret_str = "  Sendmail running: OK\n"
  ret_fail_str = ret_fail_str + "\n"
  return ret_str,ret_fail_str

def create_configfile_fn(args):
  """
  Creates config file for script linmon according to program arguments given with installation.

  Keyword arguments:
  args -- commandline arguments from argparse 
  """
  config = ""
  if args.email:
    email_addresses = ""
    for email in args.email:
      email_addresses = email_addresses + "," +email
    config = "email: " + email_addresses[1:] + "\n"
    config = config + "sendmail: " + args.sendmail + "\n"
    if args.directory:
      if args.directory[-1] == "/":
        config = config + "directory: "+ args.directory + "\n"  #install path has ending "/"
      else:
        config = config + "directory: "+ args.directory + "/" +"\n"  #install path does not have ending "/"
    if args.config:
      if args.config[-1] == "/":
        conf_path = args.config
        config = config + "config: "+ args.config + "\n"  #config path has ending "/"
      else:
        conf_path = args.config + "/"
        config = config + "config: "+ args.config + "/" +"\n"  #config path does not have ending "/"
  else:
    sys.stderr.write("No e-mail specified, e-mail is required argument\n")  #email is required argument
    sys.exit(1)
  try:
    config_file = open(conf_path+"linmon_install.conf","w")
  except FileNotFoundError:  #make directory tree for conf file
    os.makedirs(args.config, 0o755 )
    config_file = open(conf_path+"linmon_install.conf","w")
  config_file.write(config)
  config_file.close()
  ret_str = "Config file: " + conf_path + "linmon_install.conf\n"
  ret_str = ret_str + config_file_var_fn(conf_path+"linmon_install.conf")  #store config file path in env variable
  return ret_str

def config_file_var_fn(config_path):
  """
  Creates env variable for config file location.

  Keyword arguments:
  config_path -- path, where is configuration file stored
  """
  try:
    fp = open("/etc/profile.d/linmon.sh","w")
  except FileNotFoundError:
    os.makedirs("/etc/profile.d/",0o755)  #make directory tree file
    fp = open("/etc/profile.d/linmon.sh","w")
  fp.write("export LINMON_CONFIG_PATH="+config_path+"\n")  #env variable value
  os.chmod(config_path,0o644)
  fp.close()
  return "Config env file: /etc/profile.d/linmon.sh\n"

def copy_files(subdir,cwd,install_dir):
  """
  Copy files to desired location

  Keyword arguments:
  subdir -- directory to be copied
  cwd -- current working directory
  install_dir -- destination directory
  """
  for file in os.listdir(cwd+"/"+subdir):  #copy monitoring scripts with directory
    try:
      shutil.copy2(cwd + "/" + subdir + "/" + file,install_dir + subdir + "/" + file)
      os.chmod(install_dir + subdir + "/" + file,0o750)
    except FileNotFoundError:  #destination directory does not exist
      os.makedirs(install_dir+subdir,0o755)
      shutil.copy2(cwd + "/" + subdir + "/" + file,install_dir + subdir + "/" + file)
      os.chmod(install_dir + subdir + "/" + file,0o750)
    except IsADirectoryError:
      pass
    
def copy_scipts_fn():
  """
  Copy dirs and files from installation diretory to commandline specified place.
  """
  cwd = os.getcwd()
  install_dir = linmon_builtin.read_configfile_fn("directory")
  config_dir = linmon_builtin.read_configfile_fn("config")
  for py_file in glob.glob("*.py"):
    try:
      shutil.copy2(cwd+"/"+py_file,install_dir+py_file)  #copy all *.py files from root
    except FileNotFoundError:  #make directory tree
      os.makedirs(install_dir,0o755)
      shutil.copy2(cwd+"/"+py_file,install_dir+py_file)
    os.chmod(install_dir+py_file,0o750)
  copy_files("packages",cwd,install_dir)
  copy_files("monitoring_scripts",cwd,install_dir)
  copy_files("monitoring_scripts/packages",cwd,install_dir)
  copy_files("syslog_scripts",cwd,install_dir)
  copy_files("syslog_scripts/packages",cwd,install_dir)

  for file in os.listdir(cwd+"/configs"):  #copy config files
    shutil.copy2(cwd+"/configs/"+file,config_dir+file)
    os.chmod(config_dir+file,0o644)

  if unitinfo.init_system_fn() == "systemd":  #systemd is used
    fp = open(cwd+"/init_scripts/linmon.service","r")
    service_file = fp.read()
    fp.close()
    try:
      fp = open("/etc/systemd/system/linmon.service","w")
      fp.write(re.sub("ExecStart=(.*)","ExecStart="+install_dir+"linmon.py",service_file))  #change default paths in service file to commandline specified
    except FileNotFoundError:  #create directory tree
      os.makedirs("/etc/systemd/system/",0o755)
      fp = open("/etc/systemd/system/linmon.service","w")
      fp.seek(0)
      fp.write(re.sub("ExecStart=(.*)","ExecStart="+install_dir+"linmon.py",service_file))  #change default paths in service file to commandline specified
      fp.truncate()
    fp.close()
    os.chmod("/etc/systemd/system/linmon.service",0o644)
  elif unitinfo.init_system_fn() == "init":
    fp = open(cwd+"/init_scripts/linmon","r")
    service_file = fp.read()
    fp.close()
    try:
      fp = open("/etc/init.d/linmon","w")
      fp.write(re.sub("DAEMON_PATH=.*","DAEMON_PATH=\"" + install_dir + "\"",service_file))  #change default paths in service file to commandline specified
    except FileNotFoundError:
      os.makedirs("/etc/init.d",0o755)
      fp = open("/etc/init.d/linmon","w")
      fp.seek(0)
      fp.write(re.sub("DAEMON_PATH=.*","DAEMON_PATH=\"" + install_dir + "\"",service_file))  #change default paths in service file to commandline specified
      fp.truncate()
    fp.close()
    os.chmod("/etc/init.d/linmon",0o750)
    fp = open("/etc/inittab","a")
    fp.write("linm:2345:respawn:"+install_dir+"linmon.py\n")  #add option to start service when linmon crashes
    fp.close()
    subprocess.run(["init","q"]) 
  elif unitinfo.init_system_fn() == "upstart":
    fp = open(cwd+"/init_scripts/linmon.conf","r")
    service_file = fp.read()
    fp.close()
    try:
      fp = open("/etc/init/linmon.conf","w")
      fp.write(re.sub("exec.*","exec "+install_dir+"linmon.py",service_file))  #change default paths in service file to commandline specified
    except FileNotFoundError:  #create directory tree
      os.makedirs("/etc/init/",0o755)
      fp = open("/etc/init/linmon.conf","w")
      fp.seek(0)
      fp.write(re.sub("exec.*","exec "+install_dir+"linmon.py",service_file))  #change default paths in service file to commandline specified
      fp.truncate()
    fp.close()
    os.chmod("/etc/init/linmon.conf",0o644)
  else:
    pass

def remove_script_fn():
  """
  Uninstalling and removing script components
  """
  conf_file = linmon_builtin.read_configfile_fn("config")
  installed_dir = linmon_builtin.read_configfile_fn("directory")
  print("Stopping and disabling service...")
  if unitinfo.init_system_fn() == "systemd":
    try:
      subprocess.run(["systemctl","disable","linmon"],check=True)  #stop linmon service
      subprocess.run(["systemctl","stop","linmon"],check=True)
      print("Stopping and disabling service  [OK]")
    except subprocess.SubprocessError:
      print("Stopping and disabling service  [FAIL]")
  elif unitinfo.init_system_fn() == "upstart":
    try:
      subprocess.run(["stop","linmon"],check=True)
      print("Stopping and disabling service  [OK]")
    except subprocess.SubprocessError:
      print("Stopping and disabling service  [FAIL]")
  elif unitinfo.init_system_fn() == "init":
    try:
      subprocess.run(["service","linmon","stop"],check=True)
      print("Stopping and disabling service  [OK]")
    except subprocess.SubprocessError:
      print("Stopping and disabling service  [FAIL]")
  print("Killing daemon(in case started by cron)...")
  try:
    fp = open("/var/run/linmon.pid")
    pid = fp.read()
    subprocess.run(["kill","9",pid])
    print("Killing daemon  [OK]")
  except FileNotFoundError  or subprocess.SubprocessError:
    print("Daemon was not probably started by cron")
  
  linmon_builtin.lock_file_fn()  #lock linmon.py to avoid starting it by cron
  try:
    print("Removing crontab record...")
    crontab_manipulation_fn(0)  #remove crontab
    print("Removing crontab record  [OK]")
  except OSError:
    print("Removing crontab record  [FAIL]")
  try:
    print("Removing config file " + conf_file + "...")
    shutil.rmtree(conf_file)
    print("Removing config file " + conf_file + "  [OK]")
  except OSError:
    print("Removing config file " + conf_file + "  [FAIL]")
  try:
    print("Removing /etc/profile.d/linmon.sh...")
    os.remove("/etc/profile.d/linmon.sh")
    print("Removing /etc/profile.d/linmon.sh  [OK]")
  except OSError:
    print("Removing /etc/profile.d/linmon.sh  [FAIL]")
  try:
    if unitinfo.init_system_fn() == "systemd":
      print("Removing init system file /etc/systemd/system/linmon.service...")
      os.remove("/etc/systemd/system/linmon.service")
      print("Removing init system file /etc/systemd/system/linmon.service  [OK]")
    elif unitinfo.init_system_fn() == "upstart":
      print("Removing init system file /etc/init/linmon.conf...")
      os.remove("/etc/init/linmon.conf")
      print("Removing init system file /etc/init/linmon.conf  [OK]")
    elif unitinfo.init_system_fn() == "init":
      print("Removing init system file /etc/init.d/linmon...")
      os.remove("/etc/init.d/linmon")
      print("Removing init system file /etc/init.d/linmon  [OK]")
  except OSError:
    print("Removing init system file [FAIL]")
  if unitinfo.init_system_fn() == "init":
    try:
      print("Removing record from /etc/inittab...")
      fp = open("/etc/inittab","r")
      initttab = fp.read()
      fp.close()
      fp = open("/etc/inittab","w")
      fp.write(re.sub("linm.*\n","",initttab))
      fp.close()
      print("Removing record from /etc/inittab  [OK]")
    except FileNotFoundError:
      print("Removing record from /etc/inittab  [FAIL]")
  try:
    print("Removing " + installed_dir + "...")  
    shutil.rmtree(installed_dir)
    print("Removing " + installed_dir + "  [OK]")
  except OSError:
    print("Removing " + installed_dir + "  [FAIL]")
  try:
    print("Removing /tmp/linmon...")  
    shutil.rmtree("/tmp/linmon")
    print("Removing /tmp/linmon  [OK]") 
  except OSError:
    print("Removing /tmp/linmon  [FAIL]")
  try:
    os.remove("/var/run/linmon")
    os.remove("/var/run/linmon.pid")
  except FileNotFoundError or OSError:
    pass 

def crontab_manipulation_fn(action):
  """
  Creates or removes cron record for user linmon
  """
  ret_str = ""
  ret_fail_str = ""
  if action:  #install cron for user
    crontab_line = "*/5 * * * * " + linmon_builtin.read_configfile_fn("directory") + "linmon.py\n"  #run script every 5 minutes to be sure it is running
    try:
      crontab_file = subprocess.run(["crontab","-u","root","-l"],stdout=subprocess.PIPE)  #read current crontab for root
      fp = open("/tmp/crontab","w")  #save current crontab for root
      fp.write(crontab_file.stdout.decode("utf-8"))
      fp.write(crontab_line)  #add own script cron record
      fp.close()
      subprocess.run(["crontab","-u","root","/tmp/crontab"],check=True)  #push modified crontab file
      os.remove("/tmp/crontab")
      ret_str = "  Created cron: OK\n"
      ret_fail_str = "  Created cron error(s): \n"
    except subprocess.SubprocessError or OSError:
      ret_str = "  Created cron: FAIL\n"
      ret_fail_str = "  Created cron error(s): error created cron record\n"
  else:  #remove cron record, uninstalling
    crontab_file = subprocess.run(["crontab","-u","root","-l"],stdout=subprocess.PIPE)  #read current crontab for root
    crontab_file = crontab_file.stdout.decode("utf-8")
    crontab_line = "\*/5 \* \* \* \* " + linmon_builtin.read_configfile_fn("directory") + "linmon.py\n"  #run script every 5 minutes to be sure it is running
    modified_crontab = re.sub(crontab_line,"",crontab_file)  #delete line with linmon script path from crontab file
    fp = open("/tmp/crontab","w")
    fp.write(modified_crontab)
    fp.close()
    subprocess.run(["crontab","-u","root","/tmp/crontab"],check=True)  #push modified crontab file
    os.remove("/tmp/crontab")
  return ret_str,ret_fail_str

def install_script_fn(args):
  """
  Installs script linmon, copies files, installs dependecies, notifies about installation

  Keyword arguments:
  args -- commandline arguments from argparse 
  """
  message = linmon_builtin.station_info("LINMON installation report from "+ unitinfo.hostname_fn())
  message = message + create_configfile_fn(args)

  message = message + "\n----------------------\nInstallation checklist\n"+"----------------------\n"
  message_fail = "\n-------------------\nInstallation errors\n"+"-------------------\n"
  
  msg,msg_fail = check_sendmail_run_fn()
  message = message + msg
  message_fail = message_fail + msg_fail
  
  copy_scipts_fn()
  
  msg,msg_fail = linmon_builtin.init_script_start()
  message = message + msg
  message_fail = message_fail + msg_fail
  time.sleep(10)  #in case cron would start before initscript
  
  msg,msg_fail = crontab_manipulation_fn(1)
  message = message + msg
  message_fail = message_fail + msg_fail
  
  store_install_report(message+message_fail)
  linmon_builtin.sendmail_notification_fn(message+message_fail,"/tmp/linmon/sendmail")

def main():
  parser = argparse.ArgumentParser(prog="LINMON (UN)INSTALLER", description="Linux monitoring tool (un)installer",\
                                  formatter_class=argparse.ArgumentDefaultsHelpFormatter,\
                                  usage="LINMON [-h] [-v] [-r] [-e EMAIL [-d DIRECTORY] [-c CONFIG] [-s SENDMAIL]]")
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-r","--remove",help="remove script with config files",action="store_true")
  parser.add_argument("-e","--email",help="specify email(s), where will be sent all information, more email are separetd by spaces",nargs="+",type=str)
  parser.add_argument("-s","--sendmail",help="sendmail binary absolute path in case it is different than default",action="store",default="/usr/sbin/sendmail",type=str)
  parser.add_argument("-d","--directory",help="specifies directory where script will be installed",action="store",default="/opt/linmon/")
  parser.add_argument("-c","--config",help="specifies directory where script configs will be stored",action="store",default="/etc/opt/linmon/")
  
  args = parser.parse_args()
  if args.remove and (not len(sys.argv) > 2):
    remove_script_fn()
    sys.exit(0)
  else:
    try:
      open(linmon_builtin.read_configfile_fn("directory")+"linmon.py","r")
      sys.stderr.write("Script is already installed\n")
      sys.exit(1)
    except OSError:
      try:
        os.makedirs("/tmp/linmon", 0o755)
      except FileExistsError:
        pass
      install_script_fn(args)
      sys.exit(0)  #exit after install, service has already started

if __name__ == '__main__':
    main()