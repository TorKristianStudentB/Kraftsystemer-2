import numpy as np
import copy
from collections import Counter
#husk at trafo her er ritkgi fordi busene er riktige i excelarket. Du har flere busser på samme sted.


#-----------------cutsem algoritmen utført utifra powerpoint til foreleseren------------
def cutsem(grid):
   #----initaliserer admittansmatrisen----
   N=len(grid.bus)
   Y = np.zeros((N, N), dtype=complex)
   #----initaliserer admittansmatrisen----

   #--------konverter til kodens egen identifikasjonsummer som er overens med dimensjonen-----
   def konverter_identifikasjonummer(busnr):
      i = next(bus.kodens_identifikasjonssystem for bus in grid.bus if bus.busNumber == busnr)
      return i
   #--------konverter til kodens egen identifikasjonsummer som er overens med dimensjonen-----

   #------Start: Finner 2x2 matrisen på alle linjene-----
   for l in (grid.line):
      i=konverter_identifikasjonummer(l.Frombus)
      j=konverter_identifikasjonummer(l.Tobus)
      yij = l.admittans()
      yshunt = complex(0,l.B)
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
         i=konverter_identifikasjonummer(k.Frombus)
         j=konverter_identifikasjonummer(k.Tobus)

         #----ratio i excelarket er det FYSISKE spenningsforholdet (lav Vbase / høy Vbase, f.eks. 132/380=0.347).
         #    Bussene er allerede normalisert mot egen Vbase, og da skal en nominell trafo ha tapp 1.0 i pu.
         #    Tappen i pu er derfor ratio delt på det nominelle forholdet (nominell trafo -> ratio_pu=1.0)----
         v_lav=min(grid.bus[i].Vbase, grid.bus[j].Vbase)
         v_hoy=max(grid.bus[i].Vbase, grid.bus[j].Vbase)
         ratio_pu=k.ratio/(v_lav/v_hoy)
         a=1/ratio_pu #a=1 for nominell trafo
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
#-----------------cutsem algoritmen utført utifra powerpoint til foreleseren------------


#-----------------Krons reduksjon av en vilkårlig nodematrise (brukes på Y, Y_dc, B' osv.)-----
def krons_reduser(M,k_noder):
   M = M.copy()
   gjenværende = list(range(M.shape[0]))

   for k_original in k_noder:
      k = gjenværende.index(k_original)
      behold = [i for i in range(M.shape[0]) if i != k]
      M_gammel = M.copy()

      if abs(M_gammel[k, k]) < 1e-12:
         raise ValueError(f"Diagonalverdien for node {k_original} er null")

      M = M_gammel[np.ix_(behold, behold)] - np.outer(M_gammel[behold, k], M_gammel[k, behold]) / M_gammel[k, k]

      gjenværende.pop(k)

   return M
#-----------------Krons reduksjon av en vilkårlig nodematrise (brukes på Y, Y_dc, B' osv.)-----


#-----------------Lager krons_reduksjon slik at man kan fjerne mellomstasjoner for linjer-----
def Krons_reduksjon(grid):

   Y=cutsem(grid)

   #-----------finne k noder, dette er noder som ikke har generator eller last på seg------
   def finn_k_noder():
      ikke_k_noder=[]

      for l in grid.gen:
          ikke_k_noder.append(l.bus)

      for k in grid.bus:
         if k.kunstig_buss:
            ikke_k_noder.append(k.busNumber)
         if k.P_gen != 0:
            ikke_k_noder.append(k.busNumber)
         if k.Q_gen != 0:
            ikke_k_noder.append(k.busNumber)
         if k.P_load != 0:
            ikke_k_noder.append(k.busNumber)
         if k.Q_load != 0:
            ikke_k_noder.append(k.busNumber)

      ikke_k_noder = list(set(ikke_k_noder)) #fjerner duplikater

      #----dette er de nodene/bussene som skal kjøres krons reduksjon---
      k_noder_busNumber = [k.busNumber for k in grid.bus if k.busNumber not in ikke_k_noder]
      k_noder_egen_identifikasjon = [k.kodens_identifikasjonssystem for k in grid.bus if k.busNumber not in ikke_k_noder]

      return k_noder_egen_identifikasjon,k_noder_busNumber
   #-----------finne k noder, dette er noder som ikke har generator eller last på seg------
   k_noder_egen_identifikasjon  ,  k_noder_busNumber  =finn_k_noder()
   print(f"Nodene {k_noder_busNumber} fjernes fra nettet fra Krons reduksjon")


   #-------------lager ny Y matrise fra krons redukjsonen--------------
   Y = krons_reduser(Y,k_noder_egen_identifikasjon)
   #-------------lager ny Y matrise fra krons redukjsonen--------------


   #----------lager det reduserte nettet som en kopi av nettet, uten k-nodene og grenene deres-----
   def make_new_grid_from_krons_reduktion(k_noder_busNumber,grid):
         nytt_grid = copy.deepcopy(grid)
         nytt_grid.__dict__.pop("_admittans_lagret", None)   #lagret Y hører til det fulle nettet

         #---------fjerner k-nodene og nummerer de gjenværende på nytt (samme rekkefølge som i Y)------
         nytt_grid.bus = [b for b in nytt_grid.bus if b.busNumber not in k_noder_busNumber]
         for i in range(len(nytt_grid.bus)):
            nytt_grid.bus[i].kodens_identifikasjonssystem = i
         #---------fjerner k-nodene og nummerer de gjenværende på nytt (samme rekkefølge som i Y)------

         #---------linjer og trafoer mot k-nodene er nå representert i Y, så de fjernes-----
         nytt_grid.line = [l for l in nytt_grid.line if l.Frombus not in k_noder_busNumber and l.Tobus not in k_noder_busNumber]
         nytt_grid.trafo = [t for t in nytt_grid.trafo if t.Frombus not in k_noder_busNumber and t.Tobus not in k_noder_busNumber]
         #---------linjer og trafoer mot k-nodene er nå representert i Y, så de fjernes-----

         #---------DC og FD bygger sine egne matriser på det fulle nettet og trenger k-nodene-----
         nytt_grid.k_noder_egen_identifikasjon = k_noder_egen_identifikasjon
         #---------DC og FD bygger sine egne matriser på det fulle nettet og trenger k-nodene-----
         return nytt_grid
   #----------lager det reduserte nettet som en kopi av nettet, uten k-nodene og grenene deres-----
   grid=make_new_grid_from_krons_reduktion(k_noder_busNumber,grid)


   return Y,grid
#-----------------Lager krons_reduksjon slik at man kan fjerne mellomstasjoner for linjer-----
