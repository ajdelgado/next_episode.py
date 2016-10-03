#!/usr/bin/env python
# -*- coding: utf-8 -*-
########################################################################
##
## next_episode_tp.py
## Antonio J. Delgado 2016 antonio@susurrando.com
##
## Description: Find the last downloaded episodes and find the next.
## Usage: Create the folder in the PATH variable, inside create a folder
## for each TV show (replace spaces with dots to improve the search),
## and the script will search for the downloaded episodes and download
## the next one using Transmission.
########################################################################
import sys,os,time,re,urllib2,string,tempfile, gzip
import psutil

PATH="/home/ficheros/videos/series/"
#PATHTORRENTS="/home/ficheros/torrents/"
DEBUG=0
VERSION=0.1
if 'http_proxy' in os.environ.keys():
	PROXY=os.environ['http_proxy']
else:
	PROXY=""
TRANSMISSIONUSER="admin"
TRANSMISSIONPASS=""
TRANSMISSIONSERVER="localhost"
TRANSMISSIONPORT=9091
if 'http_proxy' in os.environ.keys():
	TRANSMISSIONPROXY=os.environ['http_proxy']
else:
	TRANSMISSIONPROXY=""
USER_AGENT="next_episodes.py/v%s" % (VERSION)
LOGFILE="%s/log/next_episodes.log" % os.environ['HOME']
EXCEPTIONS=list()
URLBASE="http://torrentproject.se/?hl=en&num=20&start=0&filter=&safe=off&orderby=latest&s="
def Message(TEXT,NIVEL=0):
	global DEBUG,LOGFILE
	if DEBUG >= NIVEL:
		print TEXT
	LOGPATH=os.path.dirname(LOGFILE)
	if not os.path.exists(LOGPATH):
		if DEBUG>0:
			print "Creating folder for log file '%s'" % LOGPATH
		os.mkdir(LOGPATH,0700)
	LOGF=open(LOGFILE,"a")
	LOGF.write("%s\n" % TEXT)
	LOGF.close()

def CheckIfRunning():
	Message("Checking if this task is already running...")
	try:
		processes=psutil.get_pid_list()
	except:
		processes=psutil.pids()
	for process in processes:
		if process != os.getpid():
			try:
				ps=psutil.Process(process)
				try:
					cmdline=ps.cmdline
					try:
						len_cmdline=len(ps.cmdline)
					except:
						len_cmdline=len(ps.cmdline())
						cmdline=ps.cmdline()
					if len_cmdline>1:
						if cmdline[1] == sys.argv[0]:
							Message("Already running process %s '%s'" % (process,cmdline))
							sys.exit(1)
				except psutil.AccessDenied:
					Message("I can't read information for process %s" % process)
			except psutil.NoSuchProcess:
				Nothing=0

def Usage():
	global LOGFILE
	print "-u | --user=<USER>							User name for Transmission remote. Optional."
	print "-p | --password=<PASSWORD>					Password for Transmission remote. Optional."
	print "-s | --server=<SERVER>						Server for Transmission remote. Default: localhost."
	print "-P | --port=<PORT>							Port for Transmission remote. Default: 9091."
	print "-x | --proxy=<PROXY>							Proxy to use for HTTP requests (excluding transmission communications). If not indicated the system variable http_proxy will be used."
	print "-a | --user-agent=<USER-AGENT-STRING>		User-agent string to use for HTTP requests (excluding transmission communications). If not indicated the system variable http_proxy will be used."
	print "-l | --logfile=<LOG FILE>					Log file to record debug information. Default: %s" % LOGFILE
	print "-c | --configfile=<CONFIG FILE>				Config file with the parameters to use."
	print "-e | --exception=<TV Show folder to ignore>	Config file with the parameters to use."
	print "-t | --transmission-proxy=<PROXY URL>		Proxy URL to be used by Transmission. Default is the environmental variable http_proxy."
	print "-d | --debug									Verbose output, repeat it to increase verbosity."
	print "-h | --help									Show this help."
	print ""
	print "Config file syntax"
	print " The config file use a basic parameter=value syntax. The parameters are the same that you can use in the command line: user,password,server,port,proxy,debug and logfile."
def GetArguments():
	import getopt
	global DEBUG,TRANSMISSIONUSER,TRANSMISSIONPASS,TRANSMISSIONPORT,TRANSMISSIONSERVER,PROXY,USER_AGENT,LOGFILE,EXCEPTIONS,TRANSMISSIONPROXY
	try:
		opts, args = getopt.getopt(sys.argv[1:], "du:p:s:P:x:a:l:c:e:t:h", ["debug", "user=", "password=", "server=", "port=", "proxy=", "user-agent=", "logfile=", "configfile=", "exception=","transmission-proxy=","help"])
	except getopt.GetoptError as err:
		print str(err)
		Usage()
		sys.exit(65)
	for o, a in opts:
		if o in ("-h", "--help"):
			Usage()
			sys.exit(0)
		elif o in ("-a", "--user-agent"):
			Message("User agent for HTTP requests will be %s." % a)
			USER_AGENT=a
		elif o in ("-l", "--logfile"):
			Message("Log will be saved in '%s'." % a)
			LOGFILE=a
		elif o in ("-u", "--user"):
			Message("User name for Transmission remote will be %s." % a)
			TRANSMISSIONUSER=a
		elif o in ("-p", "--password"):
			Message("Password for Transmission set.")
			TRANSMISSIONPASS=a
		elif o in ("-s", "--server"):
			Message("Transmission server will be %s." % a)
			TRANSMISSIONSERVER=a
		elif o in ("-P", "--port"):
			Message("Port for Transmission will be %s." % a)
			TRANSMISSIONPORT=a
		elif o in ("-x", "--proxy"):
			Message("Proxy for HTTP requests will be '%s'." % a)
			PROXY=a
		elif o in ("-c", "--configfile"):
			Message("Reading config gile '%s'." % a)
			LoadConfigFile(a)
		elif o in ("-t", "--transmission-proxy"):
			Message("Using '%s' as proxy URL to communicate with transmission." % a)
			TRANSMISSIONPROXY=a
		elif o in ("-e", "--exception"):
			Message("Adding exception to TV show '%s'." % a)
			EXCEPTIONS.append(a)
		elif o in ("-d", "--debug"):
			DEBUG=DEBUG + 1
			Message("Increased debug level to %s" % DEBUG)
		elif o=="":
			Message("Remove empty lines from config file")
		else:
			assert False, "Unhandled option %s" % o
def LoadConfigFile(FILE):
	global DEBUG,TRANSMISSIONUSER,TRANSMISSIONPASS,TRANSMISSIONPORT,TRANSMISSIONSERVER,PROXY,USER_AGENT,LOGFILE,EXCEPTIONS,TRANSMISSIONPROXY
	if not os.path.exists(FILE):
		Message("The config file '%s' doesn't exist" % FILE)
		Usage()
		sys.exit(65)
	else:
		configfile=open(FILE,"r")
		content=configfile.readlines()
		configfile.close()
		for line in content:
			lcomment=line.split("#")
			line=lcomment[0]
			pair=line.split("=")
			o=pair[0].strip().lower()
			if len(pair)>1:
				a=pair[1].strip()
			else:
				a=""
			if o in ("a", "useragent"):
				Message("User agent for HTTP requests will be %s." % a)
				USER_AGENT=a
			elif o in ("l", "logfile"):
				Message("Log will be saved in '%s'." % a)
				LOGFILE=a
			elif o in ("u", "user"):
				Message("User name for Transmission remote will be %s." % a)
				TRANSMISSIONUSER=a
			elif o in ("p", "password"):
				Message("Password for Transmission set.")
				TRANSMISSIONPASS=a
			elif o in ("s", "server"):
				Message("Transmission server will be %s." % a)
				TRANSMISSIONSERVER=a
			elif o in ("P", "port"):
				Message("Port for Transmission will be %s." % a)
				TRANSMISSIONPORT=a
			elif o in ("x", "proxy"):
				Message("Proxy for HTTP requests will be '%s'." % a)
				PROXY=a
			elif o in ("t", "transmission-proxy"):
				Message("Using '%s' as proxy URL to communicate with transmission." % a)
				TRANSMISSIONPROXY=a
			elif o in ("e", "exception"):
				Message("Adding exception to TV show '%s'." % a)
				EXCEPTIONS.append(a)
			elif o in ("d", "debug"):
				DEBUG=DEBUG + 1
				Message("Increased debug level to %s" % DEBUG)
			else:
				assert False, "Unhandled option %s" % o				
def RecursiveFileListing(PATH):
	if os.path.exists(PATH) == False:
		return False
	FILES=[]
	for RAIZ, CARPETAS, SFILES in os.walk(PATH,followlinks=True):
		for FILE in SFILES:
			FILES.append(os.path.join(RAIZ,FILE))
	#for RAIZ, CARPETAS, SFILES in os.walk("/home/ficheros/incoming",followlinks=True):
		#for FILE in SFILES:
			#FILES.append(os.path.join(RAIZ,FILE))
	return FILES
def CheckTranmission():
	import transmissionrpc
	global TRANSMISSIONUSER,TRANSMISSIONPASS,TRANSMISSIONSERVER,TRANSMISSIONPORT,TRANSMISSIONPROXY
	result=True
	if 'http_proxy' in os.environ.keys():
		current_proxy=os.environ['http_proxy']
	else:
		current_proxy=""
	os.environ['http_proxy']=TRANSMISSIONPROXY
	try:
		conn=transmissionrpc.Client(TRANSMISSIONSERVER, user=TRANSMISSIONUSER,password=TRANSMISSIONPASS,port=TRANSMISSIONPORT)
		try:
			ltorrents=conn.get_torrents()
		except:
			Message("Error getting list of torrents from Transmission")
			result=False
	except transmissionrpc.error.TransmissionError,e:
		Message("Error connecting to Transmission. User=%s, Password=***, Server=%s, Port=%s. %s" % (TRANSMISSIONUSER,TRANSMISSIONSERVER,TRANSMISSIONPORT,e))
		result=False
	Message("Successfully connected to transmission (obtained %s torrents)" % len(ltorrents))
	os.environ['http_proxy']=current_proxy
	return result
def AddMagnet(URL):
	import transmissionrpc
	global TRANSMISSIONUSER,TRANSMISSIONPASS,TRANSMISSIONSERVER,TRANSMISSIONPORT,TRANSMISSIONPROXY
	if 'http_proxy' in os.environ.keys():
		current_proxy=os.environ['http_proxy']
	else:
		current_proxy=""
	os.environ['http_proxy']=TRANSMISSIONPROXY
	try:
		conn=transmissionrpc.Client(TRANSMISSIONSERVER, user=TRANSMISSIONUSER,password=TRANSMISSIONPASS,port=TRANSMISSIONPORT)
		try:
			conn.add_torrent(URL)
		except:
			Message("Error adding torrent URL '%s' to Transmission" % URL)
	except transmissionrpc.error.TransmissionError,e:
		Message("Error adding torrent to Transmission. User=%s, Password=***, Server=%s, Port=%s. %s" % (TRANSMISSIONUSER,TRANSMISSIONSERVER,TRANSMISSIONPORT,e))
	os.environ['http_proxy']=current_proxy
def LastShowEpisode(SHOW):
	global PATH
	FILES=RecursiveFileListing("%s/%s" % (PATH,SHOW))
	LASTEPISODE=0
	for FILE in FILES:
		Message("III Checking file '%s'" % FILE,2)
		EPISODE=0
		m=re.match(r".*[Ss](?P<SEASON>[0-9]{1,2})[Ee](?P<EPISODE>[0-9]{1,2}).*",FILE)
		if m != None:
			RESULT=m.groupdict()
			EPISODE=int(RESULT['SEASON'])*100+int(RESULT['EPISODE'])
		else:
			m=re.match(r".*(?P<SEASON>[0-9]{1,2})x(?P<EPISODE>[0-9]{1,2}).*",FILE)
			if m != None:
				RESULT=m.groupdict()
				EPISODE=int(RESULT['SEASON'])*100+int(RESULT['EPISODE'])
			else:
				EPISODE=0
		if EPISODE>LASTEPISODE:
			LASTEPISODE=EPISODE
	if LASTEPISODE == 0:
		Message("III There is no downloaded episodes of the show '%s' or it was the '%s'" % (SHOW,LASTEPISODE))
	else:
		Message("III Last episode downloaded from show '%s' was '%s'" % (SHOW,LASTEPISODE))
	return LASTEPISODE
def SearchNextEpisode(SHOW,LASTEPISODECOMPLETE):
	LASTSEASON="%s" % (int(round(LASTEPISODECOMPLETE/100)))
	LASTSEASON=string.rjust(LASTSEASON,2,"0")
	Message("Last season = %s" % LASTSEASON,3)
	LASTEPISODE="%s" % int(LASTEPISODECOMPLETE-(int(LASTSEASON)*100))
	LASTEPISODE=string.rjust(LASTEPISODE,2,"0")
	Message("Last episode = %s" % LASTEPISODE,3)
	NEXTEPISODE=int(LASTEPISODE)+1
	NEXTEPISODE="S%sE%s" % (LASTSEASON,string.rjust("%s" % NEXTEPISODE,2,"0"))
	
	NEXTSEASON=string.rjust("%s" % (int(LASTSEASON)+1),2,"0")
	ANOTHERNEXTEPISODE="S%sE01" % NEXTSEASON
	Message("III Possible next episodes are '%s' and '%s'" % (NEXTEPISODE,ANOTHERNEXTEPISODE))
	URL="%s%s.%s" % (URLBASE,SHOW,NEXTEPISODE)
	CONTENT=GetURLContent(URL)
	NEXTREALEPISODE="0000"
	if CONTENT == False or "did not match any documents" in CONTENT:
		URL="%s%s.%s" % (URLBASE,SHOW,ANOTHERNEXTEPISODE)
		CONTENT=GetURLContent(URL)
		if CONTENT == False or "did not match any documents" in CONTENT:
			Message("WWW I couldn't find any episode available for '%s'" % SHOW)
		else:
			NEXTREALEPISODE=ANOTHERNEXTEPISODE
	else:
		NEXTREALEPISODE=NEXTEPISODE
	Message("III Found next episode '%s'" % NEXTREALEPISODE)
	return CONTENT,NEXTREALEPISODE
def timeout(func, args=(), kwargs={}, timeout_duration=1, default=None):
    import threading
    class InterruptableThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = None
        def run(self):
            try:
                self.result = func(*args, **kwargs)
            except:
                self.result = default
    it = InterruptableThread()
    it.start()
    it.join(timeout_duration)
    if it.isAlive():
        return default
    else:
        return it.result
def SaveTmpFile(content):
	global TMPFILE
	import tempfile
	TMPFILEO=tempfile.mkstemp(prefix='tmp_', dir="/tmp/")
	TMPFILENAME=TMPFILEO[1]
	Message("Saving temporarily to '%s' (don't forget to remove it)" % (TMPFILENAME))
	TMPFILE=open(TMPFILENAME,"w")
	try:
		TMPFILE.write(content)
	finally:
		TMPFILE.close()
	return TMPFILENAME
def GetURLContent(URL):
	import requests
	content=requests.get(URL).text
	return content
def EpisodioDecimal2Par(EPISODEDECIMAL):
	DECIMALEPISODENUMBER=int(EPISODEDECIMAL.replace("S","").replace("E",""))
	SEASON=int(DECIMALEPISODENUMBER)/100
	EPISODE=DECIMALEPISODENUMBER-(SEASON*100)
	return string.rjust("%s" % SEASON,2,"0"),string.rjust("%s" % EPISODE,2,"0")
def ExpandGZIP(GZIPDATA):
	if not GZIPDATA:
		return False
	TMPFILEHS,TMPFILE=tempfile.mkstemp(".gz")
	Message("Expanding data from file '%s'" % TMPFILE)
	TMPFILEH=open(TMPFILE,"w")
	TMPFILEH.write(GZIPDATA)
	TMPFILEH.close()
	UNZIPFILE= gzip.open(TMPFILE, 'rb')
	CONTENT = UNZIPFILE.read()
	UNZIPFILE.close()
	return CONTENT
def Checks():
	global PATH, PATHTORRENTS
	if not os.path.exists(PATH):
		Message("Path '%s' doens't exist, exiting." % PATH,1)
		return False
	#if not os.path.exists(PATHTORRENTS):
		#Message("La ruta '%s' no existe, saliendo." % PATHTORRENTS,1)
		#return False
	if not CheckTranmission():
		return False
	return True
CheckIfRunning()
GetArguments()
os.environ['http_proxy']=PROXY
if not Checks():
	sys.exit(1)
SHOWS=os.listdir(PATH)
for SHOW in SHOWS:
	EXCEPTION=False
	for ESHOW in EXCEPTIONS:
		if ESHOW==SHOW:
			EXCEPTION=True
	if not EXCEPTION:
		Message("IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII")
		Message("III Checking TV show %s" % SHOW)
		LASTEPISODE=LastShowEpisode(SHOW)
		CONTENT,NEXTEPISODE=SearchNextEpisode(SHOW,LASTEPISODE)
		if CONTENT == False or CONTENT.find("did not match any documents")>-1:
			Message("III I couldn't find the next episode after '%s'" % LASTEPISODE,2)
		else:
			#CONTENT=ExpandGZIP(CONTENT)
			if len(CONTENT)==0:
				Message("EEE No data obtained in the search")
			else:
				TMPFILEHS,TMPFILE=tempfile.mkstemp()
				TMPFILEH=open(TMPFILE,"w")
				TMPFILEH.write(CONTENT)
				TMPFILEH.close()
				Message("III Saved as '%s'" % TMPFILE)
				#m=re.search(r'href="http([][a-zA-Z0-9?=/\.]+\.torrent[][a-zA-Z0-9?=/\.]+)"',CONTENT)
				#m=re.search(r'href="(http.*\.torrent[][a-zA-Z0-9?=\.]+)',CONTENT)
				m=re.search(r'href="(magnet:\?[0-9a-zA-Z\&\=\+\%\:\.]*)"',CONTENT)
				if m != None:
					TORRENTURL="%s" % m.groups(0)[0]
					Message("III Found magnet URL '%s'" % TORRENTURL)
					#CONTENTTORRENT=GetURLContent(TORRENTURL)
					FNEXTEPISODE="S%sE%s" % (EpisodioDecimal2Par(NEXTEPISODE))
					#NOMBRETORRENT="%s/%s.%s.torrent" % (PATHTORRENTS,SHOW,FNEXTEPISODE)
					#if os.path.exists(NOMBRETORRENT):
						#try:
							#os.remove(NOMBRETORRENT)
						#except IOError,e:
							#Message("EEE Error de entrada y salida eliminando torrent existente '%s'. %s" % (NOMBRETORRENT,e))
						#except:
							#Message("EEE Error eliminando torrent existente '%s'" % NOMBRETORRENT)
					#try:
						#TORRENT=open("%s" % NOMBRETORRENT,"w")
						#TORRENT.write(CONTENTTORRENT)
						#TORRENT.close()
						#os.chmod("%s" % NOMBRETORRENT,0777)
						#Message("III Guardado torrent '%s'" % NOMBRETORRENT)
					#except IOError,e:
						#Message("EEE Error de entrada y salida guardando torrent '%s'. %s" % (NOMBRETORRENT,e))
					#except:
						#Message("EEE Error guardando torrent '%s'" % NOMBRETORRENT)
					AddMagnet(TORRENTURL)
				else:
					Message("EEE I couldn't find any torrent in the search")