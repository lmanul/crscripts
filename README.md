# crscripts

Scripts for making work on Chromium and Chromium OS easier.

Typical workflow:

* `crsetupchromium`: setup a Chromium repository and build it once.
* `crrun`: run a locally built version of Chromium.
* `crrunsandbox`: run the Chromium OS version of Chromium (including window manager, etc.)
  in a sandbox.
* `crupdate`: update your existing checkout.
* `creditfilesfromcl`: opens all files opened by the given CL in the given 
  editor (or in `$EDITOR`).
* `crpatch`: patch an existing CL (simpler and quicker than `git cl patch`).
* `crtest`: run the set of tests given as argument, for instance `base_unittests`.
