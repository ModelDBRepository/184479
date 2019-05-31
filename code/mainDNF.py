#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Dymamic Neural Field simulator with finite transmission speed
# Copyright (C) 2010 Nicolas P. Rougier
# Copyright (C) 2012 - 2015 Eric J. Nichols
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
# 
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
#
# -----------------------------------------------------------------------------
#
# Dependencies:
#
#     Python 2.7...: http://www.python.org
#     Numpy:         http://www.numpy.org
#     PyOpenGL:      http://pyopengl.sourceforge.net
#     GLFW:          http://www.glfw.org
#
# -----------------------------------------------------------------------------
# Contributors:
#
#     Eric Nichols
#     Nicolas P. Rougier
#     Axel Hutt
#     Cyril Noël
#
# Contact Information:
#
#     Axel Hutt / Eric Nichols
#     INRIA Nancy
#     Equipe Neurosys
#     54603 Villers les Nancy  
#     France
#
# References:
#
#     Axel Hutt and Nicolas P. Rougier
#     "Activity spread and breathers induced by finite transmission
#      speeds in two-dimensional neural fields"
#     Physical Review Letter E, 2010.
#
# -----------------------------------------------------------------------------

if __name__ == "__main__":

    import sim.initialize as init
    init.WindUp()
