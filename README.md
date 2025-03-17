# About
This repo contains the following small blender "addons" / scripts:
- An gcode exporter:
    + Edges from the mesh of the selected object get converted into gcode moves which are written into a file.
      Only very simple objects where tested.

- An svg exporter:
    + Edges from the mesh of the selected object get converted into svg paths which are written into a file.
      A default conversion ratio of 3.77953 is set so that the image can be imported into Lightburn while keeping the right dimensions (somewhat, I'm uncertain what factors played a role - diplay resolution?)
      Only very simple objects where tested.

# Usage
Add this folder as script directory:
> Edit > Preferences > File Paths > Script Directories

# TODO
- cleanup code (duplications, ...)
- generalize code, so it's more useful
