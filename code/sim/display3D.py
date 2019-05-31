#!/usr/bin/env python
# -- coding: utf-8 --
#
# Graph a 2 dimensional matrix in 3 dimensions
# Copyright (C) 2012-2015 Eric Nichols
#
# The python binding to the glfw library (glfw.py) is Nicolas P. Rougier's 
# source code downloaded from: https://github.com/rougier/pyglfw
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
#     Python 2.7: http://www.python.org
#     NumPy:      http://numpy.scipy.org
#     PyOpenGL:   http://pyopengl.sourceforge.net
#     GLFW ≥ 3.0: http://www.glfw.org  
#
# -----------------------------------------------------------------------------
#
# Contact Information:
#
#     Eric Nichols 
#     eric.nichols AT inria.fr
#
# -----------------------------------------------------------------------------

'''
Released on Sep 24, 2014

@author: Eric Nichols
@version 1.3.5 
'''
try:
    from OpenGL.GL   import * #@UnusedWildImport Suppress 'wild import' warning
except ImportError:
    print "\nThe graph3D library cannot find installation of OpenGL.GL!\n\n"

try:
    import glfw #@UnusedWildImport Suppress 'wild import' warning
except ImportError:
    print "\nThe graph3D library cannot find the installation of glfw!\n\n"
    
try:
    import numpy as np        # For quick math calculations
except ImportError:
    print "\nThe graph3D library cannot find installation of numpy!\n\n"

import platform
if platform.system().lower() == 'darwin':
    showText = True # text is shown correctly on Mac systems
else:
    showText = False # text is not shown correctly on non-Mac systems

try:
    from PIL import Image
    ableImage = 1
except ImportError:
    ableImage = 0
    ableVideo = -1
    ffmpegString = 'Cannot save video until the PIL library is installed and found by Python.'

if ableImage == 1:
    import os
    FNULL = open(os.devnull, 'w')
    import subprocess
    try:
        subprocess.check_call(['ffmpeg'], stdout=FNULL, stderr=subprocess.STDOUT)
        ableVideo = 1
        ffmpegString = 'ffmpeg'
    except subprocess.CalledProcessError:
        ffmpegString = '/opt/local/bin/ffmpeg'
        ableVideo = 1 # that's OK
    except OSError: # ffmpeg not found
        ableVideo = -1
        
    if ableVideo < 0: # one more try for mac, unix...
        try:
            subprocess.check_call(['/opt/local/bin/ffmpeg'], stdout=FNULL, stderr=subprocess.STDOUT) 
            ffmpegString = '/opt/local/bin/ffmpeg'
            ableVideo = 1
        except subprocess.CalledProcessError:
            ffmpegString = '/opt/local/bin/ffmpeg'
            ableVideo = 1# that's OK
        except OSError: # ffmpeg not found
            ableVideo = -1
            ffmpegString = 'Cannot save video until ffmpeg path is installed and found by Python.'
else:
    ableVideo = -1 
  
import copy # for copying a matrix
import time # for video


class graph3D:
    """Display a 2 dimensional NumPy array in 3 dimensions. 
    The 3D graph can be easily manipulated in various ways.
    It can be moved, rotated and zoomed in every direction 
    and the graph's colors can be modified at run-time. 
    
    """

    def __init__(self, matrix, windowName=" ", position=None, externalUpdate=False, xyText=None):
        """Entry point and starting function of the library. 
        
        :param matrix: 2D matrix that will be displayed in 3D
        :type  matrix: NumPy array
        :param windowName: text to write at the top of the window
        :type  windowName: string
        :param position: location of the window
        :type  position: list [x, y]
        :param externalUpdate: update the matrix externally
        :type  externalUpdate: boolean
        :param xyText: static x and y values for the axis. None uses grid units.
        :type  xyText: list [xMin, xMax, yMin, yMax]

        """
        
        self.windowW  = 640 # screen width
        self.windowH  = 480 # screen height
        self.border   = 10  # border size
        self.ticksize = 10  # tick size

        # Initialize the glfw library
        if not glfw.glfwInit():
            print 'Cannot initialize the glfw library.'
            import sys
            sys.exit()

        # Create a windowed mode window and its OpenGL context
        self.mainWindow = glfw.glfwCreateWindow(self.windowW, self.windowH, windowName, None, None)
        if not self.mainWindow:
            print 'Cannot initialize the window.'
            glfw.glfwTerminate()
            sys.exit()
        self.windowName = windowName

        if position is not None:
            glfw.glfwSetWindowPos(self.mainWindow, position[0], position[1])

        # Make the window's context current
        glfw.glfwMakeContextCurrent(self.mainWindow)

        self.initializeResources(matrix, xyText)  # initialize our resources

        # Register the following callback functions with glfw
        glfw.glfwSetWindowSizeCallback( self.mainWindow, self.changeShape) # for when shape of window changes
        glfw.glfwSetKeyCallback(        self.mainWindow, self.keyPressed) # for keyboard presses
        glfw.glfwSetMouseButtonCallback(self.mainWindow, self.mouseButton) # handles mouse presses
        glfw.glfwSetCursorPosCallback(  self.mainWindow, self.mouseMoved) # called when the cursor moves

        # before we begin main loop, print instructions to the user
        self.printInstructions()

        if not externalUpdate:
            # Loop until the user closes the window
            while not glfw.glfwWindowShouldClose(self.mainWindow):
     
                # Render here
                self.updateGraph()
     
            glDeleteProgram(self.program)  # clean up on isle delete
            glfw.glfwDestroyWindow(self.mainWindow)
            glfw.glfwTerminate()
        

    def closeWindow(self):
        """Close the GL window."""
        
        # first write our data to file
        try:
            fyl = open(self.fy, "w")
            fyl.write(str(self.rot_x)         +"\n") # original glm x rotation (for resetting values)   
            fyl.write(str(self.rot_y)         +"\n") # orig glm y rotation (for resetting values)
            fyl.write(str(self.shrink)        +"\n") # orig shrink; high number makes graph smaller
            fyl.write(str(self.upDown)        +"\n") # orig up-down location of the graph
            fyl.write(str(self.leftRight)     +"\n") # orig move graph left and right on screen
            fyl.write(str(self.numColors)              +"\n") # number of colors to interpolate between
            fyl.write(str(self.topColorHeight)         +"\n") # linear 1.0 adjustbl top color height 
            fyl.write(str(self.colorLow)               +"\n") # color for low values
            fyl.write(str(self.colorMid)               +"\n") # color for middle values
            fyl.write(str(self.colorHigh)              +"\n") # color for high values
            fyl.write(str(self.colorBackground)        +"\n")  # the original background color
            fyl.write(str(self.showGraph)              +"\n") # default do not show graph and text
            fyl.write(str(self.textSize)               +"\n") # text size: 0=small(7x7), 1=medium(8x13)
            fyl.write(str(self.graphMin)               +"\n") # The minimum value to show on the graph
            fyl.write(str(self.graphMax)               +"\n") # The maximum value to show on the graph

        except IOError:
            pass
        else:
            fyl.close()

        glfw.glfwSetWindowShouldClose(self.mainWindow, 1)


    def windowOpen(self):
        """Return whether or not the glfw window is open."""
        
        if not glfw.glfwWindowShouldClose(self.mainWindow):
            return True
        
        self.closeWindow()
        return False

        
    def changeShape(self, window, w, h):
        """Change the shape and position of objects when the window shape changes.
    
        :param w: new window width
        :type  w: int
        :param h: new window height
        :type  h: int
        
        """

        # save size
        self.windowW  = w  # screen width
        self.windowH  = h  # screen height


    def setMatrix(self):
        """Update the glTexImage2D with a new glTexSubImage2D. """

        mat = copy.copy(self.matCopy) # our working copy (might need unaltered self.matCopy later)

        # The minimum values to show on the graph
        if self.graphMin == None:
            self.Vmin = mat.min()
            if self.totalMinMax:
                if self.Vmin < self.valueMin:
                    self.valueMin = self.Vmin # new all time minimum value
                elif self.Vmin > self.valueMin:
                    self.Vmin = self.valueMin
        else:
            mat [ np.where( mat < self.graphMin ) ] = self.graphMin -5000
            self.Vmin = self.graphMin

        # The maximum values to show on the graph
        if self.graphMax == None:    
            self.Vmax = mat.max() # beyond Thunderdome ;)
            if self.totalMinMax:
                if self.Vmax > self.valueMax:
                    self.valueMax = self.Vmax # new all time maximum value
                elif self.Vmax < self.valueMax:
                    self.Vmax = self.valueMax
        else:
            mat [ np.where( mat > self.graphMax ) ] = self.graphMax +5000
            self.Vmax = self.graphMax


        # *****************************************************************
        # fit the matrix into our uint8 grid ******************************
        # We need to fit the matrix into byte sized data 0-255

        # We need to fit the matrix into byte sized data 0-255
        mat -= self.Vmin  # bring matrix + or - to 0 (uint8 base)

        # update maximum value over all epocs
        maxxi = self.Vmax - self.Vmin
        if maxxi > 0.0:
            self.flatLand = False
            mat = np.round((253.0/maxxi)*mat) +1
        else:
            # The land is flat
            mat += 1

        # put transparent items within range
        mat [ np.where( mat <   0 ) ] = 0
        mat [ np.where( mat > 255 ) ] = 255

        # bind self.texture_id to GL_TEXTURE_2D
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        
        # glTexSubImage2D reloads the image into OpenGL and video card's memory
        # It could be the case that the whole texture needs updating.
        # If so, Why use glTexSubImage2D() and not glTexImage2D()? I'm not sure 
        # about this, but elements such as the texture memory might have to be 
        # freed when you use glTexImage2D() and a re-allocation of memory would
        # have to be performed. We are not changing the texture, and so we are
        # using glTexSubImage2D which replaces and does not de- and re-allocate
        # memory. At the worst case, glTexSubImage2D won't be slower than
        # glTexSubImage2D...    
        glTexSubImage2D(
            GL_TEXTURE_2D,    # GLenum target
            0,                # GLint level, 0 = base, no minimal map,
            0,                # GLint xoffset
            0,                # GLint yoffset
            self.rows,        # GLsizei width
            self.cols,        # GLsizei height
            GL_LUMINANCE,     # GLenum format
            GL_UNSIGNED_BYTE, # GLenum type
            mat               # GLvoid* matrix
        )
        
        
    def updateGraph(self, matrix = None):
        """The main drawing function.
        
        :param matrix: our 2D matrix 
        :type  matrix: NumPy array
        
        """

        # Clear the color and depth buffers
        glClearColor (self.palette[0],self.palette[1],self.palette[2],1.0) # make it white and opaque
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT) # clear buffers


        if self.run and matrix is not None: # user has not paused the simulation
            self.matCopy = matrix # update the matrix
            self.setMatrix()

        # Enable depth comparisons and update depth buffer
        glEnable(GL_DEPTH_TEST)

        # Set texture interpolation mode for displaying z axis modifications
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)  # minify
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)  # magnify

        # Create a variable depth offset for each polygon with a factor of 1
        glPolygonOffset(1, 0)
        
        # Add offset to the depth values of the polygons' fragments
        glEnable(GL_POLYGON_OFFSET_FILL)
        
        # Enable attribute_coord2d vertex attribute array
        glEnableVertexAttribArray(self.attribute_coord2d)
        
        # Bind buffer1 to GL_ARRAY_BUFFER binding point
        glBindBuffer(GL_ARRAY_BUFFER, self.buffer1)
    
        # Specify location and matrix format of attribute_coord2d when rendering
        glVertexAttribPointer(self.attribute_coord2d, 2, GL_FLOAT, GL_FALSE, 0, None)
        
        # Bind buffer2 to GL_ELEMENT_ARRAY_BUFFER binding point
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.buffer2)
    
        # Render 60000 GL_UNSIGNED_SHORT GL_TRIANGLES     # (100 * 100 * 6) = 60000
        glUniform1i(self.showGrid, 0)
        glDrawElements(GL_TRIANGLES, 60000, GL_UNSIGNED_SHORT, None) 
        glUniform1i(self.showGrid, 1)
        
        # Reset the depth offset for each polygon to a factor of 0
        glPolygonOffset(0, 0)
        
        # Disable offset to the depth values of the polygons' fragments
        glDisable(GL_POLYGON_OFFSET_FILL)

        # Start show graph !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        if self.showGraph > 0:
                
            # Draw the grid lines 
            glBegin(GL_LINES)
            for valu in np.arange(-10,11,self.graphLines[self.showGraph])/10.0:   # 5 lines    
                # These next 4 lines of code print the up-down lines
                glVertex3f(valu,self.xparam,0.0) # X-axis wall
                glVertex3f(valu,self.xparam,1.0) # X-axis wall
                glVertex3f(self.yparam,valu,0.0) # Y-axis wall
                glVertex3f(self.yparam,valu,1.0) # Y-axis wall
                    
                # These next lines of code print the left-right lines
                glVertex3f(-1.0,self.xparam,valu/2 +.5) # X-axis wall
                glVertex3f( 1.0,self.xparam,valu/2 +.5) # X-axis wall
                glVertex3f(self.yparam, 1.0,valu/2 +.5) # Y-axis wall
                glVertex3f(self.yparam,-1.0,valu/2 +.5) # Y-axis wall  
            glEnd()

            if showText:
                # X Axis *********************************************************
                glUniform1i(self.showGrid, 2)
                # title
                glUniform3fv(self.uniform_text_location, 1, [(self.xparam*-0.15), float(self.xparam), 1.22]) 
                glRasterPos3f(0.0, 0.0, 0.0)

                # X Axis *********************************************************
                # axis title
                glPushAttrib(GL_LIST_BIT)
                glListBase(self.letters[self.textSize])
                glCallLists(len('X axis'), GL_UNSIGNED_BYTE, 'X axis')
                glPopAttrib()

                # axis values 
                for indx in range(5):  # for each string
                    xlo = ( self.xposi[indx] - (self.xparam * ((len(self.xCoordTxt[indx]) * .05) / 2.0)))       
                    glUniform3fv(self.uniform_text_location, 1, [xlo, self.xparam, 1.08]) 
                    glRasterPos3f(0.0, 0.0, 0.0)    
                    glPushAttrib(GL_LIST_BIT)
                    glListBase(self.letters[self.textSize])
                    glCallLists(len(self.xCoordTxt[indx]), GL_UNSIGNED_BYTE, self.xCoordTxt[indx])
                    glPopAttrib()
                # end X Axis *****************************************************

                # Y Axis *********************************************************
                # axis title
                glUniform3fv(self.uniform_text_location, 1, [(self.yparam*1.0), (self.yparam*0.15), 1.22]) 
                glRasterPos3f(0.0, 0.0, 0.0)
                glPushAttrib(GL_LIST_BIT)
                glListBase(self.letters[self.textSize])
                glCallLists(len('Y axis'), GL_UNSIGNED_BYTE, 'Y axis')
                glPopAttrib()
                
                # axis values 
                ranger = range(int(-self.xparam*.5+.5),int(-self.xparam*.5+4.5))
                for indx in ranger:                                    # for each string
                    xlo = ( self.yposi[indx] + ( self.yparam * (len(self.yCoordTxt[indx]) * .05) / 2.0) ) 
                    glUniform3fv(self.uniform_text_location, 1, [self.yparam, xlo, 1.08]) 
                    glRasterPos3f(0.0, 0.0, 0.0)   
                    glPushAttrib(GL_LIST_BIT)
                    glListBase(self.letters[self.textSize])
                    glCallLists(len(self.yCoordTxt[indx]), GL_UNSIGNED_BYTE, self.yCoordTxt[indx])
                    glPopAttrib()
                # end Y Axis *****************************************************

                # Z Axis *********************************************************
                # axis values     
                
                # if not a flat surface
                if not self.flatLand:
                    printArray = np.linspace(self.Vmax, self.Vmin, 5)
                    
                    if max(printArray) < 1 and min(printArray) > -1: # print in scientific notation
                        printStr = [str('%.1e' % printArray[0]).replace('e-0', 'e-'),
                                    str('%.1e' % printArray[1]).replace('e-0', 'e-'),
                                    str('%.1e' % printArray[2]).replace('e-0', 'e-'),
                                    str('%.1e' % printArray[3]).replace('e-0', 'e-'),
                                    str('%.1e' % printArray[4]).replace('e-0', 'e-')]
                    
                    elif (sum ([int(x)==x for x in printArray]) < 5)  or ((printArray.max() - printArray.min()) < 10):  # print as float
                        printStr = [str('%g' % printArray[0]),
                                    str('%g' % printArray[1]),
                                    str('%g' % printArray[2]),
                                    str('%g' % printArray[3]),
                                    str('%g' % printArray[4])]
                    
                    else: # all ints
                        printStr = [str('%i' % printArray[0]),
                                    str('%i' % printArray[1]),
                                    str('%i' % printArray[2]),
                                    str('%i' % printArray[3]),
                                    str('%i' % printArray[4])]

                    # axis values 
                    for indx in range(5):  # for each string
                        if printStr[indx] == '-0' or printStr[indx] == '-0.0':
                            printStr[indx] = printStr[indx][1:] 
                        glUniform3fv(self.uniform_text_location, 1, [self.zX, self.zY, self.zpos[indx]]) 
                        glRasterPos3f(0.0, 0.0, 0.0)     
                        glPushAttrib(GL_LIST_BIT)
                        glListBase(self.letters[self.textSize])
                        glCallLists(len(printStr[indx]), GL_UNSIGNED_BYTE, printStr[indx])
                        glPopAttrib()

                else: #  self.Vmax equals self.Vmin

                    if self.Vmax < 1 and self.Vmax > -1 and self.Vmax != 0.0: # print in scientific notation
                        printStr = str('%.1e' % self.Vmax).replace('e-0', 'e-')
                    
                    elif int(self.Vmax) != self.Vmax:  # print as float
                        printStr = str('%g' % self.Vmax)
                    
                    else: # all ints
                        printStr = str('%i' % self.Vmax)
 
                    # axis values 
                    if printStr == '-0' or printStr == '-0.0':
                        printStr = printStr[1:] 
                    glUniform3fv(self.uniform_text_location, 1, [self.zX, self.zY, self.zpos[4]]) 
                    glRasterPos3f(0.0, 0.0, 0.0)     
                    glPushAttrib(GL_LIST_BIT)
                    glListBase(self.letters[self.textSize])
                    glCallLists(len(printStr), GL_UNSIGNED_BYTE, printStr)
                    glPopAttrib()

                glFlush()
                # end Z Axis *****************************************************
        # END show graph !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        # Video recording
        if self.recording == 1:                 # recording in progress
            self.saveImage(1)                   # get a video image

        # Swap front and back buffers
        glfw.glfwSwapBuffers(self.mainWindow)
        
        # Poll for and process events
        glfw.glfwPollEvents()


    def updateTitle(self, newTitle):
        """Update the window title.
        
        :param newTitle: replace the current window title with this variable
        :type  newTitle: string
        
        """
        if self.minMaxMod == 0:
            if self.recording == 0:
                glfw.glfwSetWindowTitle(self.mainWindow, newTitle)
            else:
                glfw.glfwSetWindowTitle(self.mainWindow, 'Press v key to stop recording'+newTitle) 
            glfw.glfwPollEvents() # force the update
            

    def buildRotXmatrix(self, x_radians, buildVT=True):
        """Build a rotation matrix corresponding to the x axis of the graph.
    
        :param x_radians: number of radians we moved around the circle on the x axis
        :type  x_radians: float64
        :param buildVT: build the vertex transform
        :type  buildVT: boolean
        
        """
        
        c = np.cos(x_radians) # cosine of x_radians
        s = np.sin(x_radians) # sine   of x_radians
        
        # rotation matrix of X axis
        self.rotX = np.matrix([ [ c, s, 0, 0],
                                [-s, c, 0, 0],
                                [ 0, 0, 1, 0],
                                [ 0, 0, 0, 1] ])
    
        if buildVT:                                             # build the vertex transform
            self.buildRotYmatrix(np.radians(self.rot_y), True)  # rot_x changed: Re-build rotY
        else:                                                   # do not build 
            self.buildRotYmatrix(np.radians(self.rot_y), False) # rot_x changed: Re-build rotY
    
    
    def buildRotYmatrix(self, y_radians, buildVT=True):
        """Build a rotation matrix corresponding to the y axis of the graph.
    
        :param y_radians: number of radians we moved around the circle on the y axis
        :type  y_radians: float64
        :param buildVT: build the vertex transform
        :type  buildVT: boolean
        
        """
    
        c = np.cos(y_radians) # cosine of x_radians
        s = np.sin(y_radians) # sine   of x_radians
        
        if self.rot_x < 181:                      # first half graph (imaginary) circle
            param1 = (-0.5 / 45 * self.rot_x + 1) # linear equation to fit this half
            param2 = -1                           # this will change the sign of param2
            
        else:                                     # second half graph (imaginary) circle
            param1 = (0.5 / 45 * self.rot_x - 3)  # linear equation to fit this half
            param2 = 1                            # this will keep the sign of param2
        
        if param1 < 0.0:              # param1 is negative
            param2 *= (1.0 + param1)  # add 1 +param1 
        else:                         # param1 is positive
            param2 *= (1.0 - param1)  # sub 1 -param1 
    
        # compute self.rotYmatrix: the rotation matrix to apply to the Y axis
        l = (param1 * param1 + param2 * param2) ** 0.5
        a0 = param1 / l
        a1 = param2 / l
        t0 = a0 * (1.0 - c)
        t1 = a1 * (1.0 - c)
        self.rotYmatrix = np.matrix([ [(c + t0 * a0), (t0 * a1), (-s * a1), 0.0],
                            [(t1 * a0), (c + t1 * a1), (s * a0), 0.0],
                            [(s * a1), (-s * a0), c, 0.0],
                            [ 0.0, 0.0, 0.0, 1.0] ])
    
        if buildVT:                      # if build the vertex transform
            self.buildVertexTransform(3) # do it
    
    
    def buildViewMatrix(self, buildVT=True):
        """Build a matrix corresponding to the camera positioning (self.view).
        
        :param buildVT: build the vertex transform
        :type  buildVT: boolean
    
        """
        
        # Starting with camera positioning matrix (self.view)
        eye    = np.array([self.leftRight, -2.0, 2.0])    # camera position
        center = np.array([self.leftRight,  self.upDown, 0.0]) # center of graph
        up     = np.array([0.0,  0.0, 1.0])          # up direction
        
        cenMinEye = center -eye # subtract camera position from center of graph
        
        # normalize CenMinEye by dividing each CenMinEye component by its length
        cenMinEyeNorm = cenMinEye / np.sum(cenMinEye * cenMinEye) ** 0.5 
    
        # normalize 'up' by dividing each component of up by its length.
        upNorm = up / np.sum(up * up) ** 0.5   
    
        # normalize the cross product of the 2 norms: cenMinEyeNorm and upNorm
        cenUpCross = np.cross(cenMinEyeNorm, upNorm) # cross product
        cenUpNorm = cenUpCross /np.sum(cenUpCross *cenUpCross) **0.5 # normalize
        
        # get the cross product of the 2 norms: cenMinEyeNorm and cenUpNorm
        cenUpCross = np.cross(cenUpNorm, cenMinEyeNorm) 
    
        nEye = np.dot(cenUpNorm, eye)     # dot product of cenUpNorm and eye
        cEye = np.dot(cenUpCross, eye)    # dot product of cenUpCross and eye
        mEye = np.dot(cenMinEyeNorm, eye) # dot product of cenMinEyeNorm and eye
    
        # we have all the pieces. Now build the self.view matrix
        self.view = np.matrix([cenUpNorm, cenUpCross, -cenMinEyeNorm,[0.0,0.0,0.0]])
        self.view = np.append(np.transpose(self.view), [[-nEye, -cEye, mEye, 1.0]], 0)
    
        if buildVT:                 # if build the vertex transform
            self.buildVertexTransform(2) # do it
    
    
    def buildPerspectiveMatrix(self, numMultiply=1):
        """Build a matrix corresponding to the self.perspective projection.
        
        :param numMultiply: number of matrix multiplications to perform
        :type  numMultiply: int
    
        """
        
        # the self.perspective projection matrix
        # http://www.opengl.org/sdk/docs/man2/xhtml/gluPerspective.xml
        top_bottom  = np.tan(np.radians(self.shrink / 2.0)) * 0.2
        left_right  = 0.2 / (top_bottom * (1.0 * self.windowW / self.windowH))
        self.perspective = np.matrix([[left_right,              0.0,           0.0,  0.0],
                                      [       0.0, (0.2/top_bottom),           0.0,  0.0],
                                      [       0.0,              0.0, (-10.1 / 9.9), -1.0],
                                      [       0.0,              0.0,  (-2.0 / 9.9),  0.0]])
        
        self.buildVertexTransform(numMultiply) # build the vertex transform
    
    
    def buildVertexTransform(self, numMultiply=3):
        """Multiply matrices for vertex transformation matrix.
        
        :param numMultiply: number of matrix multiplications to perform
                            these must be done in the folowing order:
                            if ==3: self.rotYmatrix * self.rotX            then...
                            if >=2: (self.rotYmatrix * self.rotX) * self.view   then...
                            if >=1: (self.rotYmatrix * self.rotX  * self.view) * self.perspective
        :type  numMultiply: int
    
        """
    
        # perform multiplication on matrices
        if numMultiply == 3: 
            self.rotationMatrix = self.rotYmatrix * self.rotX        # y rotation * x rotation
            self.rotaViewMatrix = self.rotationMatrix * self.view    #   rotation * self.view
        elif numMultiply == 2:
            self.rotaViewMatrix = self.rotationMatrix * self.view    #   rotation * self.view
    
        self.vertex_transform = self.rotaViewMatrix *self.perspective#rotationView*self.perspective
        
        # glUniformMatrix4fv function needs self.vertex_transform to be contiguous array
        self.vertex_transform = np.ascontiguousarray(self.vertex_transform, dtype=np.float32)
        # Update value at self.uniform_vertex_transform location with self.vertex_transform
        glUniformMatrix4fv(self.uniform_vertex_transform, 1, GL_FALSE, self.vertex_transform)
        

    def xyCoordTxt(self, text=None):
        """Set the x and y coordinate values. 
        
            :param text: static x and y values for the axis. None uses grid units.
            :type  text: list [xMin, xMax, yMin, yMax]
        
        """
        
        if text is None:
            self.xCoordTxt = np.array(map(str,(np.linspace(0, self.rows, 5)))) # x axis numbered text
            self.yCoordTxt = np.array(map(str,(np.linspace(0, self.cols, 5)))) # y axix numbered text
        else:
            self.xCoordTxt = np.array(map(str,(np.linspace(text[0], text[1], 5)))) # x axis numbered text
            self.yCoordTxt = np.array(map(str,(np.linspace(text[2], text[3], 5)))) # y axix numbered text

        # convert to ints if possible
        for i in range(5):
            a = float(self.xCoordTxt[i])
            if a == int(a):
                self.xCoordTxt[i] = str(int(a))
            a = float(self.yCoordTxt[i])
            if a == int(a):
                self.yCoordTxt[i] = str(int(a))


    def initializeResources(self, mat, xyText):
        """Initialize the main resources we will need to draw the graph. 
        
        :param mat: 2D matrix that will be displayed in 3D
        :type  mat: NumPy array
        :param xyText: static x and y values for the axis. None uses grid units.
        :type  xyText: list [xMin, xMax, yMin, yMax]
        
        """

        self.run = True # True: run the code, False: user wants to pause

        # Original graph values...
        try:
            directry = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
            self.fy = os.path.join(directry,"params3D")
            fyl = open(self.fy)
            self.rot_x          =  float(fyl.readline())  # original glm x rotation (for resetting values)
            self.rot_y          =  float(fyl.readline())  # orig glm y rotation (for resetting values)
            self.shrink         =  float(fyl.readline())  # orig shrink; high number makes graph smaller
            self.upDown         =  float(fyl.readline())  # orig up-down location of the graph
            self.leftRight      =  float(fyl.readline())  # orig move graph left and right on screen
            self.numColors               =  int(  fyl.readline())  # number of colors to interpolate between
            self.topColorHeight          =  float(fyl.readline())  # linear 1.0 adjustbl top color height 
            self.colorLow                =  int(  fyl.readline())  # color for low values
            self.colorMid                =  int(  fyl.readline())  # color for middle values
            self.colorHigh               =  int(  fyl.readline())  # color for high values
            self.colorBackground         =  int(  fyl.readline())  # the original background color
            self.showGraph               =  int(  fyl.readline())  # default do not show graph and text
            self.textSize                =  int(  fyl.readline())  # text size: 0=small(7x7), 1=medium(8x13)
            # Graph min and max values: None denotes showing maximum or minimum of data set. 
            temp                         =  fyl.readline().strip()  # The minimum value to show on the graph
            if temp == 'None':
                self.graphMin            =  None
            else:
                self.graphMin            =  float(temp) 
            temp                         =  fyl.readline().strip()  # The maximum value to show on the graph
            if temp == 'None':
                self.graphMax            =  None
            else:
                self.graphMax            =  float(temp)   
            
        except:
            self.rot_x          =  22.0  # original glm x rotation (for resetting values)
            self.rot_y          = 336.0  # orig glm y rotation (for resetting values)
            self.shrink         =  52.5  # orig shrink; high number makes graph smaller
            self.upDown         =   0.26 # orig up-down location of the graph
            self.leftRight      =   0.3  # orig move graph left and right on screen
            self.topColorHeight_ORIGINAL =   0.5  # orig original top color height
            self.numColors               = 2      # number of colors to interpolate between
            self.topColorHeight          = 0.5    # linear 1.0 adjustbl top color height 
            self.colorLow                = 3      # color for low values
            self.colorMid                = 1      # color for middle values
            self.colorHigh               = 1      # color for high values
            self.colorBackground         = 0      # the original background color
            self.showGraph               = 0      # default do not show graph and text
            self.textSize                = 1 # text size: 0=small(7x7), 1=medium(8x13)
            # Graph min and max values: None denotes showing maximum or minimum of data set. 
            self.graphMin                = None # The minimum value to show on the graph
            self.graphMax                = None # The maximum value to show on the graph

        else:
            fyl.close()
        
        
        # initialize letters if we are on a MacOS
        if showText:
            self.letters = self.getCharacters()
        
        # spacing for graph lines
        self.graphLines     = [5.0,5.0,5.0, 2.5,2.5, 1.25,1.25] 
          
        # Our matrix shape
        self.rows, self.cols = mat.shape # number self.rows and columns in matrix
        self.totalMinMax = True  # limit the Z axis to the largest min/max over time (false=current min/max)
        
        # Coordinates for our elements
        self.rotYmatrix = 0                                         # the rotation matrix to apply to the Y axis
        self.xposi      = np.array([-1.0, -0.5,  0.0,  0.5,  1.0])  # x axis position text
        self.yposi      = np.array([-1.0, -0.5,  0.0,  0.5,  1.0])  # x axis position text
        self.zpos       = np.array([ 0.98, 0.73, 0.48, 0.23, 0.00]) # z axis position text
        self.xyCoordTxt(xyText)
        
        # Show the graph/grid states:
        #  0: don't show the graph        
        #  2+: show the graph
        self.setTheGraph()
        
        # is the mouse button pressed?
        self.mouseDown = False # the mouse is not down

        # video parameter
        if ableImage == 1:     # need images for recording
            self.frameNum  = 0 # first frame
        self.recording = 0 # currently not recording (0) or recording (1)

        self.minMaxMod  = 0    # Modify the min or max Z axis values -1:min, 0:none, 1:max
        self.minMaxText = ''   # text input
        
        # here's the variables for the colors
        # 1: violet
        # 2: blue
        # 3: cyan
        # 4: green
        # 5: yellow
        # 6: red
        # 7: white
        # 8: black
        self.foreColors = ['blank', 'violet', 'blue', 'cyan', 'green', 'yellow', 'red', 'white', 'black']
        
        # Setup background colors
        self.backColors = ['black', 'white', 'violet', 'blue', 'cyan', 'green', 'yellow', 'red']
        self.backgroundColors = ((0.0, 0.0, 0.0), # 1: black
                                 (1.0, 1.0, 1.0), # 2: white
                                 (1.0, 0.0, 1.0), # 3: violet
                                 (0.0, 0.0, 1.0), # 4: blue
                                 (0.0, 1.0, 1.0), # 5: cyan
                                 (0.0, 1.0, 0.0), # 6: green
                                 (1.0, 1.0, 0.0), # 7: yellow
                                 (1.0, 0.0, 0.0)) # 8: red
        self.setBackgroundColor(self.colorBackground)

        # Use a dictionary ('colors') to map our color selections
        # For each of 3 list [x,y,z] digits...
        # 0 => 0.0               in glsl
        # 1 => 1.0               in glsl
        # 2 => graph_coord.z     in glsl
        # 3 => (1-graph_coord.z) in glsl
        self.colors = {
            #             low -> high
            11: [1,0,1], # violet -> violet
            21: [3,0,1], # violet -> blue
            31: [3,2,1], # violet -> cyan
            41: [3,2,3], # violet -> green   
            51: [1,2,3], # violet -> yellow 
            61: [1,0,3], # violet -> red
            71: [1,2,1], # violet -> white
            81: [3,0,3], # violet -> black
        
            # --------------------------
        
            12: [2,0,1], # blue -> violet 
            22: [0,0,1], # blue -> blue
            32: [0,2,1], # blue -> cyan
            42: [0,2,3], # blue -> green
            52: [2,2,3], # blue -> yellow
            62: [2,0,3], # blue -> red
            72: [2,2,1], # blue -> white
            82: [0,0,3], # blue -> black
        
            # --------------------------
        
            13: [2,3,1], # cyan -> violet
            23: [0,3,1], # cyan -> blue
            33: [0,1,1], # cyan -> cyan
            43: [0,1,3], # cyan -> green
            53: [2,1,3], # cyan -> yellow
            63: [2,3,3], # cyan -> red
            73: [2,1,1], # cyan -> white
            83: [0,3,3], # cyan -> black
        
            # --------------------------
        
            14: [2,3,2], # green -> violet
            24: [0,3,2], # green -> blue
            34: [0,1,2], # green -> cyan
            44: [0,1,0], # green -> green
            54: [2,1,0], # green -> yellow
            64: [2,3,0], # green -> red
            74: [2,1,2], # green -> white
            84: [0,3,0], # green -> black
            
            # --------------------------
        
            15: [1,3,2], # yellow -> violet
            25: [3,3,2], # yellow -> blue
            35: [3,1,2], # yellow -> cyan
            45: [3,1,0], # yellow -> green   
            55: [1,1,0], # yellow -> yellow 
            65: [1,3,0], # yellow -> red
            75: [1,1,2], # yellow -> white
            85: [3,3,0], # yellow -> black
            
            # --------------------------
        
            16: [1,0,2], # red -> violet
            26: [3,0,2], # red -> blue
            36: [3,2,2], # red -> cyan
            46: [3,2,0], # red- > green 
            56: [1,2,0], # red- > yellow
            66: [1,0,0], # red- > red
            76: [1,2,2], # red -> white
            86: [3,0,0], # red -> black
        
            # --------------------------
        
            17: [1,3,1], # white -> violet
            27: [3,3,1], # white -> blue 
            37: [3,1,1], # white -> cyan 
            47: [3,1,3], # white -> green
            57: [1,1,3], # white -> yellow 
            67: [1,3,3], # white -> red 
            77: [1,1,1], # white -> white
            87: [3,3,3], # white -> black
            
            # --------------------------
            
            18: [2,0,2], # black -> violet
            28: [0,0,2], # black -> blue 
            38: [0,2,2], # black -> cyan 
            48: [0,2,0], # black -> green 
            58: [2,2,0], # black -> yellow 
            68: [2,0,0], # black -> red 
            78: [2,2,2], # black -> white 
            88: [0,0,0]  # black -> black    
        }


        # The vertex shader in the OpenGL Shading Language
        from OpenGL.GL import shaders
        VERTEX_SHADER = shaders.compileShader("""#version 120\n
        varying vec4 graph_coord;       /* 4 element vector */
        uniform mat4 texture_transform; /* 4x4 matrix */
        attribute vec3 coord2d;         /* 2 element vector */
        
        uniform vec3 axisText;
        
        uniform int showGrid;           /* 1:show 0:don't show;  */
        uniform sampler2D mytexture;    /* accessable 2D TEXTURE */
        uniform mat4 vertex_transform;  /* 4x4 matrix */
        void main(void) {
            graph_coord = texture_transform * vec4(coord2d, 1.0);
            if (showGrid==0) {
                graph_coord.z = texture2D(mytexture, graph_coord.xy/2.0 + 0.5).r; /* graph_coord.z value between 0.0 and 1.0 */
                gl_Position = vertex_transform * vec4(coord2d.x, coord2d.y, graph_coord.z, 1.0);
            } 
            else {
                gl_FrontColor = gl_Color;
                if (showGrid>1) {
                    gl_Position = vertex_transform * vec4(axisText, 1.0);
                }
                else {
                    gl_Position = vertex_transform * vec4(coord2d.x, coord2d.y, graph_coord.z, 1.0);
                }
            }
              
        } """, GL_VERTEX_SHADER)
        
        # The fragment shader in the OpenGL Shading Language
        FRAGMENT_SHADER = shaders.compileShader("""#version 120\n
        varying vec4 graph_coord;   /* 4 element vector */
        uniform int showGrid;       /* 1:show 0:don't show;  */
        uniform int colorFore[6];   /* the foreground color */
        uniform float topColHeight; /* height of the top color 0.0->0.5->1.0 min->init->max */
        float colorV[4];            /* values of color */
        
        void main(void) {
            vec4 colorIt;           /* local 4 element vector to color */
            colorV[0] = 0.0;
            colorV[1] = 1.0;
        
            if (showGrid>0)
                gl_FragColor = gl_Color;
            else if (graph_coord.z == int(graph_coord.z)) {
                        discard; /* discard if 0.0 or 1.0 */
            }
            else {
        
                /* Affline interpolation    y=a*x+b */
                /* if interopolating 2 colors */
                if (colorFore[3]<0.0) {
                    colorV[2] = (topColHeight>0.5) ? (graph_coord.z / (1.0 -((topColHeight - 0.5) * 2.0))) : (topColHeight * 2.0 * graph_coord.z);
                    colorV[3] = 1.0 - colorV[2];
                    gl_FragColor   = vec4(colorV[colorFore[0]], colorV[colorFore[1]], colorV[colorFore[2]], 1.0); 
                }
    
                /*  Otherwise, interpolating 3 colors */
                else {
            
                    /* if lower 2 colors */
                    if (graph_coord.z < (1.0 - topColHeight)) {
            
                        if (topColHeight<0.5) /* if bottom half is larger than top half */
                            colorV[2] = (graph_coord.z < (0.5 - topColHeight)) ? 0.0 : (graph_coord.z - (0.5 - topColHeight)) *2.0;
            
                        else /* otherwise, bottom half is smaller than top half */
                            colorV[2] = graph_coord.z * (1.0 / (1.0 - topColHeight)); 
            
                        colorV[3] = 1.0 - colorV[2];
                        gl_FragColor   = vec4(colorV[colorFore[0]],colorV[colorFore[1]],colorV[colorFore[2]],1.0); 
                    }
            
                    /* otherwise, we're in the higher 2 colors */
                    else {
                        /* if top half is smaller than bottom half */ 
                        if (topColHeight<0.5)
                            colorV[2] = (graph_coord.z - (1.0 - topColHeight)) / topColHeight; 
            
                        /* otherwise, top half is larger than top half */
                        else   
                            colorV[2] = (graph_coord.z > (1.0 -(topColHeight-0.5))) ? 1.0 : ((graph_coord.z - (1.0 -topColHeight))  *2.0);
            
                        colorV[3] = 1.0 - colorV[2];
                        gl_FragColor   =  vec4(colorV[colorFore[3]],colorV[colorFore[4]],colorV[colorFore[5]],1.0);
                    }
                }
            }
        }""", GL_FRAGMENT_SHADER)
        
        try:
            self.program = shaders.compileProgram(VERTEX_SHADER,FRAGMENT_SHADER)
        
        except:
            self.program = glCreateProgram()             # create an empty self.program object
            glAttachShader(self.program, VERTEX_SHADER)  # attach VERTEX_SHADER to self.program object
            glAttachShader(self.program, FRAGMENT_SHADER)# attach FRAGMENT_SHADER to self.program object
            glLinkProgram(self.program)                  # Link self.program and create executable 

        # get the location of an attribute "coord2d" in self.program
        self.attribute_coord2d = glGetAttribLocation(self.program, "coord2d")
    
        # get the location of the axis color
        self.showGrid = glGetUniformLocation(self.program, "showGrid")

        # Get the location of texture_transform uniform variable 
        # (to communicate with the vertex shader) in self.program 
        self.uniform_texture_transform = glGetUniformLocation(self.program, "texture_transform")

        # Get the location of vertex_transform uniform variable 
        # (to communicate with the vertex shader) in self.program    
        self.uniform_vertex_transform = glGetUniformLocation(self.program, "vertex_transform")

        # Get the location of the axisText variable
        self.uniform_text_location = glGetUniformLocation(self.program, "axisText")

        # Get the location of the color of foreground variable
        self.uniform_foreground_color = glGetUniformLocation(self.program, "colorFore")
    
        # Get the location of the color of top color height variable
        self.uniform_top_color_height = glGetUniformLocation(self.program, "topColHeight")

        # update the matrix
        self.matCopy  = mat
        self.Vmin     = mat.min()
        self.Vmax     = mat.max()
        self.valueMin = self.Vmin
        self.valueMax = self.Vmax
        maxxi         = self.Vmax - self.Vmin
        matrix        = copy.copy(mat)
        if maxxi > 0.0:
            # uneven ground
            self.flatLand = False
            matrix -= matrix.min()  # bring matrix + or - to 0 (uint8 base)
            matrix = np.round((253.0/maxxi)*matrix) +1
        else:
            # The land is flat
            self.flatLand = True
            matrix += 1

        # Upload the graph texture with our matrix points
        glActiveTexture(GL_TEXTURE0)             # select active texture
        self.texture_id = glGenTextures(1)            # generate the texture
        glBindTexture(GL_TEXTURE_2D, self.texture_id) # bind self.texture_id to GL_TEXTURE_2D

        glTexImage2D(         # load image into OpenGL and video card memory
            GL_TEXTURE_2D,    # GLenum target
            0,                # GLint level, 0 = base, no min map
            GL_LUMINANCE,     # GLint internal format
            self.rows,        # GLsizei width
            self.cols,        # GLsizei height
            0,                # GLint border 
            GL_LUMINANCE,     # GLenum format
            GL_UNSIGNED_BYTE, # GLenum type
            matrix            # GLvoid* matrix
        )

        # create first buffer 
        self.buffer1 = 7                         # initialize to arbitrary int
        glBindBuffer(GL_ARRAY_BUFFER, self.buffer1) # bind buffer1 to GL_ARRAY_BUFFER 
        # Our vertex positions
        vertexPos = np.zeros((101, 101, 2,), dtype='float32')
        for i in range(101):
            for j in range(101):
                vertexPos[i, j, 0] = ((j - 50) / 50.0)  # 0 is our x value
                vertexPos[i, j, 1] = ((i - 50) / 50.0)  # 1 is our y value
        # glBufferData(): a new matrix store for GL_ARRAY_BUFFER buffer object
        #      (vertexPos.size * 4)-> 81608  # * 4 for floats 
        glBufferData(GL_ARRAY_BUFFER, 81608, vertexPos.tostring(), GL_STATIC_DRAW) 
    
        # create second buffer
        self.buffer2 = 8  # initialize to a different arbitrary int
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.buffer2)#bind buff2 to G_ELEMENT_AB
        # Indices tracing horizontal and vertical lines
        indices = np.zeros(60600, dtype='uint16')  # 60600 = (100*101*6)
        k = iter(range(60600))  # iterate over range of indices
        for i in range(101):    # The triangles creating filled surface
            for j in range(100):
                indices[k.next()] = ((i * 101 + j))  # tri x
                indices[k.next()] = ((i * 101 + j + 1))  # tri x
                indices[k.next()] = (((i + 1) * 101 + j + 1))  # tri x
                indices[k.next()] = ((i * 101 + j))  # tri y
                indices[k.next()] = (((i + 1) * 101 + j + 1))  # tri y
                indices[k.next()] = (((i + 1) * 101 + j))  # tri y
        # glBufferData() creates new matrix store for GL_ELEMENT_ARRAY_BUFFER object
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, 121200,#121200=ind.size*ind.itemsize 
                     indices.tostring(), GL_STATIC_DRAW) 

        glUseProgram(self.program)  # install self.program as the current rendering state
    
        #-------------------- Modify Texture Transform -----------------------------
        # Our texture transform is an identity matrix
        self.identity4 = [ 1.0, 0.0, 0.0, 0.0,
                      0.0, 1.0, 0.0, 0.0,
                      0.0, 0.0, 1.0, 0.0,
                      0.0, 0.0, 0.0, 1.0]
        
        # modify the value of the uniform variable at texture_transform
        glUniformMatrix4fv(self.uniform_texture_transform, 1, GL_FALSE, self.identity4)
    
        #-------------------- Build Display Matrices -------------------------------
        # The OpenGL Mathematics (GLM) documentation for the original code 
        # (in c++) can be found here: http://glm.g-truc.net/glm-0.9.4.pdf
    
        # set up display matrices
        self.buildRotXmatrix(np.radians(self.rot_x), False)
        self.buildViewMatrix(False)
        self.buildPerspectiveMatrix(3)
    
        #---------------------------------------------------------------------------
    
        # update the colors
        if self.numColors == 2: # interpolate between 2 colors
            glUniform1iv(self.uniform_foreground_color,4,self.colors[self.colorHigh*10+self.colorLow]+[-1])
        else:                   # interpolate between 3 colors
            glUniform1iv(self.uniform_foreground_color, 6, 
                     self.colors[self.colorMid*10+self.colorLow]+self.colors[self.colorHigh*10+self.colorMid])
        glUniform1f(self.uniform_top_color_height, self.topColorHeight)


    def changeMinMax(self):
        '''Change the Z axis limits between:
           a. the current minimum and maximum axis values and
           b. the overall min and max over the course of the simulation.
           
        ''' 
        
        # swap totalMinMax truth value
        self.totalMinMax = not self.totalMinMax

        # reset valueMin and valueMax
        if self.totalMinMax:
            self.valueMin = self.Vmin
            self.valueMax = self.Vmax
        
        
    def getCharacters(self):
        ''' Return lists for printing numbers and letters. '''
        
        axTextSmall  = ((0x39, 0x44, 0x44, 0x44, 0x44, 0x44, 0x39), # '0'  
                        (0x7c, 0x10, 0x10, 0x10, 0x10, 0x50, 0x30), # '1' 
                        (0x39, 0x40, 0x40, 0x39, 0x04, 0x04, 0x39), # '2'  also possible (0x7c, 0x20, 0x10, 0x09, 0x04, 0x04, 0x39)
                        (0x39, 0x04, 0x04, 0x39, 0x04, 0x04, 0x39), # '3' 
                        (0x09, 0x09, 0x7c, 0x49, 0x29, 0x19, 0x09), # '4' 
                        (0x79, 0x04, 0x04, 0x39, 0x40, 0x40, 0x79), # '5' 
                        (0x39, 0x44, 0x44, 0x79, 0x40, 0x40, 0x39), # '6' 
                        (0x20, 0x20, 0x10, 0x10, 0x08, 0x05, 0x7c), # '7' 
                        (0x39, 0x44, 0x44, 0x39, 0x44, 0x44, 0x39), # '8' 
                        (0x30, 0x08, 0x04, 0x3c, 0x44, 0x44, 0x39), # '9' 
                        (0x44, 0x6c, 0x38, 0x10, 0x38, 0x6c, 0x44), # 'X' 
                        (0x10, 0x10, 0x10, 0x10, 0x38, 0x6c, 0x44), # 'Y' 
                        (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00), # ' ' 
                        (0x3d, 0x48, 0x39, 0x08, 0x39, 0x00, 0x00), # 'a' 
                        (0x44, 0x28, 0x10, 0x28, 0x44, 0x00, 0x00), # 'x' 
                        (0x19, 0x10, 0x10, 0x10, 0x30, 0x00, 0x10), # 'i' 
                        (0x79, 0x04, 0x39, 0x40, 0x3d, 0x00, 0x00), # 's' 
                        (0x10, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00), # '.' 
                        (0x00, 0x00, 0x00, 0x3c, 0x00, 0x00, 0x00), # '-' 
                        (0x3c, 0x40, 0x7c, 0x44, 0x39, 0x00, 0x00)) # 'e'

        axTextMid = ((0x00, 0x00, 0x3c, 0x66, 0x66, 0x66, 0x66, 0x66, 0x66, 0x66, 0x66, 0x66, 0x3c), # '0'
                     (0x00, 0x00, 0x3c, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x78, 0x38, 0x18), # '1'
                     (0x00, 0x00, 0x7e, 0x60, 0x60, 0x60, 0x60, 0x3c, 0x06, 0x06, 0x66, 0x66, 0x3c), # '2'
                     (0x00, 0x00, 0x3c, 0x66, 0x06, 0x06, 0x06, 0x1c, 0x06, 0x06, 0x06, 0x66, 0x3c), # '3'
                     (0x00, 0x00, 0x06, 0x06, 0x06, 0x06, 0x06, 0x7f, 0x66, 0x36, 0x1e, 0x0e, 0x06), # '4'
                     (0x00, 0x00, 0x3c, 0x66, 0x06, 0x06, 0x06, 0x7c, 0x60, 0x60, 0x60, 0x60, 0x7e), # '5'
                     (0x00, 0x00, 0x3c, 0x66, 0x66, 0x66, 0x66, 0x66, 0x7c, 0x60, 0x60, 0x66, 0x3c), # '6'
                     (0x00, 0x00, 0x0c, 0x0c, 0x0c, 0x0c, 0x0c, 0x1f, 0x06, 0x06, 0x06, 0x06, 0x7e), # '7'
                     (0x00, 0x00, 0x3c, 0x66, 0x66, 0x66, 0x66, 0x3c, 0x66, 0x66, 0x66, 0x66, 0x3c), # '8'
                     (0x00, 0x00, 0x3c, 0x66, 0x06, 0x06, 0x06, 0x3e, 0x66, 0x66, 0x66, 0x66, 0x3c), # '9'
                     (0x00, 0x00, 0xc3, 0x66, 0x66, 0x3c, 0x3c, 0x18, 0x3c, 0x3c, 0x66, 0x66, 0xc3), # 'X'
                     (0x00, 0x00, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x3c, 0x3c, 0x66, 0x66, 0xc3), # 'Y'
                     (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00), # ' '
                     (0x00, 0x00, 0x7d, 0xc3, 0xc3, 0xc3, 0x7f, 0x03, 0x7e, 0x00, 0x00, 0x00, 0x00), # 'a'
                     (0x00, 0x00, 0xc3, 0xe7, 0x3c, 0x18, 0x3c, 0xe7, 0xc3, 0x00, 0x00, 0x00, 0x00), # 'x'
                     (0x00, 0x00, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x00, 0x18, 0x18, 0x00), # 'i'
                     (0x00, 0x00, 0xfe, 0x03, 0x03, 0x7e, 0xc0, 0xc0, 0x7f, 0x00, 0x00, 0x00, 0x00), # 's'
                     (0x00, 0x00, 0x18, 0x18, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00), # '.'
                     (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x3c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00), # '-'
                     (0x00, 0x00, 0x7e, 0xc0, 0xc0, 0xfe, 0xc3, 0xc3, 0x7e, 0x00, 0x00, 0x00, 0x00)) # 'e'
        
        textList = ('0','1','2','3','4','5','6','7','8','9','X','Y',' ','a','x','i','s','.','-','e')
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        chars = [glGenLists(120), glGenLists(120)] # 120 is max value
        for k in range (2):
            for i in range(len(textList)):
                j = ord(textList[i]) 
                glNewList(chars[k] + j, GL_COMPILE)
                if k==0:
                    glBitmap(7, 7, 0.0, 0.0, 6.0, 0.0, axTextSmall[i])
                else:
                    glBitmap(8, 13, 0, 0, 10, 0, axTextMid[i])
                glEndList()
        return chars
        

    def setBackgroundColor(self, newColor):
        """Set the background and graph colors.
        newColor = 0: black background
        newColor = 1: white background
        newColor = 2: violet background
        newColor = 3: blue background
        newColor = 4: cyan background
        newColor = 5: green background
        newColor = 6: yellow background
        newColor = 7: red background
        
        """
        
        self.colorBackground = newColor
        self.palette = self.backgroundColors[self.colorBackground] # color palette
        glColor3ub( 255, 255, 255 ) # draw in white

        if newColor == 0 or newColor == 3 or newColor == 7:
            glColor3ub( 255, 255, 255 ) # draw grid in white
        else:
            glColor3ub( 0, 0, 0 ) # draw grid in black


    def setTheGraph(self):
        """A function called every occasion the user rotates the graph.
        It updates the variables containing the positions of the axis and 
        also the descriptive text.

        """

        # The next part sets the x and y parameters and positions of the respective text
        if  (self.rot_y > 45) and (self.rot_y < 235):
            if (self.rot_x < 90) or (self.rot_x > 269):
                self.xparam = -1
            else:
                self.xparam = 1

            if self.rot_x < 180:
                self.yparam = -1
            else:
                self.yparam = 1
        else:
            if self.rot_x > 179:
                self.yparam = -1
            else:
                self.yparam = 1

            if (self.rot_x > 89) and (self.rot_x < 270):
                self.xparam = -1
            else:
                self.xparam = 1

        # This next section sets the x and y parameters of the Z axis text
        if showText:
            if self.rot_x < 90:
                self.zX =  1.0
                self.zY = -1.06
            elif self.rot_x < 180: 
                self.zX = -1.06
                self.zY = -1.0
            elif self.rot_x < 270:
                self.zX = -1.0
                self.zY =  1.06
            else:
                self.zX =  1.06
                self.zY =  1.0


    def handle2Colors(self, newColor, lowHigh):
        """A function called every occasion the user selects a low or high color
        in a two color range. The chosen low or high color is saved and the 
        uniform foreground color is updated with the new information.
        
        :param newColor: 1: violet
                         2: blue
                         3: cyan
                         4: green
                         5: yellow
                         6: red
                         7: white
                         8: black
        :type  newColor: int
        
        :param lowHigh: 0: low
                        1: high
        :type  lowHigh: int
        
        """
        
        # fix possible error
        if newColor > 8:
            newColor = 1
        
        # if the low value is to be changed
        if lowHigh == 0: 
            self.colorLow = newColor
    
        # otherwise, the high value is to be changed
        else:
            self.colorHigh = newColor
        
        # Update the variable at the uniform foreground color location
        glUniform1iv(self.uniform_foreground_color,4,self.colors[self.colorHigh*10+self.colorLow]+[-1])
        
        return 0

    
    def handle3Colors(self, newColor, lowMidHigh):
        """A function called every occasion the user selects a low, middle or high 
        color in a three color range. The chosen low, middle or high color is saved 
        and the uniform foreground color is updated with the new information.

        :param newColor: 1: violet
                         2: blue
                         3: cyan
                         4: green
                         5: yellow
                         6: red
                         7: white
                         8: black
        :type  newColor: int
        
        :param lowMidHigh: 0: low
                           1: mid
                           2: high
        :type  lowMidHigh: int

        """
        
        # fix possible error
        if newColor > 8:
            newColor = 1
        
        # if the low value is to be changed
        if lowMidHigh == 0: 
            self.colorLow = newColor

        # otherwise, the middle value is to be changed
        elif lowMidHigh == 1:
            self.colorMid = newColor

        # otherwise, the high value is to be changed
        else:
            self.colorHigh = newColor
    
        # Update the variable at the uniform foreground color location
        glUniform1iv(self.uniform_foreground_color, 6, 
                     self.colors[self.colorMid*10+self.colorLow]+self.colors[self.colorHigh*10+self.colorMid])
        
        return 0
    
    
    def printInstructions(self):
        """Print user options to the standard output. """
      
        # Create an information menu
        print "\nFocus the graph window by clicking on it and then..."
        print "-> Revolve the graph:" 
        print "     -right by pressing the [RIGHT] arrow key." 
        print "     -left by pressing the [LEFT] arrow key." 
        print "     -up by pressing the [UP] arrow key." 
        print "     -down by pressing the [DOWN] arrow key." 
        print "     -in all directions via the mouse." 
        print "-> Move the graph:" 
        print "     -up by pressing the [e] key." 
        print "     -down by pressing the [d] key."
        print "     -left by pressing the [s] key."
        print "     -right by pressing the [f] key." 
        print "-> Zoom the graph:"                       
        print "     -in by pressing the [PAGE UP] key."  
        print "     -out by pressing the [PAGE DOWN] key." 
        print "-> Set Z axis boundary:"                     
        print "     -new minimum value - type... 1.[n] key, 2.value 3.[ENTER] key."  
        print "     -new maximum value - type... 1.[y] key, 2.value 3.[ENTER] key." 
        print "     -return axis to minimum data value - press the [m] key."  
        print "     -return axis to maximum data value - press the [u] key." 
        print "     -return both axes to data values - press the [j] key."
        print "-> Change colors (violet, blue, cyan, green, yellow, red, white, black):" 
        print "     -background pressing the [b] key." 
        print "     -highest on the graph by pressing the [q] key."
        print "     -middle on the graph by pressing the [a] key."
        print "     -lowest on the graph by pressing the [z] key." 
        print "-> Interpolate colors from:"                       
        print "     -lowest to highest by pressing the [2] key."  
        print "     -lowest to mid and from mid and highest by pressing the [3] key." 
        print "-> Move the height of the top color:"             
        print "     -higher by pressing the [k] key."            
        print "     -lower by pressing the [l] key."             
        print "     -to original height by pressing the [o] key."
        print "-> Pause / continue the simulation by pressing the [p] key." 
        print "-> Hide or change the number of axis lines by pressing the [g] key." 
        print "-> Change font size (2 sizes) by pressing the [t] key."
        print "-> Take a screenshot by pressing the [i] key." 
        print "-> Start / stop video recording by pressing the [v] key." 
        print "-> Press ESC key to quit."
        print "--------------------------------------------------------------------\n"
    

    def keyPressed(self, window, key, scancode, action, mods):
        """Handler for GLFW Keyboard events
    
        :param key: The keybord key that was pressed
        :type  key: unsigned char
        :param action: key tapped or held down
        :type  action: int
        
        """

        # repeat the following steps
        if action == glfw.GLFW_REPEAT: 
                             
            # if user pressed the left arrow key       
            if key == glfw.GLFW_KEY_LEFT: 
                self.rot_x = (self.rot_x - 1) % 360         # decrease rotation around x axis
                self.buildRotXmatrix(np.radians(self.rot_x)) # build x rotational matrix
                if self.showGraph > 0:
                    self.setTheGraph() # update graph data  
                        
            #if user pressed the right arrow key
            elif key == glfw.GLFW_KEY_RIGHT:   
                self.rot_x = (self.rot_x + 1) % 360         # increase rotation around x axis
                self.buildRotXmatrix(np.radians(self.rot_x)) # build x rotational matrix
                if self.showGraph > 0:
                    self.setTheGraph() # update graph data
                
            # if user pressed the up arrow key
            elif key == glfw.GLFW_KEY_UP:
                self.rot_y = (self.rot_y - 1) % 360         # decrease rotation around y axis
                self.buildRotYmatrix(np.radians(self.rot_y)) # build y rotational matrix
                if self.showGraph > 0:
                    self.setTheGraph() # update graph data
            
            # if user pressed the down arrow key
            elif key == glfw.GLFW_KEY_DOWN:
                self.rot_y = (self.rot_y + 1) % 360         # increase rotation around y axis
                self.buildRotYmatrix(np.radians(self.rot_y)) # build y rotational matrix
                if self.showGraph > 0:
                    self.setTheGraph() # update graph data
            
            # if user pressed the page up key
            elif key == glfw.GLFW_KEY_PAGE_UP:
                if self.shrink > 0.6:       # This avoids 'float division by zero' later
                    self.shrink -= 0.5                  # decrease the self.perspective
                    self.buildPerspectiveMatrix()  # rebuild the self.perspective matrix
        
            # if user pressed the page down key
            elif key == glfw.GLFW_KEY_PAGE_DOWN:
                self.shrink += 0.5                      # increase the self.perspective
                self.buildPerspectiveMatrix()      # rebuild the self.perspective matrix

            # if user pressed the 'k' key
            elif key == glfw.GLFW_KEY_K:        # raise the height of the top color
                if (self.topColorHeight>=0.02):   # if it's not too low
                    self.topColorHeight -= 0.02 # raise color   
                else:
                    self.topColorHeight = 0.0 # just making sure...         
                # change the uniform top color height value
                glUniform1f(self.uniform_top_color_height, self.topColorHeight)              
        
            # if user pressed the 'l' key
            elif key == glfw.GLFW_KEY_L:          # lower the height of the top color
                if (self.topColorHeight<=0.98):  # if it's not too high
                    self.topColorHeight += 0.02 # lower color
                else:
                    self.topColorHeight = 1.0 # just making sure...
                # change the uniform top color height value
                glUniform1f(self.uniform_top_color_height, self.topColorHeight)
                        
        # only perform once
        elif action == glfw.GLFW_PRESS:

            # if numbers, '-' and '.'
            if key < glfw.GLFW_KEY_SEMICOLON: 
                
                if self.minMaxMod != 0:
                    
                    # user pressed negative key
                    if key == glfw.GLFW_KEY_MINUS:
                        self.minMaxText = '-'
                        glfw.glfwSetWindowTitle(self.mainWindow, self.titletext +self.minMaxText)
                    
                    # user pressed period key
                    elif key == glfw.GLFW_KEY_PERIOD:
                        self.minMaxText += '.'
                        glfw.glfwSetWindowTitle(self.mainWindow, self.titletext +self.minMaxText)
    
                    # possibly a number entered
                    else:
                        try:
                            self.minMaxText += str(chr(key)) # ValueError if not an int
                            glfw.glfwSetWindowTitle(self.mainWindow, self.titletext +self.minMaxText)
                        except:
                            self.minMaxMod = 0 # exit input
                            glfw.glfwSetWindowTitle(self.mainWindow, self.windowName)
                
                # if user pressed the number 2 while not changing min-max Z axis values
                elif key == glfw.GLFW_KEY_2:
                    self.numColors = 2
                    self.handle2Colors(self.colorHigh,1)

                # if user pressed the number 3 while not changing min-max Z axis values
                elif key == glfw.GLFW_KEY_3:
                    self.numColors = 3
                    self.handle3Colors(self.colorHigh,2)

            elif key > glfw.GLFW_KEY_WORLD_2: 

                # if user pressed the enter key
                if key == glfw.GLFW_KEY_ENTER:
                    if self.minMaxMod != 0:
                        try:
                            floating = float(self.minMaxText) # ValueError if not a number
                            if self.minMaxMod == -1:
                                self.graphMin = floating
                            elif self.minMaxMod == 1:
                                self.graphMax = floating
                        except:
                            pass
                        self.minMaxText = ''
                        self.minMaxMod = 0
                        glfw.glfwSetWindowTitle(self.mainWindow, self.windowName)
                        self.setMatrix()

                # if user pressed the backspace key
                elif key == glfw.GLFW_KEY_BACKSPACE:
                    if self.minMaxMod != 0:
                        self.minMaxText = self.minMaxText[:-1]
                        glfw.glfwSetWindowTitle(self.mainWindow, self.titletext +self.minMaxText)

                # if user pressed the left arrow key       
                elif key == glfw.GLFW_KEY_LEFT: 
                    self.rot_x = (self.rot_x - 1) % 360         # decrease rotation around x axis
                    self.buildRotXmatrix(np.radians(self.rot_x)) # build x rotational matrix
                    if self.showGraph > 0:
                        self.setTheGraph() # update graph data  
                            
                #if user pressed the right arrow key
                elif key == glfw.GLFW_KEY_RIGHT:   
                    self.rot_x = (self.rot_x + 1) % 360         # increase rotation around x axis
                    self.buildRotXmatrix(np.radians(self.rot_x)) # build x rotational matrix
                    if self.showGraph > 0:
                        self.setTheGraph() # update graph data
                    
                # if user pressed the up arrow key
                elif key == glfw.GLFW_KEY_UP:
                    self.rot_y = (self.rot_y - 1) % 360         # decrease rotation around y axis
                    self.buildRotYmatrix(np.radians(self.rot_y)) # build y rotational matrix
                    if self.showGraph > 0:
                        self.setTheGraph() # update graph data
                
                # if user pressed the down arrow key
                elif key == glfw.GLFW_KEY_DOWN:
                    self.rot_y = (self.rot_y + 1) % 360         # increase rotation around y axis
                    self.buildRotYmatrix(np.radians(self.rot_y)) # build y rotational matrix
                    if self.showGraph > 0:
                        self.setTheGraph() # update graph data
                
                # if user pressed the page up key
                elif key == glfw.GLFW_KEY_PAGE_UP:
                    if self.shrink > 0.6:       # This avoids 'float division by zero' later
                        self.shrink -= 0.5                  # decrease the self.perspective
                        self.buildPerspectiveMatrix()  # rebuild the self.perspective matrix
            
                # if user pressed the page down key
                elif key == glfw.GLFW_KEY_PAGE_DOWN:
                    self.shrink += 0.5                      # increase the self.perspective
                    self.buildPerspectiveMatrix()      # rebuild the self.perspective matrix
    
                # if user pressed the escape key
                elif key == glfw.GLFW_KEY_ESCAPE: #and action == glfw.GLFW_PRESS:
                    self.closeWindow()

            elif key < glfw.GLFW_KEY_M:
                if key < glfw.GLFW_KEY_G:
                    # if user pressed the a key
                    if key == glfw.GLFW_KEY_A:
                        self.numColors = 3
                        self.handle3Colors(self.colorMid+1, 1)
        
                    # if user pressed the b key
                    elif key == glfw.GLFW_KEY_B:
                        self.setBackgroundColor(np.mod(self.colorBackground+1,8))
        
                    # if user pressed the 'd' key
                    elif key == glfw.GLFW_KEY_D:        # move the graph down on the screen
                        if (self.upDown<3.5):           # if it's not too low
                            self.upDown += 0.05         # move it down
                            self.buildViewMatrix(True)  # rebuild the matrix self.view
        
                    # if user pressed the 'e' key
                    elif key == glfw.GLFW_KEY_E:        # move the graph up on the screen
                        if (self.upDown>-1.5):          # if it's not too high
                            self.upDown -= 0.05         # move it up
                            self.buildViewMatrix(True)  # rebuild the matrix self.view
                            
                    # if user pressed the 'f' key
                    elif key == glfw.GLFW_KEY_F:       # move the graph right on the screen
                        if (self.leftRight>-3.0):           # if it's not too low
                            self.leftRight -= 0.05         # move it down
                            self.buildViewMatrix(True)  # rebuild the matrix self.view

                else:
                    # if user pressed the 'g' key
                    if key == glfw.GLFW_KEY_G:     # modify grid visualization
                        self.showGraph += 2     # update axes interval
                        if self.showGraph > 6:  # too high
                            self.showGraph -= 8 # reset grid
                        else:
                            self.setTheGraph()  # update axes data
        
                    # if user pressed the 'i' key
                    elif key == glfw.GLFW_KEY_I:   # save an image of the dnf and properties windows
                        if ableImage == 1:    # PIL library is preseent to save picture
                            self.saveImage(0) # save as an image
                        else:                 # otherwise...
                            print "Cannot save image until the PIL library is installed and found by Python."
        
                    # if user pressed the 'J' key
                    elif key == glfw.GLFW_KEY_J:
                        self.graphMin = None
                        self.graphMax = None
                        self.setMatrix()
        
                    # if user pressed the 'k' key
                    elif key == glfw.GLFW_KEY_K:        # raise the height of the top color
                        if (self.topColorHeight>=0.02):   # if it's not too low
                            self.topColorHeight -= 0.02 # raise color   
                        else:
                            self.topColorHeight = 0.0 # just making sure...         
                        # change the uniform top color height value
                        glUniform1f(self.uniform_top_color_height, self.topColorHeight)              
        
                    # if user pressed the 'l' key
                    elif key == glfw.GLFW_KEY_L:          # lower the height of the top color
                        if (self.topColorHeight<=0.98):  # if it's not too high
                            self.topColorHeight += 0.02 # lower color
                        else:
                            self.topColorHeight = 1.0 # just making sure...
                        # change the uniform top color height value
                        glUniform1f(self.uniform_top_color_height, self.topColorHeight)


            elif key < glfw.GLFW_KEY_S:

                # if user pressed the 'm' key
                if key == glfw.GLFW_KEY_M:
                    self.graphMin = None
                    self.setMatrix()
    
                # if user pressed the 'n' key
                elif key == glfw.GLFW_KEY_N:
                    self.minMaxMod = -1
                    self.titletext = 'Enter minimum Z axis value: '
                    glfw.glfwSetWindowTitle(self.mainWindow, self.titletext)
    
                # if user pressed the 'o' key
                elif key == glfw.GLFW_KEY_O: # original height of the top color value
                    self.topColorHeight = 0.5   # reset to original value    
                    # change the uniform top color height value
                    glUniform1f(self.uniform_top_color_height, self.topColorHeight)
                
                # if user pressed the 'p' key
                elif key == glfw.GLFW_KEY_P:
                    self.run = not self.run  # pause/run the simulation
                    
                # if user pressed the 'q' key
                elif key == glfw.GLFW_KEY_Q:
                    if self.numColors == 2: # interpolating between 2 colors
                        self.handle2Colors(self.colorHigh+1,1)
                    else:
                        self.handle3Colors(self.colorHigh+1, 2)
                    
                # if user pressed the 'r' key
                elif key == glfw.GLFW_KEY_R:
                    self.changeMinMax() # change min/max z values

            # if user pressed the 's' key
            elif key == glfw.GLFW_KEY_S:        # move the graph left on the screen 
                if (self.leftRight<3.0):          # if it's not too high
                    self.leftRight += 0.05         # move it up
                    self.buildViewMatrix(True)  # rebuild the matrix self.view
                    
            # if user pressed the 't' key
            elif key == glfw.GLFW_KEY_T:
                self.textSize = np.mod(self.textSize+1,2)

            # if user pressed the 'u' key
            elif key == glfw.GLFW_KEY_U:
                self.graphMax = None
                self.setMatrix()

            # if user pressed the 'v' key
            elif key == glfw.GLFW_KEY_V:   # save a video of the simulation
                if ableVideo == 1:    # we are able to save video
                    if self.recording == 1: # currently recording
    
                        now = time.time() # current time
    
                        print 'Processing video...'
    
                        # find number of frames per second
                        numSecs   = now - self.vidStartTime               # number of seconds recorded
                        fle       = os.path.join(os.path.dirname(__file__), 'tmp')
                        numFrames = len([nm for nm in os.listdir(fle)]) # number of saved frames
                        frmPsec   = str(int(float(numFrames) / numSecs) * 3)    # number of frames per second
                        # print 'frames per second', frmPsec
                        #print os.getcwd()
                        os.chdir(fle)
                        # make the video as a subprocess with ffmpeg
                        # firest, make the name of the file unique, accoding to the current time
                        filename = time.asctime( time.localtime(time.time()) )  + '.mp4'
                        
                        # original mp4 video (works fine)
                        subprocess.call([ffmpegString, '-y', '-r', frmPsec, '-i', os.path.join(fle, 'img%d.png'), '-b:v', '1M', '-bt', '2M', '-vcodec', 'libx264', '-acodec', 'libfaac', '-ac', '2', '-ar', '48000', '-ab', '192k', filename], stdout=FNULL, stderr=subprocess.STDOUT)    
                        
                        # mp4 video that works with fewer parameters
                        #subprocess.call([ffmpegString, '-y', '-r', frmPsec, '-i', 'tmp/img%d.png', '-f', 'mp4', '-b', '400k', filename], stdout=FNULL, stderr=subprocess.STDOUT)    
                        
                        #flash video
                        #subprocess.call([ffmpegString, '-y', '-r', frmPsec, '-i', 'tmp/img%d.png', '-b:v', '2M', '-bt', '4M', '-ac', '2', '-ar', '48000', '-ab', '192k', '-f', 'flv', '-s', '320x240', '-aspect', '4:3', 'video.flv'], stdout=FNULL, stderr=subprocess.STDOUT)  
    
                        self.recording = 0 # stop recording
                        
                        # now delete all the created files
                        import shutil
                        shutil.move(filename, '..')
                        shutil.rmtree(fle)

                        glfw.glfwSetWindowTitle(self.mainWindow, self.windowName)
                        
                        print 'Completed saving video to %s'% (os.path.join(os.path.dirname(__file__), 'output.mp4')) 
    
                    else:                  # not currently recording
                        thePath = os.path.join(os.path.dirname(__file__), 'tmp')
                        if not os.path.exists(thePath):
                            os.makedirs(thePath)
                        
                        glfw.glfwSetWindowTitle(self.mainWindow, 'Video recording underway. Press v key to stop.')
    
                        self.frameNum  = 0 # reset first frame number
                        self.recording = 1 # start recording
                        self.saveImage(1)  # get first video image
                        self.vidStartTime = time.time() # start timer
    
                else:                 # otherwise...
                    print ffmpegString

            elif key == glfw.GLFW_KEY_Y:
                self.minMaxMod = 1
                self.titletext = 'Enter maximum Z axis value: '
                glfw.glfwSetWindowTitle(self.mainWindow, self.titletext)

            # if user pressed the z key
            elif key == glfw.GLFW_KEY_Z:
                if self.numColors == 2: # interpolating between 2 colors
                    self.handle2Colors(self.colorLow+1, 0)
                else:
                    self.handle3Colors(self.colorLow+1, 0)


    def saveImage(self, video=0, hasName=None):
        """Save an image of the window. 

        :param video: save image as an image or part of a video
        :type  video: int (0:picture, 1:video)
        
        :param hasName: give the inage a name. If None, the time will be the name
        :type  hasName: string
        
        """

        # variable name data previously taken. I'm from Boston so... dater is the new data
        #dater = glReadPixelsub(0, 0, self.windowW, self.windowH, GL_RGB).tostring()
        dater = glReadPixels(0, 0, self.windowW, self.windowH, GL_RGB, GL_UNSIGNED_BYTE)
        
        image = Image.fromstring('RGB', (self.windowW,self.windowH), dater)
        image = image.transpose(Image.FLIP_TOP_BOTTOM)

        if video == 0:   # still image requested
            if hasName:  # an image name was submitted
                filename = str(hasName) + ".png" # give the parameter to the filename
            else:        # an image name was not submitted
                filename = time.asctime( time.localtime(time.time()) )  + ".png" # use the time as a filename

            fle = os.path.join(os.path.dirname(__file__), filename) 
            print 'Saving image to %s'% (os.path.abspath(fle))  

        else:
            flea = os.path.join(os.path.dirname(__file__), 'tmp') 
            fle = os.path.join(flea, ("img" + str(self.frameNum)  + ".png"))
            self.frameNum += 1

        image.save(fle, "PNG") #"JPEG")

    
    def mouseButton(self, window, button, action, mods):
        """Callback for when a mouse button is pressed or released.

        :param window: the window that received the event
        :type  window: int
        :param button: the mouse button that was pressed or released
        :type  button: int
        :param action: one of GLFW_PRESS or GLFW_RELEASE
        :type  action: int
        :param mods:   bit field describing which modifier keys were held down
        :type  mods:   int
         
        """

        if button == glfw.GLFW_MOUSE_BUTTON_LEFT:
            if action == glfw.GLFW_PRESS:
                self.mouseDown = True
                # save the x and y position of the mouse
                self.mousePosX, self.mousePosY = glfw.glfwGetCursorPos(window)
            else:
                self.mouseDown = False    # the mouse is no longer down


    def mouseMoved(self, window, xpos, ypos):
        '''Callback for then the cursor position changes.
        
        :param window: the window that received the event
        :type  window: int
        :param xpos: the new x-coordinate, in screen coordinates, of the cursor
        :type  xpos: int
        :param ypos: the new y-coordinate, in screen coordinates, of the cursor
        :type  ypos: int
        
        '''

        if self.mouseDown: # mouse left button is pressed
            self.rot_x = (self.rot_x + int((xpos - self.mousePosX)/1.5)) % 360 # mod x ax rotatn
            self.rot_y = (self.rot_y + int((ypos - self.mousePosY)/1.5)) % 360 # mod y ax rotatn
            self.mousePosX = xpos           # update x position while mouse is clicked
            self.mousePosY = ypos           # update y position while mouse is clicked
            self.buildRotXmatrix(np.radians(self.rot_x)) # rebuild x rotation matrix
            if self.showGraph > 0:
                self.setTheGraph()                    # update graph parameters

