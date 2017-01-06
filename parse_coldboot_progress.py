#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, time, string, commands, json, re, argparse

class p_node:
    def __init__(self, name, filterkey=None, rank=2, flag=None):
        self.name = name
        self.seconds = -1.0
        self.filterkey = filterkey
        self.rank = rank
        self.flag = flag
        self.proc = None
        self.phase = None

    def aptime_set(self, timestamp, timebase):
        #print("timestamp:" + timestamp + ", timebase:" + timebase)
        timestamps = timestamp.split(':')
        self.seconds = int(timestamps[0])*3600 + int(timestamps[1])*60 + float(timestamps[2])
        if not timebase == '':
            timebase = timebase.split(':')
            self.seconds = self.seconds - (int(timebase[0])*3600 + int(timebase[1])*60 + float(timebase[2]))

    def ktime_set(self, timestamp):
        self.seconds = float(timestamp.strip())

    def phase_purify(self, phase):
        if self.phase is not None:
            self.phase = phase.replace(',', '-').strip()

class bootpgs_parser:
    def __init__(self, needDump, inputFile):
        self.nodeList = []
        self.outputDir = ""
        self.dmesgFile = "dmesg.log"
        self.logcatFile = "logcat.log"
        self.needDump = needDump
        self.inputFile = inputFile
        self.outputFile = "boot_progress.csv"
        self.service_parser = service_parser(self.nodeList)

    def initStages(self):
        with open('coldboot_progress.json', 'r') as f:
            data = json.load(f)
        for i in data["coldboot"]["stage"]:
            # print(i["name"], i["filter"], i["rank"])
            self.nodeList.append(p_node(i["name"], i["filter"], i["rank"]))

    def getLogs(self):
        if not self.needDump:
            return
        print("[1/4] Dump boot logs ...")
        logDir = "logs/"
        if os.path.exists(logDir) == False:
            os.makedirs(logDir)
        currentTime = time.strftime('%Y-%m-%d_%H:%M:%S')
        self.outputDir = logDir+currentTime+"/"
        if os.path.exists(self.outputDir) == False:
            os.makedirs(self.outputDir)
    
        dmesgCommand = "adb shell dmesg > " + self.outputDir + self.dmesgFile
        logcatCommand = "adb logcat -v time -b all -d > " + self.outputDir + self.logcatFile
        os.system(dmesgCommand)
        os.system(logcatCommand)
        self.service_parser.dumpInitrc(self.outputDir)

    def parseDmesg(self):
        print("[2/4] Parse dmesg log ...")
        #initcall_begin = r"calling  (\w+)\+0x(\w+)/0x(\w+) (\[(\w+)\])? @ (\d+)"
        initcall_begin = r"calling  (\w+)\+0x(\w+)/0x(\w+)"
        #initcall_end = r"initcall (\w+)+0x(\w+)/0x(\w+) (\[(\w+)\])? returned (\d+) after (\d+) usecs"
        initcall_end = r"initcall (\w+)\+0x(\w+)/0x(\w+)"
        if self.inputFile is not None:
            inputParam = self.inputFile.split(',')[0].strip()
            if inputParam is not '':
                self.dmesgFile = inputParam
        else:
            self.dmesgFile = self.outputDir + self.dmesgFile
        # print("<============ open dmesg file: " + self.dmesgFile)
        if not os.path.exists(self.dmesgFile):
            print("[ERROR] dmesg: " + self.dmesgFile + "not existed!")
            return
        with open(self.dmesgFile) as f:
            lines = f.readlines()
        for l in lines:
            begin_obj = re.search(initcall_begin, l)
            if begin_obj:
                begin_node = p_node(begin_obj.group(1))
                begin_node.flag = 'KB'
                begin_node.ktime_set(l.split()[1].rstrip(']'))
                self.nodeList.append(begin_node)
            end_obj = re.search(initcall_end, l)
            if end_obj:
                end_node = p_node(end_obj.group(1))
                end_node.flag = 'KE'
                end_node.ktime_set(l.split()[1].rstrip(']'))
                self.nodeList.append(end_node)

    def parseLogcat(self):
        timebase = ''
        print("[3/4] Parse logcat log ...")
        if self.inputFile is not None:
            inputParam = self.inputFile.split(',')[1].strip()
            if inputParam is not '':
                self.logcatFile = inputParam
        else:
            self.logcatFile = self.outputDir + self.logcatFile
        if not os.path.exists(self.logcatFile):
            print("[ERROR] logcat: " + self.logcatFile + "not existed!")
            return
        with open(self.logcatFile) as f:
            lines = f.readlines()
        for l in lines:
            if l.find('Linux version') != -1:
                timebase = l.split()[1]
                continue
            for node in self.nodeList:
                if node.filterkey is not None and re.search(node.filterkey, l):
                    #print("<====== filterkey: " + node.filterkey)
                    timestamp = l.split()[1]
                    node.aptime_set(timestamp, timebase)
                    node.proc = l.split()[2].split('/')[1].strip()
                    break
            self.service_parser.parseSvcLine(l, timebase)
        
    def parseLogs(self):
        self.parseDmesg()
        self.parseLogcat() 
        if self.needDump:
            self.service_parser.parseInitrc(self.outputDir)
        self.service_parser.highlightSvc()
        self.nodeList.sort(key=lambda x:x.seconds)

    def renameOutput(self, outputFile):
        os.rename(self.outputFile, outputFile)

    def getNameWithFlag(self, node):
        if node.flag is not None:
            stage_name = '[' + node.flag + '] ' + node.name
        else:
            stage_name = node.name
        return stage_name

    def showResult(self):
        out = open(self.outputFile, 'w')
        print("[4/4] Generate boot progress report ...")
        out.write('name1, name2, next, seconds, duration, process, trigger' + '\n')
        for node in self.nodeList:
            if node.seconds == -1.0:
                continue
            nextIdx = (self.nodeList.index(node)+1)%len(self.nodeList)
            if nextIdx == 0:
                nextIdx = self.nodeList.index(node)
            duration = self.nodeList[nextIdx].seconds - node.seconds
            out.write((node.rank-1)*',' + (3-node.rank)*('%-s,'%(self.getNameWithFlag(node))) + '%-s,'%(self.getNameWithFlag(self.nodeList[nextIdx])) + '%.7f,'%(node.seconds) + '%.7f'%(duration))
            if node.proc is not None:
                out.write(',%s'%(node.proc))
            if node.phase is not None:
                out.write(',%s'%(node.phase))
            out.write('\n')

        out.close()

class service_parser:
    def __init__(self, nodeList):
        self.svcList = []
        self.highSvcList = []
        self.initrcList = []
        self.nodeList = nodeList

# adb shell getprop | grep ro.product.device
#[ro.product.device]: [bxtp_abl]
    def getProductDevice(self):
        product_device_cmd = 'getprop | grep ro.product.device'
        product_device = ''
        status, output = commands.getstatusoutput('adb shell ' + product_device_cmd)
        #lines = output.splitlines()
        if output.find('ro.product.device') != -1:
            product_device = output.split()[1].lstrip('[').rstrip(']')
        return product_device

    def dumpInitrc(self, outputDir):
        with open('coldboot_progress.json', 'r') as f:
            data = json.load(f)
        for i in data["coldboot"]["initrc"]:
            self.initrcList.append(i["file"])
        self.initrcList.append('init.'+self.getProductDevice()+'.rc')
       
        for i in self.initrcList:
            os.system('adb pull  ' + i + ' ./' + outputDir)

    def parseInitrc(self, outputDir):
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
                            j.phase_purify(on_phase)
                            #print("... calling phase_set(" + on_phase + ")")

    def parseSvcLine(self, line, timebase):
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
        proc = line.split()[2].split('/')[1].rstrip('(').strip()
        svcnode = p_node(svc_name)
        svcnode.flag = flag
        svcnode.proc = proc
        svcnode.aptime_set(timestamp, timebase)
        self.svcList.append(svcnode)
        self.nodeList.append(svcnode)

    def highlightSvc(self):
        with open('coldboot_progress.json', 'r') as f:
            data = json.load(f)
        for i in data["coldboot"]["high_svc"]:
            self.highSvcList.append(i["svc"])
        for j in self.nodeList:
            for svc in self.highSvcList:
                if svc == j.name:
                    j.rank = 1

def parse_coldboot_progress(needDump, inputFile):
    reload(sys)
    sys.setdefaultencoding('utf8')
    if needDump:
        os.system("adb root")
        time.sleep(2)
    parser = bootpgs_parser(needDump, inputFile)
    parser.initStages()
    parser.getLogs()
    parser.parseLogs()
    parser.showResult()
    print("[DONE] parse_coldboot_progress")
    return parser


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-d', '--direct', action='store_true', help='direct connect DUT and dump')
    group.add_argument('-l', '--logfile', action='store', dest='logfile', help='dump from logs: dmesg,logcat')
    
    parser.add_argument('-o', '--output', action='store', dest='output', help='output csv file assignment')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s v1.3')

    args = parser.parse_args()
    boot_parser = None
    if args.direct:
        #print("__tingjiec__ args.direct")
        boot_parser = parse_coldboot_progress(True, None)
    elif args.logfile:
        #print("__tingjiec__ args.logfile, logfile:" + args.logfile)
        boot_parser = parse_coldboot_progress(False, args.logfile)
    if args.output:
        #print("__tingjiec__ args.output, output:" + args.output)
        if boot_parser is not None:
            boot_parser.renameOutput(args.output)

