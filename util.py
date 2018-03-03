import os
import re
import shlex
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
  # Testing for "corp.google.com" in the hostname isn't sufficient.
  hostname = socket.gethostname()
  if "corp.google.com" in hostname:
    return True
  lsb = subprocess.check_output(shlex.split("lsb_release -a")).decode()
  if "rodete" in lsb.lower():
    return True
  return False

def ensure_goma_installed():
  if not is_google_machine():
    # Installing Goma on a non-Google machine is not supported
    return
  goma_dir = os.path.join(os.path.expanduser("~"), "goma")
  if not os.path.exists(goma_dir):
    os.mkdir(goma_dir)
  if not os.path.exists(os.path.join(goma_dir, "compiler_proxy")):
    os.chdir(goma_dir)
    os.system("curl https://clients5.google.com/cxx-compiler-service/download/goma_ctl.py "
              "-o goma_ctl.py")
    os.system("python goma_ctl.py update")

def show_goma_warning():
  if not is_google_machine():
    # No Goma.
    return
  print("\n\n-- Warning: goma is not running, the build will be "
        "slower. Start goma with ~/goma/compiler_proxy --\n\n")
