

def NewtonRaphson(grid):

   def busclassifier(grid):
      bus=[]
      for i in range(len(grid.bus)):
         PV=False
         for j in range(len(grid.gen)):
            if grid.gen[j].bus==grid.bus[i].busNumber:
               bus.append("PV")
               PV=True
         if PV==False:
            bus.append("PQ")
      print(bus)

      
         
   bus=busclassifier(grid)


   return bus