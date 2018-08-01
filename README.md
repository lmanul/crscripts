# crscripts

Scripts for making work on Chromium and Chromium OS easier.

Typical workflow:

`crsetupchromium # setup a Chromium repository and build it once`

`crrun # run a locally built version of Chromium`

`crrunsandbox # run the Chromium OS version of Chromium (including window manager, etc.) in a sandbox`

(Make some changes to the code. Some time passes.)

`crtest # run the set of tests given as argument, for instance base_unittests`

`crupload # Upload your changes to the server`

`crupdate # update your existing checkout

`creditfilesfromcl # open all files opened by the given CL in the given editor (or in $EDITOR)`

`crpatch # patch an existing CL (simpler and quicker than git cl patch)`
