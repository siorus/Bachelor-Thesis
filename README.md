# LINMON - Linux monitoring tool
## Overview

Linmon is GNU/Linux OS monitoring tool with set of monitoring scripts written in advance. It also supports adding 
own new and existing standalone scripts with very small effort of rewriting them. Linmon uses cron-like list for running
admin specified scripts with ability to group them together in notification messages. This monitoring tool is written in Python 3.5 and uses only built-in libraries. For administrator notification is used sendmail, which is usually part of most GNU/Linux distributions. Linmon was tested with Debian 10, RHEL 7, Centos 7, Ubuntu 14.04, Ubuntu 16.04 and Devuan. It
supports SysV, Upstart and SystemD init systems. Linmon notifies administrator only if abnormal value is found, when 
everything works fine no notification is issued.

## Dependencies
* Python 3.5 or higher
* Sendmail (installed and properly configured)
* Other dependencies of monitoring and syslog scripts (see first lines of each monitoring and syslog scripts) eg.:
```
#!/usr/bin/python3

#DEPENDENCIES: blkid,smartctl(smartmontools)
```

## Before installing
### 1. Python 3 shebang
Many GNU/Linux distributions uses different symlink to Python 3. 
RHEL based Linux distributions uses symlink with minor version number. Every script in this folder has default shebang: 
```bash
#!/usr/bin/python3
```
To change shebang in all python files, run this script:
```bash 
aux_scripts/python_shebang.sh "/path/to/python3.5orhigher"
```
### 2. SMTP Relay
SMTP MTA uses default port 25, which is usually blocked due to spam prevention. One of Linmon requirements is proper 
Sendmail configuration according to your ISP's firewall rules. For testing purpose script sendmail_relay_setup.py can be used. 
It uses email address limon.relay@gmail.com, secure connection through port 587 and installs all dependencies needed by 
sendmail secure connection.

To configure and install dependencies, run this script as root:

**_Script must be run as root, sudo would fail!_**

```bash
aux_scripts/sendmail_relay_setup.py
```

## Installation
---
**NOTE** 

Installation guide uses default installation path /opt/linmon for scripts and /etc/opt/linmon for script's config files.
All chapters below count on this paths.
---

### 1. Copy script or clone it from git

### 2. Change direcory
```bash
cd /path/to/directory/with/copiedscript
```

### 3. Edit configs/scripts\_to\_run.conf
This configuration file determines what will be executed. See example:

```
5 /opt/linmon/monitoring_scripts/user_cpu_usage.py root -t 10 -i error
5 /opt/linmon/monitoring_scripts/proc_ram_mon.py systemd -m 100
5 [DISKS] /opt/linmon/monitoring_scripts/disk_usage.py -l HDC -p 90 -i error
5 [DISKS] /opt/linmon/monitoring_scripts/disk_allow.py warning
12:00 /opt/linmon/monitoring_scripts/ram_free_mon.py -p 50 -i critical
```

When group is not set, implicit group [DEFAULT] will be used (first and second line), 
otherwise whatever group name can be written e.g [DISKS]. Email messages will be 
grouped according to delay/time and within delay/time by group if more 
than one is declared. So in this example two messages will be sent 
every 5 minutes, one with group "DEFAULT" and other with group "DISKS" 
in case abnormal value was found by script.

### 4. Install
Run installation with sudo or as root. At least one email must be used, more emails 
are separated by comma. If sendmail binary is in different path than /usr/sbin/sendmail,
specify it with argument -s.
 
For install, run as root or sudo:

```bash
./install.py -e your@email.com
```
Installation report will be sent to specified email address(es) and also will be stored
in /etc/opt/linmon/instalation\_report if configuration file path was not changed.

## Usage/Running 
After successful installation script will start as daemon in the background. There are high 
availability mechanisms which ensure Linmon is running. First of all SystemD,SysV or Upstart 
will start service again, when Linmon would stop running. Then if this mechanism fails,
there is cron job which will periodically (every 5 minutes) try to run linmon daemon. 
There is a mechanism which ensures only one running Linmon instance.

### 1. Update Linmon configs
During Linmon daemon operation you can modify some configuration options:

* email addresses for notification in /etc/opt/linmon/linmon_install.conf
* scripts and its time to run in /etc/opt/linmon/scripts_to_run.conf

Other options such as install directory or configuration files directory 
cannot be changed. To change them uninstall Linmon and install it again with
different installation or configuration paths.

For update, run as root or sudo:

```
/opt/linmon/linmon.py -u
```

### 2. Maintenance mode
Maintenance mode is useful while administrator is testing stuff on machines or doing maintenance which 
can cause lot of errors or allerts caused by detected abnormal values.
There are two options for running maintenance mode:

* Run for specific amount of minutes as root or sudo:
```bash
/opt/linmon/linmon.py -m -t 10
``` 
* Run until option "-m off" is typed as root or sudo:
```bash
/opt/linmon/linmon.py -m on
/opt/linmon/linmon.py -m off
```
During maintenance mode configuration options mentioned in previous point could 
be also changed. All modifications will be loaded after maintenance mode exits. 

## Uninstallation
For uninstalling run as root or sudo:
```bash
/opt/linmon/install.py -r
```

## How to use monitoring or syslog scripts
Usage of enclosed monitoring scripts are pretty straightforward due to its names
and arguments explanation. The only problem of undestanding could come from these
arguments:
* -e/--execute - this argument defines another script or linux binary which will 
be executed, when abnormal value/threshold of script will occure.
* -i/--importance - this argument defines importance tag in email messages in four 
levels (info/warning/error/critical). This importance is not hard-code because
an administrator can consider different priority for specific threshold or abnormal value.
When this argument is omitted, default priority _info_ will be used.

Syslog scripts are named according to service/program which they monitor. There is also
special script _rsyslog\_universal.py_ which can monitor whatever service/program
according to specified log file and regex, which matches wished line/error. 

## How to write new and edit existing monitoring scripts
Example or template with commented blocks, recommended and mandatory parts of script 
can be found in _example\_scripts/monitoring\_script\_example.py_ . To differentiate comments which explain 
how to write script, keyword _GUIDE_ is used at the begining of comment. You can inspire 
and get basic knowledge what should new script contain, few steps below show 
the same as example file.

### How script notifies Linmon about error or abnormal value
Monitoring script returns string with information when abnormal value is found, 
otherwise when script has not found any problem it does not print anything or 
prints empty string. Linmon take everything different than empty string or newline 
character as abnormal value was found. Format of notification string has only 
one obligation. First line is reserved for script importance, which can 
be _info/warning/error/critical_. When first line does not contain this string, 
implicit lowest priority _info_ is used.

### Information about script dependencies
It is recommended to add line with dependencies of script at the 
begining of script. Example can be seen in example_scripts/monitoring_script\_example.py

### Recommended script arguments
It is recommended to add argument with importance in argparse, if it is omitted, every script 
no matter what monitors or what values has been reached, the lowest importance _info_ will be used.
```
add_argument("-i","--importance",help="defines priority tag in notification message",default="info",choices=["info","warning","error","critical"])
``` 

### Where to place new scripts
When installation path is _/opt/linmon/_, new monitoring scripts should be placed in
_/opt/linmon/monitoring\_scripts/_. They can be also placed wherever admin decides,
but this path is recommended due to proper scripts uninstallation and easy traceability.


## How to write new and edit existing rsyslog scripts
Recommended script arguments and how script notifies Linmon about abnormal values are the same as in previous section. Example or template can be found in _example\_scripts/rsyslog\_script\_example.py_ . There are less comments what should script contains or not as many as in _example\_scripts/monitoring\_script\_example.py_, because 
same principle is valid for syslog scripts too. 
If an error occures or abnormal value is found, script will print text to stdout, otherwise
it will not print anything or newline. To differentiate comments which explain
how to write script, keyword _GUIDE_ is used at the begining of comment.

### Where to place new scripts
When installation path is _/opt/linmon_, new syslog scripts should be placed in
_/opt/linmon/rsyslog\_scripts/_. They can be also placed wherever admin decides,
but this path is recommended due to proper scripts uninstallation and easy traceability.