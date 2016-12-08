#!/usr/bin/env python

import os, sys, time, string, commands

class p_node:
    def __init__(self, name):
        self.name = name
        self.seconds = 0.0

    def time_set(self, timestamp):
        timestamps = timestamp.split(':')
        self.seconds = int(timestamps[0])*3600 + int(timestamps[1])*60 + float(timestamps[2])

class stage_node(p_node):
    def __init__(self, name, filterkey):
        p_node.__init__(self, name)
        self.filterkey = filterkey

class svc_node(p_node):
    def __init__(self, name):
        p_node.__init__(self, name)
        self.phase = ''

    def phase_set(self, phase):
        self.phase = phase

class bootpgs_parser:
    def __init__(self):
        self.nodeList = []
        self.outputDir = ""
        self.dmesgFile = "dmesg.log"
        self.logcatFile = "logcat.log"
        self.resultFile = "out.result"
        self.initrc_parser = initrc_parser()

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
        print("... Get init.*.rc ...")
        self.initrc_parser.dump_initrc(self.outputDir)
        
    def parseLogs(self):
        print("... Parse logcat log ...")
        with open(self.outputDir+self.logcatFile) as f:
            lines = f.readlines()
        for l in lines:
            for node in self.nodeList:
                if l.find(node.filterkey) != -1:
                    #print("find ... " + node.filterkey)
                    timestamp = l.split()[1]
                    node.time_set(timestamp)
                    break
            self.initrc_parser.parse_service_line(l)
        self.initrc_parser.parse_initrc(self.outputDir)

    def showResult(self):
        print("... show boot_progress result ...")
        print("---------------------")
        for node in self.nodeList:
            print(node.name + ",\t\t" + str(node.seconds))
        self.initrc_parser.showResult()

class initrc_parser:
    def __init__(self):
        self.filter_svc = "Starting service"
        self.svcList = []
        self.initrcList = []

# adb shell getprop | grep ro.product.device
#[ro.product.device]: [bxtp_abl]
    def get_product_device(self):
        product_device_cmd = 'getprop | grep ro.product.device'
        product_device = ''
        status, output = commands.getstatusoutput('adb shell ' + product_device_cmd)
        #lines = output.splitlines()
        if output.find('ro.product.device') != -1:
            product_device = output.split()[1].lstrip('[').rstrip(']')
        return product_device

    def dump_initrc(self, outputDir):
        self.initrcList.append('init.rc')
        self.initrcList.append('init.' + self.get_product_device() + '.rc')
        self.initrcList.append('init.coredump.rc')
        self.initrcList.append('init.crashlogd.rc')
        self.initrcList.append('init.dvc_desc.rc')
        self.initrcList.append('init.environ.rc')
        self.initrcList.append('init.kernel.rc')
        self.initrcList.append('init.log-watch.rc')
        self.initrcList.append('init.logs.rc')
        self.initrcList.append('init.npk.rc')
        self.initrcList.append('init.trace.rc')
        self.initrcList.append('init.usb.configfs.rc')
        self.initrcList.append('init.usb.rc')
        self.initrcList.append('init.zygote32.rc')
        self.initrcList.append('init.zygote64_32.rc')
       
        for i in self.initrcList:
            os.system('adb pull  ' + i + ' ./' + outputDir)

    def parse_initrc(self, outputDir):
        on_phase = ''
        on_svc = ''
        for i in self.initrcList:
            #print("#### open file:" + './' + outputDir + i)
            with open('./' + outputDir + i) as f:
                lines = f.readlines()
            for l in lines:
                if l.find('on ') == 0:
                    on_phase = l.split()[1]
                    #print("... on_phase:" + on_phase)
                elif l.find('start ') == 4:
                    on_svc = l.split()[1]
                    #print("... on_svc:" + on_svc)
                    for j in self.svcList:
                        if j.name == on_svc:
                            j.phase_set(on_phase)
                            #print("... calling phase_set(" + on_phase + ")")

    def parse_service_line(self, line):
        if line.find(self.filter_svc) != -1:
            timestamp = line.split()[1]
            svc_name = line.split(self.filter_svc)[1].split('\'...')[0].lstrip(' \'')
            svcnode = svc_node(svc_name)
            svcnode.time_set(timestamp)
            self.svcList.append(svcnode)

    def showResult(self):
        print("... show service_start result ...")
        print("-------------------")
        for node in self.svcList:
            print(node.name + ",\t" + node.phase + ",\t" + str(node.seconds))

if __name__ == '__main__':
    parser = bootpgs_parser()
    parser.initStageFramework()
    parser.getLogs()
    parser.parseLogs()
    parser.showResult()

