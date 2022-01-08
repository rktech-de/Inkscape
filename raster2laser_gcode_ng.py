'''
# ----------------------------------------------------------------------------
# Copyright (C) 2022 RKtech<info@rktech.de>
# - Added 3 dithering types (based on this code https://github.com/Utkarsh-Deshmukh/image-dithering-python)
#   - Simple2D
#   - Floyd–Steinberg
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
        self.OptionParser.add_option("","--nop",action="store",type="string",dest="nop",default="",help="")
        
        # Opzioni di esportazione dell'immagine
        self.OptionParser.add_option("-d", "--directory",action="store", type="string", dest="directory", default="/home/",help="Directory for files") ####check_dir
        self.OptionParser.add_option("-f", "--filename", action="store", type="string", dest="filename", default="-1.0", help="File name")            
        self.OptionParser.add_option("","--add-numeric-suffix-to-filename", action="store", type="inkbool", dest="add_numeric_suffix_to_filename", default=True,help="Add numeric suffix to filename")            
        self.OptionParser.add_option("","--bg_color",action="store",type="string",dest="bg_color",default="",help="")
        self.OptionParser.add_option("","--resolution",action="store", type="int", dest="resolution", default="0",help="") #Usare il valore su float(xy)/resolution e un case per i DPI dell export
        self.OptionParser.add_option("","--spot_size",action="store", type="float", dest="spot_size", default="0.2",help="")
        self.OptionParser.add_option("","--grayscale_type",action="store", type="int", dest="grayscale_type", default="1",help="") 
        self.OptionParser.add_option("","--conversion_type",action="store", type="int", dest="conversion_type", default="1",help="") 
        self.OptionParser.add_option("","--BW_threshold",action="store", type="int", dest="BW_threshold", default="128",help="") 
        self.OptionParser.add_option("","--grayscale_resolution",action="store", type="int", dest="grayscale_resolution", default="256",help="") 
        
        #Velocita Nero e spostamento
        self.OptionParser.add_option("","--speed_ON",action="store", type="int", dest="speed_ON", default="200",help="") 

        # Mirror
        self.OptionParser.add_option("","--flip_x",action="store", type="inkbool", dest="flip_x", default=False,help="")
        self.OptionParser.add_option("","--flip_y",action="store", type="inkbool", dest="flip_y", default=False,help="")
        
        # Homing
        #self.OptionParser.add_option("","--homing",action="store", type="int", dest="homing", default="1",help="")

        # Commands
        self.OptionParser.add_option("","--startGCode", action="store", type="string", dest="start_gcode", default="", help="")
        self.OptionParser.add_option("","--postGCode", action="store", type="string", dest="post_gcode", default="", help="")

        self.OptionParser.add_option("","--lineCode", action="store", type="string", dest="line_code", default="", help="")
        self.OptionParser.add_option("","--pixelCode", action="store", type="string", dest="pixel_code", default="", help="")

        self.OptionParser.add_option("","--laseron", action="store", type="string", dest="laseron", default="M03", help="")
        self.OptionParser.add_option("","--laseroff", action="store", type="string", dest="laseroff", default="M05", help="")

        self.OptionParser.add_option("","--minPower",action="store", type="float", dest="min_power", default="0.0",help="")
        self.OptionParser.add_option("","--maxPower",action="store", type="float", dest="max_power", default="100.0",help="")

        self.OptionParser.add_option("","--accDistance",action="store", type="float", dest="acc_distance", default="10.0",help="")
        self.OptionParser.add_option("","--zLevel",action="store", type="float", dest="z_level", default="10.0",help="")
        self.OptionParser.add_option("","--rotDiameter",action="store", type="float", dest="rot_diameter", default="50.0",help="")
        
        self.OptionParser.add_option("","--xStartPoint",action="store", type="int", dest="x_start_point", default="0",help="")
        self.OptionParser.add_option("","--yStartPoint",action="store", type="int", dest="y_start_point", default="0",help="")
        self.OptionParser.add_option("","--scanType",action="store", type="int", dest="scan_type", default="3",help="")
        
        # Anteprima = Solo immagine BN 
        self.OptionParser.add_option("","--preview_only",action="store", type="inkbool", dest="preview_only", default=False,help="") 
        self.OptionParser.add_option("","--fullPage",action="store", type="inkbool", dest="full_page", default=True,help="") 
        

        #inkex.errormsg("BLA BLA BLA Messaggio da visualizzare") #DEBUG


            
######## 	Richiamata da __init__()
########	Qui si svolge tutto
    def effect(self):

        current_file = self.args[-1]
        bg_color = self.options.bg_color
        
        
        ##Implementare check_dir
        
        if (os.path.isdir(self.options.directory)) == True:					
            
            ##CODICE SE ESISTE LA DIRECTORY
            #inkex.errormsg("OK") #DEBUG

            
            #Aggiungo un suffisso al nomefile per non sovrascrivere dei file
            if self.options.add_numeric_suffix_to_filename :
                dir_list = os.listdir(self.options.directory) #List di tutti i file nella directory di lavoro
                temp_name =  self.options.filename
                max_n = 0
                for s in dir_list :
                    #r = re.match(r"^%s_0*(\d+)%s$"%(re.escape(temp_name),'.png' ), s)
                    r = re.match(r"^%s_0*(\d+)_.+preview\.%s$"%(re.escape(temp_name),'png' ), s)
                    if r :
                        max_n = max(max_n,int(r.group(1)))	
                self.options.filename = temp_name + "_%04d"%(max_n+1)


            #genero i percorsi file da usare
            suffix = ""
            if self.options.conversion_type == 1:
                suffix = "_BW_"+str(self.options.BW_threshold)
            elif self.options.conversion_type == 2:
                suffix = "_BW_rnd"
            elif self.options.conversion_type == 3:
                suffix = "_HT"
            elif self.options.conversion_type == 4:
                suffix = "_HTrow"
            elif self.options.conversion_type == 5:
                suffix = "_HTcol"
            elif self.options.conversion_type == 6:
                suffix = "_S2D_"+str(self.options.BW_threshold)
            elif self.options.conversion_type == 7:
                suffix = "_FS_"+str(self.options.BW_threshold)
            elif self.options.conversion_type == 8:
                suffix = "_JJN_"+str(self.options.BW_threshold)
            elif self.options.conversion_type == 9:
                suffix = "_Gray_"+str(self.options.grayscale_resolution)
            else:
                inkex.errormsg("Unknown conversion type!")
                    
            
            pos_file_png_exported = os.path.join(self.options.directory,self.options.filename+".png") 
            pos_file_png_BW = os.path.join(self.options.directory,self.options.filename+suffix+"_preview.png") 
            pos_file_gcode = os.path.join(self.options.directory,self.options.filename+suffix+".ngc") 

            #Esporto l'immagine in PNG
            self.exportPage(pos_file_png_exported,current_file,bg_color)
            
            #DA FARE
            #Manipolo l'immagine PNG per generare il file Gcode
            self.PNGtoGcode(pos_file_png_exported,pos_file_png_BW,pos_file_gcode)
            
            # remove the exported picture 
            if os.path.isfile(pos_file_png_exported):
                os.remove(pos_file_png_exported)    
                
        else:
            inkex.errormsg("Directory does not exist! Please specify existing directory!")
    

    
    
########	ESPORTA L IMMAGINE IN PNG		
######## 	Richiamata da effect()
            
    def exportPage(self,pos_file_png_exported,current_file,bg_color):		
        ######## CREAZIONE DEL FILE PNG ########
        #Crea l'immagine dentro la cartella indicata  da "pos_file_png_exported"
        # -d 127 = risoluzione 127DPI  =>  5 pixel/mm  1pixel = 0.2mm
        ###command="inkscape -C -e \"%s\" -b\"%s\" %s -d 127" % (pos_file_png_exported,bg_color,current_file) 

        if self.options.resolution < 1:
            DPI = 1.0 / self.options.spot_size * 25.4
        else:
            DPI = float(self.options.resolution) * 25.4


        if self.options.full_page:
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
        
        if self.options.grayscale_type == 1:
            #0.21R + 0.71G + 0.07B
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrice[y][x] = int(pixels[pixel_position]*0.21 + pixels[(pixel_position+1)]*0.71 + pixels[(pixel_position+2)]*0.07)
        
        elif self.options.grayscale_type == 2:
            #(R+G+B)/3
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrice[y][x] = int((pixels[pixel_position] + pixels[(pixel_position+1)]+ pixels[(pixel_position+2)]) / 3 )

        elif self.options.grayscale_type == 3:
            #R
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrice[y][x] = int(pixels[pixel_position])

        elif self.options.grayscale_type == 4:
            #G
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrice[y][x] = int(pixels[(pixel_position+1)])
        
        elif self.options.grayscale_type == 5:
            #B
            for y in range(h): # y varia da 0 a h-1
                for x in range(w): # x varia da 0 a w-1
                    pixel_position = (x + y * w)*4 if metadata['alpha'] else (x + y * w)*3
                    matrice[y][x] = int(pixels[(pixel_position+2)])
                
        elif self.options.grayscale_type == 6:
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
        
        if self.options.conversion_type == 1:
            # B/W fixed threshold
            soglia = self.options.BW_threshold
            conversionTypeText = 'B/W fixed threshold (TH:%i)'%(soglia)
            
            for y in range(h): 
                for x in range(w):
                    if matrice[y][x] >= soglia :
                        matrice_BN[y][x] = WHITE
                    else:
                        matrice_BN[y][x] = BLACK

                
        elif self.options.conversion_type == 2:
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
    
            
        elif self.options.conversion_type == 3:
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


        elif self.options.conversion_type == 4:
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


        elif self.options.conversion_type == 5:
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
        
        elif self.options.conversion_type == 6:
            # Simple2D
            soglia = self.options.BW_threshold
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


        elif self.options.conversion_type == 7:
            # Floyd-Steinberg
            soglia = self.options.BW_threshold
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

        elif self.options.conversion_type == 8:
            # Jarvis-Judice-Ninke
            soglia = self.options.BW_threshold
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
        elif self.options.conversion_type == 9:
            #Grayscale
            conversionTypeText = 'Jarvis-Judice-Ninke (Res:%i)'%(self.options.grayscale_resolution)
            
            if self.options.grayscale_resolution == 256:
                matrice_BN = matrice
            else:
                # create look up tabel
                lookUpTabel = range(256)
                #grayscale_resolution = 256 / self.options.grayscale_resolution
                if self.options.grayscale_resolution > 1:
                    a = (255.0/(self.options.grayscale_resolution-1))
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
        if self.options.preview_only == False: #Genero Gcode solo se devo

            def generateGCodeLine(source, values):
                gCodeString = source
                for key in values.keys():
                    gCodeString = gCodeString.replace('{'+key+'}', values[key])
                    
                return gCodeString

            xOffset = 0.0          # set 0 point of G-Code
            yOffset = 0.0          # set 0 point of G-Code

            maxPower = self.options.max_power
            minPower = self.options.min_power
            feedRate = self.options.speed_ON
            accel_distance = self.options.acc_distance
            zPos = self.options.z_level
            abDiameter = self.options.rot_diameter

            scanType = self.options.scan_type
            xZeroPoint = self.options.x_start_point
            yZeroPoint = self.options.y_start_point
            #lineCmd = 'G0 X{XPOS} Y{YPOS}{NL}G1 X{XPOS} Y{YPOS} A{APOS} B{BPOS} F{FEED}'
            #pixelCmd = 'Mx{POWT} G1 X{XPOS} Y{YPOS} A{APOS} B{BPOS} S{POWF}'
            #lineCmd = '(Y={SCNL} {PDIR}){NL}G0 X{XPOS} Y{YPOS}{NL}({SCNC}) G1 X{XPOS} Y{YPOS} F{FEED}'
            #pixelCmd = '({SCNC}) G1 X{XPOS} Y{YPOS} Mx{POWT} {PCMT} '
            lineCmd = self.options.line_code
            pixelCmd = self.options.pixel_code
            laserOnCmd = self.options.laseron
            laserOffCmd = self.options.laseroff
            
            GCODE_NL = '\n'
            valueList = {'NL':   GCODE_NL,
                         'XPOS': '0',
                         'YPOS': '0',
                         'ZPOS': '%g'%(zPos),
                         'APOS': '0',
                         'BPOS': '0',
                         'FEED': '%g'%(feedRate),
                         'POWT': '0',
                         'POWF': '0',
                         'PCMF': '',
                         'PCMT': '',
                         'SCNC': '0',
                         'SCNL': '0',
                         'PDIR': '=='}

 
            ########################################## Start gCode
            if self.options.flip_x == True:
                for y in range(h):
                    matrice_BN[y].reverse()				

            if self.options.flip_y == True: #Inverto asse Y solo se flip_y = False     
                #-> coordinate Cartesiane (False) Coordinate "informatiche" (True)
                matrice_BN.reverse()				

            # distance between lines (steps)
            if self.options.resolution < 1:
                Scala = self.options.spot_size 
            else:
                Scala = 1.0/float(self.options.resolution)

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
            file_gcode.write(';   Resolution:               %g x %g pixel'%(w, h) + GCODE_NL)
            file_gcode.write(';   Size:                     %g x %g mm'%(w*Scala, h*Scala) + GCODE_NL)
            file_gcode.write(';   Flip X:                   %s'%('Yes' if self.options.flip_x else 'No') + GCODE_NL)
            file_gcode.write(';   Flip Y:                   %s'%('Yes' if self.options.flip_y else 'No') + GCODE_NL)
            file_gcode.write(';' + GCODE_NL)
            file_gcode.write('; Parameters:'+ GCODE_NL)
            file_gcode.write(';   Zero point:               %s/%s'%(xOffsetText,yOffsetText) + GCODE_NL)
            file_gcode.write(';   Laser spot size           %g mm'%(Scala) + GCODE_NL)
            file_gcode.write(';   Engraving speed:          %g mm/min'%(feedRate) + GCODE_NL)
            file_gcode.write(';   Minimum power value:      %g'%(minPower) + GCODE_NL)
            file_gcode.write(';   Maximum power value:      %g'%(maxPower) + GCODE_NL)
            file_gcode.write(';   Acceleration distance:    %g mm'%(accel_distance) + GCODE_NL)
            file_gcode.write(';   Conversion algorithm:     %s'%(conversionTypeText) + GCODE_NL)
            file_gcode.write(';   Scan Type:                %s'%(scanTypeText) + GCODE_NL)
            file_gcode.write(GCODE_NL)
            file_gcode.write('; Start Code' + GCODE_NL)	
            file_gcode.write(generateGCodeLine(self.options.start_gcode, valueList) + GCODE_NL)	

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
                
                # search for first and last pixel with laser on
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
                            valueList['PCMT'] = laserOnCmd if powerTo > minPower else laserOffCmd
                            valueList['PCMF'] = laserOnCmd if powerFrom > minPower else laserOffCmd
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
                                

            ########################################## Post gCode
            file_gcode.write('; End Code' + GCODE_NL)
            file_gcode.write(generateGCodeLine(self.options.post_gcode, valueList) + GCODE_NL)
            file_gcode.close() #Chiudo il file




######## 	######## 	######## 	######## 	######## 	######## 	######## 	######## 	######## 	


def _main():
    e=GcodeExport()
    e.affect()
    
    exit()

if __name__=="__main__":
    _main()




