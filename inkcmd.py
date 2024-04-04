# ----------------------------------------------------------------------------
# Copyright (C) 2023 RKtech <info@rktech.de>
# V1.00 19.09.2023
#
# This module will try to find the correct Inkscape instance to handle the CLI commands, and also check for the used version.
# Specially if it is started as a AppImage.
# ----------------------------------------------------------------------------

import sys
import os
import re
import subprocess

# Possibly it should be fixed in more recent version of Inkscape. See https://gitlab.com/inkscape/extensions/-/merge_requests/589, https://gitlab.com/inkscape/inkscape/-/issues/4163.
# As a workaround, you may add: 
os.environ["SELF_CALL"] = "true"

class Init:
    """
    Search for the correct path to run inkscape commands within python extensions and btw. get the version
    """

    def __init__(self, inkscape_command='inkscape'):
        # get inkscape version, the standard way
        inkscape_version_string = '0'
        inkscape_version = 0
        inkscape_major =   0
        inkscape_mid =     0
        inkscape_minor =   0

        # try the standard command
        commands = 'inkscape' + os.linesep

        # search for a running AppImage instance on Linux systems
        if sys.platform.startswith('linux'):
            command = r'ps -xao command | grep -oe ".*\/[iI]nkscape.*\.AppImage"'
            p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return_code = p.wait()
            stdout, stderr = p.communicate()
            commands += stdout.decode('utf8')
            
        #sys.stderr.write(commands+"\n")
        #sys.stderr.write("***********************************\n")

        for tmp_command in commands.splitlines():
            #sys.stderr.write(tmp_command+"\n")
            #sys.stderr.write("***********************************\n")

            p = subprocess.Popen(tmp_command+' --version', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return_code = p.wait()
            stdout, stderr = p.communicate()

            tmp_inkscape_version = 0

            m = re.search(r'Inkscape\s(\d+)\.(\d+)\.(\d+)\s', stdout.decode('utf8'))
            if m:
                tmp_inkscape_major = int(m.group(1))
                tmp_inkscape_mid =   int(m.group(2))
                tmp_inkscape_minor = int(m.group(3))
                tmp_inkscape_version = tmp_inkscape_major * 1000000 + tmp_inkscape_mid * 1000 + tmp_inkscape_minor
                tmp_inkVersion = "%i.%i.%i"%(tmp_inkscape_major, tmp_inkscape_mid, tmp_inkscape_minor)

            m = re.search(r'Inkscape\s(\d+)\.(\d+)\s', stdout.decode('utf8'))
            if m:
                tmp_inkscape_major = int(m.group(1))
                tmp_inkscape_mid =   int(m.group(2))
                tmp_inkscape_minor = 0
                tmp_inkscape_version = tmp_inkscape_major * 1000000 + tmp_inkscape_mid * 1000 + tmp_inkscape_minor
                tmp_inkVersion = "%i.%i"%(tmp_inkscape_major, tmp_inkscape_mid)

            # use command for highest running version
            if tmp_inkscape_version > inkscape_version:
                inkscape_command =        tmp_command
                inkscape_version =        tmp_inkscape_version
                inkscape_version_string = tmp_inkVersion
                inkscape_major =          tmp_inkscape_major
                inkscape_mid =            tmp_inkscape_mid
                inkscape_minor =          tmp_inkscape_minor

        ########################################################################
        # last try could be a search with "which inkscape" and use absolute path
        ########################################################################

        self.command =       inkscape_command
        self.version_int =   inkscape_version
        self.version =       inkscape_version_string
        self.version_major = inkscape_major
        self.version_mid =   inkscape_mid
        self.version_minor = inkscape_minor


    def execute(self, parameter=""):
        retStdOut = ""
        retError = ""
        if self.version_int <= 0:
            retError = "ERROR: No Inkscape executable found!"
        elif parameter == '':
            retError = "ERROR: Some parameters needed!"
        else:
            p = subprocess.Popen('%s %s'%(self.command, parameter) , shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return_code = p.wait()
            stdout, stderr = p.communicate()
            retStdOut = stdout.decode('utf8')
            retError  = stderr.decode('utf8')
            #retStdOut = "OK! %s"%(parameter)
            
        return (retStdOut, retError)
        
