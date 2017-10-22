#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Verson 1.3    2016/01/05   Compare方法はサイズとタイムスタンプ（Shallow）だけで判断しないよう修正
#

from Tkinter import *
from tkMessageBox import showinfo
from tkMessageBox import showwarning
from tkMessageBox import askquestion
import re
import filecmp
import sys
import time
import os
import codecs
import tarfile

versionTxt = "1.3"

window = Tk()
window.wm_withdraw()

def writeReport(fname, diffs):
	f = open(fname,"w")
	
	f.write(u"=== ファイル比較レポート ===\n".encode('utf-8'))
	f.write(u"ベースファイル：　".encode('utf-8')+os.path.basename(baseFile).encode('utf-8')+"\n\n")
	f.write(u"■　比較結果\n".encode('utf-8'))
	f.write(u"\n".encode('utf-8'))
	
	ngCnt = 0
	
	for diff in diffs:	
		txt = os.path.basename(diff[0]) + "\t"
		txt += diff[1]
		f.write(txt.encode('utf-8')+"\n")
		if diff[2] != None:
			ngCnt += 1

	if ngCnt>0:
		f.write(u"\n■　差分詳細".encode('utf-8')+"\n")
		for diff in diffs:
			if diff[2] != None:
				txt = u"・" + os.path.basename(diff[0]) + diff[1]
				txt += "\n" + diff[2]
				f.write(txt.encode('utf-8')+"\n")
			
	f.close()

# ファイルの差分を取ります
def getFilesDeepDiff(baseLines, testLines):
	diffs = []
	
	j = 0
	lastTitle = ""
	for i in range(0,len(baseLines)):
		if j>=len(testLines) or baseLines[i] != testLines[j]:
			#txt = "Line "+str(i+1)+"\n"
			baseProblemLine = os.path.basename(baseFile) + ": " + baseLines[i].rstrip() + "\n"
			if j<len(testLines):
				newJ = j+1
				
				found = False
				
				for xx in range(j, len(testLines)):
					if baseLines[i] == testLines[xx]:
						found = True
						newJ = xx
						break
				
				if found:
					for k in range(j,newJ):
						diffs.append("[ Added ] "+testLines[k].rstrip())
					j = newJ+1
					
					# Pack Added + Deleted into Modified when Possible
					# 可能な場合はAddedとDeletedを一つのModifiedに纏める
					if len(diffs)>1:
						prev = diffs[len(diffs)-2]
						mprev = re.match(r"^(\[ Deleted \] )([^=]+)=(.*)$", prev)
						if mprev:
							curr = diffs[len(diffs)-1]
							mcurr = re.match(r"^(\[ Added \] )([^=]+)=(.*)$", curr)
							if mcurr and mprev.group(2) == mcurr.group(2):
								diffs.pop()
								diffs.pop()
								diffs.append("[ Modified ] "+mprev.group(2)+"="+mprev.group(3)+u" → "+mcurr.group(3))
					
				else:
					diffs.append("[ Deleted ] "+baseLines[i].rstrip())
			else:
				diffs.append("[ Deleted ] "+baseLines[i].rstrip())
		else:
			j+=1

	if j<len(testLines):
		while j<len(testLines):
			diffs.append("[ Added ]"+testLines[j].rstrip())
			j += 1
		
	return diffs

# 共通のファイルを検索しまし
def findBaseFile(files):
	rets = []
	bestBase = "" 
	
	bases = dict()
	
	for baseTest in files:
		base = baseTest
		rest = list(set(files) - set(baseTest))
		ngCnt = 0
		for testFile in rest:
			if not filecmp.cmp(base, testFile, shallow=False):
				ngCnt += 1
		
		bases[baseTest] = ngCnt
		
		if ngCnt < len(files)/2:
			bestBase = baseTest
			break
			
	smaller = len(files)
	for base in bases.keys():
		if bases[base] < smaller:
			smaller = bases[base]
			bestBase = base
	
	filesList = files
	filesList.remove(bestBase)
	
	return [bestBase, filesList]
	
# フォルダーを指定した場合、ConfigDumpを探してみる
def findConfigDumps(files):
	newList = []
	
	for i in range(0,len(files)):
		item = files[i]
		if os.path.isdir(item):
			for cfgFile in os.listdir(item):
				if cfgFile.startswith("configdump_"):
					newList.append(os.path.join(item, cfgFile))
					break
					
	return newList

# Return:　ソートをかけたらファイルの行
def getSorted(file):
	f = codecs.open(file, "r", "utf-8")
	try:
		baseLines = f.readlines()
	except:
		f.close()
		f = codecs.open(file, "r", "sjis")
		try:
			baseLines = f.readlines()
		except:
			showwarning("ERROR",u"「"+os.path.basename(file)+u"」の文字コードは不明です。")
			exit()

	baseLines.sort()
	f.close()
	return baseLines
	
def getTarFilesConfigDump(files):
	newList = []
	for file in files:
		with tarfile.open(file) as tar:
			for tarinfo in tar.getmembers():
				if (tarinfo.name.endswith(".log") or tarinfo.name.endswith(".txt")) and "/configdump_" in tarinfo.name:
					dirName = os.path.dirname(file)
					tarElementName = os.path.basename(tarinfo.name)
					tarinfo.name = tarElementName
					tar.extract(tarinfo,dirName)	
					newList.append(os.path.join(dirName, tarElementName))
					break
	return newList
			
if len(sys.argv)<3:
	showwarning("FileCompareTool "+versionTxt,u"比較対象をドラッグ＆ドロップで指定してください。")
else:
	args = sys.argv[1:]
	args.sort()
	reportFileBasePath = os.path.dirname(args[0])

	origin = ""
	if args[0].endswith(".gz") or args[0].endswith(".tar"):
		cfgDumpFiles = getTarFilesConfigDump(args)
		origin = u"tarファイル"
	else:
		cfgDumpFiles = findConfigDumps(args)
		origin = u"フォルダー"
	
	if len(cfgDumpFiles) == len(args):
		questionTxt = origin+u"の中にありました下記ConfigDump("+str(len(cfgDumpFiles))+u"件)を比較しますか？\n\n"
		questionTxt += "\n".join([os.path.basename(c) for c in cfgDumpFiles])
		response = askquestion(u"ConfigDump比較",questionTxt,icon="question")
		if response == "yes":
			args = cfgDumpFiles
		else:
			showinfo("ERROR",u"ファイルを指定してください。")
			exit()
	
	baseCheck = findBaseFile(args)
	
	baseFile = baseCheck[0]
	filePaths = baseCheck[1]
	filePaths.sort()
	print filePaths
	
	result = []
	detailedResult = []
	ngCnt = 0
	for testFile in filePaths:
		baseFileName = os.path.basename(baseFile)
		txt = ""
		diffList = []
		detailedTxt = None

		if filecmp.cmp(baseFile, testFile, shallow=False):
			txt += "[OK]"
			#detailedResult.append([testFile,None])
		else:
			txt += "[NG]"
			
			sortedBaseLines = getSorted(baseFile)
			sortedTestLines = getSorted(testFile)
			
			if len(sortedBaseLines) == len(sortedTestLines) and set(sortedBaseLines) == set(sortedTestLines):
				txt += u" [ソート後OK]"
			else:
#				f = open("aaa.txt","w")
#				f.writelines("\n".join(sortedBaseLines))
#				f.close()
#				
#				f = open("bbb.txt","w")
#				f.writelines("\n".join(sortedTestLines))
#				f.close()
#				
				ngCnt += 1
				diffList = getFilesDeepDiff(sortedBaseLines, sortedTestLines)
				txt += " (x" + str(len(diffList))+")"
				detailedTxt = "\n".join(diffList)				

		detailedResult.append([testFile,txt,detailedTxt])
		
		result.append(os.path.basename(testFile) + " " + txt)

	reportFileName = "fileCompareReport_" + time.strftime("%Y%m%d_%H%M%S") + ".txt"
	reportFilePath = os.path.join(reportFileBasePath,reportFileName)
	
	#print detailedResult
	
	writeReport(reportFilePath, detailedResult)
	
	if ngCnt==0:
		showinfo(u"差分なし", u"全ファイル比較結果：　[ 差分なし ]\n\nbase: "+os.path.basename(baseFile)+"\n\n"+"\n".join(result))
	else:
		showwarning(u"差分あり", u"全ファイル比較結果：　[ 差分あり ]\n\nbase: "+os.path.basename(baseFile)+"\n\n"+"\n".join(result)+u"\n\n詳細については「"+reportFileName+u"」をご確認ください。")
		