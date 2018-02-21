import os
import re
import socket
import subprocess
import sys

def system_silent(command, options):
  if options.verbose:
    print("Running '" + command + "'...")
  if not options.dryrun:
    os.system(command + ("" if options.verbose else " > /dev/null 2>&1"))

# Returns whether a process containing the given name is running.
def is_process_running(process):
  s = subprocess.Popen(["ps", "axw"],stdout=subprocess.PIPE)
  for x in s.stdout:
    if re.search(process, x.decode()):
      return True
  return False

def is_online():
  host = "8.8.8.8"
  timeout = 2
  port = 53
  try:
    socket.setdefaulttimeout(timeout)
    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
    return True
  except Exception as ex:
    return False

def is_google_machine():
  # Testing for "corp.google.com" in the hostname doesn't always work.
  hostname = socket.gethostname()
  if "corp.google.com" in hostname:
    return True
  if os.path.exists("/usr/local/google/"):
    return True
  return False
