
import numpy as np

def cutsem(grid):
   #----initaliserer admittansmatrisen----
   N=len(grid.bus)
   Y = np.zeros((N, N), dtype=complex)
   #----initaliserer admittansmatrisen----

   #------Start: Finner 2x2 matrisen på alle linjene-----
   for l in (grid.line):
      i=l.Frombus
      j=l.Tobus
      yij=l.admittans()
      yshunt=complex(0,l.B)

      #---------ikke diagonal-------
      Y[i,j]=Y[i,j]+(-1*yij)
      Y[j,i]=Y[j,i]+ (-1*yij)
      #---------ikke diagonal-------

      #---------diagonal------------
      Y[i,i]=Y[i,i]+yij+yshunt/2
      Y[j,j]=Y[j,j]+yij+yshunt/2
      #---------diagonal------------

   #------END: Finner 2x2 matrisen på alle linjene-----

   #------Start: Finner 2x2 matrisen på alle trafoene-----
   for k in grid.trafo:
      if k.Type=='tap':
         a=1/k.ratio #alle ratioene er <1, så lavest spenning er i teller
         i=k.Frombus
         j=k.Tobus
         yij=k.admittans()

         if grid.bus[i].Vbase>=grid.bus[j].Vbase:
            #---------ikke diagonal-------
            Y[i,j]= Y[i,j]+(-1*yij/a)
            Y[j,i]=Y[j,i]+(-1*yij/a)
            #---------ikke diagonal-------

            #---------diagonal------------
            Y[i,i]=Y[i,i]+yij/a**2
            Y[j,j]=Y[j,j]+yij
            #---------diagonal------------
         else: #variablebytte på i og j
            q=i
            p=j
            i=p
            j=q
            #---------ikke diagonal-------
            Y[i,j]=Y[i,j]+(-1*yij/a)
            Y[j,i]=Y[j,i]+(-1*yij/a)
            #---------ikke diagonal-------

            #---------diagonal------------
            Y[i,i]=Y[i,i]+yij/a**2
            Y[j,j]=Y[j,j]+yij
            #---------diagonal------------
   #------Start: Finner 2x2 matrisen på alle trafoene-----


   return Y
