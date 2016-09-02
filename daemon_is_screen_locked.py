#!/usr/bin/env python
import os, sys, time

import daemon
import subprocess

log_file = os.path.abspath(sys.argv[1])
with open(log_file, 'w') as f:
    f.write("")

with daemon.DaemonContext():
    cmd = subprocess.Popen(["gdbus monitor -e -d com.canonical.Unity -o /com/canonical/Unity/Session"],
            shell=True, stdout=subprocess.PIPE)

    while True:
        time.sleep(0.1)
#        with open(log_file, 'a') as f:
#            f.write("========\n")
        try:
            line = cmd.stdout.readline()
            print line

            if "com.canonical.Unity.Session.Unlocked" in line:
                log_string = "Unlocked\n"
            elif "com.canonical.Unity.Session.Locked" in line:
                log_string = "Locked\n"
            else:
                log_string = ""


            if log_string:
                with open(log_file, 'w') as f:
                    f.write(log_string)

        except Exception:
            import traceback
            with open(log_file+".err", 'a') as f:
                traceback.print_exc(None, f);

