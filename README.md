# next_episode.py
Description: Find the last downloaded episodes and find the next.
Usage: Create the folder in the PATH variable, inside create a folder for each TV show (replace spaces with dots to improve the search), and the script will search for the downloaded episodes and download the next one using Transmission. Also check the transmission variable to fit your set up.
Requirements: urllib2, gzip, psutil, transmissionrpc, threading, socket, httplib, magic, gzip, cookielib
