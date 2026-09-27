#-----------Denne algoritmen har jeg laget selv, og har kodet den på ark før den kom her--------
def theveninZth(grid,bus1,bus2):
      Par=[]
      Z=[]

      #--------------bygger par og Z listen for algoritmen min--------------#kanskje inkludere trafo???
      def bygge_par_og_Z_listen():
         for i in range(len(grid.line)):
            a=grid.line[i].Frombus
            b=grid.line[i].Tobus
            Par.append([a,b])
            Z.append(1/grid.line[i].admittans())
         return Par,Z
      #--------------bygger par og Z listen for algoritmen min--------------#kanskje inkludere trafo???
      bygge_par_og_Z_listen()

      def antall(node):
         return sum(rad.count(node) for rad in Par)

      while not (len(Par)==1 and set(Par[0])=={bus1,bus2}):
       endret=False
       for l in range(len(Par)):
         a=Par[l][0]
         b=Par[l][1]

         #----------endrer Par og Z listen hvis det er serie-----------
         def Serie_a():
                        for i, rad in enumerate(Par):
                           if i!=l and a in rad:
                              andre_tall = rad[1] if rad[0] == a else rad[0]
                              Z[l]=Z[l]+Z[i]
                              Par[l][0]=andre_tall
                              del Par[i]
                              del Z[i]
                              break
         #----------endrer Par og Z listen hvis det er serie-----------

         #----------endrer Par og Z listen hvis det er serie-----------
         def Serie_b():
                        for i, rad in enumerate(Par):
                           if i!=l and b in rad:
                              andre_tall = rad[1] if rad[0] == b else rad[0]
                              Z[l]=Z[l]+Z[i]
                              Par[l][1]=andre_tall
                              del Par[i]
                              del Z[i]
                              break
         #----------endrer Par og Z listen hvis det er serie-----------

         #----------endrer Par og Z listen hvis det er Parrarell-------
         def Parrarell():
                        for i, rad in enumerate(Par):
                           if i!=l and set(rad)=={a,b}:
                              Z[l]=(Z[l]*Z[i])/(Z[l]+Z[i])
                              del Par[i]
                              del Z[i]
                              break
         #----------endrer Par og Z listen hvis det er Parrarell-------

         #----------Hvis ikke serie eller parrarell, så er det delta stjerne-----
         def delta_stjerne(indekser, variant):

            if variant == "Delta":
               i1, i2, i3 = indekser
               a, b = Par[i1]
               c = next(node for node in Par[i2] if node not in (a, b))
               Z_ab = Z[i1]
               Z_bc = Z[i2]
               Z_ca = Z[i3]

               Z_sum = Z_ab + Z_bc + Z_ca

               Z_a = Z_ab * Z_ca / Z_sum
               Z_b = Z_ab * Z_bc / Z_sum
               Z_c = Z_bc * Z_ca / Z_sum

               ny_node = max(max(rad) for rad in Par if all(isinstance(x, (int, float)) for x in rad)) + 1

               return [[a, ny_node],[b, ny_node],[c, ny_node]], [Z_a, Z_b, Z_c]


            elif variant == "Stjerne":

               sentral = node

               ytre = [Par[i][1] if Par[i][0] == sentral else Par[i][0] for i in indekser]

               Y_sum = sum(1/Z[i] for i in indekser)

               nye_Par=[]
               nye_Z=[]
               for m in range(len(ytre)):
                  for n in range(m+1, len(ytre)):
                     nye_Par.append([ytre[m], ytre[n]])
                     nye_Z.append(Z[indekser[m]] * Z[indekser[n]] * Y_sum)

               return nye_Par, nye_Z
         #----------Hvis ikke serie eller parrarell, så er det delta stjerne-----

         #----------en sjekk for å se om noden er sentrum i en stjerne---------
         def delta_stjerne_true(node):
            indekser = [j for j,rad in enumerate(Par) if node in rad]
            if node!=bus1 and node!=bus2 and len(indekser)>=3 and all(Par[j][0]!=Par[j][1] for j in indekser):
               return True,"Stjerne",indekser
            return False,None,indekser
         #----------en sjekk for å se om noden er sentrum i en stjerne---------


         if a==b:
              del Par[l]
              del Z[l]

         elif any(i!=l and set(rad)=={a,b} for i,rad in enumerate(Par)):
              Parrarell()

         elif (a!=bus1 and a!=bus2) and antall(a)==1:
              del Par[l]
              del Z[l]

         elif (b!=bus1 and b!=bus2) and antall(b)==1:
              del Par[l]
              del Z[l]

         elif (a!=bus1 and a!=bus2) and antall(a)==2:
              Serie_a()

         elif (b!=bus1 and b!=bus2) and antall(b)==2:
              Serie_b()

         else:
              for node in (a,b):
                 Delta_stjerne_true,variant,indekser=delta_stjerne_true(node)
                 if Delta_stjerne_true:
                    nye_Par,nye_Z=delta_stjerne(indekser,variant)
                    for i in sorted(indekser, reverse=True):
                       del Par[i]
                       del Z[i]
                    Par.extend(nye_Par)
                    Z.extend(nye_Z)
                    break
              else:
                 continue

         endret=True
         break

       if not endret:
          raise ValueError("Fant ingen vei mellom bus1 og bus2")
      return Z[0]
#-----------Denne algoritmen har jeg laget helt selv, og har kodet den på ark før den kom her--------