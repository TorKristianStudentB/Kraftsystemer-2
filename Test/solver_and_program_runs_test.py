from GridMaker.Imports import openpyxl

#--------tester om excelarket stemmer med malen for excelarket---------------
def sjekk_excel_struktur(excelfile, struktur_excel_arket):
   """Sjekker at excelfilen har samme struktur som test_trøndelagsnettet.xlsx:
   samme ark (navn og rekkefølge) og samme kolonneoverskrifter (navn og rekkefølge).
   Returnerer (ok: bool, feil: list[str])."""
   feil = []
   wb = openpyxl.load_workbook(excelfile, read_only=True, data_only=True)
   try:
      ark = wb.sheetnames
      ref_ark = list(struktur_excel_arket)

      mangler = [a for a in ref_ark if a not in ark]
      ekstra = [a for a in ark if a not in struktur_excel_arket]
      if mangler:
            feil.append(f"Mangler ark: {mangler}")
      if ekstra:
            feil.append(f"Ekstra ark: {ekstra}")
      if not mangler and not ekstra and ark != ref_ark:
            feil.append(f"Feil arkrekkefølge: {ark}, forventet {ref_ark}")

      for navn, ref_kol in struktur_excel_arket.items():
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


#--------tester om alt fylles inn i grid uten problemer---------------
def Fills_in_grid_from_Excel_without_error(grid_g):
   grid = grid_g
   
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


#--------Tester Newton-Raphson--------
def test_solver_NR(grid_g):
    grid=grid_g
    grid.loadflowsolutionNR()

    assert grid.solution.konvergerte == True
#--------Tester Newton-Raphson--------


#--------Tester DC Power Flow--------
def test_solver_DCPF(grid_g):
    grid = grid_g
    grid.DCPF()

    assert grid.solution.konvergerte
#--------Tester DC Power Flow--------


#--------Tester Fast Decoupled Power Flow--------
def test_solver_FDPF(grid_g):
    grid = grid_g
    grid.FDLF()

    assert grid.solution.konvergerte
#--------Tester Fast Decoupled Power Flow--------




    
    


