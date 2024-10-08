# GCode generator for raster images

:warning: The code is now for Inkscape > 1.1 only

### Usage of "Raster2Laser NG"

:book: For a detailed description take a look into the WIKI: [User Manual](https://github.com/rktech-de/Inkscape/wiki/User-Manual)

### Change-log

**23.08.2024**

* Speed up engraving bigger pictures within "fastest" mode by using traveling speed (e.g. with G0 command) when laser is off in a scan line for a longer distance
* Add new configuration "Laser off travel code"

**30.03.2024**

* Change code to work with Inkscape > 1.1 (Tested with 1.1.2, 1.2.2 and 1.3 Linux-AppImg, 1.2.1 Win10)
* Reorder of the configuration settings

**09.04.2023**

* Fix some 1.1. related Issues (inkscape put all output in stderr and script stops)

**14.03.2022**

- Fix some 1.1. related Issues

**12.03.2022**

- Adapted to work with 0.9x and 1.1.x (Tested with 0.92.5 and 1.1.2)

**06.03.2022**

- Add function "Invert (Black/White)" while processing laser power, e.g. for slate

**18.01.2022**

* Add new configuration "Optimize scan line"
* Add new configuration "Gamma value for laser power output"
* Add new configuration "Interleaved line scan with fixed laser power"
* Add variable Pixel Value {POWL}, get maximal power value in current scan line
* Change gray scale setting "0.21R + 0.71G + 0.07B" so a white pixel keeps white

**15.01.2022**

* Add new configuration "Zig zag offset"
* Fix: image was shifted by one pixel in y direction
* Fix: avoid scientific numbers in GCode output

**13.01.2022**

* Add variable Pixel Value {PIXV} 
* Add configuration "Laser on threshold" to control laser on/off command

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

The pull down entry name can be changed in the *.inx file, look for `<submenu name="GCode Laser tools"/>`

### Note

Fork from: https://github.com/305engineering/Inkscape
