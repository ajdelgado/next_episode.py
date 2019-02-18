#!/usr/bin/env python3
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
import sys,os,time,re,urllib.request,urllib.error,urllib.parse,string,tempfile, gzip
import psutil
import requests
import logging
from logging.handlers import SysLogHandler
from logging.handlers import RotatingFileHandler

CONFIG=dict()
CONFIG['path']="/home/ficheros/videos/series/"
CONFIG['config-file']=""
CONFIG['user-agent']="Mozilla/5.0 (X11; Linux i686; rv:5.0) Gecko/20100101 Firefox/5.0"
CONFIG['proxy']=""
CONFIG['debug']=False
CONFIG['logfile']=os.environ['HOME'] + "/log/next_episodes_2.log"
CONFIG['transmission-user']="admin"
CONFIG['transmission-pass']=""
CONFIG['transmission-server']="localhost"
CONFIG['transmission-port']=9091
CONFIG['transmission-proxy']=""
CONFIG['exceptions']=list()
CONFIG['base_url']="https://eztv.io/showlist/"
def CheckIfRunning():
	log.info("Checking if this task is already running...")
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
							Messalog.infoge("Already running process %s '%s'" % (process,cmdline))
							sys.exit(1)
				except psutil.AccessDenied:
					log.info("I can't read information for process %s" % process)
			except psutil.NoSuchProcess:
				Nothing=0


def SaveTmpFile(content):
	global TMPFILE
	import tempfile
	TMPFILEO=tempfile.mkstemp(prefix='tmp_', dir="/tmp/")
	TMPFILENAME=TMPFILEO[1]
	log.info("Saving temporarily to '%s' (don't forget to remove it)" % (TMPFILENAME))
	TMPFILE=open(TMPFILENAME,"w")
	try:
		TMPFILE.write(content)
	finally:
		TMPFILE.close()
	return TMPFILENAME
def GetURLContent(URL):
	content=requests.get(URL).text
	return content
def GetArguments():
	global CONFIG
	for arg in sys.argv:
		if arg == "-v" or arg == "-d" or arg == "--verbose" or arg == "--debug":
			CONFIG['debug'] = True
			log.info("Enable debug level")
		elif arg == "-h" or arg == "--help":
			Usage()
		elif arg.find("=")>-1:
			aarg=arg.split("=",1)
			if aarg[0]=="--exception":
				CONFIG['exceptions'].append(aarg[1])
				log.info("Added exception '%s'" % aarg[1])
			elif aarg[0]=="--config-file":
				CONFIG['config-file']=aarg[1]
				log.info("Will read config file '%s' (after processing command line arguments)" % aarg[1])
			elif aarg[0]=="--proxy":
				CONFIG['proxy']=aarg[1]
				log.info("Will use proxy '%s'" % CONFIG['proxy'])
			else:
				parameter = aarg[0].replace("--","")
				CONFIG[parameter] = aarg[1]
				log.info('Parameter "{}" set to "{}"'.format(parameter, CONFIG[parameter]))
		if CONFIG['config-file']!="":
			ReadConfigFile()
def ReadConfigFile():
	global CONFIG
	import os
	if not os.path.exists(CONFIG['config-file']):
		log.info("The configuration file '%s' doesn't exist" % CONFIG['config-file'])
		return False
	f_config=open(CONFIG['config-file'],"r")
	for line in f_config:
		a_line=line.split("=",1)
		if len(a_line)>1:
			val=a_line[1].replace(chr(13),"").replace(chr(10),"").strip('"')
			if a_line[0]=="exception":
				CONFIG['exceptions'].append(val)
				log.info("Adding exception '%s' from config file" % val)
			else:
				for k in CONFIG.keys():
					if a_line[0]==k:
						CONFIG[k]=val
						if a_line[0].find("pass")>-1:
							val="***"
						log.info("Setting option '%s' as '%s' from config file" % (a_line[0],val))
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
		log.debug("Checking file '%s'" % FILE)
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
		log.info("There is no downloaded episodes of the show '%s' or it was the '%s'" % (SHOW,LASTEPISODE))
	else:
		log.info("Last episode downloaded from show '%s' was '%s'" % (SHOW,LASTEPISODE))
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
	if SHOWS_CONTENT == "" or SHOWS_CONTENT is None or SHOWS_CONTENT is False:
		log.info("Nothing obtained from the base url '%s'. There is no Internet connection or the URL is broken?" % CONFIG['base_url'],FORCE=True)
		sys.exit(1)
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
				if int(episode_num) > int(last):
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
		log.info("'%s' not found in base url" % SHOW,FORCE=True)
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
			#magnet
			magnet_soup=cols[2].find(class_="magnet")
			if magnet_soup != None:
				episode['magnet']=magnet_soup['href']
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
	return False

def NextEpisode(last_episode):
	if last_episode==0:
		same_season="S01E01"
		next_season="S01E01"
		next_season_zero="S01E00"
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
	if "episodes" in list(SHOW_INFO.keys()):
		for episode in SHOW_INFO['episodes']:
			#print episode['file_name']
			if episode['file_name'].find(file_name)>-1:
				return episode
	return False
def AddMagnet(URL):
	import transmissionrpc
	global CONFIG
	if URL is False:
		return False
	if 'http_proxy' in list(os.environ.keys()):
		current_proxy=os.environ['http_proxy']
	else:
		current_proxy=""
	os.environ['http_proxy']=CONFIG['transmission-proxy']
	try:
		conn=transmissionrpc.Client(CONFIG['transmission-server'],
									user=CONFIG['transmission-user'],
									password=CONFIG['transmission-pass'],
									port=CONFIG['transmission-port'])
		try:
			conn.add_torrent(URL)
		except:
			log.info("Error adding torrent URL '%s' to Transmission" % URL)
	except transmissionrpc.error.TransmissionError as e:
		log.info("Error adding torrent to Transmission. "
				 "User=%s, Password=***, Server=%s, "
				 "Port=%s. %s" % (CONFIG['transmission-user'],
				 				  CONFIG['transmission-server'],
								   CONFIG['transmission-port'],
								   e))
	os.environ['http_proxy']=current_proxy
starttime=time.time()
log = logging.getLogger()
log.setLevel(logging.getLevelName('DEBUG'))

sysloghandler = SysLogHandler()
sysloghandler.setLevel(logging.getLevelName('DEBUG'))
log.addHandler(sysloghandler)

streamhandler = logging.StreamHandler(sys.stdout)
streamhandler.setLevel(logging.getLevelName('DEBUG'))
log.addHandler(streamhandler)

GetArguments()
if CONFIG['debug']:
	log.setLevel(logging.getLevelName('DEBUG'))
else:
	log.setLevel(logging.getLevelName('WARNING'))
if not os.path.exists(os.path.dirname(CONFIG['logfile'])):
	os.mkdir(os.path.dirname(CONFIG['logfile']))
filehandler = RotatingFileHandler(CONFIG['logfile'],
							  maxBytes=1000000,
							  backupCount=5)
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
filehandler.setFormatter(formatter)
filehandler.setLevel(logging.getLevelName('DEBUG'))
log.addHandler(filehandler)

CheckIfRunning()
EZTVSHOWS=EZTVGetShows()
SHOWS_DIRS=os.listdir(CONFIG['path'])
for SHOW in SHOWS_DIRS:
	SKIPTHIS=False
	for EXCEPTION in CONFIG['exceptions']:
		if SHOW == EXCEPTION:
			log.info("Skipping show '%s' due to exception in configuration." % SHOW)
			SKIPTHIS=True
	if not SKIPTHIS:
		log.info("Checking show '%s'" % SHOW)
		EZTVSHOW=EZTVGetShow(SHOW,EZTVSHOWS)
		if not EZTVSHOW:
			log.warn("NOT found '%s' in EZTV" % SHOW)
		else:
			log.info("FOUND in '%s' in EZTV as '%s'" % (SHOW,EZTVSHOW['name']))
			show_info=EZTVGetShowInformation(EZTVSHOW)
			LAST_EPISODE=LastShowEpisode(SHOW)
			log.info("Last episode downloaded was %s" % LAST_EPISODE)
			NEXT_EPISODE=NextEpisode(LAST_EPISODE)
			#To-Do: Get 3 returned variable with next_season_zero
			log.info("Next episode to download is %s or %s or %s" % NEXT_EPISODE)
			EZTVEpisode=EZTVGetEpisodeByFileName(EZTVSHOW,NEXT_EPISODE[0])
			if 'last_episode' in list(EZTVSHOW.keys()):
				log.info("Last episode in EZTV is '%s'" % EZTVSHOW['last_episode'])
			if not EZTVEpisode:
				EZTVEpisode=EZTVGetEpisodeByFileName(EZTVSHOW,NEXT_EPISODE[1])
			if not EZTVEpisode:
				EZTVEpisode=EZTVGetEpisodeByFileName(EZTVSHOW,NEXT_EPISODE[2])
			if not EZTVEpisode:
				log.info("No new episode available to download.")
			else:
				if 'magnet' in list(EZTVEpisode.keys()):
					EPISODEURL=EZTVEpisode['magnet']
				elif 'torrent_url' in list(EZTVEpisode.keys()):
					EPISODEURL=EZTVEpisode['torrent_url']
				else:
					log.error("URL for torrent not found in the episode:%s" % EZTVEpisode)
					log.info(EZTVEpisode)
					EPISODEURL=False
				AddMagnet(EPISODEURL)
duration=time.time()-starttime
log.info("It took %s seconds to process all TV shows" % duration)
