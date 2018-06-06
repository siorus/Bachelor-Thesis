#!/usr/bin/python3

#DEPENDENCIES: hpssacli|ssacli|hpacucli

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

def print_output(str_out,importance,script):
  """
  Prints output to stdout when threshold is reached.

  Keyword arguments:
  str_out -- physical drive status
  importance -- given script importance
  script -- script to be executed when threshol is reached
  """
  if str_out != "":
    ret_str = importance + "\n"
    ret_str = ret_str + "Tempereture threshold has been reached\n"
    ret_str = ret_str + str_out
    if script is not None:
      script_action(script)
  else:
    ret_str = ""
  return ret_str

def slot_serial_no(cli,slot):
  """
  Returns dictionary with slot serial and info about it

  Keyword arguments:
  cli -- type of used HP cli
  slot -- specified HP array slot
  """
  cli_out = subprocess.run([cli,"ctrl","all","show"],stdout=subprocess.PIPE)
  cli_out = cli_out.stdout.decode("utf-8")
  dict_of_slots = {}  #key is serial of slot and value is slot detail info
  slot_no = re.search(".*Slot *(" + slot +").*",cli_out).group(1)  #key of dict, serial of slot
  dict_of_slots[slot_no] = re.search(".*Slot *(" + slot +").*",cli_out).group(0)  #value of dict info about slot
  return dict_of_slots

def slot_list(cli):
  """
  Returns list of all slots in machine

  Keyword arguments:
  cli -- type of used HP cli
  """
  cli_out = subprocess.run([cli,"ctrl","all","show"],stdout=subprocess.PIPE)
  cli_out = cli_out.stdout.decode("utf-8")
  dict_of_slots = {}
  for line in cli_out.split("\n"):  #every slot with serial no.
    if line.isspace() or line:  #ommit whitespaces
      dict_of_slots[(re.search(".*Slot *(\d+).*",line).group(1))] = re.search(".*Slot *(\d+).*",line).group(0)  #slot is key in dict, whole line is its value with serial no.
  return dict_of_slots

def slot_pd_temp(cli,slot,slot_details,temp):
  """
  Returns physical drives, which reached threshold tmeperature value

  Keyword arguments:
  cli -- type of used HP cli
  slot -- specified HP array slot
  slot_details -- slot serial with detail info
  temp -- own specified temperature
  """
  cli_out = subprocess.run([cli,"ctrl","slot="+slot,"pd","all","show","status"],stdout=subprocess.PIPE)  #list physical devices in specific slot
  cli_out = cli_out.stdout.decode("utf-8")
  first_run = True  #in case more failed physical drives in one slot and printing only one head with serial no. of slot
  ret_str = ""
  for line in cli_out.split("\n"):  #scan PD in slot line by line
    try: 
      if (line.isspace() or line):  #ommit whitespaces
        pd_id = re.search("(.*)physicaldrive +(.*?) +\(.*",line).group(2)
        pd_details = subprocess.run([cli,"ctrl","slot="+slot,"pd",pd_id,"show","detail"],stdout=subprocess.PIPE)  #get details of failed PD
        pd_details = pd_details.stdout.decode("utf-8")
        current_temp = int(re.search("Current Temperature \(C\): (\d+)",pd_details).group(1))
        if temp == None:
          max_temp =  int(re.search("Maximum Temperature \(C\): (\d+)",pd_details).group(1))
        else:
          max_temp = int(temp)
        if current_temp >= max_temp:
          ret_str = ret_str + "THRESHOLD TEMPERATURE: " + str(max_temp) + "\n"
          ret_str = ret_str + "CURRENT TEMPERATURE: " + str(current_temp) + "\n"
          if first_run:
            ret_str = ret_str + slot_details + "\n"  #append type of slot and serial no. 
            first_run = False
          ret_str = ret_str + re.search("physicaldrive[\S\s]*\n+",pd_details).group(0)  #filter only drive info
    except:
      continue
  return ret_str

def main():
  version = 1.0
  parser = argparse.ArgumentParser(prog="disk_temp_hp.py", description="Monitoring HP array disk temperature", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument("-v","--version",action="version", version="%(prog)s"+" "+str(version))
  parser.add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
  disks = parser.add_mutually_exclusive_group(required=True)
  disks.add_argument("-s","--slot",help="defines one slot to be monitored",action="store",type=str)
  disks.add_argument("-a","--allslots",help="defines all slots connected to machine",action="store_true")
  parser.add_argument("-c","--cli",help="defines installed cli command which monitors arrays",default="hpacucli",choices=["hpacucli","hpssacli","ssacli"])
  parser.add_argument("-t","--temp",help="ignore manufacturer set disk max temp, use this specified",action="store",type=int)
  parser.add_argument("-e","--execute",help="run specified script after threshold value or error found",action="store",type=str)
  args = parser.parse_args()
  
  if args.slot:  #one slot was specified
    try:
      slot_info = slot_serial_no(args.cli,args.slot)
      pd_status = slot_pd_temp(args.cli,args.slot,slot_info[args.slot],args.temp)
      ret_str = print_output(pd_status,args.importance,args.execute)
    except AttributeError:
      print("Defined slot " + args.slot + " does not exist")
      sys.exit(1)
  elif args.allslots:  #scan all available slots
    pd_status = ""
    dict_of_slots = slot_list(args.cli)  #store all slots with serial numbers
    for slot in dict_of_slots:  #scan slot one by one
      pd_status = pd_status + slot_pd_temp(args.cli,slot,dict_of_slots[slot],args.temp)  #failed physical drives with more details
    ret_str = print_output(pd_status,args.importance,args.execute)
  print(ret_str)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print(e)
