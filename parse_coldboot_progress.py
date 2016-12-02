#!/usr/bin/env python

import os, sys, time, string

import matplotlib as pl
from matplotlib.ticker import MultipleLocator, FuncFormatter
import numpy as np

class stage_node:
    def __init__(self, name, filterkey):
        self.name = name
        self.filterkey = filterkey
        self.seconds = 0.0

    def time_set(self, seconds):
        self.seconds = seconds

class stage_parser:
    def __init__(self):
        self.nodeList = []
        self.outputDir = ""
        self.dmesgFile = "dmesg.log"
        self.logcatFile = "logcat.log"
        self.resultFile = "out.result"

    def initStageFramework(self):
        self.nodeList.append(stage_node("init_start", "init started"))
        self.nodeList.append(stage_node("zygote_start", "START com.android.internal.os.ZygoteInit"))
        self.nodeList.append(stage_node("preload_start", "boot_progress_preload_start"))
        self.nodeList.append(stage_node("preload_end", "boot_progress_preload_end"))
        self.nodeList.append(stage_node("system_run", "boot_progress_system_run"))
        self.nodeList.append(stage_node("pms_system_scan_start", "boot_progress_pms_system_scan_start"))
        self.nodeList.append(stage_node("pms_data_scan_start", "boot_progress_pms_data_scan_start"))
        self.nodeList.append(stage_node("pms_scan_end", "boot_progress_pms_scan_end"))
        self.nodeList.append(stage_node("pms_ready", "boot_progress_pms_ready"))
        self.nodeList.append(stage_node("ams_ready", "boot_progress_ams_ready"))
        self.nodeList.append(stage_node("enable_screen", "boot_progress_enable_screen"))
        #self.nodeList.append(stage_node("display_launcher", "Displayed com.google.android.googlequicksearchbox/com.google.android.launcher.GEL"))
        self.nodeList.append(stage_node("bootanim_exit", "Service 'bootanim'"))

    def getLogs(self):
        logDir = "logs/"
        if os.path.exists(logDir) == False:
            os.makedirs(logDir)
        currentTime = time.strftime('%Y-%m-%d_%H:%M:%S')
        self.outputDir = logDir+currentTime+"/"
        if os.path.exists(self.outputDir) == False:
            os.makedirs(self.outputDir)
    
        dmesgCommand = "adb shell dmesg > " + self.outputDir + self.dmesgFile
        logcatCommand = "adb logcat -v time -b all -d > " + self.outputDir + self.logcatFile
        print("... Get dmesg log ...")
        os.system(dmesgCommand)
        print("... Get logcat log ...")
        os.system(logcatCommand)

    def parseLogs(self):
        print("... Parse logcat log ...")
        with open(self.outputDir+self.logcatFile) as f:
            lines = f.readlines()
        for l in lines:
            for node in self.nodeList:
                if l.find(node.filterkey) != -1:
                    #print("find ... " + node.filterkey)
                    timestamp = l.split()[1]
                    timestamps = timestamp.split(':')
                    seconds = int(timestamps[0])*3600 + int(timestamps[1])*60 + float(timestamps[2])
                    node.time_set(seconds)
                    break

    def showResult(self):
        print("... Show Result ...")
        print("---------------------")
        for node in self.nodeList:
            print(node.name + ":\t\t" + str(node.seconds))

if __name__ == '__main__':
    parser = stage_parser()
    parser.initStageFramework()
    parser.getLogs()
    parser.parseLogs()
    parser.showResult()

