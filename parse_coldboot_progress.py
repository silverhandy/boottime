#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, time, string, commands, json, re, argparse

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
        self.proc = proc.strip()

class svc_node(p_node):
    def __init__(self, name, proc, flag):
        p_node.__init__(self, name)
        self.proc = proc
        self.phase = ''
        self.rank = 2
        self.flag = flag

    def phase_set(self, phase):
        self.phase = phase.replace(',', '-').strip()

class bootpgs_parser:
    def __init__(self, needDump, inputFile):
        self.nodeList = []
        self.outputDir = ""
        self.dmesgFile = "dmesg.log"
        self.logcatFile = "logcat.log"
        self.needDump = needDump
        self.inputFile = inputFile
        self.outputFile = "bootprogress.csv"
        self.service_parser = service_parser()

    def initStages(self):
        with open('coldboot_progress.json', 'r') as f:
            data = json.load(f)
        for i in data["coldboot"]["stage"]:
            # print(i["name"], i["filter"], i["rank"])
            self.nodeList.append(stage_node(i["name"], i["filter"], i["rank"]))

    def getLogs(self):
        if not self.needDump:
            return

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

    def parseDmesg(self):
        print("... Parse dmesg log ...")
        if self.inputFile is not None:
            inputParam = self.inputFile.split(',')[0].strip()
            if inputParam is not '':
                self.dmesgFile = inputParam
        else:
            self.dmesgFile = self.outputDir + self.dmesgFile
        with open(self.dmesgFile) as f:
            lines = f.readlines()
        for l in lines:
            pass


    def parseLogcat(self):
        timebase = ''
        print("... Parse logcat log ...")
        if self.inputFile is not None:
            inputParam = self.inputFile.split(',')[1].strip()
            if inputParam is not '':
                self.logcatFile = inputParam
        else:
            self.logcatFile = self.outputDir + self.logcatFile
        with open(self.logcatFile) as f:
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
        
        if self.needDump:
            self.service_parser.parse_initrc(self.outputDir)

        self.nodeList.sort(key=lambda x:x.seconds)

    def renameOutput(self, outputFile):
        os.rename(self.outputFile, outputFile)

    def showResult(self):
        delta = 0.0
        out = open(self.outputFile, 'w')
        print("<=========== show boot_progress result")
        out.write("<========== show boot_progress result\n")
        print('name1, name2, seconds, delta, proc, phase')
        out.write('name1, name2, seconds, delta, proc, phase' + '\n')
        for node in self.nodeList:
            if node.seconds == -1.0:
                continue
            delta = self.nodeList[(self.nodeList.index(node)+1)%len(self.nodeList)].seconds - node.seconds
            if delta < 0: delta = 0
            if hasattr(node, "flag"):
                print((node.rank-1)*',' + (3-node.rank)*('['+node.flag+'] '+'%-s,'%(node.name)) + '%s,'%(str(node.seconds)) + '%s,'%(str(delta)) + '%s,'%(node.proc) + '%s'%(node.phase))
                out.write((node.rank-1)*',' + (3-node.rank)*('['+node.flag+'] '+'%-s,'%(node.name)) + '%s,'%(str(node.seconds)) + '%s,'%(str(delta)) + '%s,'%(node.proc) + '%s'%(node.phase) + '\n')
            else:
                print((node.rank-1)*',' + (3-node.rank)*('%-s,'%(node.name)) + '%s,'%(str(node.seconds)) + '%s,'%(str(delta)) + '%s'%(node.proc))
                out.write((node.rank-1)*',' + (3-node.rank)*('%-s,'%(node.name)) + '%s,'%(str(node.seconds)) + '%s,'%(str(delta)) + '%s'%(node.proc)  + '\n')

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
        proc = line.split()[2].split('/')[1].rstrip('(').strip()
        svcnode = svc_node(svc_name, proc, flag)
        svcnode.time_set(timestamp, timebase)
        self.svcList.append(svcnode)
        stageList.append(svcnode)

def parse_coldboot_progress(needDump, inputFile):
    reload(sys)
    sys.setdefaultencoding('utf8')
    if needDump:
        os.system("adb root")
        time.sleep(2)
    parser = bootpgs_parser(needDump, inputFile)
    parser.initStages()
    parser.getLogs()
    parser.parseDmesg()
    parser.parseLogcat()
    parser.showResult()
    return parser


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-d', '--direct', action='store_true', help='direct connect DUT and dump')
    group.add_argument('-l', '--logfile', action='store', dest='logfile', help='dump from logs: dmesg,logcat')
    
    parser.add_argument('-o', '--output', action='store', dest='output', help='output csv file assignment')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s v1.2')

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

