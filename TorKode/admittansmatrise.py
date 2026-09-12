#Anvender cutsem algoritmen
import numpy as np

def cutsem(grid):

   n1=len(grid.line)
   #n2=len(grid.trafo)
   #print(n2)

   N=n1        #+n2

   Y = np.zeros((N, N), dtype=complex)

   for l in (grid.line):
      i=l.Frombus
      j=l.Tobus
      yij=l.admittans()
      yshunt=complex(0,l.B)

      #---------ikke diagonal-------
      Y[i,j]= -1*yij
      Y[j,i]= -1*yij    
      #---------ikke diagonal-------

      #---------diagonal------------          
      Y[i,i]=Y[i,i]+yij+yshunt/2
      Y[j,j]=Y[i,i]+yij+yshunt/2
      #---------diagonal------------
   
      
      """
      #------------Hør med foreleser hvordan primær og sekundær er gitt med tanke på a:1-------
      if isinstance(l,trafo):  

         if l.type=="tap":
            a=l.ratio
            i=l.Frombus
            j=l.Tobus
            yij=l.admittans()
   
            #---------ikke diagonal-------
            Y[i,j]= -1*yij/a   
            #---------ikke diagonal-------
   
            #---------diagonal------------          
            Y[i,i]=Y[i,i]+yij/a^2
            Y[j,j]=Y[i,i]+yij
            #---------diagonal------------

         #-----------må undersøke denne mer--------
         #if l.type=="phase-shifting":
         #-----------må undersøke denne mer--------
         """

   return Y      
            

         




