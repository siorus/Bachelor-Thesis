#!/usr/bin/python3

#DEPENDENCIES: ping,ping6

import argparse
import re
import subprocess
import sys

def script_action(script):
  """
  Run specified script.
  """
  subprocess.run(script.split(" "))

def print_output(failed_ips,importance,script):
  """
  Prints output to stdout when machine with ip is not pingable.

  Keyword arguments:
  failed_ips -- list with ips that was not pingable
  importance -- given script importance
  script -- script to be executed when threshol is reached
  """
  if failed_ips != []:
    ret_str = importance + "\n"
    ret_str = ret_str + "Machines with these IP addresses might be powered off, they are not responding to PING:\n"
    for ip in failed_ips:
      ret_str = ret_str + ip + "\n"
    if script is not None:
      script_action(script)
  else:
    ret_str = ""
  return ret_str

def ping(type_of_ip,examined_list):
  """
  Pings specified ip addresses and returns list with unsuccessful pings

  Keyword arguments:
  type_of_ip -- IPv4 or IPv6
  examined_list -- list with ip addresses to be examined
  """
  failer_ips = []
  if type_of_ip == "4":
    for ip in examined_list:
      ping_out = subprocess.run(["ping", ip ,"-c", "2"],stdout=subprocess.PIPE)
      if re.search(".*0 received.*",ping_out.stdout.decode("utf-8")):
        failer_ips.append(ip)
  else:
    for ip in examined_list:
      ping_out = subprocess.run(["ping6", ip ,"-c", "2"],stdout=subprocess.PIPE)
      if re.search(".*0 received.*",ping_out.stdout.decode("utf-8")):
        failer_ips.append(ip)
  return failer_ips

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="node_alive.py", description="Monitors specified server active state",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  parser.add_argument("-t","--type",help="defines whether addresses are ipv4 or ipv6",choices=["4","6"],required=True)
  load_type = parser.add_mutually_exclusive_group(required=True)
  load_type.add_argument("-s","--server",help="ip addresses of monitored servers, more ips are separated by spaces",nargs="+",type=str)
  load_type.add_argument("-c","--config",help="configuration file with specified servers to be monitored, one line one ip",action="store")

  args = parser.parse_args()
  
  if args.config is not None:
    fp = open(args.config,"r")
    config = fp.read()
    failed_ips = ping(args.type,config.splitlines())  #ping ips in file delimited by newline
  else:
    failed_ips = ping(args.type,args.server)  #ping ips from cmd line delimited with spaces

  ret_str = print_output(failed_ips,args.importance,args.execute)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
