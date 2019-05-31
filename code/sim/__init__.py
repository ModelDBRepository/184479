#!/usr/bin/env python
# -- coding: utf-8 --

# get current directory and destination file (fyl)
import os
directry = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
fyl  = os.path.join(directry,'dnf.py')

# Which data to show
# 0 = show V0 matrix - do not update V
# 1 = show V matrix after V updates
# 2 = show input matrix
# 3 = show kernel matrix
import values as p
showData = int(p.showData)

# simulate over time?
simOVERtime = True

# voltage input from external source?
externalI = True

if showData == 2: # only show V at time=0
   simOVERtime = False 
    
elif showData == 4 and 'updateK' not in dir(p): # only show K at time = 0
    simOVERtime = False

elif 'updateI' not in dir(p): # only show I at time = 0
    if showData == 3: 
        simOVERtime = False
    elif p.I is None:
        externalI = False
    elif isinstance(p.I, int) or isinstance(p.I, float):
        if p.I == 0.0:
            externalI = False

# if running updates is not chosen,
# display only time=0 data
if not simOVERtime: 
    
    # open file and write for all showData > 1
    file = open(fyl, 'w')
    file.write('class Data():\n')
    file.write('    def __init__(self):\n')
    file.write('        import values as p\n')

    if showData == 2:
        file.write('        self.output = p.V0\n')
        title = 'V0min: %.12f     V0max: %.12f' %(p.V0.min(),p.V0.max())
    elif showData == 3:
        file.write('        self.output = p.I\n')
        title = 'Imin: %.12f     Imax: %.12f' %(p.I.min(),p.I.max())
    elif showData == 4:
        file.write('        self.output = p.K\n')
        title = 'Kmin: %.12f     Kmax: %.12f' %(p.K.min(),p.K.max())
    
    file.write('        from sim import display3D as g3\n')
    file.write('        self.dim3=g3.graph3D(self.output, \'')
    file.write(title)
    file.write('\', externalUpdate=True, xyText=[0,' +str(p.l) +',0,' +str(p.l) +'])\n')
    file.write('        self.dim3.changeMinMax()\n')
    file.write('        while self.dim3.windowOpen():\n')
    file.write('            self.dim3.updateGraph(self.output)\n')
    file.close()
    
# simulate over time (beyond t=0)           
else:
    
    # copy universal dnf.py code
    import shutil
    shutil.copyfile(os.path.join(directry,'dnf_template'), os.path.join(directry,'dnf.py'))

    with open(fyl, "a") as file:
        noizy = True

        # if the user wants to update I after the simulation starts
        if 'updateI' in dir(p):
            file.write('            # update I\n')
            foundit = False
            with open(os.path.join(os.path.join(directry, os.pardir), 'values.py'), 'r') as reed:
                for line in reed:
                    if line.lstrip().startswith('def updateI'):
                        foundit = True
                    elif foundit:
                        if '  return ' in line:
                            foundit = False
                            line = line.split('#',1)[0] # cut everything at # and after
                            if line.split('return ',1)[1].strip() != 'I':
                                file.write('        ' +line.replace('return', 'self.I ='))
                        else:
                            if 'time' in line:
                                line = line.replace('time', 'self.epoc')
                                if '==' in line and ':' in line:
                                    temp = line[line.rindex('==')+2:line.rindex(':')]
                                    line = line.replace(temp, str(int(float(temp)/p.dt)))
                            if "I=" in line.replace(" ", ""):
                                line = line.replace('I', 'self.I',1)
                            file.write('        ' +line)
            file.write('\n') # ad a space

        # if the user wants to update K after the simulation starts
        if 'updateK' in dir(p):
            file.write('            # update K\n')
            foundit = False
            with open(os.path.join(os.path.join(directry, os.pardir), 'values.py'), 'r') as reed:
                for line in reed:
                    if line.lstrip().startswith('def updateK'):
                        foundit = True
                    elif foundit:
                        if '  return ' in line:
                            foundit = False
                            line = line.replace('time', 'self.epoc')
                            line = line.split('#',1)[0] # cut everything at and after #
                            if line.split('return ',1)[1].strip() != 'K':
                                line = line.replace('K', 'self.K_')
                                file.write('        ' +line.replace('return', 'self.K_ ='))
                        else:
                            if 'time' in line:
                                line = line.replace('time', 'self.epoc')
                                if '==' in line and ':' in line:
                                    temp = line[line.rindex('==')+2:line.rindex(':')]
                                    line = line.replace(temp, str(int(float(temp)/p.dt)))
                            if "K" in line:
                                line = line.replace('K', 'self.K_')
                            file.write('        ' +line)
            file.write('            self.finite() \n\n') # ad a space

        if p.eta == 0.0:  # do not calculate second derivative
            file.write('            # update V\n')
            try:
                if p.noiseVcont is None or p.noiseVcont == 0.0: # do not add noise added every epoc
                    if externalI:                               # input from external source
                        file.write('            self.Vexcite += self.dt/self.gammafactor*(-self.Vexcite+L+self.I)\n\n') 
                    else:                                       # no external input
                        file.write('            self.Vexcite += self.dt/self.gammafactor*(-self.Vexcite+L)\n\n') 
                    noizy = False
            except:
                pass
            if noizy:
                if externalI:                               # input from external source
                    file.write('            self.Vexcite += self.dt/self.gammafactor*(-self.Vexcite+L+self.I) +np.random.normal(0,1.0,(self.n,self.n))*self.noisy\n\n') 
                else:
                    file.write('            self.Vexcite += self.dt/self.gammafactor*(-self.Vexcite+L) +np.random.normal(0,1.0,(self.n,self.n))*self.noisy\n\n')

        else: # calculate second derivative
            file.write('            # perform first and second order calculation\n')
            file.write('            self.VexciteOLD = self.Vexcite\n')
            try:
                if p.noiseVcont is None or p.noiseVcont == 0.0: # no noise added every epoc
                    file.write('            self.Vexcite += self.dt*self.Uexcite\n')
                    noizy = False
            except:
                pass
            if noizy:
                file.write('            self.Vexcite += self.dt*self.Uexcite +np.random.normal(0,1.0,(self.n,self.n))*self.noisy\n')
            if externalI: # input from external source
                file.write('            self.Uexcite += (self.dt*(-self.gammafactor*self.Uexcite-self.VexciteOLD+L+self.I))/self.etafactor\n\n')
            else:
                file.write('            self.Uexcite += (self.dt*(-self.gammafactor*self.Uexcite-self.VexciteOLD+L))/self.etafactor\n\n')
    
        file.write('            # update U\n')
        if 'updateS' in dir(p): # modern method
            file.write('            self.U = [fftshift(fft2(ifftshift(p.updateS(self.Vexcite)))),] + self.U[:-1]\n\n')
            rewrite = False # do not rewrite updateS
        else:                   # archaic method
            file.write('            self.U = [fftshift(fft2(ifftshift(p.S(self.Vexcite)))),] + self.U[:-1]\n\n')
            rewrite = True # rewrite updateS
        
        file.write('            # update the window title\n')
        compare = int(p.dt*1000)
        if compare >= 100:
            file.write('            self.dim3.updateTitle(\'%.1f seconds     Vmin: %.12f     Vmax: %.12f\'%((self.epoc*self.dt),self.Vexcite.min(),self.Vexcite.max()))\n\n')
        elif compare >= 10:
            file.write('            self.dim3.updateTitle(\'%.2f seconds     Vmin: %.12f     Vmax: %.12f\'%((self.epoc*self.dt),self.Vexcite.min(),self.Vexcite.max()))\n\n')
        elif compare >= 1:
            file.write('            self.dim3.updateTitle(\'%.3f seconds     Vmin: %.12f     Vmax: %.12f\'%((self.epoc*self.dt),self.Vexcite.min(),self.Vexcite.max()))\n\n')
        else:
            file.write('            self.dim3.updateTitle(\'%.4f seconds     Vmin: %.12f     Vmax: %.12f\'%((self.epoc*self.dt),self.Vexcite.min(),self.Vexcite.max()))\n\n')

        file.write('        # else if maximum calculation time reached\n')
        file.write('        elif self.epoc-1 == self.simRange:\n')
        file.write('            self.dim3.run = False\n')
        file.write('            print \'Maximum simulation time of\', self.endtime, \'seconds has been reached.\'\n')
        file.write('            self.epoc +=1\n\n')

        if showData == 3:
            file.write('        return self.I # return the I matrix\n')
        if showData == 4:
            file.write('        return self.K_ # return the kernel matrix\n')
        else:
            file.write('        return self.Vexcite # return the V matrix\n')

# we have some more editing to do
if simOVERtime: 
    
    # if showing I or K 
    if showData > 2:
        rd = open(fyl).read() 
        if showData == 3:
            rd = rd.replace('self.dim3=g3.graph3D(self.Vexcite,', 'self.dim3=g3.graph3D(self.I,')
        else:
            rd = rd.replace('self.dim3=g3.graph3D(self.Vexcite,', 'self.dim3=g3.graph3D(self.K_,')
        f = open(fyl, 'w')
        f.write(rd)
        f.close()
    elif showData == 1:
        if rewrite == True: #  rewrite updateS
            rd = open(fyl).read()
            rd = rd.replace('updateS', 'S')
            f = open(fyl, 'w')
            f.write(rd)
            f.close()
        