#!/usr/bin/env python3.8
import os, sys, time

import daemon
import subprocess

log_file = os.path.abspath(sys.argv[1])
with open(log_file, 'w') as f:
    f.write("")

with daemon.DaemonContext():
    cmd = subprocess.Popen(["dbus-monitor --session \"type='signal',interface='org.gnome.ScreenSaver'\""],
            shell=True, stdout=subprocess.PIPE)

    prepare = False
    should_write = False
    log_string = ""
    while True:
        time.sleep(0.1)
#        with open(log_file, 'a') as f:
#            f.write("========\n")
        try:
            line = cmd.stdout.readline()
            line = line.decode("utf-8")
            print(line)

            if "path=/org/gnome/ScreenSaver; interface=org.gnome.ScreenSaver; member=ActiveChanged" in line:
                prepare = True
                print(" - set prepare")
                continue

            if prepare and "boolean true" in line:
                log_string = "Locked\n"
                should_write = True
            elif prepare and "boolean false" in line:
                log_string = "Unlocked\n"
                should_write = True
            else:
                should_write = False
            prepare = False

            if should_write:
                with open(log_file, 'w') as f:
                    f.write(log_string)
                print(f" - wrote {log_string}")

        except Exception:
            import traceback
            with open(log_file+".err", 'a') as f:
                traceback.print_exc(None, f);

