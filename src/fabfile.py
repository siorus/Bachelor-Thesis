#!/usr/bin/python3

from fabric.api import run,env,put

env.user = "root"
env.hosts = ["192.168.126.129","192.168.126.128","192.168.126.131","192.168.126.133"]
env.password = "root"
env.warn_only = True

def copy_to_remote():
  print("Creating temporary directory for installer...")
  run("mkdir /tmp/linmon_installer")
  print("Copying currrent directory content to \"/tmp/linmon_installer\"...")
  put(".","/tmp/linmon_installer")

def execute_permissions():
  print("Setting install script permissions to 750...")
  run("chmod -R 750 /tmp/linmon_installer")

def sendmail_relay():
  print("Configuring sendmail to use specified relay server...")
  run("/tmp/linmon_installer/aux_scripts/sendmail_relay_setup.py")

def fix_interpret(shebang):
  run("cd /tmp/linmon_installer && aux_scripts/python_shebang.sh %s" % shebang)

def install(email):
  copy_to_remote()
  execute_permissions()
  fix_interpret("/usr/bin/python3.6")
  email = "-e " + email
  run("cd /tmp/linmon_installer && /tmp/linmon_installer/install.py %s" %email)

def install_with_smtprelay(email):
  copy_to_remote()
  execute_permissions()
  fix_interpret("/usr/bin/python3.6")
  run("/tmp/linmon_installer/aux_scripts/sendmail_relay_setup.py")
  email = "-e " + email
  run("cd /tmp/linmon_installer && /tmp/linmon_installer/install.py %s" %email)

def remove():
  run("/opt/linmon/install.py -r")

def maintenance_on():
  run("/opt/linmon/linmon.py -m on")

def maintenance_off():
  run("/opt/linmon/linmon.py -m off")

def maintenance_time(time_to_run):
  run("/opt/linmon/linmon.py -t " + time_to_run)