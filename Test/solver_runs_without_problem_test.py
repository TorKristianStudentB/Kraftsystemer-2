#------------------fungerer oppsettet som vi har nå------------
def test_at_alt_kjører_fra_lese_excel_til_alle_solverene_kjøres():

   #--------tester om excelarket stemmer med malen for excelarket---------------
   def readexcelark():
      import openpyxl

      # Referansestruktur hentet fra Grid/test_trøndelagsnettet.xlsx (ark -> overskrifter i rad 1)
      REF_STRUKTUR = {
         "bus": ["bus_id", "name", "bidz", "Vbase", "lat", "lon", "S_base [MVA] ",
                  "V [P.U]", "Angle [rad]", "P_gen", "Q_gen", "P_load", "Q_load"],
         "gen": ["name", "type", "type2", "Pmax", "Qmax", "Qmin", "bus", "lat", "lon",
                  "Unnamed: 9", "Unnamed: 10"],
         "line": ["line_id", "area0", "bus0", "bus1", "length", "Vbase", "lat", "lon",
                  "R", "X", "B", "name", "eic code"],
         "trafo": ["transformer_id", "bus0", "bus1", "ratio", "R", "X", "name"],
         "link": ["index", "name", "area0", "area1", "bus0", "bus1", "lat", "lon", "Pinj"],
      }


      def sjekk_excel_struktur(filsti, referanse=REF_STRUKTUR):
         """Sjekker at excelfilen har samme struktur som test_trøndelagsnettet.xlsx:
         samme ark (navn og rekkefølge) og samme kolonneoverskrifter (navn og rekkefølge).
         Returnerer (ok: bool, feil: list[str])."""
         feil = []
         wb = openpyxl.load_workbook(filsti, read_only=True, data_only=True)
         try:
            ark = wb.sheetnames
            ref_ark = list(referanse)

            mangler = [a for a in ref_ark if a not in ark]
            ekstra = [a for a in ark if a not in referanse]
            if mangler:
                  feil.append(f"Mangler ark: {mangler}")
            if ekstra:
                  feil.append(f"Ekstra ark: {ekstra}")
            if not mangler and not ekstra and ark != ref_ark:
                  feil.append(f"Feil arkrekkefølge: {ark}, forventet {ref_ark}")

            for navn, ref_kol in referanse.items():
                  if navn not in ark:
                     continue
                  rad = next(wb[navn].iter_rows(min_row=1, max_row=1, values_only=True), ())
                  kol = list(rad)
                  while kol and kol[-1] is None:  # fjern tomme celler på slutten
                     kol.pop()
                  if kol != ref_kol:
                     mgl = [k for k in ref_kol if k not in kol]
                     eks = [k for k in kol if k not in ref_kol]
                     if mgl or eks:
                        feil.append(f"Ark '{navn}': mangler kolonner {mgl}, ekstra kolonner {eks}")
                     else:
                        feil.append(f"Ark '{navn}': feil kolonnerekkefølge {kol}")
         finally:
            wb.close()
         return (not feil), feil
      #--------tester om excelarket stemmer med malen for excelarket---------------
   #--------tester om excelarket stemmer med malen for excelarket---------------
   readexcelark()


   #--------tester om alt fylles inn i grid uten problemer---------------
   def Fills_in_grid_from_Excel_without_error():
      from GridMaker.Imports import MakeGrid,excelfilepath
      grid = MakeGrid(excelfilepath)
      
      errors = []

      # ---------------- GRID ----------------
      if grid is None:
         raise ValueError("grid er None")

      if not hasattr(grid, "Name") or grid.Name is None or grid.Name == "":
         errors.append("grid.Name mangler")

      # ---------------- BASE VALUES ----------------
      if not hasattr(grid, "Base") or grid.Base is None:
         errors.append("grid.Base mangler")
      else:
         if not hasattr(grid.Base, "Sbase") or grid.Base.Sbase is None:
            errors.append("grid.Base.Sbase mangler")

         if not hasattr(grid.Base, "Vbase") or grid.Base.Vbase is None:
            errors.append("grid.Base.Vbase mangler")

      # ---------------- LISTS ----------------
      for attr in ["bus", "line", "trafo", "gen"]:
         if not hasattr(grid, attr) or getattr(grid, attr) is None:
            errors.append(f"grid.{attr} mangler")
         elif not isinstance(getattr(grid, attr), list):
            errors.append(f"grid.{attr} er ikke en liste")

      # Hvis en av listene mangler eller ikke er en liste,
      # stopper vi før vi går gjennom objektene.
      if errors:
         return errors

      # ---------------- BUS ----------------
      for i, bus in enumerate(grid.bus):
         prefix = f"grid.bus[{i}]"

         if bus is None:
            errors.append(f"{prefix} er None")
            continue

         required = [
            "busNumber",
            "Name",
            "Volt",
            "Angle",
            "P_gen",
            "Q_gen",
            "P_load",
            "Q_load",
            "bidz",
            "Vbase",
            "kodens_identifikasjonssystem",
         ]

         for attr in required:
            if not hasattr(bus, attr) or getattr(bus, attr) is None:
                  errors.append(f"{prefix}.{attr} mangler")

         if hasattr(bus, "Name") and bus.Name == "":
            errors.append(f"{prefix}.Name er tom")

         if hasattr(bus, "bidz") and bus.bidz == "":
            errors.append(f"{prefix}.bidz er tom")

      # ---------------- LINE ----------------
      for i, line in enumerate(grid.line):
         prefix = f"grid.line[{i}]"

         if line is None:
            errors.append(f"{prefix} er None")
            continue

         required = [
            "lineNumber",
            "Name",
            "R",
            "X",
            "B",
            "Frombus",
            "Tobus",
            "lenght",
         ]

         for attr in required:
            if not hasattr(line, attr) or getattr(line, attr) is None:
                  errors.append(f"{prefix}.{attr} mangler")

         if not hasattr(line, "admittans") or not callable(line.admittans):
            errors.append(f"{prefix}.admittans() mangler")

      # ---------------- TRAFO ----------------
      for i, trafo in enumerate(grid.trafo):
         prefix = f"grid.trafo[{i}]"

         if trafo is None:
            errors.append(f"{prefix} er None")
            continue

         required = [
            "Name",
            "Type",
            "ratio",
            "Frombus",
            "Tobus",
            "R",
            "X",
         ]

         for attr in required:
            if not hasattr(trafo, attr) or getattr(trafo, attr) is None:
                  errors.append(f"{prefix}.{attr} mangler")

         if not hasattr(trafo, "admittans") or not callable(trafo.admittans):
            errors.append(f"{prefix}.admittans() mangler")

      # ---------------- GENERATOR ----------------
      for i, gen in enumerate(grid.gen):
         prefix = f"grid.gen[{i}]"

         if gen is None:
            errors.append(f"{prefix} er None")
            continue

         required = [
            "name",
            "bus",
            "P_max",
         ]

         for attr in required:
            if not hasattr(gen, attr) or getattr(gen, attr) is None:
                  errors.append(f"{prefix}.{attr} mangler")

         if hasattr(gen, "name") and gen.name == "":
            errors.append(f"{prefix}.name er tom")

      # ---------------- RESULT ----------------
      if errors:
         print(f"Fant {len(errors)} feil i grid:")
         for error in errors:
            print(f" - {error}")
      else:
         print("True: Alle obligatoriske verdier er fylt inn.")

      return errors,grid
   #--------tester om alt fylles inn i grid uten problemer---------------
   errors,grid=Fills_in_grid_from_Excel_without_error()


   #--------Tester om alle solverene vi har laget kjører-------------
   def test_solvers(grid):

      try:
         grid.loadflowsolutionNR()
      except Exception as e:
         print(f"NR feilet: {e}")

      try:
         grid.DCPF()
      except Exception as e:
         print(f"DCPF feilet: {e}")

      try:
         grid.FDPF()
      except Exception as e:
         print(f"FDPF feilet: {e}")
   #--------Tester om alle solverene vi har laget kjører-------------
   test_solvers  
#------------------fungerer oppsettet som vi har nå------------
test_at_alt_kjører_fra_lese_excel_til_alle_solverene_kjøres()

    
    


