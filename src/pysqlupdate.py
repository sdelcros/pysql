#!/usr/bin/python
# -*- coding: utf-8 -*-

# Sébastien Renard (sebastien.renard@digitalfox.org)
# Code licensed under GNU GPL V2

"""This module check for PySQL updates and help user to update PySQL online"""

# Python import
import urllib2
import re
import sys
from os.path import dirname, isdir, isfile, islink, join
from os import access, listdir, mkdir, unlink, X_OK
from shutil import copy, copytree, rmtree
import tarfile

# PySQL imports
from pysqlexception import PysqlException
from pysqlio import PysqlIO
from pysqlcolor import CYAN, RED, RESET

PYSQL_DOWNLOAD="http://www.digitalfox.org/projets/download/"
UPDATEDIR="update"
PYSQLROOTDIR="pysql"

def checkForUpdate(proxy=None, user="", password=""):
    """Check if the current PySQL is the latest one"""
    releases=[]     # Release list
    # Get IO handler
    io=PysqlIO.getIOHandler()
    
    # Web stuff to get available releases
    if proxy:
        proxy_handler=urllib2.ProxyHandler({'http': proxy})
        proxy_auth_handler=urllib2.HTTPBasicAuthHandler()
        proxy_auth_handler.add_password("realm", "host", user, password)
        opener=urllib2.build_opener(proxy_handler, proxy_auth_handler)
    else:
        opener=urllib2.build_opener()
    try:
        page=opener.open(PYSQL_DOWNLOAD)
        for line in page.readlines():
            result=re.match(".*pysql-(.+).tar.gz.*", line)
            if result:
                if result.group(1)!="snapshot":
                    releases.append(Version(result.group(1)))
        releases.sort()
        last=releases[-1]
        current=Version(currentVersion())
        
        io(_("Available releases : %s") % ", ".join([str(i) for i in releases]))
        io(_("Latest is %s") % last)
        io(_("Current is %s") % current)
        if current.isSnapshot:
            io(_("You are in snapshot release - move to last [r]elease or last [s]napshot (r/s) ?"))
            answer=io.read()
            if answer in ("r", "release"):
                update(opener, last)
            else:
                update(opener, "snapshot")
        elif last>current:
            io(_("A new release is available (%s). Do you want to update (y/n) ?") % last)
            answer=io.read()
            if answer in ("y", "yes"):
                update(opener, last)
            else:
                io(_("Ok, bye"))
        else:
            io(_("PySQL is up to date. No need to update"))
    except urllib2.URLError, e:
        io(RED + _("Cannot reach PySQL Website (%s)") % e + RESET)

def currentVersion():
    """@return: current pysql version according to 'version' file"""
    try:
        return file(join(dirname(sys.argv[0]), "version")).readline().strip("\n")
    except:
        raise PysqlException(_("Unable to read 'version' file. Do you remove or change it ?"))

def update(opener, version):
    """Update PySQL
    @param opener: URL handle to download PySQL tarball
    @type opener: urllib2 opener object
    @param version: target version for update
    @type version: string
    @return: True if everything is Ok, else False"""
    io=PysqlIO.getIOHandler()
    io(CYAN + _("=>update to version %s<=") % version + RESET)
    
    # Create an update dir in PySQL dist and download tarball into it
    filename="pysql-"+str(version)+".tar.gz"
    pysqlPath=dirname(sys.argv[0])
    updatePath=join(pysqlPath, UPDATEDIR)
    newPath=join(updatePath, PYSQLROOTDIR)
    if not access(updatePath, X_OK):
        mkdir(updatePath)    
    # Remove any previous aborted install
    if access(newPath, X_OK):
        try:
            rmtree(newPath)
        except IOError, e:
            io(RED + _("Cannot remove previous aborted update. Please remove it by hand (%s)") % e + RESET)
            return False
    try:
        tmpFile=file(join(updatePath, filename), "w")
        io.write(_("Downloading from PySQL Website... "))
        tmpFile.write(opener.open(PYSQL_DOWNLOAD+filename).read())
        tmpFile.close()
        io(CYAN+_("Done !") + RESET)
        io.write(_("Opening archive and copying files to pysql directory..."))
        tarball=tarfile.open(join(updatePath, filename), mode="r:gz")
        for tarinfo in tarball:
            tarball.extract(tarinfo, "update")
        tarball.close()
    except urllib2.URLError, e:
        io(RED+ _("Failed to download file from PySQL WebSite (%s)") % e + RESET)
        return False
    except IOError, e:
        io(RED+ _("Cannot write archive file to %s (%s)") % (updatePath, e) + RESET)
        return False
    try:
        blacklist=("pysqlrc",) # Files that should not be copied !
        for item in listdir(newPath):
            if item in blacklist:
                continue
            if isdir(item):
                try:
                    rmtree(join(pysqlPath, item))
                except OSError, e:
                    io(RED+_("Cannot remove %s (%s)") % (item, e) + RESET)
                copytree(join(newPath, item), join(pysqlPath, item))
            elif isfile(item) and not islink(item):
                try:
                    unlink(join(pysqlPath, item))
                except OSError, e:
                    io(RED+_("Cannot remove %s (%s)") % (item, e) + RESET)
                copy(join(newPath, item), join(pysqlPath, item))
        io(CYAN+_("Done !") + RESET)
        # Some cleanup
        io.write(_("Cleanup... "))
        rmtree(updatePath)
        io(CYAN+_("Done !") + RESET)
        io(CYAN+_("Update successul !") + RESET)
        return True
    except (IOError,OSError) , e:
        io(RED+ _("Error while copying files (%s)") % e + RESET)
        return False

class Version:
    """Pysql Version handling according to release policy
    Release model : Major.Minor.Fix
    Major and minor are mandatory, fix is optionnal
    Release can be "snapshot" (case unsensitive). 
    If not defined, major/minor/fix are set to empty str "" 
    Standard comparison operator are defined : <, >, <=, <= and =="""
    def __init__(self, versionStr):
        """Create version instance from version str"""
        self.major=""
        self.minor=""
        self.fix=""
        self.isSnapshot=False
        
        if versionStr.lower()=="snapshot":
            self.isSnapshot=True
        elif versionStr.count(".")==1:
            (self.major, self.minor)=versionStr.split(".")
        elif versionStr.count(".")==2:
            (self.major, self.minor, self.fix)=versionStr.split(".")
        else:
            raise PysqlException(_("Bad release scheme (%s)") % versionStr)

    def __lt__(self, version):
        if self.isSnapshot or version.isSnapshot:
            raise PysqlException(_("Cannot compare with snapshot release"))
        elif self.major<version.major:
            return True
        elif self.major>version.major:
            return False
        elif self.major==version.major:
            if self.minor<version.minor:
                return True
            elif self.minor>version.minor:
                return False
            elif self.minor==version.minor:
                if self.fix<version.fix:
                    return True
                else:
                    return False

    def __gt__(self, version):
        return (version<self)
    
    def __eq__(self, version):
        if self.major==version.major and self.minor==version.minor and self.fix==version.fix:
            return True
        else:
            return False
    
    def __le__(self, version):
        return (self==version or self<version)
    
    def __ge__(self, version):
        return (version<=self)
    
    def __str__(self):
        if self.isSnapshot:
            return "snapshot"
        else:
            return ".".join((self.major, self.minor, self.fix)).rstrip(".")