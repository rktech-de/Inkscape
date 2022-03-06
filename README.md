# GCode generator for raster images

for Inkscape 0.9x

### Changelog

**06.03.2022**

- Add function "Invert (Black/White)" while prcessing laser power, e.g. for slate

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

The pull down entry can be changed in the *.inx file, look for `<submenu name="GCode Laser tools"/>`

### Usage of "Raster2Laser NG"

Take a look into the WIKI: [User Manual](https://github.com/rktech-de/Inkscape/wiki/User-Manual)

### Note

Fork from: https://github.com/305engineering/Inkscape
