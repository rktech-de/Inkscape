# GCode generator for raster images

for Inkscape 0.9x

### Short Description

this is a fork of "305engineering raster2laser" code

- Raster 2 Laser GCode generator is an extension to generate Gcode for a laser cutter/engraver (or pen plotter), it can generate various type of outputs from a simple B&W (on/off) to a more detailed Gray scale (pwm)
- I added some more image processing functions and a new GCode generator
  - Added  dithering types (Simple2D, Floyd–Steinberg, Jarvis-Judice-Ninke)
  - Modify gray scale conversion with lookup table and any number of 2..256 gray steps
  - Add image conversion "Flip X"
  - Use image size of full page or the outline of all objects
  - Define resolution with laser spot size
  - The exported inkscape image (not the preview) is deleted after processing
- New B/W to GCode generator with this features
  - Set min/max laser power values
  - Allow user configurable GCode init, line, and exit Code
  - Calculate positions for rotary axis with a given diameter
  - Add a distance to move the laser for acceleration and deceleration with laser power off
  - set position of zero point
  - Scanline in X or Y direction


### Installing

Simply copy all the *.py and *.inx files into the folder "Extensions" of Inkscape. Where this is located, take a look into *"Edit => Settings => System"* and use one of the folders configured in *"User extensions"* or *"Inkscape extensions"*

> e.g. Linux  "/usr/share/inkscape/extensions" 


for unix (& mac maybe) change the permission on the file:

```bash
chmod 755 *.py
chmod 644 *.inx
```

The extension can be started with: *Extension => GCode Laser Tools => Raster2Laser NG*

The pull down entry can be changed in the *.inx file, look for <submenu name="GCode Laser tools"/>

### Usage of "Raster2Laser NG"

[Required file: png.py / raster2laser_gcode_ng.inx / raster2laser_gcode_ng.py]

- Resize the inkscape document to match the dimension of your working area on the laser cutter/engraver (Shift+Ctrl+D)
- Draw or import the image
- To run the extension go to: *Extension => GCode Laser Tools => Raster2Laser NG*
- Play!

### Motivation

my setup and why I did this fork:

For Laser engraving and cutting I use this gantry cutter ([AL-1110](https://webseite.sorotec.de/produkte/alu-line/)) with this laser ([PLH3D-6W](https://optlasersgrav.com/Engraving-Laser-Heads-PLH3D-6W-Series)). And because it needs some time (distance) to accelerate to the set feed rate I have add the *"Distance for acceleration"* value which is added to the beginning and end of a scan line, so the engraving process is done with constant velocity.

In my machine configuration I'm using not the spindle PWM and enable but I use a separate controller which is connected to the analog and digital in- and outputs which are available via [M62 to M68](http://linuxcnc.org/docs/html/gcode/m-code.html#mcode:m62-m65) codes. Therefore I made the GCode generation more flexible.

Even if I tested it only with my setup it should be now possible to use any other machine setup now.

### Detailed description 

.... todo but a first desciption of the code generator config is done ....

#### Configuration Page "G-Code"

The GCode generator didn't "produce" any kind of G or M commands in the script (only some lines with comments with the used settings). It only generate the values for positions and power which can be used in this configuration.

| Setting                 | Description                                                  |
| ----------------------- | ------------------------------------------------------------ |
| Init code               | Anything you need to setup your machine, you can add the homing sequence here.<br />Among other things I'm starting the laser power supply and wait for the ready signal.<br />You can insert *{NL}* to seperate the commands in different lines. |
| Post code               | This is the code placed at the end of the GCode file, the M2 command has to be placed here. I also switch off the laser power here. |
| Start of line code      | This code line is generated at the beginning of a new scan line. I use this to go to the start position. the variables *{XPOS}* and *{YPOS}* are substituted with the coordinates. The acceleration distance is included here. you can use *{APOS}* and *{BPOS}* when you are using a rotary A or B axis, this values are in degree and calculated with the workpice diameter setting. Here A corespondent with Y and B with X. <br />*{PDIR}* will give an arrow with the **p**ath **dir**ection, and *{SCNL}* will give the **sc**a**n** **l**ine number. I use this for a comment in the GCode file. Also *{NL}* is possible. |
| Power level change code | This code line is generated anytime the laser power level changes. Here you should use the *{PCMT}* variable to set the laser ON/OFF command or *{POWT}* variable to set the laser power value defined by the MIN/MAX value for white/black. Also *{XPOS}*, *{YPOS}*, *{APOS}* and *{BPOS}* can (must) be used here. |
| Laser ON command        | when using the *{PCMT}* variable in the code config, it is substituted with this command when the image pixel is not white ( < 255). Not useful for gray-scale images |
| Laser OFF command       | when using the *{PCMT}* variable in the code config, it is substituted with this command when the image pixel is white ( = 255). Not useful for gray-scale images |

... to be continued

### Note

Fork from: https://github.com/305engineering/Inkscape
