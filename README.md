# crscripts

Scripts for making work on Chromium and Chromium OS easier.

Start by cloning this directory:

`git clone https://github.com/lmanul/crscripts.git`

Then, it's probably best to add the new cloned directory to your $PATH. After 
that, typical workflow:

`crsetupchromium # setup a Chromium repository and build it once`

`crbuild # build Chromium`

![crbuild Screenshot](https://github.com/lmanul/crscripts/blob/master/screenshots/crbuild.gif)

`crrunsandbox # run the Chromium OS version of Chromium (including window manager, etc.) in a sandbox`

`crrun # run a locally built version of Chromium`

(Make some changes to the code.)

`crtest ash_unittests # run the set of tests given as argument`

`crupload # Upload your changes to the server`

(Some time passes.)

`crupdate # update your existing checkout`

`creditfiles gedit # open all files opened in the current CL with the 
given editor (or $EDITOR, or whichever editor was used last time)`

Can also be:

`creditfilesfromcl CL_NUMBER`

where the CL number is explicit.

`crpatch # patch an existing CL (simpler and quicker than git cl patch)`
