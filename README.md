# GCode generator for raster images

for Inkscape 0.9x

### Short Description

**10.01.2022**

* Rename and reorder parameters (also internally) and set more common default values
* Add debug switch to write all (internal) parameters into the CGode file

**08.01.2022**

this is a fork of "305engineering raster2laser" code

- Raster 2 Laser GCode generator is an extension to generate GCode for a laser cutter/engraver (or pen plotter), it can generate various type of outputs from a simple B&W (on/off) to a more detailed Gray scale (pwm)
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

- Resize the inkscape document to match the dimension of your working area on the laser cutter/engraver (Shift+Ctrl+D) or disable the `Use page outline` setting
- Draw or import the image
- To run the extension go to: *Extension => GCode Laser Tools => Raster2Laser NG*
- Play!

### Motivation

my setup and why I did this fork:

For Laser engraving and cutting I use this gantry cutter ([AL-1110](https://webseite.sorotec.de/produkte/alu-line/)) with this laser ([PLH3D-6W](https://optlasersgrav.com/Engraving-Laser-Heads-PLH3D-6W-Series)). And because it needs some time (distance) to accelerate to the set feed rate I have add the *"Distance for acceleration"* value which is added to the beginning and end of a scan line, so the engraving process is done with constant velocity.

In my machine configuration I'm using not the spindle PWM and enable but I use a separate controller which is connected to the analog and digital in- and outputs which are available via [M62 to M68](http://linuxcnc.org/docs/html/gcode/m-code.html#mcode:m62-m65) codes. Therefore I made the GCode generation more flexible.

Even if I tested it only with my setup it should be now possible to use any other machine setup now.



### Detailed description 

#### Image Precessing

... ToDo ...

#### GCode Parser

The CGode generation is done completely different then in the fork master repository. 

The GCode generator didn't "produce" any kind of G or M commands in the python script (only some lines with comments with the settings at the beginning). It only generate the values for positions and power which can be used in this GCode configurations.

* `Init code`: put in here everithing you need to setup your machine once at startup
* `Start of line code`: put here the commands you need at the beginning of a new scanline
* `Power level change code`: this code is executed whenever the laser power value changes. It will be always set to minimum power level at the end of a scanline
* `Post code`: put in here everithing you need to stop your machine once at the end

Possible variables to be used for this four parameters

| Variable | description                                                  |
| -------- | ------------------------------------------------------------ |
| {NL}     | New line in the GCode file at this position, currently hard-coded with '\n'. At the end of an config string an newline is automatically added |
| {XPOS}   | calculated X position                                        |
| {YPOS}   | calculated Y position                                        |
| {ZPOS}   | always the configured "Z level" value                        |
| {APOS}   | calculated A position of an rotary axis, based on the Y position and the *workpiece diameter* |
| {BPOS}   | calculated B position of an rotary axis, based on the X position and the *workpiece diameter* |
| {FEED}   | always the configured "Feed rate" value                      |
| {POWT}   | calculated laser power, based on gray level and laser power min/max configuration |
| {PCMT}   | substituted by the *Laser ON command* or *Laser OFF command* string depending on grey level |
| {SCNL}   | actual scan line number for comment purpose                  |
| {SCNC}   | actual column number for comment purpose                     |
| {PDIR}   | depends on current scan line move direction. Will be: "->", "<-", "/\\" or "\\/" |

#### Image slicing

Depending on the `Scan image lines` configuration the slicing is done horizontal (X or B) or vertical (Y or A). The slicing will always start top-left from the inkskape image. I will describe it for the horizontal slicing, vor vertical it is the same but 90° rotated.

In the scan line the most left and right not white pixel is searched. This is the beginning and end position of the engraving path and the laser should move here with constant velocity (feed rate). So the most left and right withe area is not used for the path calculation. With the setting `Distance for acceleration` an additional distance is added to the left and right of the engraving path with laser power set to `Minimum laser power value` to allow the machine to accelerate and decelerate. This will prevent darker/deeper engraving at the left and right side of the engraved picture. Even if this setting is set to 0, it will be added one pixel with laser power minimum on both sides.

If the complete scan line is white no GCode is generated for this line. The start position of the next line will be calculated  depending on the `Scan image lines` setting.

`Left to Right`: laser engraving will always start on the left side and travel to the right.

`Right to Left`: laser engraving will always start on the right side and travel to the left.

`Zig Zag X`: the laser will always move left to right at even and right to left at odd scan lines (start counting with line 0 as even) no matter if there are blank lines in between.

`Fastest X`: with every new line it is calculated if the left/right or right/left start point is the nearest on from the current end position.

#### Configuration Page "Image setup"

Todo....

#### Configuration Page "G-Code"

| Setting                      | Description                                                  |
| ---------------------------- | ------------------------------------------------------------ |
| `Name of this GCode setting` | The idea is, that in the final version there are more G-Code pages planned to easily switch between different setups, this field give you the possibility to give it a meaningful name. it is also put in the comment part of the GCode file |
| `Init code`                  | Anything you need to setup your machine, you can add the homing sequence here.<br />Among other things I'm starting the laser power supply and wait for the ready signal.<br />You can insert *{NL}* to seperate the commands in different lines. |
| `Post code`                  | This is the code placed at the end of the GCode file, the M2 command has to be placed here. I also switch off the laser power here. |
| `Start of line code`         | This code line is generated at the beginning of a new scan line. I use this to go to the start position. the variables *{XPOS}* and *{YPOS}* are substituted with the coordinates. The acceleration distance is included here. you can use *{APOS}* and *{BPOS}* when you are using a rotary A or B axis, this values are in degree and calculated with the workpice diameter setting. Here A corespondent with Y and B with X. <br />*{PDIR}* will give an arrow with the **p**ath **dir**ection, and *{SCNL}* will give the **sc**a**n** **l**ine number. I use this for a comment in the GCode file. Also *{NL}* is possible. |
| `Power level change code`    | This code line is generated anytime the laser power level changes. Here you should use the *{PCMT}* variable to set the laser ON/OFF command or *{POWT}* variable to set the laser power value defined by the MIN/MAX value for white/black. Also *{XPOS}*, *{YPOS}*, *{APOS}* and *{BPOS}* can (must) be used here. |
| `Laser ON command`           | when using the *{PCMT}* variable in the code config, it is substituted with this command when the image pixel is below 50% gray. Not useful for gray-scale images |
| `Laser OFF command`          | when using the *{PCMT}* variable in the code config, it is substituted with this command when the image pixel is above 50% gray. Not useful for gray-scale images |
| `engraving feed rate`        | This value is put into the *{FEED}* variable                 |
| `Minimum laser power value`  | This value is put into the *{POWT}* variable if the image pixel is set white. |
| `Maximum laser power value`  | This value is put into the *{POWT}* variable if the image pixel is set black. |
| `Distance for acceleration`  | This is the distance added to the left/right or top/bottom to allow the machine to accelerate and decelerate without affect to the engraving |
| `Z position`                 | This value is put into the `{ZPOS}` variable                 |
| `Flip X`                     | The pixel image data is flipped at the X axis (upside down) before prozessing the GCode (Preview image is not flipped). This is useful if your machine coordinate system is different from otheres, if the rotary axis is mounted 180° turned or if you engrave on the backside of glass. To get the final result in the same format then the inkscape image |
| `Flip Y`                     | The pixel image data is flipped at the Y axis before prozessing the GCode (Preview image is not flipped). |
| `Zero point for width`       | This will set the zero point for the GCode coordinate system to `Left`, `Center` or `Right`. Flipping the image has no affect to this setting |
| `Zero point for height`      | This will set the zero point for the GCode coordinate system to `Top`, `Middle` or `Bottom`. Flipping the image has no affect to this setting |
| `Scan image lines`           | define the processing of the direction of the engraving path as described above in the slicing section. |

### Note

Fork from: https://github.com/305engineering/Inkscape
