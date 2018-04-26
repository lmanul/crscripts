import json
import os
import platform
import re
import shlex
import socket
import subprocess
import sys
import urllib.request

from optparse import OptionParser

SILENT = " > /dev/null 2>&1"

def get_chromium_src_dir():
  return os.path.join(os.path.expanduser("~"), "chromium", "src")

def get_options_and_args(parser=None):
  if not parser:
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
    ("" if options.verbose else SILENT))

def run(command, description, options):
  print(description)
  if options.verbose:
    print("Running '" + command + "'...")
  if options.dryrun:
    return 0
  else:
    if "ninja" in command and not options.verbose:
      child = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, universal_newlines=True)
      monitor_compile_progress(child)
      return child.wait()
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
        "slower. Start goma with ~/goma/compiler_proxy -- we suggest running "
        "that in a 'screen' session\n"
        "In a future version, goma will be started automatically.\n\n")

def common_gn_args():
  return  [
    "enable_nacl = false",
    # Not strictly true, but this unlocks more targets
    'target_os = "chromeos"',
    "remove_webcore_debug_symbols = true",
  ]

def monitor_compile_progress(child_process):
  print("")
  for stdout_line in iter(child_process.stdout.readline, ""):
    parsed = re.match(r"\[(.+)/(.+)\]", stdout_line)
    if parsed:
      progress_ten_thousandths = int(float(parsed.group(1)) / float(parsed.group(2)) * 10000)
      sys.stdout.write("\033[F") # Clear the previous print
      # Print in green
      print('\033[92m' + str(float(progress_ten_thousandths)/100.0) + "%" + '\033[0m')

def get_last_revision_number_for_cl(cl):
  url = "https://chromium-review.googlesource.com/changes/chromium%2Fsrc~" + str(cl) + "/detail"
  response = urllib.request.urlopen(url)
  data = response.read().decode("utf8")
  data = "\n".join(data.split("\n")[1:])
  parsed_data = json.loads(data)
  messages = parsed_data["messages"]
  latest_revision = 0
  for m in messages:
    if "_revision_number" in m:
      latest_revision = max(latest_revision, int(m["_revision_number"]))
  return latest_revision

def get_open_files_for_cl(cl):
  revision = int(get_last_revision_number_for_cl(cl))
  print("Last revision is " + str(revision))
  url = "https://chromium-review.googlesource.com/changes/chromium%2Fsrc~" + str(cl) + "/revisions/" + str(revision) + "/files"
  response = urllib.request.urlopen(url)
  data = response.read().decode("utf8")
  # For some reason, the first line contains spurious brackets
  data = "\n".join(data.split("\n")[1:])
  parsed_data = json.loads(data)
  return sorted([f for f in parsed_data if not "COMMIT_MSG" in f])

def read_config_from_file():
  PATH = os.path.expanduser("~") + "/.crrc"
  config = {}
  if os.path.exists(PATH):
    lines = open(PATH, "r").readlines()
    for l in lines:
      parts = l.split("=", 1)
      config[parts[0].strip()] = parts[1].strip()
    print(config)
  return config
  
def save_config(config):
  PATH = os.path.expanduser("~") + "/.crrc"
  if not os.path.exists(PATH):
    os.system("touch " + PATH)
  f = open(PATH, "w")
  buffer = ""
  for k in config:
    buffer += str(k) + "=" + str(config[k]) + "\n"
  f.write(buffer)
  f.close()
