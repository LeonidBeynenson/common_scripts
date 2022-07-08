#This script is a modified version of the Active Window Logger script by Scott Sherrill-Mix
#The original version of the script may be found here:
# http://scott.sherrillmix.com/blog/programmer/active-window-logger/

import wx
from win32gui import GetWindowText, GetForegroundWindow
from time import strftime, localtime, time, sleep
from ctypes import windll, Structure, c_uint, sizeof, byref
import os #, time
#from datetime import datetime
import psutil
import sys

# This var is used for a rude hack with global vars, sorry
USERNAME=os.environ["USERNAME"]

def is_daemon_run():
    procs = [p for p in psutil.process_iter() if 'python' in p.name()]
    procs = [p for p in procs if p.pid != os.getpid()]
    cur_file_name = os.path.basename(__file__)
    for p in procs:
        cmdline = p.cmdline()
        if len(cmdline) > 1 and os.path.basename(cmdline[1]) == cur_file_name:
            print(f'Found existing daemon process pid={p.pid}')
            return True
    return False


class TaskBarApp(wx.Frame):
    def __init__(self, parent, id, title, username="lbeynens"):
        wx.Frame.__init__(self, parent, -1, title, size = (1, 1), style=wx.FRAME_NO_TASKBAR|wx.NO_FULL_REPAINT_ON_RESIZE)

        self.TIMESTEP = 10000 #ms
        self.WAS_ACTIVE = True
        self.TIME_OF_SCREENSAVER_START = 0

        self.LOG_FILE_FOLDER = f"C:/cygwin64/home/{username}/worklog/"
        self.LOG_FILE_PATH = os.path.join(self.LOG_FILE_FOLDER, "winlog_" + self.CurDate())

        self.ICONS_FOLDER = f"C:/cygwin64/home/{username}/bin/"
        self.LOGON_ICON_PATH = os.path.join(self.ICONS_FOLDER, 'logon.ico')
        self.LOGOFF_ICON_PATH = os.path.join(self.ICONS_FOLDER, 'logoff.ico')

        self.COMPUTER_PREFIX = "P"

        print("Will log into", self.LOG_FILE_PATH)

        self.ICON_STATE = 1
        self.ID_ICON_TIMER=wx.NewId()
#        self.tbicon = wx.TaskBarIcon()
#        icon = wx.Icon(self.LOGON_ICON_PATH, wx.BITMAP_TYPE_ICO)
#        self.tbicon.SetIcon(icon, 'Logging')
#        self.tbicon.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarLeftDClick)
#        self.tbicon.Bind(wx.EVT_TASKBAR_RIGHT_UP, self.OnTaskBarRightClick)
        self.Bind(wx.EVT_TIMER, self.MainStep, id=self.ID_ICON_TIMER)
        self.SetIconTimer()
        self.Show(True)
        self.lastInputInfo = self.LASTINPUTINFO()
        self.lastInputInfo.cbSize = sizeof(self.lastInputInfo)
        if self.DoesLogFileExist():
            print(f"Log file {self.LOG_FILE_PATH} exists, add rest line")
            self.Write("\nrest ????????\n\n")
        self.WriteLog("__LOGGERSTART__", 0)

    def OnTaskBarLeftDClick(self, evt):
        if self.ICON_STATE == 0:
            self.WriteLog("__LOGGERUNPAUSE__", 0)
            self.StartIconTimer()
            icon = wx.Icon(self.LOGON_ICON_PATH, wx.BITMAP_TYPE_ICO)
            self.tbicon.SetIcon(icon, 'Logging')
            self.ICON_STATE = 1
        else:
            self.StopIconTimer()
            self.WriteLog("__LOGGERPAUSE__", 0)
            icon = wx.Icon(self.LOGOFF_ICON_PATH, wx.BITMAP_TYPE_ICO)
            self.tbicon.SetIcon(icon, 'Not Logging')
            self.ICON_STATE = 0

    def OnTaskBarRightClick(self, evt):
        self.StopIconTimer()
        self.WriteLog( "__LOGGERSTOP__", 0)
        self.tbicon.Destroy()
        self.Close(True)
        wx.GetApp().ProcessIdle()
        print("End of work")

    def SetIconTimer(self):
        self.icontimer = wx.Timer(self, self.ID_ICON_TIMER)
        self.icontimer.Start(self.TIMESTEP)

    def StartIconTimer(self):
        try:
            self.icontimer.Start(self.TIMESTEP)
        except:
            pass

    def StopIconTimer(self):
        try:
            self.icontimer.Stop()
        except:
            pass

    def MainStep(self, evt):
        try:
            windll.user32.GetLastInputInfo(byref(self.lastInputInfo))
            idleDelta = float(windll.kernel32.GetTickCount() - self.lastInputInfo.dwTime) / 1000
            window_text = GetWindowText(GetForegroundWindow())

            is_active = (len(window_text) > 0) and (window_text != "Windows Default Lock Screen") and (idleDelta < 60)

            if is_active:
                if not self.WAS_ACTIVE:
                    dt_sleep = time() - self.TIME_OF_SCREENSAVER_START
                    if dt_sleep > 60:
                        log_line_from_screensaver_work = "rest {} min on {} ??????????????????????????????".format(int(dt_sleep/60), self.COMPUTER_PREFIX)
                        self.Write("\n" + log_line_from_screensaver_work + "\n\n")
#                    else: #very small rest
#                        self.Write("\n") #is it required?

                self.WriteLog(window_text, str(idleDelta) )
                self.TIME_OF_SCREENSAVER_START = 0

            else: #is_active == False
                if self.WAS_ACTIVE:
                    self.TIME_OF_SCREENSAVER_START = time()

            self.WAS_ACTIVE = is_active
        except Exception:
            import traceback
            #err_file = os.path.join(log_file_dir, "winlog_" + cur_date + ".err")
            #with open(err_file, 'a') as f:
            traceback.print_exc(None, None);

    def WriteLog(self, text, idle_time):
        log_line = '%s\t%s\t%-100s\t%f sec\n' % (self.Now(), self.COMPUTER_PREFIX, text, float(idle_time))
        self.Write(log_line)

    def DoesLogFileExist(self):
        return os.path.isfile(self.LOG_FILE_PATH)

    def Write(self, log_line):
        f=open(self.LOG_FILE_PATH, 'a', encoding="utf8", errors='ignore')
        f.write (log_line)
        f.close()

    def Now(self):
        return strftime("%Y-%m-%d_%H-%M-%S", localtime())

    def CurDate(self):
        timestamp_str = self.Now()
        cur_date = timestamp_str.split("_")[0]
        return cur_date


    class LASTINPUTINFO(Structure):
        _fields_ = [("cbSize", c_uint),("dwTime", c_uint)]

class MyApp(wx.App):
    def OnInit(self):
        self.username=USERNAME
        print(f"self.username={self.username}")
        frame = TaskBarApp(None, -1, ' ', self.username)
        frame.Center(wx.BOTH)
        frame.Show(False)
        return True

def main():
    if is_daemon_run():
        print('The daemon is already run -- exiting')
        sleep(2)
        return 0
    app = MyApp(0)
    app.MainLoop()

if __name__ == '__main__':
    main()
