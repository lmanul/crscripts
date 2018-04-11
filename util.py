import os
import platform
import re
import shlex
import socket
import subprocess
import sys

from optparse import OptionParser

def get_options_and_args():
  parser = OptionParser()
  parser.add_option("-v", "--verbose", dest="verbose",
                    action="store_true",
                    help="show verbose messages")
  parser.add_option("-d", "--dryrun", dest="dryrun",
                    action="store_true",
                    help="dry run, log what we plan to do but don't actually do anything")

  return parser.parse_args()

def system_silent(command, options):
  return os.system(command +
    ("" if options.verbose else " > /dev/null 2>&1"))

def run(command, description, options):
  print(description)
  print("options is " + str(options))
  if options.verbose:
    print("Running '" + command + "'...")
  if options.dryrun:
    return 0
  else:
    return system_silent(command, options)

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
  if "rodete" in " ".join(platform.dist()):
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
    if not os.path.exists("compiler_proxy"):
      print("!!!!!\n\ngoma installation failed. Are there network/auth issues?\n\n!!!!!")

def show_goma_warning():
  if not is_google_machine():
    # No Goma.
    return
  print("\n\n-- Warning: goma is not running, the build will be "
        "slower. Start goma with ~/goma/compiler_proxy --\n"
        "In a future version, goma will be started automatically.\n\n")

def common_gn_args():
  return  [
    "enable_nacl = false",
    "remove_webcore_debug_symbols = true",
  ]

