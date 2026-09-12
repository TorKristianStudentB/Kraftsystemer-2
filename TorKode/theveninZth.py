def theveninZth(grid,bus1,bus2):

   #------oppstart-----
   mainlist=[]
   mainlist.append(bus1)
   mainlist.append(f"end {bus2}")
   index=[]
   index.append(0)
   index.append(0)
   #------oppstart-----




   #par er enkelt linjer
   #så må ta en loop for alle frombus og tilbus

   #---------leter etter linjer koblet til node i--------
   def connections(node):
      midlertidig=[]
      midlertidigindex=[]
      for l in grid.line:
         if l.Frombus==node:
            midlertidig.append(l.Tobus)
            midlertidigindex.append(f"1+{l.Tobus}")
         if l.Tobus==node:
            midlertidig.append(l.Frombus)
            midlertidigindex.append(f"1+{l.Frombus}")
      mainlist.append([node,midlertidig])
      index.append([node,midlertidigindex])

   connections(bus1)


   
   #---------leter etter linjer koblet til node i --------



   return print("mainlist:",mainlist,"index:",index)
    