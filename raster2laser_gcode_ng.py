'''
# ----------------------------------------------------------------------------
# Copyright (C) 2022 RKtech<info@rktech.de>
# - Added 3 dithering types (based on this code https://github.com/Utkarsh-Deshmukh/image-dithering-python)
#   - Simple2D
#   - Floyd-Steinberg
#   - Jarvis-Judice-Ninke
# - Modify gray scale conversion with lookup table and any number of 2..256 gray steps
# - Add image conversion "Flip X"
# - Use image size of full page or the outline of all objects
# - Define resolution with laser spot size
# - New B/W to GCode generator with this features
#   - Set min/max laser power values
#   - Allow user configurable GCode init, line, and exit Code
#   - Calculate positions for rotary axis with a given diameter
#   - Add a distance to move the laser for acceleration and deceleration with laser power off
#   - set position of zero point
#   - Scanline in X or Y direction
#
# Todo:
# - Add a variable Z axis geometry, e.g. linear or arc defined by 3 points
# - Check feed rate for rotary axis
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# Copyright (C) 2014 305engineering <305engineering@gmail.com>
# Original concept by 305engineering.
#
# "THE MODIFIED BEER-WARE LICENSE" (Revision: my own :P):
# <305engineering@gmail.com> wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff (except sell). If we meet some day, 
# and you think this stuff is worth it, you can buy me a beer in return.
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ----------------------------------------------------------------------------
'''


import sys
import os
import re
import subprocess
import math
import inkex
import png
import array
import collections


# Pull Request #23
# from Pull Request "https://github.com/305engineering/Inkscape/pull/23"
#sys.path.append('/usr/share/inkscape/extensions')
#sys.path.append('/Applications/Inkscape.app/Contents/Resources/extensions') 

def errormsg(msg):
    sys.stderr.write(msg+"\n")
    

def extensions_path_fallback():
    sys.path.append('/usr/share/inkscape/extensions')
    sys.path.append('/Applications/Inkscape.app/Contents/Resources/extensions')


## get inkscape major version 
try:
    command='inkscape --version'
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return_code = p.wait()
    stdout, stderr = p.communicate()
    inkVersion = stdout.decode('utf8').split(' ')[1]
    majorVersion = int(inkVersion.split('.')[0])
except:
    # if inkscape version is not accessible, do a guess based on the python version
    if sys.version_info.major < 3:
        inkVersion = "0.9x"
        majorVersion = 0
    else:
        inkVersion = "1.x"
        majorVersion = 1
#pyVersion = sys.version.split(' ')[0]
#errormsg( "Inkscape Version: " + inkVersion + " => " + str(majorVersion) + "\n" + "Python Version: " + pyVersion)


## get extension dir
try:
    command='inkscape --extension-directory'
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return_code = p.wait()
    stdout, stderr = p.communicate()
    extensions_path = stdout.strip()

    if extensions_path:
        sys.path.append(extensions_path)
    else:
        extensions_path_fallback()
except subprocess.CalledProcessError:
    extensions_path_fallback()



class GcodeExport(inkex.Effect):

    ######## read Inkscape parameters
    def __init__(self):
        """init the effetc library and get options from gui"""
        inkex.Effect.__init__(self)

        # To make the notebook parameter happy
        self.OptionParser.add_option("","--nopNB",action="store",type="string",dest="nopNB",default="",help="")
        
        # Image Settings
        self.OptionParser.add_option("-d", "--imgDirName",action="store", type="string", dest="imgDirName", default="/home/",help="Directory for files")
        self.OptionParser.add_option("-f", "--imgFileName", action="store", type="string", dest="imgFileName", default="-1.0", help="File name")            
        self.OptionParser.add_option("","--imgNumFileSuffix", action="store", type="inkbool", dest="imgNumFileSuffix", default=True,help="Add numeric suffix to filename")            
        self.OptionParser.add_option("","--imgBGcolor", action="store",type="string",dest="imgBGcolor",default="",help="")
        self.OptionParser.add_option("","--imgResolution", action="store", type="int", dest="imgResolution", default="0",help="")
        self.OptionParser.add_option("","--imgSpotSize", action="store", type="float", dest="imgSpotSize", default="0.2",help="")
        self.OptionParser.add_option("","--imgGrayType", action="store", type="int", dest="imgGrayType", default="1",help="") 
        self.OptionParser.add_option("","--imgConvType", action="store", type="int", dest="imgConvType", default="1",help="") 
        self.OptionParser.add_option("","--imgBWthreshold", action="store", type="int", dest="imgBWthreshold", default="128",help="") 
        self.OptionParser.add_option("","--imgGrayResolution", action="store", type="int", dest="imgGrayResolution", default="256",help="") 
        self.OptionParser.add_option("","--imgRotDiameter",action="store", type="float", dest="imgRotDiameter", default="50.0",help="")
        self.OptionParser.add_option("","--imgFullPage",action="store", type="inkbool", dest="imgFullPage", default=True,help="") 
        self.OptionParser.add_option("","--imgPreviewOnly",action="store", type="inkbool", dest="imgPreviewOnly", default=False,help="") 
        self.OptionParser.add_option("","--dbg", type="inkbool", dest="debug", default=False,help="not stored")

        # GCode (1) Settings
        self.OptionParser.add_option("","--gc1Setting", action="store", type="string", dest="gc1Setting", default="", help="")
        self.OptionParser.add_option("","--gc1StartCode", action="store", type="string", dest="gc1StartCode", default="", help="")
        self.OptionParser.add_option("","--gc1PostCode", action="store", type="string", dest="gc1PostCode", default="", help="")
        self.OptionParser.add_option("","--gc1LineCode", action="store", type="string", dest="gc1LineCode", default="", help="")
        self.OptionParser.add_option("","--gc1PixelCode", action="store", type="string", dest="gc1PixelCode", default="", help="")
        self.OptionParser.add_option("","--gc1LaserOn", action="store", type="string", dest="gc1LaserOn", default="M03", help="")
        self.OptionParser.add_option("","--gc1LaserOff", action="store", type="string", dest="gc1LaserOff", default="M05", help="")
        self.OptionParser.add_option("","--gc1LOnThreshold",action="store", type="int", dest="gc1LOnThreshold", default="254",help="") 
        self.OptionParser.add_option("","--gc1FeedRate",action="store", type="int", dest="gc1FeedRate", default="200",help="") 
        self.OptionParser.add_option("","--gc1MinPower",action="store", type="float", dest="gc1MinPower", default="0.0",help="")
        self.OptionParser.add_option("","--gc1MaxPower",action="store", type="float", dest="gc1MaxPower", default="100.0",help="")
        self.OptionParser.add_option("","--gc1AccDistance",action="store", type="float", dest="gc1AccDistance", default="10.0",help="")
        self.OptionParser.add_option("","--gc1LevelZ",action="store", type="float", dest="gc1LevelZ", default="10.0",help="")
        self.OptionParser.add_option("","--gc1FlipX",action="store", type="inkbool", dest="gc1FlipX", default=False,help="")
        self.OptionParser.add_option("","--gc1FlipY",action="store", type="inkbool", dest="gc1FlipY", default=False,help="")
        self.OptionParser.add_option("","--gc1Invert",action="store", type="inkbool", dest="gc1Invert", default=False,help="")
        self.OptionParser.add_option("","--gc1Gamma",action="store", type="float", dest="gc1Gamma", default="1.0",help="")
        self.OptionParser.add_option("","--gc1ZeroPointX",action="store", type="int", dest="gc1ZeroPointX", default="0",help="")
        self.OptionParser.add_option("","--gc1ZeroPointY",action="store", type="int", dest="gc1ZeroPointY", default="0",help="")
        self.OptionParser.add_option("","--gc1OptScnLine",action="store", type="int", dest="gc1OptScnLine", default="1",help="")
        self.OptionParser.add_option("","--gc1ScanType",action="store", type="int", dest="gc1ScanType", default="3",help="")
        self.OptionParser.add_option("","--gc1ZigZagOffset",action="store", type="float", dest="gc1ZigZagOffset", default="0",help="")
        self.OptionParser.add_option("","--gc1Interleaved",action="store", type="inkbool", dest="gc1Interleaved", default=False,help="")

            
    ## create PNG file(s)
    def effect(self):

        current_file = self.args[-1]
        bg_color = self.options.imgBGcolor
        
        ## check dir
        if (os.path.isdir(self.options.imgDirName)) == True:
            
            # find next unused suffix numger
            if self.options.imgNumFileSuffix :
                dir_list = os.listdir(self.options.imgDirName)
                temp_name =  self.options.imgFileName
                max_n = 0
                for s in dir_list :
                    r = re.match(r"^%s_0*(\d+)_.+preview\.%s$"%(re.escape(temp_name),'png' ), s)
                    if r :
                        max_n = max(max_n,int(r.group(1)))	
                self.options.imgFileName = temp_name + "_%04d"%(max_n+1)

            # create file suffix
            suffix = ""
            if self.options.imgConvType == 1:
                suffix = "_BW_"+str(self.options.imgBWthreshold)
            elif self.options.imgConvType == 2:
                suffix = "_BW_rnd"
            elif self.options.imgConvType == 3:
                suffix = "_HT"
            elif self.options.imgConvType == 4:
                suffix = "_HTrow"
            elif self.options.imgConvType == 5:
                suffix = "_HTcol"
            elif self.options.imgConvType == 6:
                suffix = "_S2D_"+str(self.options.imgBWthreshold)
            elif self.options.imgConvType == 7:
                suffix = "_FS_"+str(self.options.imgBWthreshold)
            elif self.options.imgConvType == 8:
                suffix = "_JJN_"+str(self.options.imgBWthreshold)
            elif self.options.imgConvType == 9:
                suffix = "_Gray_"+str(self.options.imgGrayResolution)
            else:
                errormsg("Unknown conversion type!")
            
            pos_file_png_exported = os.path.join(self.options.imgDirName,self.options.imgFileName+".png") 
            pos_file_png_BW = os.path.join(self.options.imgDirName,self.options.imgFileName+suffix+"_preview.png") 
            pos_file_gcode = os.path.join(self.options.imgDirName,self.options.imgFileName+suffix+".ngc") 
            
            # inkscape returns a warning if file will not end wit '.svg' so add it to the tmp file
            current_svg_file = current_file + ".svg"
            command='mv %s %s' % (current_file, current_svg_file)
            p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return_code = p.wait()
            stdout, stderr = p.communicate()
            if stderr:
                msg = 'CMD:\n'+ command + '\n\nSTDOUT:\n' + stdout.decode('utf8')+"\n\nSTDERR:\n"+stderr.decode('utf8')
                errormsg(msg)
                exit()

            # Generate PNG from SVG
            ret = self.exportPage(pos_file_png_exported, current_svg_file, bg_color)
            
            # Generate Gcode from PNG
            self.PNGtoGcode(pos_file_png_exported, pos_file_png_BW, pos_file_gcode)
            
            # remove the exported picture 
            if os.path.isfile(pos_file_png_exported):
                os.remove(pos_file_png_exported)    

            # remove the tmp svg picture 
            if os.path.isfile(current_svg_file):
                os.remove(current_svg_file)    
                
        else:
            errormsg("Directory does not exist! Please specify existing '--imgDirName'!")
    

    
    ## Export PNG from Inkscape        
    def exportPage(self,pos_file_png_exported, current_file, bg_color):		
        if self.options.imgResolution < 1:
            DPI = str(round(1.0 / self.options.imgSpotSize * 25.4, 3))
        else:
            DPI = str(round(float(self.options.imgResolution) * 25.4, 3))

        # select export command option depending on major version
        if majorVersion < 1:
            # 0.9x
            exportCmd = '-e'
        else:
            # 1.x
            exportCmd = '-o'

        if self.options.imgFullPage:
            imageCmd = '-C'
        else:
            imageCmd = '-D'

        command='inkscape %s %s "%s" -b "%s" -d %s %s' % (imageCmd, exportCmd, pos_file_png_exported, bg_color, DPI, current_file)
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return_code = p.wait()
        stdout, stderr = p.communicate()
        # inkscape 1.1.2 put any output in stderr, so only stop processing if there is a warning in it.
        if "WARNING" in stderr.decode('utf8'):
            msg = 'CMD:\n'+ command + '\n\nSTDOUT:\n' + stdout.decode('utf8')+"\n\nSTDERR:\n"+stderr.decode('utf8')
            command='inkscape --version'
            p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return_code = p.wait()
            stdout, stderr = p.communicate()
            msg = msg + '\n\nVersion: ' + stdout.decode('utf8')
            errormsg(msg)
            exit()

    ## Convert PNG to GCode
    def PNGtoGcode(self,pos_file_png_exported,pos_file_png_BW,pos_file_gcode):
            
        reader = png.Reader(pos_file_png_exported) # read PNG File from Inkscape export
        
        w, h, pixels, metadata = reader.read_flat()
        
        matrice = [[255 for i in range(w)]for j in range(h)]  # create an empty (White) image matrix for grayscale data

        ##############################################################################################################
        ## Convert (RGB) image into 8bit greyscale 
        ##############################################################################################################
        
        if self.options.imgGrayType == 1:
            #0.21R + 0.71G + 0.07B
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    #matrice[y][x] = int(pixels[pixel_position]*0.21 + pixels[(pixel_position+1)]*0.71 + pixels[(pixel_position+2)]*0.07)
                    matrice[y][x] = int(pixels[pixel_position]*0.213 + pixels[(pixel_position+1)]*0.713 + pixels[(pixel_position+2)]*0.074)
        
        elif self.options.imgGrayType == 2:
            #(R+G+B)/3
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrice[y][x] = int((pixels[pixel_position] + pixels[(pixel_position+1)]+ pixels[(pixel_position+2)]) / 3 )

        elif self.options.imgGrayType == 3:
            #R
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrice[y][x] = int(pixels[pixel_position])

        elif self.options.imgGrayType == 4:
            #G
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrice[y][x] = int(pixels[(pixel_position+1)])
        
        elif self.options.imgGrayType == 5:
            #B
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrice[y][x] = int(pixels[(pixel_position+2)])
                
        elif self.options.imgGrayType == 6:
            #Max Color
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    list_RGB = pixels[pixel_position] , pixels[(pixel_position+1)] , pixels[(pixel_position+2)]
                    matrice[y][x] = int(max(list_RGB))

        else:
            #Min Color
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    list_RGB = pixels[pixel_position] , pixels[(pixel_position+1)] , pixels[(pixel_position+2)]
                    matrice[y][x] = int(min(list_RGB))
        

        ##############################################################################################################
        ## Generate black and white or greyscale image
        ##############################################################################################################
        WHITE = 255
        BLACK =   0
        W=WHITE
        B=BLACK
        WHITE_FP = 1.0
        
        matrice_BN = [[WHITE for i in range(w)]for j in range(h)]
        matrice_FP = [[WHITE_FP for i in range(w)]for j in range(h)]
        
        conversionTypeText = 'unknown'
        
        if self.options.imgConvType == 1:
            # B/W fixed threshold
            soglia = self.options.imgBWthreshold
            conversionTypeText = 'B/W fixed threshold (TH:%i)'%(soglia)
            
            for y in range(h): 
                for x in range(w):
                    if matrice[y][x] >= soglia :
                        matrice_BN[y][x] = WHITE
                    else:
                        matrice_BN[y][x] = BLACK

                
        elif self.options.imgConvType == 2:
            # B/W random threshold
            from random import randint
            conversionTypeText = 'B/W random threshold'
            
            for y in range(h): 
                for x in range(w): 
                    soglia = randint(20,235)
                    if matrice[y][x] >= soglia :
                        matrice_BN[y][x] = WHITE
                    else:
                        matrice_BN[y][x] = BLACK
    
            
        elif self.options.imgConvType == 3:
            # Halftone
            conversionTypeText = 'Halftone'
            
            Step1 = [[W,W,W,W,W],[W,W,W,W,W],[W,W,B,W,W],[W,W,W,W,W],[W,W,W,W,W]]
            Step2 = [[W,W,W,W,W],[W,W,B,W,W],[W,B,B,B,W],[W,W,B,W,W],[W,W,W,W,W]]
            Step3 = [[W,W,B,W,W],[W,B,B,B,W],[B,B,B,B,B],[W,B,B,B,W],[W,W,B,W,W]]
            Step4 = [[W,B,B,B,W],[B,B,B,B,B],[B,B,B,B,B],[B,B,B,B,B],[W,B,B,B,W]]
            
            for y in range(int(h/5)): 
                for x in range(int(w/5)): 
                    media = 0
                    for y2 in range(5):
                        for x2 in range(5):
                            media +=  matrice[y*5+y2][x*5+x2]
                    media = media /25
                    for y3 in range(5):
                        for x3 in range(5):
                            if media >= 250 and media <= 255:   matrice_BN[y*5+y3][x*5+x3] =    WHITE
                            if media >= 190 and media < 250:    matrice_BN[y*5+y3][x*5+x3] =    Step1[y3][x3]
                            if media >= 130 and media < 190:    matrice_BN[y*5+y3][x*5+x3] =    Step2[y3][x3]
                            if media >= 70 and media < 130:     matrice_BN[y*5+y3][x*5+x3] =    Step3[y3][x3]
                            if media >= 10 and media < 70:      matrice_BN[y*5+y3][x*5+x3] =    Step4[y3][x3]		
                            if media >= 0 and media < 10:       matrice_BN[y*5+y3][x*5+x3] =    BLACK


        elif self.options.imgConvType == 4:
            # Halftone row
            conversionTypeText = 'Halftone row'

            Step1r = [W,W,B,W,W]
            Step2r = [W,B,B,W,W]
            Step3r = [W,B,B,B,W]
            Step4r = [B,B,B,B,W]

            for y in range(h): 
                for x in range(int(w/5)): 
                    media = 0
                    for x2 in range(5):
                        media +=  matrice[y][x*5+x2]
                    media = media /5
                    for x3 in range(5):
                        if media >= 250 and media <= 255:       matrice_BN[y][x*5+x3] =     WHITE
                        if media >= 190 and media < 250:        matrice_BN[y][x*5+x3] =     Step1r[x3]
                        if media >= 130 and media < 190:        matrice_BN[y][x*5+x3] =     Step2r[x3]
                        if media >= 70 and media < 130:         matrice_BN[y][x*5+x3] =     Step3r[x3]
                        if media >= 10 and media < 70:          matrice_BN[y][x*5+x3] =     Step4r[x3]
                        if media >= 0 and media < 10:           matrice_BN[y][x*5+x3] =     BLACK


        elif self.options.imgConvType == 5:
            # Halftone column
            conversionTypeText = 'Halftone column'

            Step1c = [W,W,B,W,W]
            Step2c = [W,B,B,W,W]
            Step3c = [W,B,B,B,W]
            Step4c = [B,B,B,B,W]

            for y in range(int(h/5)):
                for x in range(w):
                    media = 0
                    for y2 in range(5):
                        media +=  matrice[y*5+y2][x]
                    media = media /5
                    for y3 in range(5):
                        if media >= 250 and media <= 255:       matrice_BN[y*5+y3][x] =     WHITE
                        if media >= 190 and media < 250:        matrice_BN[y*5+y3][x] =     Step1c[y3]
                        if media >= 130 and media < 190:        matrice_BN[y*5+y3][x] =     Step2c[y3]
                        if media >= 70 and media < 130:         matrice_BN[y*5+y3][x] =     Step3c[y3]
                        if media >= 10 and media < 70:          matrice_BN[y*5+y3][x] =     Step4c[y3]
                        if media >= 0 and media < 10:           matrice_BN[y*5+y3][x] =     BLACK
        
        elif self.options.imgConvType == 6:
            # Simple2D
            soglia = self.options.imgBWthreshold
            conversionTypeText = 'Simple2D (TH:%i)'%(soglia)
            
            for y in range(h):
                for x in range(w):
                    pixl = matrice[y][x]
                    if pixl >= soglia: pixl = WHITE
                    matrice_FP[y][x] = float(pixl) / 255.0

            for y in range(0, h-1):
                for x in range(0, w-1):
                    # threshold step
                    if matrice_FP[y][x] > 0.5:
                        err = matrice_FP[y][x] - 1.0
                        matrice_FP[y][x] = 1.0
                    else:
                        err = matrice_FP[y][x]
                        matrice_FP[y][x] = 0.0
                    # error diffusion step
                    matrice_FP[y  ][x+1] =  matrice_FP[y  ][x+1] + (0.5 * err)
                    matrice_FP[y+1][x  ] =  matrice_FP[y+1][x  ] + (0.5 * err)

            for y in range(h):
                for x in range(w):
                    pixl = int(matrice_FP[y][x] * 255)
                    if pixl > WHITE: pixl = WHITE
                    if pixl < BLACK: pixl = BLACK
                    matrice_BN[y][x] = pixl


        elif self.options.imgConvType == 7:
            # Floyd-Steinberg
            soglia = self.options.imgBWthreshold
            conversionTypeText = 'Floyd-Steinberg (TH:%i)'%(soglia)

            for y in range(h):
                for x in range(w):
                    pixl = matrice[y][x]
                    if pixl >= soglia: pixl = WHITE
                    matrice_FP[y][x] = float(pixl) / 255.0

            for y in range(0, h-1):
                for x in range(1, w-1):
                    if matrice_FP[y][x] > 0.5:
                        err = matrice_FP[y][x] - 1.0
                        matrice_FP[y][x] = 1.0
                    else:
                        err = matrice_FP[y][x]
                        matrice_FP[y][x] = 0.0
                    # error diffusion step
                    matrice_FP[y  ][x+1] =  matrice_FP[y  ][x+1] + ((7.0/16.0) * err)
                    matrice_FP[y+1][x-1] =  matrice_FP[y+1][x-1] + ((3.0/16.0) * err)
                    matrice_FP[y+1][x  ] =  matrice_FP[y+1][x  ] + ((5.0/16.0) * err)
                    matrice_FP[y+1][x+1] =  matrice_FP[y+1][x+1] + ((1.0/16.0) * err)

            for y in range(h):
                for x in range(w):
                    pixl = int(matrice_FP[y][x] * 255)
                    if pixl > WHITE: pixl = WHITE
                    if pixl < BLACK: pixl = BLACK
                    matrice_BN[y][x] = pixl

        elif self.options.imgConvType == 8:
            # Jarvis-Judice-Ninke
            soglia = self.options.imgBWthreshold
            conversionTypeText = 'Jarvis-Judice-Ninke (TH:%i)'%(soglia)
            
            for y in range(h):
                for x in range(w):
                    pixl = matrice[y][x]
                    if pixl >= soglia: pixl = WHITE
                    matrice_FP[y][x] = float(pixl) / 255.0

            for y in range(0, h-2):
                for x in range(2, w-2):
                    # threshold step
                    if matrice_FP[y][x] > 0.5:
                        err = matrice_FP[y][x] - 1.0
                        matrice_FP[y][x] = 1.0
                    else:
                        err = matrice_FP[y][x]
                        matrice_FP[y][x] = 0.0
                    # error diffusion step
                    matrice_FP[y  ][x+1] =  matrice_FP[y  ][x+1] + ((7.0/48.0) * err)
                    matrice_FP[y  ][x+2] =  matrice_FP[y  ][x+2] + ((5.0/48.0) * err)

                    matrice_FP[y+1][x-2] =  matrice_FP[y+1][x-2] + ((3.0/48.0) * err)
                    matrice_FP[y+1][x-1] =  matrice_FP[y+1][x-1] + ((5.0/48.0) * err)
                    matrice_FP[y+1][x  ] =  matrice_FP[y+1][x  ] + ((7.0/48.0) * err)
                    matrice_FP[y+1][x+1] =  matrice_FP[y+1][x+1] + ((5.0/48.0) * err)
                    matrice_FP[y+1][x+2] =  matrice_FP[y+1][x+2] + ((3.0/48.0) * err)

                    matrice_FP[y+2][x-2] =  matrice_FP[y+2][x-2] + ((1 / 48) * err)
                    matrice_FP[y+2][x-1] =  matrice_FP[y+2][x-1] + ((3 / 48) * err)
                    matrice_FP[y+2][x  ] =  matrice_FP[y+2][x  ] + ((5 / 48) * err)
                    matrice_FP[y+2][x+1] =  matrice_FP[y+2][x+1] + ((3 / 48) * err)
                    matrice_FP[y+2][x+2] =  matrice_FP[y+2][x+2] + ((1 / 48) * err)

            for y in range(h):
                for x in range(w):
                    pixl = int(matrice_FP[y][x] * 255)
                    if pixl > WHITE: pixl = WHITE
                    if pixl < BLACK: pixl = BLACK
                    matrice_BN[y][x] = pixl
        elif self.options.imgConvType == 9:
            #Grayscale
            conversionTypeText = 'Grayscale (Res:%i)'%(self.options.imgGrayResolution)
            
            if self.options.imgGrayResolution == 256:
                matrice_BN = matrice
            else:
                # create look up tabel
                lookUpTabel = list(range(256))
                #grayscale_resolution = 256 / self.options.imgGrayResolution
                if self.options.imgGrayResolution > 1:
                    a = (255.0/(self.options.imgGrayResolution-1))
                else:  
                    a = 255.0
                for idx in range(256):
                    lookUpTabel[idx] = int(round(round(float(idx) / a) * a))	
                        
                for y in range(h): 
                    for x in range(w):
                        matrice_BN[y][x] = lookUpTabel[matrice[y][x]]
            
        else:
            errormsg("Convertion type does not exist!")


        # Save preview image
        file_img_BN = open(pos_file_png_BW, 'wb')
        png_img = png.Writer(w, h, greyscale=True, bitdepth=8)
        png_img.write(file_img_BN, matrice_BN)
        file_img_BN.close()


        ##############################################################################################################
        ## Generate G-Code
        ##############################################################################################################
        if self.options.imgPreviewOnly == False: #Genero Gcode solo se devo

            def generateGCodeLine(source, values):
                gCodeString = source
                for key in values.keys():
                    gCodeString = gCodeString.replace('{'+key+'}', values[key])
                    
                return gCodeString
            
            def floatToString(floatValue):
                result = ('%.4f' % floatValue).rstrip('0').rstrip('.')
                return '0' if result == '-0' else result

            xOffset = 0.0          # set 0 point of G-Code
            yOffset = 0.0          # set 0 point of G-Code

            abDiameter = self.options.imgRotDiameter

            settingName = self.options.gc1Setting
            maxPower = self.options.gc1MaxPower
            minPower = self.options.gc1MinPower
            feedRate = self.options.gc1FeedRate
            accelDistance = self.options.gc1AccDistance
            zPos = self.options.gc1LevelZ
            optimizedScanLine = self.options.gc1OptScnLine
            offsetZigZag = self.options.gc1ZigZagOffset
            scanType = self.options.gc1ScanType
            xZeroPoint = self.options.gc1ZeroPointX
            yZeroPoint = self.options.gc1ZeroPointY
            startCmd = self.options.gc1StartCode
            postCmd = self.options.gc1PostCode
            lineCmd = self.options.gc1LineCode
            pixelCmd = self.options.gc1PixelCode
            laserOnCmd = self.options.gc1LaserOn
            laserOffCmd = self.options.gc1LaserOff
            laserOnThreshold = self.options.gc1LOnThreshold
            singlePowerInterleaved = self.options.gc1Interleaved
            flipX = self.options.gc1FlipX
            flipY = self.options.gc1FlipY
            invertBW = self.options.gc1Invert
            laserGamma = self.options.gc1Gamma
            
            if maxPower <= minPower:
                errormsg("Maximum laser power value must be greater then minimum laser power value!")

            
            GCODE_NL = '\n'
            valueList = collections.OrderedDict()
            valueList['PCMF'] = laserOffCmd     # must be first, so it is parsed fist and can include the other variables
            valueList['PCMT'] = laserOffCmd     # must be first, so it is parsed fist and can include the other variables
            valueList['NL'] =   GCODE_NL
            valueList['XPOS'] = '0'
            valueList['YPOS'] = '0'
            valueList['ZPOS'] = '%s'%(floatToString(zPos))
            valueList['APOS'] = '0'
            valueList['BPOS'] = '0'
            valueList['FEED'] = '%s'%(floatToString(feedRate))  # Feed Rate Configuration value
            valueList['SCNC'] = 'init'
            valueList['SCNL'] = 'init'
            valueList['PDIR'] = 'init'
            valueList['POWT'] = '%s'%(floatToString(minPower))  # Calculated Pixel Power (To direction, Standard GCode behavior)
            valueList['POWF'] = '%s'%(floatToString(minPower))  # Calculated Pixel Power (From direction)
            valueList['POWM'] = '%s'%(floatToString(minPower))  # Power Min Configuration value
            valueList['POWX'] = '%s'%(floatToString(maxPower))  # Power Max Configuration value
            valueList['POWL'] = '%s'%(floatToString(0))         # Power Max in Line
            valueList['PIXV'] = '%i'%(WHITE+1)                  # Pixel Value (0=Black ... 255=White, 256=travel path)

 
            ########################################## Start gCode
            if flipX == True:
                for y in range(h):
                    matrice_BN[y].reverse()

            if flipY == True: #Inverto asse Y solo se flip_y = False     
                #-> coordinate Cartesiane (False) Coordinate "informatiche" (True)
                matrice_BN.reverse()
                
            if invertBW == True:
                for y in range(h):
                    matrice_BN[y] = [ WHITE-j for j in matrice_BN[y] ]


            # distance between lines (steps)
            if self.options.imgResolution < 1:
                Scala = self.options.imgSpotSize 
            else:
                Scala = 1.0/float(self.options.imgResolution)

            if accelDistance <= 0:
                accelDistance = Scala
                
            xOffsetText = 'unknown'
            if xZeroPoint == 0:
                # left
                xOffset = 0.0
                xOffsetText = 'Left'
            elif xZeroPoint == 1:
                # center
                xOffset = -1.0 * float(w) * Scala / 2.0
                xOffsetText = 'Center'
            elif xZeroPoint == 2:
                # right
                xOffset = -1.0 * float(w) * Scala
                xOffsetText = 'Right'

            yOffsetText = 'unknown'
            if yZeroPoint == 0:
                # top
                yOffset = 0.0
                yOffsetText = 'Top'
            elif yZeroPoint == 1:
                # middle
                yOffset = float(h) * Scala / 2.0
                yOffsetText = 'Middle'
            elif yZeroPoint == 2:
                # bottom
                yOffset = float(h) * Scala
                yOffsetText = 'Bottom'

            scanTypeText = 'unknown'
            scanX = True
            if scanType == 0:
                # Always left -> right
                scanTypeText = 'Always left -> right'
                scanX = True
            elif scanType == 1:
                # Always right <- left
                scanTypeText = 'Always right <- left'
                scanX = True
            elif scanType == 2:
                # Always zigzag
                scanTypeText = 'Always zigzag X'
                scanX = True
            elif scanType == 3:
                # Fastes path
                scanTypeText = 'Fastest X'
                scanX = True
            elif scanType == 4:
                # Always top \/ bottom
                scanTypeText = 'Always top \/ bottom'
                scanX = False
            elif scanType == 5:
                # Always bottom /\ top
                scanTypeText = 'Always bottom /\\ top'
                scanX = False
            elif scanType == 6:
                # Always zigzag
                scanTypeText = 'Always zigzag Y'
                scanX = False
            elif scanType == 7:
                # Fastes path
                scanTypeText = 'Fastest Y'
                scanX = False

            file_gcode = open(pos_file_gcode, 'w')  #Creo il file
            
            #Configurazioni iniziali standard Gcode
            file_gcode.write('; Generated with:'+ GCODE_NL)
            file_gcode.write(';   Inkscape %s and "Raster 2 Laser Gcode generator NG"'%(inkVersion) + GCODE_NL)
            file_gcode.write(';   by RKtech (based on 305 Engineering code)' + GCODE_NL)
            file_gcode.write(';' + GCODE_NL)
            file_gcode.write('; Image:'+ GCODE_NL)
            file_gcode.write(';   Pixel size:               %i x %i'%(w, h) + GCODE_NL)
            file_gcode.write(';   Size:                     %s x %s mm'%(floatToString(w*Scala), floatToString(h*Scala)) + GCODE_NL)
            file_gcode.write(';' + GCODE_NL)
            file_gcode.write('; Parameter setting "%s":'%(settingName)+ GCODE_NL)
            file_gcode.write(';   Zero point:               %s/%s'%(xOffsetText,yOffsetText) + GCODE_NL)
            file_gcode.write(';   Laser spot size           %s mm'%(floatToString(Scala)) + GCODE_NL)
            file_gcode.write(';   Engraving speed:          %s mm/min'%(floatToString(feedRate)) + GCODE_NL)
            file_gcode.write(';   Minimum power value:      %s'%(floatToString(minPower)) + GCODE_NL)
            file_gcode.write(';   Maximum power value:      %s'%(floatToString(maxPower)) + GCODE_NL)
            file_gcode.write(';   Acceleration distance:    %s mm'%(floatToString(accelDistance)) + GCODE_NL)
            file_gcode.write(';   Conversion algorithm:     %s'%(conversionTypeText) + GCODE_NL)
            file_gcode.write(';   Scan Type:                %s'%(scanTypeText) + GCODE_NL)
            file_gcode.write(';   Flip X:                   %s'%('Yes' if flipX else 'No') + GCODE_NL)
            file_gcode.write(';   Flip Y:                   %s'%('Yes' if flipY else 'No') + GCODE_NL)
            if self.options.debug:
                file_gcode.write(';' + GCODE_NL)
                file_gcode.write('; Debug Parameters:'+ GCODE_NL)
                file_gcode.write(';   --imgDirName              "%s"'%(self.options.imgDirName) + GCODE_NL)
                file_gcode.write(';   --imgFileName             "%s"'%(self.options.imgFileName) + GCODE_NL)
                file_gcode.write(';   --imgNumFileSuffix        "%s"'%(self.options.imgNumFileSuffix) + GCODE_NL)
                file_gcode.write(';   --imgBGcolor              "%s"'%(self.options.imgBGcolor) + GCODE_NL)
                file_gcode.write(';   --imgResolution           "%s"'%(self.options.imgResolution) + GCODE_NL)
                file_gcode.write(';   --imgSpotSize             "%s"'%(self.options.imgSpotSize) + GCODE_NL)
                file_gcode.write(';   --imgGrayType             "%s"'%(self.options.imgGrayType) + GCODE_NL)
                file_gcode.write(';   --imgConvType             "%s"'%(self.options.imgConvType) + GCODE_NL)
                file_gcode.write(';   --imgBWthreshold          "%s"'%(self.options.imgBWthreshold) + GCODE_NL)
                file_gcode.write(';   --imgGrayResolution       "%s"'%(self.options.imgGrayResolution) + GCODE_NL)
                file_gcode.write(';   --imgRotDiameter          "%s"'%(self.options.imgRotDiameter) + GCODE_NL)
                file_gcode.write(';   --imgFullPage             "%s"'%(self.options.imgFullPage) + GCODE_NL)
                file_gcode.write(';   --imgPreviewOnly          "%s"'%(self.options.imgPreviewOnly) + GCODE_NL)
                file_gcode.write(';   --gc1Setting              "%s"'%(settingName) + GCODE_NL)
                file_gcode.write(';   --gc1StartCode            "%s"'%(startCmd) + GCODE_NL)
                file_gcode.write(';   --gc1PostCode             "%s"'%(postCmd) + GCODE_NL)
                file_gcode.write(';   --gc1LineCode             "%s"'%(lineCmd) + GCODE_NL)
                file_gcode.write(';   --gc1PixelCode            "%s"'%(pixelCmd) + GCODE_NL)
                file_gcode.write(';   --gc1LaserOn              "%s"'%(laserOnCmd) + GCODE_NL)
                file_gcode.write(';   --gc1LaserOff             "%s"'%(laserOffCmd) + GCODE_NL)
                file_gcode.write(';   --gc1LOnThreshold         "%s"'%(laserOnThreshold) + GCODE_NL)
                file_gcode.write(';   --gc1FeedRate             "%s"'%(feedRate) + GCODE_NL)
                file_gcode.write(';   --gc1MinPower             "%s"'%(minPower) + GCODE_NL)
                file_gcode.write(';   --gc1MaxPower             "%s"'%(maxPower) + GCODE_NL)
                file_gcode.write(';   --gc1AccDistance          "%s"'%(accelDistance) + GCODE_NL)
                file_gcode.write(';   --gc1LevelZ               "%s"'%(zPos) + GCODE_NL)
                file_gcode.write(';   --gc1FlipX                "%s"'%(flipX) + GCODE_NL)
                file_gcode.write(';   --gc1FlipY                "%s"'%(flipY) + GCODE_NL)
                file_gcode.write(';   --gc1Invert               "%s"'%(invertBW) + GCODE_NL)
                file_gcode.write(';   --gc1Gamma                "%s"'%(laserGamma) + GCODE_NL)
                file_gcode.write(';   --gc1ZeroPointX           "%s"'%(xZeroPoint) + GCODE_NL)
                file_gcode.write(';   --gc1ZeroPointY           "%s"'%(yZeroPoint) + GCODE_NL)
                file_gcode.write(';   --gc1OptScnLine           "%s"'%(optimizedScanLine) + GCODE_NL)
                file_gcode.write(';   --gc1ScanType             "%s"'%(scanType) + GCODE_NL)
                file_gcode.write(';   --gc1ZigZagOffset         "%s"'%(offsetZigZag) + GCODE_NL)
                file_gcode.write(';   --gc1Interleaved          "%s"'%(singlePowerInterleaved) + GCODE_NL)
                
            file_gcode.write(GCODE_NL)
            file_gcode.write('; Start Code' + GCODE_NL)	
            file_gcode.write(generateGCodeLine(startCmd, valueList) + GCODE_NL)	

            ########################################## Picture gCode
            file_gcode.write(GCODE_NL + '; Image Code' + GCODE_NL)	

            lastPosition = 0.0
            zigZagOffset = 0.0
            scanLeftRight = False

            scanLines = h if scanX else w
            imageColums = w if scanX else h
            #scanLines = range(h) if scanX else range(w)
            #scanLine = y
            
            ##################################################################
            # Iterate scan Lines
            for scanLine in range(scanLines): 


                #
                if scanX:
                    imageLineDataMaster = matrice_BN[scanLine]
                    yPos = -1.0 * float(scanLine)*Scala + yOffset
                    valueList['YPOS'] = '%s'%(floatToString(yPos))
                    valueList['APOS'] = '%s'%(floatToString(yPos * 360.0 / (math.pi * abDiameter)))
                else:
                    imageLineDataMaster = [matrice_BN[j][scanLine] for j in range(imageColums)]
                    xPos = float(scanLine)*Scala + xOffset
                    valueList['XPOS'] = '%s'%(floatToString(xPos))
                    valueList['BPOS'] = '%s'%(floatToString(xPos * 360.0 / (math.pi * abDiameter)))
                valueList['SCNL'] = '%i'%(scanLine)
            
                # Multi Line, repeat the line, each with single power values from light to dark
                if singlePowerInterleaved:
                    repeats = []
                    for j in reversed(range(WHITE-1)):
                        if j in imageLineDataMaster:
                            repeats.append(j)
                else:
                    repeats = range(1)
                    
                for repeat in repeats:
                    if singlePowerInterleaved:
                        imageLineData = [(repeat if imageLineDataMaster[j] == repeat else WHITE) for j in range(imageColums)]
                        minPixelValue = repeat
                        valueList['SCNL'] = '%i.%03i'%(scanLine,repeat)
                    else:
                        imageLineData = imageLineDataMaster
                        minPixelValue = min(imageLineData)
                    
                    maxLinePower = (float(WHITE - minPixelValue) * (maxPower - minPower) / 255.0) + minPower
                    valueList['POWL'] = '%s'%(floatToString(maxLinePower))
                    
                    
                    ## Scan line optimization
                    first_laser_on = -1
                    last_laser_on = -1
                    if optimizedScanLine == 1:
                        # search for first and last pixel with laser on (Pixel value not pure white)
                        # "remove blank lines, reduce scan line length"
                        for j in range(imageColums):
                            #if imageLineData[j] != WHITE:
                            if imageLineData[j] <= laserOnThreshold:
                                first_laser_on = j
                                break
                        for j in reversed(range(imageColums)):
                            #if imageLineData[j] != WHITE:
                            if imageLineData[j] <= laserOnThreshold:
                                last_laser_on = j
                                break                
                    elif optimizedScanLine == 2:
                        # check if there is at least one not white pixel
                        # "remove blank lines only"
                        for j in range(imageColums):
                            #if imageLineData[j] != WHITE:
                            if imageLineData[j] <= laserOnThreshold:
                                first_laser_on = 0
                                last_laser_on = imageColums-1
                                break
                    else:
                        # move the laser above the hole page
                        # "no movement optimization"
                        first_laser_on = 0
                        last_laser_on = imageColums-1
                        
                    ## direction movement optimization        
                    if scanType == 0:
                        # alsways left -> right
                        scanLeftRight = True
                    elif scanType == 1:
                        # alsways right <- left
                        scanLeftRight = False
                    elif scanType == 2:
                        # alsways zigzag X
                        scanLeftRight = False if scanLeftRight else True
                    elif scanType == 3:
                        # fastes path X
                        startLeft =  float(first_laser_on)*Scala - accelDistance + xOffset
                        startRight = float(last_laser_on+1)*Scala + accelDistance + xOffset
                        if abs(lastPosition-startLeft) < abs(lastPosition-startRight):
                            scanLeftRight = True
                        else:
                            scanLeftRight = False
                    elif scanType == 4:
                        # alsways top \/ bottom
                        scanLeftRight = True
                    elif scanType == 5:
                        # alsways bottom /\ top
                        scanLeftRight = False
                    elif scanType == 6:
                        # alsways zigzag X
                        scanLeftRight = False if scanLeftRight else True
                    elif scanType == 7:
                        # fastes path Y
                        startLeft =  -1.0 * (float(first_laser_on)*Scala - accelDistance) + yOffset
                        startRight = -1.0 * (float(last_laser_on+1)*Scala + accelDistance) + yOffset
                        if abs(lastPosition-startLeft) < abs(lastPosition-startRight):
                            scanLeftRight = True
                        else:
                            scanLeftRight = False
                        
                    if first_laser_on >= 0 and last_laser_on >= 0:
                        directionCountX = 0
                        directionCountY = 0
                        if scanLeftRight:
                            # left to right / top to bottom
                            scanColumns = range(first_laser_on, last_laser_on+1)
                            startLine = first_laser_on
                            directionCount = 1
                            reverseOffset = 0
                            accelDist = accelDistance
                            valueList['PDIR'] = '->' if scanX else '\/'
                            zigZagOffset = 0.0

                        else:
                            # right to left / bottom to top
                            scanColumns = range(last_laser_on, first_laser_on-1, -1)
                            startLine = last_laser_on
                            directionCount = -1
                            reverseOffset = 1
                            accelDist = 0.0 - accelDistance
                            valueList['PDIR'] = '<-' if scanX else '/\\'    
                            zigZagOffset = offsetZigZag

                        # accelerate phase
                        if scanX:
                            xPos = float(startLine + reverseOffset)*Scala - accelDist + xOffset + zigZagOffset
                        else:
                            yPos = -1.0 * (float(startLine + reverseOffset)*Scala - accelDist) + yOffset + zigZagOffset

                        pixelValue     = WHITE + 1      # travel phase
                        pixelValueFrom = pixelValue
                        pixelValueTo   = pixelValue

                        power     = minPower
                        powerFrom = power
                        powerTo   = power

                        valueList['SCNC'] = 'acc'
                        valueList['XPOS'] = '%s'%(floatToString(xPos))
                        valueList['YPOS'] = '%s'%(floatToString(yPos))
                        valueList['ZPOS'] = '%s'%(floatToString(zPos))
                        valueList['APOS'] = '%s'%(floatToString(yPos * 360.0 / (math.pi * abDiameter)))
                        valueList['BPOS'] = '%s'%(floatToString(xPos * 360.0 / (math.pi * abDiameter)))
                        valueList['POWT'] = '%s'%(floatToString(powerTo))
                        valueList['POWF'] = '%s'%(floatToString(powerFrom))
                        valueList['PCMT'] = laserOffCmd
                        valueList['PCMF'] = laserOffCmd
                        valueList['PIXV'] = '%i'%(pixelValueTo)
                        
                        file_gcode.write(generateGCodeLine(lineCmd, valueList) + GCODE_NL)

                        ##################################################################
                        # Iterate scan columns
                        laserPowerCange = True
                        for scanColumn in scanColumns:
                            if laserPowerCange:
                                if scanX:
                                    xPos = float(scanColumn + reverseOffset)*Scala + xOffset + zigZagOffset
                                else:
                                    yPos = -1.0 * float(scanColumn + reverseOffset)*Scala + yOffset + zigZagOffset

                                pixelValueTo   = pixelValue
                                pixelValue     = imageLineData[scanColumn]
                                pixelValueFrom = pixelValue
                                    
                                powerTo   = power
                                #power = (float(WHITE - pixelValue) * (maxPower - minPower) / 255.0) + minPower
                                power = ((WHITE_FP - ((float(pixelValue) / float(WHITE)) ** laserGamma)) * (maxPower - minPower)) + minPower
                                powerFrom = power

                                valueList['SCNC'] = '%i'%(scanColumn+reverseOffset)    
                                valueList['XPOS'] = '%s'%(floatToString(xPos))
                                valueList['YPOS'] = '%s'%(floatToString(yPos))
                                valueList['ZPOS'] = '%s'%(floatToString(zPos))
                                valueList['APOS'] = '%s'%(floatToString(yPos * 360.0 / (math.pi * abDiameter)))
                                valueList['BPOS'] = '%s'%(floatToString(xPos * 360.0 / (math.pi * abDiameter)))
                                valueList['POWT'] = '%s'%(floatToString(powerTo))
                                valueList['POWF'] = '%s'%(floatToString(powerFrom))
                                valueList['PCMT'] = laserOnCmd if pixelValueTo   <= laserOnThreshold else laserOffCmd
                                valueList['PCMF'] = laserOnCmd if pixelValueFrom <= laserOnThreshold else laserOffCmd
                                valueList['PIXV'] = '%i'%(pixelValueTo)
                                file_gcode.write(generateGCodeLine(pixelCmd, valueList) + GCODE_NL)
                        
                            laserPowerCange = False
                            if scanColumn == scanColumns[-1]:
                                laserPowerCange = True
                                #print(x, matrice_BN[y][x], 0, laserPowerCange)
                            else:
                                if imageLineData[scanColumn] != imageLineData[scanColumn + directionCount]:
                                    laserPowerCange = True
                                #print(x, matrice_BN[y][x], matrice_BN[y][x+directionCount], laserPowerCange)

                        
                        if scanX:
                            xPos = float(scanColumn + 1 - reverseOffset)*Scala + xOffset + zigZagOffset
                        else:
                            yPos = -1.0 * float(scanColumn + 1 - reverseOffset)*Scala + yOffset + zigZagOffset
                            
                        pixelValueTo   = pixelValue
                        pixelValue     = WHITE + 1      # travel phase
                        pixelValueFrom = pixelValue

                        powerTo   = power
                        power     = minPower
                        powerFrom = power

                        valueList['SCNC'] = '%i'%(scanColumn+1-reverseOffset)    
                        valueList['XPOS'] = '%s'%(floatToString(xPos))
                        valueList['YPOS'] = '%s'%(floatToString(yPos))
                        valueList['ZPOS'] = '%s'%(floatToString(zPos))
                        valueList['APOS'] = '%s'%(floatToString(yPos * 360.0 / (math.pi * abDiameter)))
                        valueList['BPOS'] = '%s'%(floatToString(xPos * 360.0 / (math.pi * abDiameter)))
                        valueList['POWT'] = '%s'%(floatToString(powerTo))
                        valueList['POWF'] = '%s'%(floatToString(powerFrom))
                        valueList['PCMT'] = laserOnCmd if pixelValueTo <= laserOnThreshold else laserOffCmd
                        valueList['PCMF'] = laserOffCmd
                        valueList['PIXV'] = '%i'%(pixelValueTo)
                        file_gcode.write(generateGCodeLine(pixelCmd, valueList) + GCODE_NL)

                        # decelerate phase
                        if scanX:
                            xPos = float(scanColumn + 1 - reverseOffset)*Scala + accelDist + xOffset + zigZagOffset
                        else:
                            yPos = -1.0 * (float(scanColumn + 1 - reverseOffset)*Scala + accelDist) + yOffset + zigZagOffset

                        pixelValueTo   = pixelValue

                        powerTo = power
                        
                        valueList['SCNC'] = 'dec'    
                        valueList['XPOS'] = '%s'%(floatToString(xPos))
                        valueList['YPOS'] = '%s'%(floatToString(yPos))
                        valueList['ZPOS'] = '%s'%(floatToString(zPos))
                        valueList['APOS'] = '%s'%(floatToString(yPos * 360.0 / (math.pi * abDiameter)))
                        valueList['BPOS'] = '%s'%(floatToString(xPos * 360.0 / (math.pi * abDiameter)))
                        valueList['POWT'] = '%s'%(floatToString(powerTo))
                        valueList['PCMT'] = laserOffCmd
                        valueList['PIXV'] = '%i'%(pixelValueTo)
                        file_gcode.write(generateGCodeLine(pixelCmd, valueList) + GCODE_NL)

                        lastPosition = xPos if scanX else yPos


            ########################################## Post gCode
            valueList['SCNL'] = 'exit'
            valueList['SCNC'] = 'exit'
            valueList['PDIR'] = 'exit'

            file_gcode.write('; End Code' + GCODE_NL)
            file_gcode.write(generateGCodeLine(postCmd, valueList) + GCODE_NL)
            file_gcode.close() #Chiudo il file




#######################################################################
## MAIN
#######################################################################

def _main():
    e=GcodeExport()
    e.affect()
    
    exit()

if __name__=="__main__":
    _main()




