# ----------------------------------------------------------------------------
# Copyright (C) 2024 RKtech<info@rktech.de>
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


import sys
import os
import re
import subprocess
import math
import inkex
import png
import array
import collections
import inkcmd

r2l_version = "1.0.4"

# Pull Request #23
# from Pull Request "https://github.com/305engineering/Inkscape/pull/23"
# inkscape > 1.0.0. didn't have the '--extension-directory' parameter any more, so it is removed now
#sys.path.append('/usr/share/inkscape/extensions')
#sys.path.append('/Applications/Inkscape.app/Contents/Resources/extensions') 

def errormsg(msg):
    sys.stderr.write(msg+"\n")


icmd = inkcmd.Init()

# For testing the inkcmd.py
#errormsg("******************************************************")
#errormsg("Inkscape V=%i.%i.%i=%i"%(icmd.version_major, icmd.version_mid, icmd.version_minor, icmd.version_int))
#errormsg(icmd.version)
#errormsg(icmd.command)
#errormsg("-----------------")
#errormsg("STD=<%s>, ERR=<%s>"%icmd.execute("--version"))
#errormsg("******************************************************")

if (icmd.version_major < 1) or ((icmd.version_major == 1) and (icmd.version_mid < 1)):
    errormsg("******************************************************")
    errormsg(" will not run with Inkscape version < 1.1.0")
    errormsg("******************************************************")
    exit()
  
    

class GcodeExport(inkex.Effect):

    ######## read Inkscape parameters
    def __init__(self):
        """init the effetc library and get options from gui"""
        inkex.Effect.__init__(self)

        # To make the notebook parameter happy
        self.arg_parser.add_argument("--nopNB",             type=str,           dest="nopNB",               default="")

        # Config Settings (NOT IMPLEMENTED NOW)
        self.arg_parser.add_argument("--cfgFileName",       type=str,           dest="cfgFileName",         default="")
        self.arg_parser.add_argument("--cfgUseP1",          type=inkex.Boolean, dest="cfgUseP1",            default=False)            
        self.arg_parser.add_argument("--cfgUseG1",          type=inkex.Boolean, dest="cfgUseG1",            default=False)            
        
        # Image Settings
        self.arg_parser.add_argument("--imgDirName",        type=str,           dest="imgDirName",          default="/home/",   help="Directory for files")
        self.arg_parser.add_argument("--imgFileName",       type=str,           dest="imgFileName",         default="gcode",    help="File name")            
        self.arg_parser.add_argument("--imgNumFileSuffix",  type=inkex.Boolean, dest="imgNumFileSuffix",    default=True,       help="Add numeric suffix to filename")            
        self.arg_parser.add_argument("--imgBGcolor",        type=str,           dest="imgBGcolor",          default="")
        self.arg_parser.add_argument("--imgResolution",     type=int,           dest="imgResolution",       default="0")
        self.arg_parser.add_argument("--imgSpotSize",       type=float,         dest="imgSpotSize",         default="0.2")
        self.arg_parser.add_argument("--imgGrayType",       type=int,           dest="imgGrayType",         default="1") 
        self.arg_parser.add_argument("--imgConvType",       type=int,           dest="imgConvType",         default="1") 
        self.arg_parser.add_argument("--imgBWthreshold",    type=int,           dest="imgBWthreshold",      default="128") 
        self.arg_parser.add_argument("--imgGrayResolution", type=int,           dest="imgGrayResolution",   default="256") 
        self.arg_parser.add_argument("--imgRotDiameter",    type=float,         dest="imgRotDiameter",      default="50.0")
        self.arg_parser.add_argument("--imgFullPage",       type=inkex.Boolean, dest="imgFullPage",         default=True) 
        self.arg_parser.add_argument("--imgPreviewOnly",    type=inkex.Boolean, dest="imgPreviewOnly",      default=False) 
        self.arg_parser.add_argument("--dbg",               type=inkex.Boolean, dest="debug",               default=False)

        # GCode (1) Settings
        self.arg_parser.add_argument("--gc1Setting",        type=str,           dest="gc1Setting",          default="")
        self.arg_parser.add_argument("--gc1StartCode",      type=str,           dest="gc1StartCode",        default="")
        self.arg_parser.add_argument("--gc1PostCode",       type=str,           dest="gc1PostCode",         default="")
        self.arg_parser.add_argument("--gc1LineCode",       type=str,           dest="gc1LineCode",         default="")
        self.arg_parser.add_argument("--gc1OffTravelCode",  type=str,           dest="gc1OffTravelCode",         default="")
        self.arg_parser.add_argument("--gc1PixelCode",      type=str,           dest="gc1PixelCode",        default="")
        self.arg_parser.add_argument("--gc1LaserOn",        type=str,           dest="gc1LaserOn",          default="M03")
        self.arg_parser.add_argument("--gc1LaserOff",       type=str,           dest="gc1LaserOff",         default="M05")
        self.arg_parser.add_argument("--gc1LOnThreshold",   type=int,           dest="gc1LOnThreshold",     default="254") 
        self.arg_parser.add_argument("--gc1FeedRate",       type=int,           dest="gc1FeedRate",         default="200") 
        self.arg_parser.add_argument("--gc1MinPower",       type=float,         dest="gc1MinPower",         default="0.0")
        self.arg_parser.add_argument("--gc1MaxPower",       type=float,         dest="gc1MaxPower",         default="100.0")
        self.arg_parser.add_argument("--gc1AccDistance",    type=float,         dest="gc1AccDistance",      default="10.0")
        self.arg_parser.add_argument("--gc1LevelZ",         type=float,         dest="gc1LevelZ",           default="10.0")
        self.arg_parser.add_argument("--gc1FlipX",          type=inkex.Boolean, dest="gc1FlipX",            default=False)
        self.arg_parser.add_argument("--gc1FlipY",          type=inkex.Boolean, dest="gc1FlipY",            default=False)
        self.arg_parser.add_argument("--gc1Invert",         type=inkex.Boolean, dest="gc1Invert",           default=False)
        self.arg_parser.add_argument("--gc1Gamma",          type=float,         dest="gc1Gamma",            default="1.0")
        self.arg_parser.add_argument("--gc1ZeroPointX",     type=int,           dest="gc1ZeroPointX",       default="0")
        self.arg_parser.add_argument("--gc1ZeroPointY",     type=int,           dest="gc1ZeroPointY",       default="0")
        self.arg_parser.add_argument("--gc1OptScnLine",     type=int,           dest="gc1OptScnLine",       default="1")
        self.arg_parser.add_argument("--gc1ScanType",       type=int,           dest="gc1ScanType",         default="3")
        self.arg_parser.add_argument("--gc1ZigZagOffset",   type=float,         dest="gc1ZigZagOffset",     default="0")
        self.arg_parser.add_argument("--gc1Interleaved",    type=inkex.Boolean, dest="gc1Interleaved",      default=False)

        self.conversionTypeText = 'unknown'
           
    ##############################################################################################################################
    ## Proceed Extension 
    ## Return: <PNG-File> and optional <G-Code-File>
    ##############################################################################################################################
    def effect(self):

        #current_file = self.args[-1]
        svg_file = self.options.input_file
        
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
            
            
            # Generate PNG from SVG
            self.exportPNG(pos_file_png_exported, svg_file, bg_color)
            
            # Convert Image to BW/Greyscale
            #self.PNGtoGcode(pos_file_png_exported, pos_file_png_BW, pos_file_gcode)
            imgData = self.convertImg(pos_file_png_exported, pos_file_png_BW)

            # Generate Gcode from Image (if not unselected)
            if self.options.imgPreviewOnly == False:
                self.imgToGcode(imgData, pos_file_gcode)
            
            # remove the exported PNG picture 
            if os.path.isfile(pos_file_png_exported):
                os.remove(pos_file_png_exported)    


        else:
            errormsg("Directory does not exist! Please specify existing '--imgDirName'!")
    


    ##############################################################################################################################
    ## Export PNG from Inkscape        
    ## Return: a PNG-File
    ##############################################################################################################################
    def exportPNG(self, png_file_out, svg_file_in, bg_color):

        if self.options.imgResolution < 1:
            DPI = str(round(1.0 / self.options.imgSpotSize * 25.4, 3))
        else:
            DPI = str(round(float(self.options.imgResolution) * 25.4, 3))

        if self.options.imgFullPage:
            imageCmd = '-C'
        else:
            imageCmd = '-D'
        
        #command='%s %s -o "%s" -b "%s" -d %s %s' % (inkscape_command, imageCmd, png_file_out, bg_color, DPI, svg_file_in)
        #p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #return_code = p.wait()
        #stdout, stderr = p.communicate()
        #msg  = "-------------------------------------------------------\n"
        #msg += 'CMD:\n'+ command + '\n\n'
        #msg += 'STDOUT:\n' + stdout.decode('utf8') + '\n\n'
        #msg += 'STDERR:\n' + stderr.decode('utf8') + '\n\n'
        #msg += "-------------------------------------------------------\n"
        #errormsg(msg)
        
        # inkscape in some versions returns a warning if file will not end with '.svg' but ignore it
        parameters = '%s -o "%s" -b "%s" -d %s %s' % (imageCmd, png_file_out, bg_color, DPI, svg_file_in)
        stdout, stderr =  icmd.execute(parameters)
        
        # even inkscape produce some Warnings, ignore them and test if file "png_file_out" exist
        if not os.path.isfile(png_file_out):
            msg  = 'Error: file "%s" was not created\n\n'%(png_file_out)
            msg += 'STDOUT:\n' + stdout + '\n\n'
            msg += 'STDERR:\n' + stderr + '\n\n'
            errormsg(msg)
            exit()
            



    ##############################################################################################################################
    ## Apply PNG-File conversion
    ## Return: (width, heigth, PixelMatix)
    ##############################################################################################################################
    def convertImg(self, png_file_in, png_preview_out):
        WHITE = 255
        BLACK =   0
            
        reader = png.Reader(png_file_in)                        # open PNG File from Inkscape export
        w, h, pixels, metadata = reader.read_flat()             # read PNG data
        matrix = [[WHITE for i in range(w)]for j in range(h)]   # create an empty (White) image matrix

        ##############################################################################################################
        ## Convert (RGB) image into 8bit greyscale 
        ##############################################################################################################
        
        if self.options.imgGrayType == 1:
            #-----------------------------------------------------
            # 0.21R + 0.71G + 0.07B
            #-----------------------------------------------------
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    #matrix[y][x] = int(pixels[pixel_position]*0.21 + pixels[(pixel_position+1)]*0.71 + pixels[(pixel_position+2)]*0.07)
                    matrix[y][x] = int(pixels[pixel_position]*0.213 + pixels[(pixel_position+1)]*0.713 + pixels[(pixel_position+2)]*0.074)
        
        elif self.options.imgGrayType == 2:
            #-----------------------------------------------------
            # (R+G+B)/3
            #-----------------------------------------------------
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrix[y][x] = int((pixels[pixel_position] + pixels[(pixel_position+1)]+ pixels[(pixel_position+2)]) / 3 )

        elif self.options.imgGrayType == 3:
            #-----------------------------------------------------
            # R
            #-----------------------------------------------------
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrix[y][x] = int(pixels[pixel_position])

        elif self.options.imgGrayType == 4:
            #-----------------------------------------------------
            # G
            #-----------------------------------------------------
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrix[y][x] = int(pixels[(pixel_position+1)])
        
        elif self.options.imgGrayType == 5:
            #-----------------------------------------------------
            # B
            #-----------------------------------------------------
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrix[y][x] = int(pixels[(pixel_position+2)])
                
        elif self.options.imgGrayType == 6:
            #-----------------------------------------------------
            # Max Color
            #-----------------------------------------------------
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    list_RGB = pixels[pixel_position] , pixels[(pixel_position+1)] , pixels[(pixel_position+2)]
                    matrix[y][x] = int(max(list_RGB))

        else:
            #-----------------------------------------------------
            # Min Color
            #-----------------------------------------------------
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    list_RGB = pixels[pixel_position] , pixels[(pixel_position+1)] , pixels[(pixel_position+2)]
                    matrix[y][x] = int(min(list_RGB))
        

        ##############################################################################################################
        ## Generate black and white or greyscale image
        ##############################################################################################################
        W=WHITE     # for a smaler matrix definition
        B=BLACK
        WHITE_FP = 1.0
        
        matrix_int =   [[WHITE for i in range(w)]for j in range(h)]
        
        if self.options.imgConvType == 1:
            #-----------------------------------------------------
            # B/W fixed threshold
            #-----------------------------------------------------
            theshold = self.options.imgBWthreshold
            self.conversionTypeText = 'B/W fixed threshold (TH:%i)'%(theshold)
            
            for y in range(h): 
                for x in range(w):
                    if matrix[y][x] >= theshold :
                        matrix_int[y][x] = WHITE
                    else:
                        matrix_int[y][x] = BLACK

                
        elif self.options.imgConvType == 2:
            #-----------------------------------------------------
            # B/W random threshold
            #-----------------------------------------------------
            from random import randint
            self.conversionTypeText = 'B/W random threshold'
            
            for y in range(h): 
                for x in range(w): 
                    theshold = randint(20,235)
                    if matrix[y][x] >= theshold :
                        matrix_int[y][x] = WHITE
                    else:
                        matrix_int[y][x] = BLACK
    
            
        elif self.options.imgConvType == 3:
            #-----------------------------------------------------
            # Halftone
            #-----------------------------------------------------
            self.conversionTypeText = 'Halftone'
            
            Step1 = [[W,W,W,W,W],[W,W,W,W,W],[W,W,B,W,W],[W,W,W,W,W],[W,W,W,W,W]]
            Step2 = [[W,W,W,W,W],[W,W,B,W,W],[W,B,B,B,W],[W,W,B,W,W],[W,W,W,W,W]]
            Step3 = [[W,W,B,W,W],[W,B,B,B,W],[B,B,B,B,B],[W,B,B,B,W],[W,W,B,W,W]]
            Step4 = [[W,B,B,B,W],[B,B,B,B,B],[B,B,B,B,B],[B,B,B,B,B],[W,B,B,B,W]]
            
            for y in range(int(h/5)): 
                for x in range(int(w/5)): 
                    media = 0
                    for y2 in range(5):
                        for x2 in range(5):
                            media +=  matrix[y*5+y2][x*5+x2]
                    
                    media = media /25
                    for y3 in range(5):
                        for x3 in range(5):
                            if media >= 250 and media <= 255:   matrix_int[y*5+y3][x*5+x3] =    WHITE
                            if media >= 190 and media < 250:    matrix_int[y*5+y3][x*5+x3] =    Step1[y3][x3]
                            if media >= 130 and media < 190:    matrix_int[y*5+y3][x*5+x3] =    Step2[y3][x3]
                            if media >= 70 and media < 130:     matrix_int[y*5+y3][x*5+x3] =    Step3[y3][x3]
                            if media >= 10 and media < 70:      matrix_int[y*5+y3][x*5+x3] =    Step4[y3][x3]		
                            if media >= 0 and media < 10:       matrix_int[y*5+y3][x*5+x3] =    BLACK


        elif self.options.imgConvType == 4:
            #-----------------------------------------------------
            # Halftone row
            #-----------------------------------------------------
            self.conversionTypeText = 'Halftone row'

            Step1r = [W,W,B,W,W]
            Step2r = [W,B,B,W,W]
            Step3r = [W,B,B,B,W]
            Step4r = [B,B,B,B,W]

            for y in range(h): 
                for x in range(int(w/5)): 
                    media = 0
                    for x2 in range(5):
                        media +=  matrix[y][x*5+x2]
                    
                    media = media /5
                    for x3 in range(5):
                        if media >= 250 and media <= 255:       matrix_int[y][x*5+x3] =     WHITE
                        if media >= 190 and media < 250:        matrix_int[y][x*5+x3] =     Step1r[x3]
                        if media >= 130 and media < 190:        matrix_int[y][x*5+x3] =     Step2r[x3]
                        if media >= 70 and media < 130:         matrix_int[y][x*5+x3] =     Step3r[x3]
                        if media >= 10 and media < 70:          matrix_int[y][x*5+x3] =     Step4r[x3]
                        if media >= 0 and media < 10:           matrix_int[y][x*5+x3] =     BLACK


        elif self.options.imgConvType == 5:
            #-----------------------------------------------------
            # Halftone column
            #-----------------------------------------------------
            self.conversionTypeText = 'Halftone column'

            Step1c = [W,W,B,W,W]
            Step2c = [W,B,B,W,W]
            Step3c = [W,B,B,B,W]
            Step4c = [B,B,B,B,W]

            for y in range(int(h/5)):
                for x in range(w):
                    media = 0
                    for y2 in range(5):
                        media +=  matrix[y*5+y2][x]
                    
                    media = media /5
                    for y3 in range(5):
                        if media >= 250 and media <= 255:       matrix_int[y*5+y3][x] =     WHITE
                        if media >= 190 and media < 250:        matrix_int[y*5+y3][x] =     Step1c[y3]
                        if media >= 130 and media < 190:        matrix_int[y*5+y3][x] =     Step2c[y3]
                        if media >= 70 and media < 130:         matrix_int[y*5+y3][x] =     Step3c[y3]
                        if media >= 10 and media < 70:          matrix_int[y*5+y3][x] =     Step4c[y3]
                        if media >= 0 and media < 10:           matrix_int[y*5+y3][x] =     BLACK
        
        elif self.options.imgConvType == 6:
            #-----------------------------------------------------
            # Simple2D
            #-----------------------------------------------------
            theshold = self.options.imgBWthreshold
            matrix_float = [[1.0 for i in range(w)]for j in range(h)]
            self.conversionTypeText = 'Simple2D (TH:%i)'%(theshold)
            
            for y in range(h):
                for x in range(w):
                    pixel = matrix[y][x]
                    if pixel >= theshold: pixel = WHITE
                    matrix_float[y][x] = float(pixel) / 255.0

            for y in range(0, h-1):
                for x in range(0, w-1):
                    # threshold step
                    if matrix_float[y][x] > 0.5:
                        err = matrix_float[y][x] - 1.0
                        matrix_float[y][x] = 1.0
                    else:
                        err = matrix_float[y][x]
                        matrix_float[y][x] = 0.0
                    # error diffusion step
                    matrix_float[y  ][x+1] =  matrix_float[y  ][x+1] + (0.5 * err)
                    matrix_float[y+1][x  ] =  matrix_float[y+1][x  ] + (0.5 * err)

            for y in range(h):
                for x in range(w):
                    pixel = int(matrix_float[y][x] * 255)
                    if pixel > WHITE: pixel = WHITE
                    if pixel < BLACK: pixel = BLACK
                    matrix_int[y][x] = pixel


        elif self.options.imgConvType == 7:
            #-----------------------------------------------------
            # Floyd-Steinberg
            #-----------------------------------------------------
            theshold = self.options.imgBWthreshold
            matrix_float = [[1.0 for i in range(w)]for j in range(h)]
            self.conversionTypeText = 'Floyd-Steinberg (TH:%i)'%(theshold)

            for y in range(h):
                for x in range(w):
                    pixel = matrix[y][x]
                    if pixel >= theshold: pixel = WHITE
                    matrix_float[y][x] = float(pixel) / 255.0

            for y in range(0, h-1):
                for x in range(1, w-1):
                    if matrix_float[y][x] > 0.5:
                        err = matrix_float[y][x] - 1.0
                        matrix_float[y][x] = 1.0
                    else:
                        err = matrix_float[y][x]
                        matrix_float[y][x] = 0.0
                    # error diffusion step
                    matrix_float[y  ][x+1] =  matrix_float[y  ][x+1] + ((7.0/16.0) * err)
                    matrix_float[y+1][x-1] =  matrix_float[y+1][x-1] + ((3.0/16.0) * err)
                    matrix_float[y+1][x  ] =  matrix_float[y+1][x  ] + ((5.0/16.0) * err)
                    matrix_float[y+1][x+1] =  matrix_float[y+1][x+1] + ((1.0/16.0) * err)

            for y in range(h):
                for x in range(w):
                    pixel = int(matrix_float[y][x] * 255)
                    if pixel > WHITE: pixel = WHITE
                    if pixel < BLACK: pixel = BLACK
                    matrix_int[y][x] = pixel

        elif self.options.imgConvType == 8:
            #-----------------------------------------------------
            # Jarvis-Judice-Ninke
            #-----------------------------------------------------
            theshold = self.options.imgBWthreshold
            matrix_float = [[1.0 for i in range(w)]for j in range(h)]
            self.conversionTypeText = 'Jarvis-Judice-Ninke (TH:%i)'%(theshold)
            
            for y in range(h):
                for x in range(w):
                    pixel = matrix[y][x]
                    if pixel >= theshold: pixel = WHITE
                    matrix_float[y][x] = float(pixel) / 255.0

            for y in range(0, h-2):
                for x in range(2, w-2):
                    # threshold step
                    if matrix_float[y][x] > 0.5:
                        err = matrix_float[y][x] - 1.0
                        matrix_float[y][x] = 1.0
                    else:
                        err = matrix_float[y][x]
                        matrix_float[y][x] = 0.0
                    # error diffusion step
                    matrix_float[y  ][x+1] =  matrix_float[y  ][x+1] + ((7.0/48.0) * err)
                    matrix_float[y  ][x+2] =  matrix_float[y  ][x+2] + ((5.0/48.0) * err)

                    matrix_float[y+1][x-2] =  matrix_float[y+1][x-2] + ((3.0/48.0) * err)
                    matrix_float[y+1][x-1] =  matrix_float[y+1][x-1] + ((5.0/48.0) * err)
                    matrix_float[y+1][x  ] =  matrix_float[y+1][x  ] + ((7.0/48.0) * err)
                    matrix_float[y+1][x+1] =  matrix_float[y+1][x+1] + ((5.0/48.0) * err)
                    matrix_float[y+1][x+2] =  matrix_float[y+1][x+2] + ((3.0/48.0) * err)

                    matrix_float[y+2][x-2] =  matrix_float[y+2][x-2] + ((1 / 48) * err)
                    matrix_float[y+2][x-1] =  matrix_float[y+2][x-1] + ((3 / 48) * err)
                    matrix_float[y+2][x  ] =  matrix_float[y+2][x  ] + ((5 / 48) * err)
                    matrix_float[y+2][x+1] =  matrix_float[y+2][x+1] + ((3 / 48) * err)
                    matrix_float[y+2][x+2] =  matrix_float[y+2][x+2] + ((1 / 48) * err)

            for y in range(h):
                for x in range(w):
                    pixel = int(matrix_float[y][x] * 255)
                    if pixel > WHITE: pixel = WHITE
                    if pixel < BLACK: pixel = BLACK
                    matrix_int[y][x] = pixel

        elif self.options.imgConvType == 9:
            #-----------------------------------------------------
            # Grayscale
            #-----------------------------------------------------
            self.conversionTypeText = 'Grayscale (Res:%i)'%(self.options.imgGrayResolution)
            
            if self.options.imgGrayResolution == 256:
                matrix_int = matrix
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
                        matrix_int[y][x] = lookUpTabel[matrix[y][x]]
            
        else:
            errormsg("Convertion type does not exist!")


        # Save preview image
        file_img = open(png_preview_out, 'wb')
        png_img = png.Writer(w, h, greyscale=True, bitdepth=8)
        png_img.write(file_img, matrix_int)
        file_img.close()
        
        return (w, h, matrix_int)


    ##############################################################################################################################
    ## Convert PNG-File to GCode-File
    ## Return: with, heigth, PixelMatix
    ##############################################################################################################################
    def imgToGcode(self, imageData, gcode_file_out):
        WHITE    = 255
        WHITE_FP = 1.0

        w, h, matrix_int = imageData

        ##############################################################################################################
        ## G-Code helper
        ##############################################################################################################
        def generateGCodeLine(source, values):
            gCodeString = source
            for key in values.keys():
                gCodeString = gCodeString.replace('{'+key+'}', values[key])
            return gCodeString
        
        def floatToString(floatValue):
            result = ('%.4f' % floatValue).rstrip('0').rstrip('.')
            return '0' if result == '-0' else result

        ##############################################################################################################
        ## Generate G-Code
        ##############################################################################################################
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
        offsetZigZag = round(self.options.gc1ZigZagOffset, 4)
        scanType = self.options.gc1ScanType
        xZeroPoint = self.options.gc1ZeroPointX
        yZeroPoint = self.options.gc1ZeroPointY
        startCmd = self.options.gc1StartCode
        postCmd = self.options.gc1PostCode
        lineCmd = self.options.gc1LineCode
        travelCmd = self.options.gc1OffTravelCode
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
                matrix_int[y].reverse()

        if flipY == True: #Inverto asse Y solo se flip_y = False     
            #-> coordinate Cartesiane (False) Coordinate "informatiche" (True)
            matrix_int.reverse()
            
        if invertBW == True:
            for y in range(h):
                matrix_int[y] = [ WHITE-j for j in matrix_int[y] ]


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
        scanFast = False
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
            scanFast = True
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
            scanFast = True

        file_gcode = open(gcode_file_out, 'w')
        
        # generate G-Code header
        file_gcode.write('; Generated with:'+ GCODE_NL)
        file_gcode.write(';   Inkscape %s'%(icmd.version) + GCODE_NL)
        file_gcode.write(';   Raster 2 Laser Gcode generator NG %s by RKtech'%(r2l_version) + GCODE_NL)
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
        file_gcode.write(';   Conversion algorithm:     %s'%(self.conversionTypeText) + GCODE_NL)
        file_gcode.write(';   Scan Type:                %s'%(scanTypeText) + GCODE_NL)
        file_gcode.write(';   Flip X:                   %s'%('Yes' if flipX else 'No') + GCODE_NL)
        file_gcode.write(';   Flip Y:                   %s'%('Yes' if flipY else 'No') + GCODE_NL)
        if self.options.debug:
            file_gcode.write(';' + GCODE_NL)
            file_gcode.write('; Debug Parameters:'+ GCODE_NL)
            file_gcode.write(';   Inkscape Command          "%s"'%(icmd.command) + GCODE_NL)
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
            file_gcode.write(';   --gc1OffTravelCode        "%s"'%(travelCmd) + GCODE_NL)
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
                imageLineDataMaster = matrix_int[scanLine]
                yPos = -1.0 * float(scanLine)*Scala + yOffset
                valueList['YPOS'] = '%s'%(floatToString(yPos))
                valueList['APOS'] = '%s'%(floatToString(yPos * 360.0 / (math.pi * abDiameter)))
            else:
                imageLineDataMaster = [matrix_int[j][scanLine] for j in range(imageColums)]
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
                    file_gcode.write(generateGCodeLine(travelCmd, valueList) + GCODE_NL)
                    
                    ##################################################################
                    # Iterate scan columns
                    laserPowerCange = True
                    detectOffDistance = False 
                    detectOffDistanceStart = 0.0
                    detectOffDistanceEnd = 0.0
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
                            valueList['ZPOS'] = '%s'%(floatToString(zPos))
                            valueList['POWT'] = '%s'%(floatToString(powerTo))
                            valueList['POWF'] = '%s'%(floatToString(powerFrom))
                            valueList['PCMT'] = laserOnCmd if pixelValueTo   <= laserOnThreshold else laserOffCmd
                            valueList['PCMF'] = laserOnCmd if pixelValueFrom <= laserOnThreshold else laserOffCmd
                            valueList['PIXV'] = '%i'%(pixelValueTo)

                            # neu ++
                            if scanFast and power == minPower and detectOffDistance == False:
                                detectOffDistance = True
                                if scanX:
                                    detectOffDistanceStart = float(scanColumn + reverseOffset)*Scala + xOffset + zigZagOffset
                                else:
                                    detectOffDistanceStart = -1.0 * float(scanColumn + reverseOffset)*Scala + yOffset + zigZagOffset
                            if scanFast and power != minPower and detectOffDistance == True:
                                detectOffDistance = False
                                if scanX:
                                    detectOffDistanceEnd = float(scanColumn + reverseOffset)*Scala + xOffset + zigZagOffset
                                    xPos1 = detectOffDistanceStart + accelDist
                                    xPos2 = detectOffDistanceEnd - accelDist
                                    yPos1 = yPos
                                    yPos2 = yPos
                                else:
                                    detectOffDistanceEnd = -1.0 * float(scanColumn + reverseOffset)*Scala + yOffset + zigZagOffset
                                    xPos1 = xPos
                                    xPos2 = xPos
                                    yPos1 = detectOffDistanceStart - accelDist
                                    yPos2 = detectOffDistanceEnd + accelDist

                                if abs(detectOffDistanceStart - detectOffDistanceEnd) >= abs(3 * accelDist):
                                    file_gcode.write("(*** DEBUG : Start = %f / End = %f / Diff = %f / 3*ADis = %f)"%(detectOffDistanceStart, detectOffDistanceEnd, detectOffDistanceStart-detectOffDistanceEnd,(3 * accelDist)) + GCODE_NL)

                                    valueList['XPOS'] = '%s'%(floatToString(xPos1))
                                    valueList['YPOS'] = '%s'%(floatToString(yPos1))
                                    valueList['APOS'] = '%s'%(floatToString(yPos1 * 360.0 / (math.pi * abDiameter)))
                                    valueList['BPOS'] = '%s'%(floatToString(xPos1 * 360.0 / (math.pi * abDiameter)))
                                    file_gcode.write(generateGCodeLine(pixelCmd, valueList) + GCODE_NL)

                                    valueList['XPOS'] = '%s'%(floatToString(xPos2))
                                    valueList['YPOS'] = '%s'%(floatToString(yPos2))
                                    valueList['APOS'] = '%s'%(floatToString(yPos2 * 360.0 / (math.pi * abDiameter)))
                                    valueList['BPOS'] = '%s'%(floatToString(xPos2 * 360.0 / (math.pi * abDiameter)))
                                    # file_gcode.write(generateGCodeLine("G0 X{XPOS} Y{YPOS}", valueList) + GCODE_NL)
                                    file_gcode.write(generateGCodeLine(travelCmd, valueList) + GCODE_NL)

                                    file_gcode.write("(*** DEBUG )" + GCODE_NL)



                            # neu --

                            valueList['XPOS'] = '%s'%(floatToString(xPos))
                            valueList['YPOS'] = '%s'%(floatToString(yPos))
                            valueList['APOS'] = '%s'%(floatToString(yPos * 360.0 / (math.pi * abDiameter)))
                            valueList['BPOS'] = '%s'%(floatToString(xPos * 360.0 / (math.pi * abDiameter)))
                            file_gcode.write(generateGCodeLine(pixelCmd, valueList) + GCODE_NL)
                    
                        laserPowerCange = False
                        if scanColumn == scanColumns[-1]:
                            laserPowerCange = True
                            #print(x, matrix_int[y][x], 0, laserPowerCange)
                        else:
                            if imageLineData[scanColumn] != imageLineData[scanColumn + directionCount]:
                                laserPowerCange = True
                            #print(x, matrix_int[y][x], matrix_int[y][x+directionCount], laserPowerCange)

                    
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
    e.run()
    exit()

if __name__=="__main__":
    _main()




