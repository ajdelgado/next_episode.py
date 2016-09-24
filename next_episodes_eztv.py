#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
##
## next_episodes_2.py
## Antonio J. Delgado 2016
##
## Description: Locate next episodes of TV shows in a given path
##
########################################################################
##
## To-Do:
##
##
########################################################################
import sys,os,time,re,urllib2,string,tempfile, gzip
import psutil
import requests

CONFIG=dict()
CONFIG['path']="/home/ficheros/videos/series/"
CONFIG['config-file']=""
CONFIG['syslog']=True
CONFIG['user-agent']="Mozilla/5.0 (X11; Linux i686; rv:5.0) Gecko/20100101 Firefox/5.0"
CONFIG['debug']=0
CONFIG['proxy']=""
CONFIG['logfile']=os.environ['HOME'] + "/log/next_episodes_2.log"
CONFIG['transmission-user']="admin"
CONFIG['transmission-pass']=""
CONFIG['transmission-server']="localhost"
CONFIG['transmission-port']=9091
CONFIG['transmission-proxy']=""
CONFIG['exceptions']=list()
CONFIG['base_url']="https://eztv.ag/showlist/"
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


def Message(TEXT,FORCE=False,LEVEL=0,SYSLOG=False):
	global CONFIG
	import syslog,sys
	try:
		TEXT=TEXT.decode("utf8")
	except:
		try:
			TEXT=TEXT.encode("ascii", 'replace')
		except:
			TEXT=TEXT
	#To a log file
	#if not os.path.exists(os.path.dirname(CONFIG['logfile'])):
		#os.mkdir(os.path.dirname(CONFIG['logfile']))
	#logf=open(CONFIG['logfile'],"a")
	#try:
		#logf.write(TEXT)
	#except:
		#TEXT=TEXT.encode("utf8")
		#logf.write(TEXT)
	#logf.close()
	#To syslog
	if SYSLOG:
		syslog.syslog(TEXT)
	#To screen
	if int(CONFIG['debug']) > LEVEL or FORCE:
		if FORCE:
			sFORCE="True"
		else:
			sFORCE="False"
		#sys.stdout.write("%s (debug=%s force=%s level=%s)\n" % (TEXT,CONFIG['debug'],sFORCE,LEVEL))
		sys.stdout.write("%s\n" % TEXT)
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
	content=requests.get(URL).text
	return content
def GetURLContent2(URL):
	global CONFIG
	import urllib2,zipfile,socket,httplib,magic,zlib,sys,gc,gzip,tempfile,cookielib
	gc.collect()
	if CONFIG['proxy'] != "":
		PROXY=CONFIG['proxy']
	else:
		try:
			if 'http_proxy' in os.environ.keys():
				PROXY=os.environ["http_proxy"]
			else:
				PROXY=""
		except:
			PROXY=""
	if PROXY != "":
		#proxy = urllib2.ProxyHandler({'http': os.environ["http_proxy"]})
		proxy = urllib2.ProxyHandler({'http': PROXY})
		opener = urllib2.build_opener(proxy,urllib2.HTTPCookieProcessor(cookielib.CookieJar()))
	else:
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.CookieJar()))
	opener.addheaders = [('User-agent', CONFIG['user-agent'])]
	opener.addheaders = [('Accept-encoding', 'deflate')] 

	try:
		stream = opener.open(URL,None,10)
	except urllib2.URLError, e:
                try:
                        res=e.code
                        Message("Error (URL) opening URL '%s'. %s. Code: %s" % (URL,e,e.code))
                except:
                        res=e
                        Message("Error (URL) opening URL '%s'. %s." % (URL,e))
                return res
	except urllib2.HTTPError, e:
		Message("Error (HTTP) opening URL '%s'. %s. Code: %s" % (URL,e,e.code))
		return e.code
	except:
		Message("Unknown error opening URL '%s'" % (URL))
		return False		
	data = stream.read()
	encoded = stream.headers.get('Content-Encoding')
	server = stream.headers.get('Server')
	if encoded == 'deflate':
		Message("Server returned encoded data, trying to deflate it",LEVEL=2)
		before = len(data)
		try:
			data = zlib.decompress(data)
		except zlib.error:
			Message("Error deflating data from '%s'." % URL,True)
			return ""
		after=len(data)
		return data
	elif encoded == 'gzip':
		o,fn=tempfile.mkstemp()
		f=open(fn,"w")
		f.write(data)
		f.close()
		f=gzip.open(fn,"r")
		data=f.read()
		f.close()
		return data
	else:
		Message("Server returned uncompressed data (encoding is '%s')" % encoded,LEVEL=2)
		return data
def GetArguments():
	global CONFIG
	for arg in sys.argv:
		if arg == "-v" or arg == "-d" or arg == "--verbose" or arg == "--debug":
			if isinstance( CONFIG['debug'], str):
				CONFIG['debug']=int(CONFIG['debug'])+1
			else:
				CONFIG['debug']=CONFIG['debug']+1
			Message("Increased debug level to %s" % CONFIG['debug'])
		elif arg == "-h" or arg == "--help":
			Usage()
		elif arg.find("=")>-1:
			aarg=arg.split("=",1)
			if aarg[0]=="--exception":
				CONFIG['exceptions'].append(aarg[1])
				Message("Added exception '%s'" % aarg[1])
			elif aarg[0]=="--config-file":
				CONFIG['config-file']=aarg[1]
				Message("Will read config file '%s' (after processing command line arguments)" % aarg[1])
			elif aarg[0]=="--proxy":
				CONFIG['proxy']=aarg[1]
				Message("Will use proxy '%s'" % CONFIG['proxy'])
		if CONFIG['config-file']!="":
			ReadConfigFile()
def ReadConfigFile():
	global CONFIG
	import os
	if not os.path.exists(CONFIG['config-file']):
		Message("The configuration file '%s' doesn't exist" % CONFIG['config-file'])
		return False
	f_config=open(CONFIG['config-file'],"r")
	for line in f_config:
		a_line=line.split("=",1)
		if len(a_line)>1:
			val=a_line[1].replace(chr(13),"").replace(chr(10),"").strip('"')
			if a_line[0]=="exception":
				CONFIG['exceptions'].append(val)
				Message("Adding exception '%s' from config file" % val)
			else:
				for k in CONFIG.iterkeys():
					if a_line[0]==k:
						CONFIG[k]=val
						if a_line[0].find("pass")>-1:
							val="***"
						Message("Setting option '%s' as '%s' from config file" % (a_line[0],val))
	f_config.close()
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

def LastShowEpisode(SHOW):
	global CONFIG
	FILES=RecursiveFileListing("%s/%s" % (CONFIG['path'],SHOW))
	LASTEPISODE=0
	for FILE in FILES:
		FILE=FILE.replace("//","/")
		Message("III Checking file '%s'" % FILE,LEVEL=3)
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
def re_replace(string,pattern,replacement):
	import re
	m=re.search(pattern,string)
	if m != None:
		string=string.replace(m.group(1),replacement)
	return string
def EZTVGetShows():
	from bs4 import BeautifulSoup
	global CONFIG
	SHOWS=list()
	SHOWS_CONTENT=GetURLContent(CONFIG['base_url'])
	SHOWS_SOUP = BeautifulSoup(SHOWS_CONTENT, 'html.parser')
	for show_a in SHOWS_SOUP.find_all("a",class_="thread_link"):
		SHOW=dict()
		SHOW['href']=show_a['href']
		#SHOW['name']=re_replace(show_a.text,"( \(20[0-9]{2}\))","").strip(" ")
		SHOW['name']=show_a.text.strip(" ")

		list_url=CONFIG['base_url'].split("/")
		SERVER_URL=list_url[0] + "/" + list_url[1] + "/" + list_url[2]
		SHOW['href']=SERVER_URL + SHOW['href']
		
		SHOWS.append(SHOW)
	return SHOWS
		
	
def EZTVGetShowInformation(show):
	import re
	global CONFIG
	show_info=dict()
	show_info['name']=show['name']
	show_info['href']=show['href']
	content=GetURLContent(show['href'])
	
	#Status
	#House Status: <b>Ended</b><br/>
	m=re.search('%s Status: <b>(.*)</b><br/>' % show['name'],content)
	if m != None:
		show_info['status']=m.group(1)
	
	#NextEpisode
	#Next Episode is <span style="color: #0f559d; font-weight: bold;">Season 6 Episode 10</span> and airs on <b>6/26/2016, 09:00 PM</b>.
	m=re.search('Next Episode is <span style="color: #0f559d; font-weight: bold;">Season ([0-9]*) Episode ([0-9]*)</span> and airs on.',content)
	if m != None:
		season=m.group(1)
		episode=m.group(2)
		show_info['next_episode']=(season,episode)
	
	show_info['episodes']=EZTVGetShowEpisodes(show,content)
	show_info['last_episode']=EZTVLastEpisode(show_info)
	
	return show_info
def EZTVLastEpisode(show):
	import re
	last=0
	last_epi=None
	if "episodes" in show:
		for episode in show['episodes']:
			m=re.search("(S[0-9]*E[0-9]*)",episode['file_name'])
			if m != None:
				episode_num=m.group(1).replace("S","").replace("E","")
				if episode_num > last:
					last = episode_num
					last_epi=episode
	return last,last_epi
	
def EZTVSeachShowURL(SHOW,SHOWS_CONTENT):
	global CONFIG
	SHOW=SHOW.lower()
	SHOW2=re_replace(SHOW,"^(the\.)","")
	if SHOW != SHOW2:
		SHOW=SHOW2 + ", the"
	m=re.search('<a href="([a-z0-9A-Z\/\-]*)" class="thread_link">%s</a></td>' % SHOW,SHOWS_CONTENT.lower())
	list_url=CONFIG['base_url'].split("/")
	SERVER_URL=list_url[0] + "/" + list_url[1] + "/" + list_url[2]
	if m != None:
		SHOW_URL=SERVER_URL + m.group(1)
		return SHOW_URL
	else:
		Message("'%s' not found in base url" % SHOW,FORCE=True)
		return False
def EZTVGetShowEpisodes(show,content):
	from bs4 import BeautifulSoup
	episodes=list()
	soup=BeautifulSoup(content, 'html.parser')
	episodes_trs=soup.find_all("tr",class_="forum_header_border")
	for tr in episodes_trs:
		episode=dict()
		cols=tr.find_all("td",class_="forum_thread_post")
		if len(cols)>4:
			#file name
			episode['file_name']=cols[1].a.text
			#print episode['file_name']
			#magnet
			magnet_soup=cols[2].find(class_="magnet")
			if magnet_soup != None:
				episode['magnet']=magnet_soup['href']
				#print episode['magnet']
			else:
				downloads=cols[2].find_all(class_=re.compile("download_"))
				for download in downloads:
					episode['torrent_url']=download['href']
					#To-Do check if the URL works before using it

			#size
			episode['size']=cols[3].text
			#age
			episode['age']=cols[4].text
			episodes.append(episode)
	return episodes
def SimplifyShowName(show_name):
	new_name=show_name.lower().replace("."," ").replace("'","").replace("  "," ").replace("(","").replace(")","").strip(" ").replace(":","").replace("!","")
	new_name=re_replace(new_name,"( 20[0-9][0-9]),","")
	new_name=re_replace(new_name,"( 20[0-9][0-9])$","")
	new_name2=re_replace(new_name,"^(the )","")
	if new_name2 != new_name:
		new_name=new_name2 + ", the"
	return new_name
def EZTVGetShow(show_name,EZTVSHOWS):
	for eztv_show in EZTVSHOWS:
		simply_show_name=SimplifyShowName(show_name)
		simply_eztv_name=SimplifyShowName(eztv_show['name'])
		if simply_show_name == simply_eztv_name:
			return eztv_show
		#else:
			#if len(simply_eztv_name)>1:
				#if simply_show_name[0] == simply_eztv_name[0] and simply_show_name[1] == simply_eztv_name[1]:
					#print simply_show_name + "<>" + simply_eztv_name
	return False

def NextEpisode(last_episode):
	if last_episode==0:
		same_season="S00E01"
		next_season="S00E01"
		next_season_zero="S00E00"
	else:
		season=int(round(last_episode/100))
		episode=last_episode-(season*100)
		
		sseason="%s" % season
		sepisode="%s" % (episode+1)
		same_season="S%sE%s" % (sseason.rjust(2,"0"),sepisode.rjust(2,"0"))
		
		next_season="%s" % (int(season)+1)
		next_season_zero="S%sE00" % next_season.rjust(2,"0")
		next_season="S%sE01" % next_season.rjust(2,"0")
	return same_season,next_season_zero,next_season

def EZTVGetEpisodeByFileName(SHOW,file_name):
	SHOW_INFO=EZTVGetShowInformation(SHOW)
	if "episodes" in SHOW_INFO.keys():
		for episode in SHOW_INFO['episodes']:
			#print episode['file_name']
			if episode['file_name'].find(file_name)>-1:
				return episode
	return False
def AddMagnet(URL):
	import transmissionrpc
	global CONFIG
	if 'http_proxy' in os.environ.keys():
		current_proxy=os.environ['http_proxy']
	else:
		current_proxy=""
	os.environ['http_proxy']=CONFIG['transmission-proxy']
	try:
		conn=transmissionrpc.Client(CONFIG['transmission-server'], user=CONFIG['transmission-user'],password=CONFIG['transmission-pass'],port=CONFIG['transmission-port'])
		try:
			conn.add_torrent(URL)
		except:
			Message("Error adding torrent URL '%s' to Transmission" % URL)
	except transmissionrpc.error.TransmissionError,e:
		Message("Error adding torrent to Transmission. User=%s, Password=***, Server=%s, Port=%s. %s" % (CONFIG['transmission-user'],CONFIG['transmission-server'],CONFIG['transmission-port'],e))
	os.environ['http_proxy']=current_proxy

CheckIfRunning()
GetArguments()
print "Arguments processed, debug=%s" % CONFIG['debug']
EZTVSHOWS=EZTVGetShows()
SHOWS_DIRS=os.listdir(CONFIG['path'])
for SHOW in SHOWS_DIRS:
	SKIP=False
	for EXCEPTION in CONFIG['exceptions']:
		if SHOW == EXCEPTION:
			Message("III Skipping show '%s' due to exception in configuration." % SHOW,LEVEL=2)
			SKIP=True
	if not SKIP:
		Message("III Checking show '%s'" % SHOW,FORCE=True)
		EZTVSHOW=EZTVGetShow(SHOW,EZTVSHOWS)
		if not EZTVSHOW:
			Message("WWW NOT found '%s' in EZTV" % SHOW,FORCE=True)
		else:
			Message("III FOUND in '%s' in EZTV as '%s'" % (SHOW,EZTVSHOW['name']))
			show_info=EZTVGetShowInformation(EZTVSHOW)
			LAST_EPISODE=LastShowEpisode(SHOW)
			Message("III Last episode downloaded was %s" % LAST_EPISODE)
			NEXT_EPISODE=NextEpisode(LAST_EPISODE)
			#To-Do: Get 3 returned variable with next_season_zero
			Message("III Next episode to download is %s or %s or %s" % NEXT_EPISODE)
			EZTVEpisode=EZTVGetEpisodeByFileName(EZTVSHOW,NEXT_EPISODE[0])
			if 'last_episode' in EZTVSHOW.keys():
				Message("III Last episode in EZTV is '%s'" % EZTVSHOW['last_episode'])
			if not EZTVEpisode:
				EZTVEpisode=EZTVGetEpisodeByFileName(EZTVSHOW,NEXT_EPISODE[1])
			if not EZTVEpisode:
				EZTVEpisode=EZTVGetEpisodeByFileName(EZTVSHOW,NEXT_EPISODE[2])
			if not EZTVEpisode:			
				Message("III No new episode available to download.")
			else:
				if 'magnet' in EZTVEpisode.keys():
					EPISODEURL=EZTVEpisode['magnet']
				elif 'torrent_url' in EZTVEpisode.keys():
					EPISODEURL=EZTVEpisode['torrent_url']
				else:
					Message("EEE URL for torrent not found in the episode")
					Message(EZTVEpisode)
				AddMagnet(EPISODEURL)
