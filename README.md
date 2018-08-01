# crscripts

Scripts for making work on Chromium and Chromium OS easier.

Typical workflow:

`crsetupchromium # setup a Chromium repository and build it once`

`crrun # run a locally built version of Chromium`

`crrunsandbox # run the Chromium OS version of Chromium (including window manager, etc.) in a sandbox`

(Make some changes to the code.)

`crtest # run the set of tests given as argument, for instance base_unittests`

`crupload # Upload your changes to the server`

(Some time passes.)

`crupdate # update your existing checkout

`creditfilesfromcl CL_NUMBER gedit # open all files opened by the given CL in the given editor (or in $EDITOR)`

Can also be just:

`creditfilesfromcl`

which will open the same editor and CL as last time.

`crpatch # patch an existing CL (simpler and quicker than git cl patch)`
