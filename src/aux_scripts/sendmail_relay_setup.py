#!/usr/bin/python3

import re
import subprocess
import os
import copy
import io
import sys
import shutil
import argparse

def init_system():
  """
  Return type of initsystem
  """
  try:
    init_path = os.readlink("/proc/1/exe")
  except OSError:
    init_path = "Unknown"
  if re.search("systemd",init_path):
    ret = "systemd"
  elif re.search("init",init_path):
    ps_out = subprocess.run(["ps","-ef"],stdout=subprocess.PIPE)
    init_ps = re.findall("(upstart)|(Upstart)|(UPSTART)",ps_out.stdout.decode("utf-8"))
    if len(init_ps) > 1:
      ret = "upstart"
    else:
      ret = "init"
  else:
    ret = "Unknown"
  return ret

def package_manager_fn():
  """
  Return used package manager in distribution
  """
  packages = {'/etc/debian_version': 'apt', '/etc/deb-release': 'apt', '/etc/fedora-release': 'dnf', '/etc/centos-release': 'yum', '/etc/redhat-release': 'yum'}
  for release_path in packages:
    try:
      fp = open(release_path,'r')
      pkg_mgr = packages[release_path]
      fp.close()
    except:
      pkg_mgr = "Unknown"
    if (pkg_mgr != "Unknown"):
      break
  if pkg_mgr == "Unknown":
    print("Unknown package manager, cannot auto detect, specify it with -p argument")
    sys.exit(2)
  return pkg_mgr.rstrip('\n')

def restart_sendmail():
  """
  Restarting sendmail service.
  """
  init = init_system()
  ret = ""
  if init == "systemd":
    try:
      subprocess.run(['systemctl',"restart","sendmail"],check=True)
    except subprocess.SubprocessError or PermissionError or OSError:
      ret = "Cannot start/stop service"
  elif (init == "init") or (init == "upstart"):
    try:
      subprocess.run(['service',"sendmail","restart"],check=True)
    except (subprocess.TimeoutExpired,subprocess.CalledProcessError,PermissionError):
      ret = "Cannot start/stop service"
  else:
    ret = "Cannot start/stop service, unknown init system"
  return ret

def dependencies_install_fn(package_manager):
  """
  Install script and user dependencies.
  """
  pkgs_to_install = ["sendmail","sendmail-bin","sendmail-cf","libsasl2-modules","cyrus-sasl-plain"]
  ret = ""
  if package_manager == None:
    package_manager = package_manager_fn()
  try:
    if package_manager == "apt":  #package manager apt: Debian,Ubuntu...
      subprocess.run(["apt-get","update","-y"])
    else:
      subprocess.run([package_manager,"update","-y"])  #package manager yum,dnf
  except (subprocess.TimeoutExpired,subprocess.CalledProcessError):
    ret = ret + "Cannot update repositories\n"

  if package_manager == "apt":  #package manager apt: Debian,Ubuntu...
    for pkg in pkgs_to_install:
      try: 
        subprocess.run(["apt-get","install","-y",pkg],check=True)
      except (subprocess.TimeoutExpired,subprocess.CalledProcessError,PermissionError):
        if (pkg != "sendmail") or (pkg != "sendmail-bin"):
          ret = ret + "Cannot install " + pkg + "\n"
  elif (package_manager == "yum") or (package_manager == "dnf"):
    for pkg in pkgs_to_install:  
      try:
        subprocess.run([package_manager,"install","-y",pkg],check=True)  #package manager yum,dnf
      except (subprocess.TimeoutExpired,subprocess.CalledProcessError,PermissionError):
        if (pkg != "sendmail") or (pkg != "sendmail-bin"):
          ret = ret + "Cannot install " + pkg + "\n"
  else:
    ret = ret + "Unknown package manager, cannot install dependencies\n"
  return ret

def auth_file():
  ret = ""
  try:
      fp = open("/etc/mail/auth/authinfo","w")
  except FileNotFoundError:  #make directory tree
      os.makedirs("/etc/mail/auth",0o700)
  fp = open("/etc/mail/auth/authinfo","w")
  auth_file = "AuthInfo:smtp.egmail.com \"U:linmon.relay@gmail.com\" \"I:linmon.relay@gmail.com\" \"P:Linmon1gmail\" \"M:PLAIN\"\n" + \
              "AuthInfo: \"U:linmon.relay@gmail.com\" \"I:linmon.relay@gmail.com\" \"P:Linmon1gmail\" \"M:PLAIN\""
  fp.write(auth_file)
  fp.close()
  fp = open("/etc/mail/auth/authinfo","r")
  try:
    #os.system("makemap hash /etc/mail/auth/authinfo.db < /etc/mail/auth/authinfo")
    #subprocess.Popen(["/home/juraj/hsh.sh"])
    subprocess.run(["makemap", "-r","hash","/etc/mail/auth/authinfo.db"],stdin=fp,check=True)
  except subprocess.SubprocessError or PermissionError:
    ret = "Cannot make hash\n"
  os.chmod("/etc/mail/auth/authinfo.db",0o640)
  os.chmod("/etc/mail/auth/authinfo",0o640)
  fp.close()
  return ret

def sendmail_conf():
  gmail_relay = ["define(`SMART_HOST',`[smtp.gmail.com]')dnl\n" + \
                "define(`confAUTH_OPTIONS', `A p')dnl\n" + \
                "TRUST_AUTH_MECH(`EXTERNAL DIGEST-MD5 CRAM-MD5 LOGIN PLAIN')dnl\n" + \
                "define(`confAUTH_MECHANISMS', `EXTERNAL GSSAPI DIGEST-MD5 CRAM-MD5 LOGIN PLAIN')dnl\n" + \
                "FEATURE(`authinfo',`hash /etc/mail/auth/authinfo.db')dnl\n" + \
                "define(`RELAY_MAILER_ARGS', `TCP $h 587')\n" + \
                "define(`ESMTP_MAILER_ARGS', `TCP $h 587')\n" + \
                "MASQUERADE_AS(`gmail.com')dnl\n"]
  fp = open("/etc/mail/sendmail.mc","r")
  sendmail = fp.read()
  sendmail_modified = ""
  index = 0
  fp.close()
  os.rename("/etc/mail/sendmail.mc","/etc/mail/sendmail.mc.old")
  fp = open("/etc/mail/sendmail.mc","w")
  for line in sendmail.splitlines():
    if re.search("MAILER\(",line) != None:
     sendmail_modified = sendmail.splitlines(True)[:index] + gmail_relay + sendmail.splitlines(True)[index:]
     break
    index = index + 1
  fp.write("".join(sendmail_modified))
  fp.close()

def main():
  parser = argparse.ArgumentParser(prog="SENDMAIL RELAY SETUP", description="Testing setup for smtp relay")
  parser.add_argument("-p","--package",help="in case autedect of used package manager fails",action="store")
  parser.add_argument("-r","--remove",help="restore original sendmail configuration",action="store_true")
  args = parser.parse_args()
  if args.remove:
    os.rename("/etc/mail/sendmail.mc.old","/etc/mail/sendmail.mc")
    #shutil.rmtree("/etc/mail/auth")
    fp = open("/etc/mail/sendmail.cf","w")
    try:
      subprocess.run(["m4", "/etc/mail/sendmail.mc"],stdout=fp)
    except subprocess.SubprocessError:
      pass
    fp.close
    restart_sendmail()
    sys.exit(0)

  ret = ""
  ret = dependencies_install_fn(args.package)
  sendmail_conf()
  ret = ret + auth_file()
  fp = open("/etc/mail/sendmail.cf","w")
  try:
    subprocess.run(["m4", "/etc/mail/sendmail.mc"],stdout=fp)
  except subprocess.SubprocessError:
    ret = ret + "Cannot compile sendmail with new configuration\n"
  fp.close
  ret = ret + restart_sendmail()
  print(ret)


if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
