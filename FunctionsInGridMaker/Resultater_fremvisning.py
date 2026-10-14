import copy
import textwrap
from datetime import datetime
import numpy as np

def resultater_fremvisning(grid,metode,excelfilepath=None):

   m = str(metode).lower()   #metode bestemmer hvilken løser som kjøres, ikke bare navnet i utskriften
   løser = "FDLF" if ("fast" in m or "fd" in m) else "DCPF" if "dc" in m else "loadflowsolutionNR"
   if grid.solution is None: getattr(grid, løser)()


   #---------------finner overtredelser i et løst nett, som liste av (nøkkel, tekst), nøkkelen er busnummer/linjenummer og ikke indeks---------------
   def finn_overtredelser(g):
      s, Sb, B = g.solution, g.Base.Sbase, g.bus
      n = len(B)
      arr = lambda x: np.array(x, float) * Sb if x is not None and len(x) == n else np.full(n, np.nan)
      grense = lambda ob, a: np.array([np.nan if getattr(o, a, None) is None else getattr(o, a) for o in ob], float)
      gsum = lambda a: np.array([sum(getattr(x, a) or 0 for x in g.gen if x.bus == b.busNumber) or np.nan for b in B])
      V, P, Q = np.array(s.volt, float), arr(s.power), arr(s.qower)
      S, Smax = np.hypot(P, Q), grense(B, "S_max")
      Vmin, Vmax = grense(B, "V_min"), grense(B, "V_max")
      Pg, Qg = P + grense(B, "P_load") * Sb, Q + grense(B, "Q_load") * Sb
      Pgmax, Qgmax, Qgmin = gsum("P_max") * Sb, gsum("Q_max") * Sb, gsum("Q_min") * Sb
      Fc = np.array(s.flow_in_line, complex) * (Sb if np.iscomplexobj(s.flow_in_line) else 1) if s.flow_in_line is not None and len(s.flow_in_line) == len(g.line) else np.full(len(g.line), np.nan + 0j)   #kompleks = p.u., reell = allerede MW
      Fs, Lmax = np.abs(Fc), grense(g.line, "S_max")
      tol = 1e-3   #MW/MVAr, ellers gir flyttallsfeil falske overtredelser når NR legger Q akkurat på grensen
      bus = lambda i: f"Bus {B[i].busNumber} ({B[i].Name})"
      ov  = [(("V", B[i].busNumber), f"{bus(i)}: V = {V[i]:.4f} pu utenfor [{Vmin[i]}, {Vmax[i]}]") for i in np.where((V < Vmin) | (V > Vmax))[0]]
      ov += [(("S", B[i].busNumber), f"{bus(i)}: S = {S[i]:.1f} MVA over S_max = {Smax[i]:.1f}") for i in np.where(S > Smax + tol)[0]]
      ov += [(("P", B[i].busNumber), f"{bus(i)}: P_gen = {Pg[i]:.1f} MW over P_max = {Pgmax[i]:.1f}") for i in np.where(Pg > Pgmax + tol)[0]]
      ov += [(("Qmax", B[i].busNumber), f"{bus(i)}: Q_gen = {Qg[i]:.1f} MVAr over Q_max = {Qgmax[i]:.1f}") for i in np.where(Qg > Qgmax + tol)[0]]
      ov += [(("Qmin", B[i].busNumber), f"{bus(i)}: Q_gen = {Qg[i]:.1f} MVAr under Q_min = {Qgmin[i]:.1f}") for i in np.where(Qg < Qgmin - tol)[0]]
      ov += [(("L", g.line[i].lineNumber), f"Linje {g.line[i].lineNumber} ({g.line[i].Name}): S = {Fs[i]:.1f} MVA over S_max = {Lmax[i]:.1f}") for i in np.where(Fs > Lmax + tol)[0]]
      return ov
   #---------------finner overtredelser i et løst nett, som liste av (nøkkel, tekst)---------------


   #---------------N-1 fra den eksisterende funksjonen: (True/False, linjer som feiler alene, linje der trappevis uttak feiler, serier som feiler, overtredelser per uttak)---------------
   n1, feilet_kun_en, feilet_trappevis, feilet_serier, n1_overtredelser = grid.N_minus_en()


   s, n, B = grid.solution, len(grid.bus), grid.bus
   V, th = np.array(s.volt, float), np.degrees(np.array(s.angle, float))
   ov = [t for nokkel, t in finn_overtredelser(grid)]


   #---------------N-1: bare overtredelsene som kommer i tillegg til nettet uten uttak, for samme løser som boksen---------------
   løsernavn = {"loadflowsolutionNR": "NR", "FDLF": "FD", "DCPF": "DC"}[løser]
   base = [t.split(" =")[0] for t in ov]   #bussen/linjen og typen, uten tallene
   n1_nye = []   #(linjen som er tatt ut, nye overtredelser)
   for nokkel, liste in n1_overtredelser.items():
      if len(nokkel[0]) == 1 and nokkel[1] == løsernavn:
         nye = [t for t in liste if t.split(" =")[0] not in base]
         if nye:
            n1_nye.append((nokkel[0][0], nye))
   n1 = n1 and n1_nye == []


   #---------------utskrift i statsmodels-stil---------------
   l1 = "=" * 80
   p = lambda t="": print(textwrap.fill(t, width=80, subsequent_indent="      ") if t else "")   #lange linjer brytes og fortsetter innrykket, ingenting kuttes
   rad = lambda a, b, c, d: p(f"{f'{a} {b}':<38}{c} {d}")
   print(f"\n{l1}")
   p(f"{'Lastflyt-resultater':^80}")
   print(l1)
   rad("Metode:", metode, "Antall busser:", n)
   rad("Dato:", datetime.now().strftime("%Y-%m-%d %H:%M"), "Antall linjer:", len(grid.line))
   rad("Konvergert:", str(s.konvergerte), "Antall trafoer:", len(grid.trafo))
   rad("Iterasjoner:", f"{s.iterasjoner} Kjøretid [s]: {s.kjoretid:.4f}", "Antall generatorer:", len(grid.gen))
   rad("N-1 kriteriet:", str(n1), "", "")
   rad("V min / max [pu]:", f"{np.nanmin(V):.4f}/{np.nanmax(V):.4f}", "Vinkel min/max [°]:", f"{np.nanmin(th):.2f}/{np.nanmax(th):.2f}")
   print(l1)
   p(f"Overtredelser: {len(ov)}" if ov else "Overtredelser: ingen, alle verdier er innenfor grensene")
   for k, t in enumerate(ov, 1): p(f"  [{k}] {t}")
   if n1: p("Overtredelser N-1: ingen")
   for linje_id, nye in n1_nye:
      p(f"Overtredelse N-1 (Linje {linje_id} tatt ut):")
      for k, t in enumerate(nye, 1): p(f"  [{k}] {t}")
   for id in feilet_kun_en: p(f"Overtredelse N-1 (Linje {id} tatt ut): konvergerte ikke")
   for id in feilet_trappevis: p(f"Overtredelse N-1 (Linje {id} tatt ut, trappevis sammen med de foregående): konvergerte ikke")
   for serie in feilet_serier: p(f"Overtredelse N-1 (Linje {', '.join(str(i) for i in serie)} tatt ut): konvergerte ikke")
   print(l1)


#-------------kjører alle løserne på hver sin kopi av nettet-------------
def kjor_alle_solvere(grid):
   solvere = {"Newton-Raphson": "loadflowsolutionNR", "DC": "DCPF", "Fast decoupled": "FDLF", "PP Newton-Raphson": "validating_PP_NR", "PP DC": "validating_PP_DC", "PP Fast decoupled": "validating_PP_FDPF"}
   for tittel, m in solvere.items():
      g = copy.deepcopy(grid)   #send inn et grid som ikke er kjørt
      try: getattr(g, m)()
      except Exception as e: print(f"\n{tittel}: feilet ({type(e).__name__}: {e})"); continue
      resultater_fremvisning(g, tittel)
