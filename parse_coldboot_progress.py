#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, time, string, commands, json, re, getopt

class p_node:
    def __init__(self, name):
        self.name = name
        self.seconds = -1.0
        self.rank = 0
        self.proc = ''

    def time_set(self, timestamp, timebase):
        #print("timestamp:" + timestamp + ", timebase:" + timebase)
        timestamps = timestamp.split(':')
        self.seconds = int(timestamps[0])*3600 + int(timestamps[1])*60 + float(timestamps[2])
        if not timebase == '':
            timebase = timebase.split(':')
            self.seconds = self.seconds - (int(timebase[0])*3600 + int(timebase[1])*60 + float(timebase[2]))

class stage_node(p_node):
    def __init__(self, name, filterkey, rank):
        p_node.__init__(self, name)
        self.filterkey = filterkey
        self.rank = rank

    def proc_set(self, proc):
        self.proc = proc

class svc_node(p_node):
    def __init__(self, name, proc, flag):
        p_node.__init__(self, name)
        self.proc = proc
        self.phase = ''
        self.rank = 2
        self.flag = flag

    def phase_set(self, phase):
        phase = phase.replace(',', '-')
        self.phase = phase

class bootpgs_parser:
    def __init__(self):
        self.nodeList = []
        self.outputDir = ""
        self.dmesgFile = "dmesg.log"
        self.logcatFile = "logcat.log"
        self.resultFile = "bootprogress.csv"
        self.service_parser = service_parser()

    def initStages(self):
        with open('coldboot_progress.json', 'r') as f:
            data = json.load(f)
        for i in data["coldboot"]["stage"]:
            # print(i["name"], i["filter"], i["rank"])
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
        self.service_parser.dump_initrc(self.outputDir)
        
    def parseLogs(self, logs):
        timebase = ''
        print("... Parse logcat log ...")
        if logs is not None:
            logcatFile = logs
        else:
            logcatFile = self.outputDir + self.logcatFile
        with open(logcatFile) as f:
            lines = f.readlines()
        for l in lines:
            if l.find('Linux version') != -1:
                timebase = l.split()[1]
                continue
            for node in self.nodeList:
                if hasattr(node, "filterkey") and l.find(node.filterkey.encode('utf-8')) != -1:
                    # print("find ... " + node.filterkey)
                    timestamp = l.split()[1]
                    node.time_set(timestamp, timebase)
                    proc = l.split()[2].split('/')[1]
                    if proc == node.filterkey:
                        node.proc_set(proc)
                    break
            
            self.service_parser.parse_service_line(l, timebase, self.nodeList)
        
        if logs is None:
            self.service_parser.parse_initrc(self.outputDir)

        self.nodeList.sort(key=lambda x:x.seconds)

    def showResult(self, logs):
        delta = 0.0
        if logs is not None:
            outputFile = self.resultFile
        else:
            outputFile = self.outputDir + self.resultFile
        out = open(outputFile, 'w')
        print("\n<=========== show boot_progress result")
        out.write("\n<========== show boot_progress result\n")
        print('name_1, name_2, name_3, seconds, delta, proc, phase')
        out.write('name_1, name_2, name_3, seconds, delta, proc, phase' + '\n')
        for node in self.nodeList:
            if node.seconds == -1.0:
                continue
            delta = self.nodeList[(self.nodeList.index(node)+1)%len(self.nodeList)].seconds - node.seconds
            if delta < 0: delta = 0
            if hasattr(node, "flag"):
                print((node.rank-1)*'\t,' + '[' + node.flag + '] ' + '%-20s,'%(node.name) + (3-node.rank)*'\t,' + '%5s,'%(str(node.seconds)) + '%5s,'%(str(delta)) + '%10s,'%(node.proc) + '%10s'%(node.phase))
                out.write((node.rank-1)*'\t,' + '[' + node.flag + '] ' + '%-20s,'%(node.name) + (3-node.rank)*'\t,' + '%5s,'%(str(node.seconds)) + '%5s,'%(str(delta)) + '%10s,'%(node.proc) + '%10s'%(node.phase) + '\n')
            else:
                print((node.rank-1)*'\t,' + '%-20s,'%(node.name) + (3-node.rank)*'\t,' + '%5s,'%(str(node.seconds)) + '%5s,'%(str(delta)) + '%10s'%(node.proc))
                out.write((node.rank-1)*'\t,' + '%-20s,'%(node.name) + (3-node.rank)*'\t,' + '%5s,'%(str(node.seconds)) + '%5s,'%(str(delta)) + '%10s'%(node.proc)  + '\n')

        out.close()

class service_parser:
    def __init__(self):
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
        with open('coldboot_progress.json', 'r') as f:
            data = json.load(f)
        for i in data["coldboot"]["initrc"]:
            self.initrcList.append(i["file"])
        self.initrcList.append('init.'+self.get_product_device()+'.rc')
       
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
        flag = 'X'
        svc_name = ''
        if line.find(': Starting service ') != -1:
            flag = 'N'
            svc_name = line.split('service ')[1].split('\'...')[0].strip().strip('\'')
            #print("<---- N: svc_name: " + svc_name)
        elif line.find(': Starting ') != -1:
            flag = 'A'
            svc_name = line.split('Starting ')[1].split('...')[0].strip()
        elif line.find(': Start proc ') != -1:
            flag = 'P'
            svc_name = line.split('proc ')[1].split(' for')[0]
        else:
            return

        svc_name = svc_name.replace(',', '')
        timestamp = line.split()[1]
        proc = line.split()[2].split('/')[1].rstrip('(')
        svcnode = svc_node(svc_name, proc, flag)
        svcnode.time_set(timestamp, timebase)
        self.svcList.append(svcnode)
        stageList.append(svcnode)

def parse_coldboot_progress(mode, arg):
    reload(sys)
    sys.setdefaultencoding('utf8')
    os.system("adb root")
    time.sleep(2)
    parser = bootpgs_parser()
    parser.initStages()
    if mode == '-d':
        parser.getLogs()
    parser.parseLogs(arg)
    parser.showResult(arg)

if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:], "hf:d")
    for op, value in opts:
        if op == "-h":
            print("Usage: \nDirect connect DUT and parse: \n\tparse_coldboot_progress.py -d")
            print("Parse using existed logcat file: \n\tparse_coldboot_progress.py -f #logcatFile")
            sys.exit()
        elif op == "-f":
            path = value
            print("Get file {0}".format(path))
            parse_coldboot_progress('-f', path)
            sys.exit()
        elif op == "-d":
            parse_coldboot_progress('-d', None)
            sys.exit()

