#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, time, string, commands, json

class p_node:
    def __init__(self, name):
        self.name = name
        self.seconds = 0.0
        self.rank = 0

    def time_set(self, timestamp, timebase):
        timestamps = timestamp.split(':')
        self.seconds = int(timestamps[0])*3600 + int(timestamps[1])*60 + float(timestamps[2])
        timebase = timebase.split(':')
        self.seconds = self.seconds - (int(timebase[0])*3600 + int(timebase[1])*60 + float(timebase[2]))

class stage_node(p_node):
    def __init__(self, name, filterkey, rank):
        p_node.__init__(self, name)
        self.filterkey = filterkey
        self.rank = rank

class svc_node(p_node):
    def __init__(self, name):
        p_node.__init__(self, name)
        self.phase = ''
        self.rank = 2

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

    def initStages(self):
        with open('coldboot_progress.json', 'r') as f:
            data = json.load(f)
        for i in data["stage"]:
            #print(i["name"], i["filter"], i["rank"])
            self.nodeList.append(stage_node(i["name"], i["filter"], i["rank"]))

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
        timebase = ''
        print("... Parse logcat log ...")
        with open(self.outputDir+self.logcatFile) as f:
            lines = f.readlines()
        for l in lines:
            if l.find('Linux version') != -1:
                timebase = l.split()[1]
                continue
            for node in self.nodeList:
                if hasattr(node, "filterkey") and l.find(node.filterkey) != -1:
                    print("find ... " + node.filterkey)
                    timestamp = l.split()[1]
                    node.time_set(timestamp, timebase)
                    break

            self.initrc_parser.parse_service_line(l, timebase, self.nodeList)
        self.initrc_parser.parse_initrc(self.outputDir)

        self.nodeList.sort(key=lambda x:x.seconds)

    def showResult(self):
        out = open(self.outputDir + self.resultFile,'a')
        print("\n... show boot_progress result ...")
        out.write("\n... show boot_progress result ...\n")
        print("---------------------")
        out.write("---------------------\n")
        for node in self.nodeList:
            print((node.rank-1)*'\t' + '%-20s,'%(node.name) + (5-node.rank)*'\t' + '%5s'%(str(node.seconds)))
            out.write((node.rank-1)*'\t' + '%-20s,'%(node.name) + (5-node.rank)*'\t' + '%5s'%(str(node.seconds)) + '\n')
        out.close()
        self.initrc_parser.showResult(self.outputDir + self.resultFile)

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
        self.initrcList.append('init.debug-charging.rc')
        self.initrcList.append('init.diag.rc')
        self.initrcList.append('init.lmdump.rc')
        self.initrcList.append('init.telephony-config.rc')
       
        for i in self.initrcList:
            os.system('adb pull  ' + i + ' ./' + outputDir)

    def parse_initrc(self, outputDir):
        on_phase = ''
        on_svc = ''
        for i in self.initrcList:
            #print("#### open file:" + './' + outputDir + i)
            if not os.path.exists('./' + outputDir + i):
                continue
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

    def parse_service_line(self, line, timebase, stageList):
        if line.find(self.filter_svc) != -1:
            timestamp = line.split()[1]
            svc_name = line.split(self.filter_svc)[1].split('\'...')[0].lstrip(' \'')
            svcnode = svc_node("service "+svc_name)
            svcnode.time_set(timestamp, timebase)
            self.svcList.append(svcnode)
            stageList.append(svcnode)

    def showResult(self, resultFile):
        out = open(resultFile,'a')
        print("\n... show service_start result ...")
        out.write("\n... show service_start result ...\n")
        print("-------------------")
        out.write("-------------------\n")
        for node in self.svcList:
            # print(node.name + ",\t" + node.phase + ",\t" + str(node.seconds))
            print('%-30s,'%(node.name) + 3*'\t' + '%5s,'%(str(node.seconds)) + 2*'\t' + '%10s'%(node.phase))
            out.write('%-30s,'%(node.name) + 3*'\t' + '%5s,'%(str(node.seconds)) + 2*'\t' + '%10s'%(node.phase) + '\n')
        out.close()

if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf8')
    os.system("adb root")
    time.sleep(2)
    parser = bootpgs_parser()
    parser.initStages()
    parser.getLogs()
    parser.parseLogs()
    parser.showResult()

