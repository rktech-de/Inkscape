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

sys.path.append('/usr/share/inkscape/extensions')
sys.path.append('/Applications/Inkscape.app/Contents/Resources/extensions') 

import subprocess
import math

import inkex
import png
import array


class GcodeExport(inkex.Effect):

######## 	Richiamata da _main()
    def __init__(self):
        """init the effetc library and get options from gui"""
        inkex.Effect.__init__(self)

        # To make the notebook parameter happy
        self.OptionParser.add_option("","--nopNB",action="store",type="string",dest="nopNB",default="",help="")
        
        # Image Settings
        self.OptionParser.add_option("-d", "--imgDirName",action="store", type="string", dest="imgDirName", default="/home/",help="Directory for files") ####check_dir
        self.OptionParser.add_option("-f", "--imgFileName", action="store", type="string", dest="imgFileName", default="-1.0", help="File name")            
        self.OptionParser.add_option("","--imgNumFileSuffix", action="store", type="inkbool", dest="imgNumFileSuffix", default=True,help="Add numeric suffix to filename")            
        self.OptionParser.add_option("","--imgBGcolor", action="store",type="string",dest="imgBGcolor",default="",help="")
        self.OptionParser.add_option("","--imgResolution", action="store", type="int", dest="imgResolution", default="0",help="") #Usare il valore su float(xy)/resolution e un case per i DPI dell export
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
        self.OptionParser.add_option("","--gc1FeedRate",action="store", type="int", dest="gc1FeedRate", default="200",help="") 
        self.OptionParser.add_option("","--gc1MinPower",action="store", type="float", dest="gc1MinPower", default="0.0",help="")
        self.OptionParser.add_option("","--gc1MaxPower",action="store", type="float", dest="gc1MaxPower", default="100.0",help="")
        self.OptionParser.add_option("","--gc1AccDistance",action="store", type="float", dest="gc1AccDistance", default="10.0",help="")
        self.OptionParser.add_option("","--gc1LevelZ",action="store", type="float", dest="gc1LevelZ", default="10.0",help="")
        self.OptionParser.add_option("","--gc1FlipX",action="store", type="inkbool", dest="gc1FlipX", default=False,help="")
        self.OptionParser.add_option("","--gc1FlipY",action="store", type="inkbool", dest="gc1FlipY", default=False,help="")
        self.OptionParser.add_option("","--gc1ZeroPointX",action="store", type="int", dest="gc1ZeroPointX", default="0",help="")
        self.OptionParser.add_option("","--gc1ZeroPointY",action="store", type="int", dest="gc1ZeroPointY", default="0",help="")
        self.OptionParser.add_option("","--gc1ScanType",action="store", type="int", dest="gc1ScanType", default="3",help="")

            
######## 	Richiamata da __init__()
########	Qui si svolge tutto
    def effect(self):

        current_file = self.args[-1]
        bg_color = self.options.imgBGcolor
        
        
        ##Implementare check_dir
        
        if (os.path.isdir(self.options.imgDirName)) == True:					
            
            ##CODICE SE ESISTE LA DIRECTORY
            #inkex.errormsg("OK") #DEBUG

            
            #Aggiungo un suffisso al nomefile per non sovrascrivere dei file
            if self.options.imgNumFileSuffix :
                dir_list = os.listdir(self.options.imgDirName) #List di tutti i file nella imgDirName di lavoro
                temp_name =  self.options.imgFileName
                max_n = 0
                for s in dir_list :
                    #r = re.match(r"^%s_0*(\d+)%s$"%(re.escape(temp_name),'.png' ), s)
                    r = re.match(r"^%s_0*(\d+)_.+preview\.%s$"%(re.escape(temp_name),'png' ), s)
                    if r :
                        max_n = max(max_n,int(r.group(1)))	
                self.options.imgFileName = temp_name + "_%04d"%(max_n+1)


            #genero i percorsi file da usare
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
                inkex.errormsg("Unknown conversion type!")
                    
            
            pos_file_png_exported = os.path.join(self.options.imgDirName,self.options.imgFileName+".png") 
            pos_file_png_BW = os.path.join(self.options.imgDirName,self.options.imgFileName+suffix+"_preview.png") 
            pos_file_gcode = os.path.join(self.options.imgDirName,self.options.imgFileName+suffix+".ngc") 

            #Esporto l'immagine in PNG
            self.exportPage(pos_file_png_exported,current_file,bg_color)
            
            #DA FARE
            #Manipolo l'immagine PNG per generare il file Gcode
            self.PNGtoGcode(pos_file_png_exported,pos_file_png_BW,pos_file_gcode)
            
            # remove the exported picture 
            if os.path.isfile(pos_file_png_exported):
                os.remove(pos_file_png_exported)    
                
        else:
            inkex.errormsg("Directory does not exist! Please specify existing imgDirName!")
    

    
    
########	ESPORTA L IMMAGINE IN PNG		
######## 	Richiamata da effect()
            
    def exportPage(self,pos_file_png_exported,current_file,bg_color):		
        ######## CREAZIONE DEL FILE PNG ########
        #Crea l'immagine dentro la cartella indicata  da "pos_file_png_exported"
        # -d 127 = risoluzione 127DPI  =>  5 pixel/mm  1pixel = 0.2mm
        ###command="inkscape -C -e \"%s\" -b\"%s\" %s -d 127" % (pos_file_png_exported,bg_color,current_file) 

        if self.options.imgResolution < 1:
            DPI = 1.0 / self.options.imgSpotSize * 25.4
        else:
            DPI = float(self.options.imgResolution) * 25.4


        if self.options.imgFullPage:
            # export page
            #command="inkscape -C -e \"%s\" -b\"%s\" %s -d %s" % (pos_file_png_exported,bg_color,current_file,DPI) #Comando da linea di comando per esportare in PNG
            command='inkscape -C -e "%s" -b"%s" %s -d %s'%(pos_file_png_exported,bg_color,current_file,DPI) #Comando da linea di comando per esportare in PNG
        else:
            #export drawing
            command='inkscape -D -e "%s" -b"%s" %s -d %s'%(pos_file_png_exported,bg_color,current_file,DPI) #Comando da linea di comando per esportare in PNG
                                
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return_code = p.wait()
        f = p.stdout
        err = p.stderr


########	CREA IMMAGINE IN B/N E POI GENERA GCODE
######## 	Richiamata da effect()

    def PNGtoGcode(self,pos_file_png_exported,pos_file_png_BW,pos_file_gcode):
            
        ######## GENERO IMMAGINE IN SCALA DI GRIGI ########
        #Scorro l immagine e la faccio diventare una matrice composta da list


        reader = png.Reader(pos_file_png_exported)#File PNG generato
        
        w, h, pixels, metadata = reader.read_flat()
        
        
        matrice = [[255 for i in range(w)]for j in range(h)]  #List al posto di un array
        

        #Scrivo una nuova immagine in Scala di grigio 8bit
        #copia pixel per pixel 

        ##############################################################################################################
        ## Convert image into greyscale 
        ##############################################################################################################
        
        if self.options.imgGrayType == 1:
            #0.21R + 0.71G + 0.07B
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrice[y][x] = int(pixels[pixel_position]*0.21 + pixels[(pixel_position+1)]*0.71 + pixels[(pixel_position+2)]*0.07)
        
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
        

        ####Ora matrice contiene l'immagine in scala di grigi

        ##############################################################################################################
        ## Generate black and white or greyscale image
        ##############################################################################################################
        WHITE = 255
        BLACK =   0
        W=WHITE
        B=BLACK
        
        matrice_BN = [[255 for i in range(w)]for j in range(h)]
        matrice_FP = [[1.0 for i in range(w)]for j in range(h)]
        
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
            
            for y in range(h/5): 
                for x in range(w/5): 
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
                for x in range(w/5): 
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

            for y in range(h/5):
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
            conversionTypeText = 'Jarvis-Judice-Ninke (Res:%i)'%(self.options.imgGrayResolution)
            
            if self.options.imgGrayResolution == 256:
                matrice_BN = matrice
            else:
                # create look up tabel
                lookUpTabel = range(256)
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
            inkex.errormsg("Convertion type does not exist!")


        ####Ora matrice_BN contiene l'immagine in Bianco (255) e Nero (0)


        #### SALVO IMMAGINE IN BIANCO E NERO ####
        file_img_BN = open(pos_file_png_BW, 'wb') #Creo il file
        Costruttore_img = png.Writer(w, h, greyscale=True, bitdepth=8) #Impostazione del file immagine
        Costruttore_img.write(file_img_BN, matrice_BN) #Costruttore del file immagine
        file_img_BN.close()	#Chiudo il file


        ##############################################################################################################
        ## Generate G-Code
        ##############################################################################################################
        if self.options.imgPreviewOnly == False: #Genero Gcode solo se devo

            def generateGCodeLine(source, values):
                gCodeString = source
                for key in values.keys():
                    gCodeString = gCodeString.replace('{'+key+'}', values[key])
                    
                return gCodeString

            xOffset = 0.0          # set 0 point of G-Code
            yOffset = 0.0          # set 0 point of G-Code

            maxPower = self.options.gc1MaxPower
            minPower = self.options.gc1MinPower
            feedRate = self.options.gc1FeedRate
            accel_distance = self.options.gc1AccDistance
            zPos = self.options.gc1LevelZ
            abDiameter = self.options.imgRotDiameter

            scanType = self.options.gc1ScanType
            xZeroPoint = self.options.gc1ZeroPointX
            yZeroPoint = self.options.gc1ZeroPointY
            #lineCmd = 'G0 X{XPOS} Y{YPOS}{NL}G1 X{XPOS} Y{YPOS} A{APOS} B{BPOS} F{FEED}'
            #pixelCmd = 'Mx{POWT} G1 X{XPOS} Y{YPOS} A{APOS} B{BPOS} S{POWF}'
            #lineCmd = '(Y={SCNL} {PDIR}){NL}G0 X{XPOS} Y{YPOS}{NL}({SCNC}) G1 X{XPOS} Y{YPOS} F{FEED}'
            #pixelCmd = '({SCNC}) G1 X{XPOS} Y{YPOS} Mx{POWT} {PCMT} '
            lineCmd = self.options.gc1LineCode
            pixelCmd = self.options.gc1PixelCode
            laserOnCmd = self.options.gc1LaserOn
            laserOffCmd = self.options.gc1LaserOff
            laserOnOffThreshold = (0.5 * (maxPower-minPower) / 255.0) + minPower            

            if maxPower <= minPower:
                inkex.errormsg("Maximum laser power value must be greater then minimum laser power value!")

            
            GCODE_NL = '\n'
            valueList = {'NL':   GCODE_NL,
                         'XPOS': '0',
                         'YPOS': '0',
                         'ZPOS': '%g'%(zPos),
                         'APOS': '0',
                         'BPOS': '0',
                         'FEED': '%g'%(feedRate),
                         'POWT': '%g'%(minPower),
                         'POWF': '%g'%(minPower),
                         'PCMF': laserOffCmd,
                         'PCMT': laserOffCmd,
                         'SCNC': 'init',
                         'SCNL': 'init',
                         'PDIR': 'init'}

 
            ########################################## Start gCode
            if self.options.gc1FlipX == True:
                for y in range(h):
                    matrice_BN[y].reverse()				

            if self.options.gc1FlipY == True: #Inverto asse Y solo se flip_y = False     
                #-> coordinate Cartesiane (False) Coordinate "informatiche" (True)
                matrice_BN.reverse()				

            # distance between lines (steps)
            if self.options.imgResolution < 1:
                Scala = self.options.imgSpotSize 
            else:
                Scala = 1.0/float(self.options.imgResolution)

            if accel_distance <= 0:
                accel_distance = Scala
                
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
                yOffset = float(h-1) * Scala / 2.0
                yOffsetText = 'Middle'
            elif yZeroPoint == 2:
                # bottom
                yOffset = float(h-1) * Scala
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
            file_gcode.write(';   Inkscape and "Raster 2 Laser Gcode generator"' + GCODE_NL)
            file_gcode.write(';   by RKtech (based on 305 Engineering code)' + GCODE_NL)
            file_gcode.write(';' + GCODE_NL)
            file_gcode.write('; Image:'+ GCODE_NL)
            file_gcode.write(';   Pixel size:               %g x %g'%(w, h) + GCODE_NL)
            file_gcode.write(';   Size:                     %g x %g mm'%(w*Scala, h*Scala) + GCODE_NL)
            file_gcode.write(';' + GCODE_NL)
            file_gcode.write('; Parameter setting "%s":'%(self.options.gc1Setting)+ GCODE_NL)
            file_gcode.write(';   Zero point:               %s/%s'%(xOffsetText,yOffsetText) + GCODE_NL)
            file_gcode.write(';   Laser spot size           %g mm'%(Scala) + GCODE_NL)
            file_gcode.write(';   Engraving speed:          %g mm/min'%(feedRate) + GCODE_NL)
            file_gcode.write(';   Minimum power value:      %g'%(minPower) + GCODE_NL)
            file_gcode.write(';   Maximum power value:      %g'%(maxPower) + GCODE_NL)
            file_gcode.write(';   Acceleration distance:    %g mm'%(accel_distance) + GCODE_NL)
            file_gcode.write(';   Conversion algorithm:     %s'%(conversionTypeText) + GCODE_NL)
            file_gcode.write(';   Scan Type:                %s'%(scanTypeText) + GCODE_NL)
            file_gcode.write(';   Flip X:                   %s'%('Yes' if self.options.gc1FlipX else 'No') + GCODE_NL)
            file_gcode.write(';   Flip Y:                   %s'%('Yes' if self.options.gc1FlipY else 'No') + GCODE_NL)
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
                file_gcode.write(';   --gc1Setting              "%s"'%(self.options.gc1Setting) + GCODE_NL)
                file_gcode.write(';   --gc1StartCode            "%s"'%(self.options.gc1StartCode) + GCODE_NL)
                file_gcode.write(';   --gc1PostCode             "%s"'%(self.options.gc1PostCode) + GCODE_NL)
                file_gcode.write(';   --gc1LineCode             "%s"'%(self.options.gc1LineCode) + GCODE_NL)
                file_gcode.write(';   --gc1PixelCode            "%s"'%(self.options.gc1PixelCode) + GCODE_NL)
                file_gcode.write(';   --gc1LaserOn              "%s"'%(self.options.gc1LaserOn) + GCODE_NL)
                file_gcode.write(';   --gc1LaserOff             "%s"'%(self.options.gc1LaserOff) + GCODE_NL)
                file_gcode.write(';   --gc1FeedRate             "%s"'%(self.options.gc1FeedRate) + GCODE_NL)
                file_gcode.write(';   --gc1MinPower             "%s"'%(self.options.gc1MinPower) + GCODE_NL)
                file_gcode.write(';   --gc1MaxPower             "%s"'%(self.options.gc1MaxPower) + GCODE_NL)
                file_gcode.write(';   --gc1AccDistance          "%s"'%(self.options.gc1AccDistance) + GCODE_NL)
                file_gcode.write(';   --gc1LevelZ               "%s"'%(self.options.gc1LevelZ) + GCODE_NL)
                file_gcode.write(';   --gc1FlipX                "%s"'%(self.options.gc1FlipX) + GCODE_NL)
                file_gcode.write(';   --gc1FlipY                "%s"'%(self.options.gc1FlipY) + GCODE_NL)
                file_gcode.write(';   --gc1ZeroPointX           "%s"'%(self.options.gc1ZeroPointX) + GCODE_NL)
                file_gcode.write(';   --gc1ZeroPointY           "%s"'%(self.options.gc1ZeroPointY) + GCODE_NL)
                file_gcode.write(';   --gc1ScanType             "%s"'%(self.options.gc1ScanType) + GCODE_NL)
            file_gcode.write(GCODE_NL)
            file_gcode.write('; Start Code' + GCODE_NL)	
            file_gcode.write(generateGCodeLine(self.options.gc1StartCode, valueList) + GCODE_NL)	

            ########################################## Picture gCode
            file_gcode.write(GCODE_NL + '; Image Code' + GCODE_NL)	

            lastPosition = 0.0
            scanLeftRight = False

            scanLines = range(h) if scanX else range(w)
            #scanLine = y
            for scanLine in scanLines: 
                #
                if scanX:
                    y = scanLine
                    yPos = -1.0 * float(y)*Scala + yOffset
                    valueList['YPOS'] = '%g'%(yPos)
                    valueList['APOS'] = '%g'%(yPos * 360.0 / (math.pi * abDiameter))
                else:
                    x = scanLine
                    xPos = float(x)*Scala + yOffset
                    valueList['XPOS'] = '%g'%(xPos)
                    valueList['BPOS'] = '%g'%(xPos * 360.0 / (math.pi * abDiameter))
                valueList['SCNL'] = '%g'%(scanLine)
            
                #file_gcode.write('; Y-Pos = ' + str(yPos) + '\n')
                
                # search for first and last pixel with laser on (Pixel value not white)
                first_laser_on = -1
                last_laser_on = -1
                if scanX:
                    for x in range(w):
                        if matrice_BN[y][x] != WHITE:
                            first_laser_on = x
                            break
                    for x in reversed(range(w)):
                        if matrice_BN[y][x] != WHITE:
                            last_laser_on = x
                            break
                else:
                    for y in range(h):
                        if matrice_BN[y][x] != WHITE:
                            first_laser_on = y
                            break
                    for y in reversed(range(h)):
                        if matrice_BN[y][x] != WHITE:
                            last_laser_on = y
                            break
                        
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
                    startLeft =  float(first_laser_on)*Scala - accel_distance + xOffset
                    startRight = float(last_laser_on+1)*Scala + accel_distance + xOffset
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
                    startLeft =  -1.0 * (float(first_laser_on)*Scala - accel_distance) + yOffset
                    startRight = -1.0 * (float(last_laser_on+1)*Scala + accel_distance) + yOffset
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
                        if scanX:
                            x = first_laser_on
                            directionCountX = 1
                        else:
                            y = first_laser_on
                            directionCountY = 1
                        reverseOffset = 0
                        accelDist = accel_distance
                        valueList['PDIR'] = '->' if scanX else '\/'   
                    else:
                        # right to left / bottom to top
                        scanColumns = range(last_laser_on, first_laser_on-1, -1)
                        if scanX:
                            x = last_laser_on
                            directionCountX = -1
                        else:
                            y = last_laser_on
                            directionCountY = -1
                        reverseOffset = 1
                        accelDist = 0.0 - accel_distance
                        valueList['PDIR'] = '<-' if scanX else '/\\'    

                    # accelerate phase
                    if scanX:
                        xPos = float(x+reverseOffset)*Scala - accelDist + xOffset
                    else:
                        yPos = -1.0 * (float(y+reverseOffset)*Scala - accelDist) + yOffset

                    power = minPower
                    powerFrom = power
                    powerTo   = power

                    valueList['SCNC'] = 'acc'
                    valueList['XPOS'] = '%g'%(xPos)
                    valueList['YPOS'] = '%g'%(yPos)
                    valueList['ZPOS'] = '%g'%(zPos)
                    valueList['APOS'] = '%g'%(yPos * 360.0 / (math.pi * abDiameter))
                    valueList['BPOS'] = '%g'%(xPos * 360.0 / (math.pi * abDiameter))
                    valueList['POWT'] = '%g'%(powerTo)
                    valueList['POWF'] = '%g'%(powerFrom)
                    valueList['PCMT'] = laserOffCmd
                    valueList['PCMF'] = laserOffCmd
                    file_gcode.write(generateGCodeLine(lineCmd, valueList) + GCODE_NL)

                    # xPos = float(x)*Scala + xOffset
                    # print("G1 X%g Y%g S%g"%(xPos, yPos, power))
                    laserPowerCange = True
                    for scanColumn in scanColumns:
                        if scanX:
                            x = scanColumn
                        else:
                            y = scanColumn
                            
                        if laserPowerCange:
                            if scanX:
                                xPos = float(x+reverseOffset)*Scala + xOffset
                            else:
                                yPos = -1.0 * float(y+reverseOffset)*Scala + yOffset
                                
                            powerTo   = power
                            power = (float(255-matrice_BN[y][x]) * (maxPower-minPower) / 255.0) + minPower
                            powerFrom = power

                            valueList['SCNC'] = '%g'%(scanColumn+reverseOffset)    
                            valueList['XPOS'] = '%g'%(xPos)
                            valueList['YPOS'] = '%g'%(yPos)
                            valueList['ZPOS'] = '%g'%(zPos)
                            valueList['APOS'] = '%g'%(yPos * 360.0 / (math.pi * abDiameter))
                            valueList['BPOS'] = '%g'%(xPos * 360.0 / (math.pi * abDiameter))
                            valueList['POWT'] = '%g'%(powerTo)
                            valueList['POWF'] = '%g'%(powerFrom)
                            valueList['PCMT'] = laserOnCmd if powerTo > laserOnOffThreshold else laserOffCmd
                            valueList['PCMF'] = laserOnCmd if powerFrom > laserOnOffThreshold else laserOffCmd
                            file_gcode.write(generateGCodeLine(pixelCmd, valueList) + GCODE_NL)
                    
                        laserPowerCange = False
                        if scanColumn == scanColumns[-1]:
                            laserPowerCange = True
                            #print(x, matrice_BN[y][x], 0, laserPowerCange)
                        else:
                            if matrice_BN[y][x] != matrice_BN[y+directionCountY][x+directionCountX]:
                                laserPowerCange = True
                            #print(x, matrice_BN[y][x], matrice_BN[y][x+directionCount], laserPowerCange)

                    if scanX:
                        xPos = float(x+1-reverseOffset)*Scala + xOffset
                    else:
                        yPos = -1.0 * float(y+1-reverseOffset)*Scala + yOffset
                        
                    powerTo   = power
                    power = minPower
                    powerFrom = power

                    valueList['SCNC'] = '%g'%(scanColumn+1-reverseOffset)    
                    valueList['XPOS'] = '%g'%(xPos)
                    valueList['YPOS'] = '%g'%(yPos)
                    valueList['ZPOS'] = '%g'%(zPos)
                    valueList['APOS'] = '%g'%(yPos * 360.0 / (math.pi * abDiameter))
                    valueList['BPOS'] = '%g'%(xPos * 360.0 / (math.pi * abDiameter))
                    valueList['POWT'] = '%g'%(powerTo)
                    valueList['POWF'] = '%g'%(powerFrom)
                    valueList['PCMT'] = laserOnCmd if powerTo > minPower else laserOffCmd
                    valueList['PCMF'] = laserOffCmd
                    file_gcode.write(generateGCodeLine(pixelCmd, valueList) + GCODE_NL)

                    # decelerate phase
                    if scanX:
                        xPos = float(x+1-reverseOffset)*Scala + accelDist + xOffset
                    else:
                        yPos = -1.0 * (float(y+1-reverseOffset)*Scala + accelDist) + yOffset

                    powerTo   = power

                    valueList['SCNC'] = 'dec'    
                    valueList['XPOS'] = '%g'%(xPos)
                    valueList['YPOS'] = '%g'%(yPos)
                    valueList['ZPOS'] = '%g'%(zPos)
                    valueList['APOS'] = '%g'%(yPos * 360.0 / (math.pi * abDiameter))
                    valueList['BPOS'] = '%g'%(xPos * 360.0 / (math.pi * abDiameter))
                    valueList['POWT'] = '%g'%(powerTo)
                    valueList['PCMT'] = laserOffCmd
                    file_gcode.write(generateGCodeLine(pixelCmd, valueList) + GCODE_NL)

                    lastPosition = xPos if scanX else yPos

                    valueList['SCNL'] = 'exit'
                    valueList['SCNC'] = 'exit'
                    valueList['PDIR'] = 'exit'

            ########################################## Post gCode
            file_gcode.write('; End Code' + GCODE_NL)
            file_gcode.write(generateGCodeLine(self.options.gc1PostCode, valueList) + GCODE_NL)
            file_gcode.close() #Chiudo il file




######## 	######## 	######## 	######## 	######## 	######## 	######## 	######## 	######## 	


def _main():
    e=GcodeExport()
    e.affect()
    
    exit()

if __name__=="__main__":
    _main()




