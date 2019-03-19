import json
import multiprocessing
import ntpath
import os
import platform
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

from multiprocessing.dummy import Pool as ThreadPool
from optparse import OptionParser

SILENT = " > /dev/null 2>&1"
DEPOT_TOOLS = "depot_tools"

COLOR_FORMAT_PREF = '\033['
COLOR_FORMAT_SUFF_PERCENT = 'm{0:.2f}%\033[0m'
COLOR_FORMAT_SUFF_STRING = 'm{}\033[0m'
COLOR_FORMAT_RED_PERCENT    = COLOR_FORMAT_PREF + str(91) + COLOR_FORMAT_SUFF_PERCENT
COLOR_FORMAT_YELLOW_PERCENT = COLOR_FORMAT_PREF + str(33) + COLOR_FORMAT_SUFF_PERCENT
COLOR_FORMAT_GREEN_PERCENT  = COLOR_FORMAT_PREF + str(92) + COLOR_FORMAT_SUFF_PERCENT
COLOR_FORMAT_RED_STRING    = COLOR_FORMAT_PREF + str(91) + COLOR_FORMAT_SUFF_STRING
COLOR_FORMAT_YELLOW_STRING = COLOR_FORMAT_PREF + str(33) + COLOR_FORMAT_SUFF_STRING
COLOR_FORMAT_GREEN_STRING  = COLOR_FORMAT_PREF + str(92) + COLOR_FORMAT_SUFF_STRING

CPU_TO_JOB_MULTIPLIER = 5
CPU_TO_JOB_MULTIPLIER_GOMA = 10

def get_chromium_src_dir():
  return os.path.join(os.path.expanduser("~"), "chromium", "src")

def get_crscripts_dir():
  return os.path.dirname(os.path.realpath(__file__))

def get_goma_dir():
  return os.path.join(os.path.expanduser("~"), "goma")

def get_out_dir():
  return "out/Default"

def get_job_count():
  n_cpus = multiprocessing.cpu_count()
  multi = CPU_TO_JOB_MULTIPLIER_GOMA if is_goma_running() else CPU_TO_JOB_MULTIPLIER
  return n_cpus * multi

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

def get_current_branch():
  return subprocess.check_output(shlex.split(
    "git rev-parse --abbrev-ref HEAD")).decode().strip()

def get_branches():
  raw = subprocess.check_output(shlex.split("git branch")).decode().strip()
  chars_to_ignore = "* "
  return [b[len(chars_to_ignore):] for b in raw.split("\n")]

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

def is_goma_running():
  return is_process_running("compiler_proxy")

def get_goma_dir():
  return os.path.join(os.path.expanduser("~"), "goma")

def common_gn_args():
  args = [
    "enable_nacl = false",
    # Not strictly true, but this unlocks more targets
    'target_os = "chromeos"',
    "blink_symbol_level = 0",
    "is_debug = false",
    "is_component_build = true",
  ]
  if is_goma_running():
    print(COLOR_FORMAT_GREEN_STRING.format("Goma is running."))
    args.append("use_goma = true")
    args.append('goma_dir = "' + get_goma_dir() + '"')
  else:
    print(COLOR_FORMAT_YELLOW_STRING.format(
        "Goma is not running, the build may be slower."))
    args.append("use_goma = false")
  return args

def format_remaining_time(seconds):
  if seconds < 2:
    return "< 1s"
  m, s = divmod(seconds, 60)
  h, m = divmod(m, 60)
  output = ""
  if h > 0:
    output += str(h) + "h "
    if m < 10:
      output += "0"
  if m > 0:
    output += str(m) + "m "
    if s < 10:
      output += "0"
  output += str(s) + "s"
  return output

def display_progress(percent, what, eta_seconds):
  cols = shutil.get_terminal_size().columns
  sys.stdout.write("\033[F") # Clear the previous print
  if percent > 66.6:
    color_format = COLOR_FORMAT_GREEN_PERCENT
  elif percent > 33.3:
    color_format = COLOR_FORMAT_YELLOW_PERCENT
  else:
    color_format = COLOR_FORMAT_RED_PERCENT

  eta = " " + format_remaining_time(eta_seconds)

  sys.stdout.write(color_format.format(percent))
  filler_size = cols - len("xx.xx% ") - len(eta)
  if percent == 100:
    filler_size -= 1
  sys.stdout.write(" ")
  filler_done_size = int(percent / 100.0 * float(filler_size))
  filler_todo_size = filler_size - filler_done_size
  if filler_size > 0:
    sys.stdout.write("#" * filler_done_size)
    sys.stdout.write("." * filler_todo_size)
  sys.stdout.write(eta + "\n")
  sys.stdout.flush()

def monitor_compile_progress(child_process):
  print("")
  now_ms = int(time.time() * 1000)
  start_ms = now_ms
  last_ms = now_ms
  where_time_is_spent = {}
  for stdout_line in iter(child_process.stdout.readline, ""):
    parsed = re.match(r"^\[(.+)/(.+)\] [A-Z]+ (.*)$", stdout_line)
    if parsed:
      progress_ten_thousandths = int(float(parsed.group(1)) / float(parsed.group(2)) * 10000)
      what = ntpath.dirname(parsed.group(3))
      if what.startswith("obj/"):
        what = what[4:]
      if what.startswith("//"):
        what = what[2:]
      if ":" in what:
        what = what[:what.index(":")]
      path_parts = what.split("/")
      if len(path_parts) > 2:
        what = "/".join(path_parts[0:2])
      if what not in where_time_is_spent:
        where_time_is_spent[what] = 0
      percent = float(progress_ten_thousandths)/100.
      now_ms = int(time.time() * 1000)
      percent_per_second = percent / ((now_ms - start_ms) / 1000)
      if percent_per_second == 0:
        percent_per_second = 0.0001
      estimated_remaining_seconds = \
          int((100.0 - percent) / percent_per_second)
      display_progress(percent, what, estimated_remaining_seconds)
      spent = now_ms - last_ms
      where_time_is_spent[what] += spent
      last_ms = now_ms
  # We're done. Show that we're at 100%.
  display_progress(100, ".", 0)
  print("\n")
  flattened = []
  for key, value in where_time_is_spent.items():
    temp = [key, value]
    # Time spent on "." is not helpful.
    if key != ".":
      flattened.append(temp)
  flattened = sorted(flattened, reverse=True, key = lambda el : el[1])
  if len(flattened) > 0:
    for i in range(min(5, len(where_time_is_spent))):
      if len(flattened) > i:
        rounded_seconds = round(flattened[i][1] / 1000)
        if rounded_seconds > 0:
          print(str(rounded_seconds) + "s spent on " + flattened[i][0])

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
      if l.startswith("#"):
        continue
      parts = l.split("=", 1)
      config[parts[0].strip()] = parts[1].strip()
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

def get_issue_number():
  os.chdir(get_chromium_src_dir())
  output = subprocess.check_output(shlex.split("git cl issue")).decode().strip()
  if "Issue number" not in output:
    return None
  matches = re.match("Issue number: (\d+) .*", output)
  if matches:
    return matches.group(1)
  else:
    print("This branch isn't associated with any CL. " + \
        "Please run 'crupload' to create a CL.")

def find_all_test_targets(options):
  sys.stdout.write("Looking for test targets... ")
  sys.stdout.flush()
  os.chdir(get_chromium_src_dir())
  all_targets = subprocess.check_output(shlex.split(
      "gn ls  " + get_out_dir())).decode("utf-8").split("\n")
  # Remove the leading "//"
  all_test_targets = sorted([t[2:] for t in all_targets if t.endswith("tests")])
  sys.stdout.write("" + str(len(all_test_targets)) + " targets.")
  print("")
  if options.verbose:
    for t in all_test_targets:
      print("\t" + t)
  return all_test_targets

def ensure_depot_tools(options):
  if os.path.exists(DEPOT_TOOLS):
    print(DEPOT_TOOLS + " is already checked out, updating it...")
    os.chdir(DEPOT_TOOLS)
    os.system("git pull")
    os.chdir("..")
  else:
    print("Fetching " + DEPOT_TOOLS + "...")
    system_silent("git clone "
                  "https://chromium.googlesource.com/chromium/tools/depot_tools.git",
                  options)

  if not os.path.exists(DEPOT_TOOLS):
    print("I wasn't able to fetch the depot tools. Aborting. "
          "Potential fix: delete your ~/.gitcookies")
    return False
  return True
