#!/usr/bin/python3

import subprocess
import os
import re

def hostname_fn():
  """
  Return hostname of machine
  """
  try:
    hostname = subprocess.run(["hostname"], stdout=subprocess.PIPE)
    hostname = hostname.stdout.decode('ascii').rstrip('\n')
  except subprocess.SubprocessError:
      fp = open("/etc/hostname","r")
      hostname = fp.read()
      fp.close()
  return hostname

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
  return pkg_mgr.rstrip('\n')

def full_dist_name_fn():
  """
  Return GNU/Linux distribution name
  """
  try:
    fp = open("/etc/os-release","r")
    release_info = fp.read()
    dist_name = re.search("PRETTY_NAME.*",release_info).group(0)
    fp.close()
    dist_name = dist_name.replace("PRETTY_NAME=","")
    dist_name = dist_name.replace("\"", "")
  except OSError:
    print("ERROR: Full distributio name not found")
    dist_name = "Unknown"
  return dist_name

def kernel_version_fn():
  """
  Return kernel version
  """
  try:
    kern_ver = subprocess.run(['uname', '-r'], stdout=subprocess.PIPE)
    kern_ver = kern_ver.stdout.decode('ascii').rstrip('\n')
  except subprocess.SubprocessError:  #uname is not present or working
    fp = open("/proc/version","r")
    kern_ver = re.search('(.*?\ )(.*?\ )(.*?\ )(.*?)',fp.read()).group(3)
    fp.close()
  return kern_ver

def arch_fn():
  """
  Return architecture
  """
  try:
    arch = subprocess.run(['uname','-m'],stdout=subprocess.PIPE)
    ret = arch.stdout.decode('ascii').rstrip('\n')
  except subprocess.SubprocessError:
    ret = "Unknown"
  return ret

def init_system_fn():
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

def adapter_ip_fn():
  """
  Retruns all network adapters that are "UP"
  """
  adapters = subprocess.run(['ip','addr'], stdout=subprocess.PIPE)
  adapters_up = re.findall(".* (.*?): .* state UP.*",adapters.stdout.decode('ascii'))  #UP network adapters
  adapter_list_up = {}
  for i in adapters_up:
      regex = "(.*?) "+ i +": (.* state UP.*)\n.*\n( *inet )(.*?) .*"
      adapter_list_up[i] = re.search(regex, adapters.stdout.decode('ascii')).group(4)  #dictionary adapter:ip
  return adapter_list_up
