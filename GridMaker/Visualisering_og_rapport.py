from GridMaker.Imports import np, plt, PdfPages, datetime,Rectangle,FancyBboxPatch,Circle,Line2D
import networkx as nx
import matplotlib.colors as mcolors



#---------------------Lager rapporten----------------------------------------
def lag_rapport(grid, V, angle, P, Q, filnavn="kraftsystem_rapport.pdf"):

    # Disse navnene fylles inn av Design_av_utsende() lenger ned (via
    # "nonlocal"), slik at resten av lag_rapport - og hjelpefunksjonene
    # under - kan bruke dem. De må "finnes" her først for at nonlocal skal
    # ha noe å peke på.
    (A4_BREDDE, A4_HOYDE, NAVY, BLUE, LYSBLA, ROD, LYSROD, GRONN, AMBER,
     GRABAKGRUNN, TEKST, DEMPET, LINJEGRA, TOTALT_SIDER, HODE_Y, HODE_H,
     INNHOLD_TOPP, INNHOLD_BUNN, FOT_LINJE_Y) = (None,) * 19

    (_ny_side, _kort_tekst, _sidehode, _sidefot, _side_med_innramming,
     _seksjonstittel, _rad, _beregn_ramme, _velg_side_og_rute, _kpi_kort) = (None,) * 10

    #---------------lager rapport------------------------------
    def  Design_av_utsende():
        nonlocal A4_BREDDE, A4_HOYDE, NAVY, BLUE, LYSBLA, ROD, LYSROD, GRONN, AMBER
        nonlocal GRABAKGRUNN, TEKST, DEMPET, LINJEGRA, TOTALT_SIDER, HODE_Y, HODE_H
        nonlocal INNHOLD_TOPP, INNHOLD_BUNN, FOT_LINJE_Y
        nonlocal _ny_side, _kort_tekst, _sidehode, _sidefot, _side_med_innramming
        nonlocal _seksjonstittel, _rad, _beregn_ramme, _velg_side_og_rute, _kpi_kort

        # =======================================================================
        # DESIGN – FARGER, MÅL OG SMÅHJELPERE
        # =======================================================================

        A4_BREDDE = 8.27
        A4_HOYDE = 11.69

        NAVY = "#17324F"
        BLUE = "#2E75B6"
        LYSBLA = "#EAF2FB"
        ROD = "#C0392B"
        LYSROD = "#FBEAE8"
        GRONN = "#2E8B57"
        AMBER = "#C9821A"
        GRABAKGRUNN = "#F4F6F8"
        TEKST = "#26313F"
        DEMPET = "#6B7684"
        LINJEGRA = "#D8DEE4"

        TOTALT_SIDER = 5

        # Innholdsområdet er felles for alle sider (figur-fraksjon-koordinater)
        HODE_Y = 0.930
        HODE_H = 0.070
        INNHOLD_TOPP = 0.905
        INNHOLD_BUNN = 0.085
        FOT_LINJE_Y = 0.055

        plt.rcParams.update({
            "font.family": "DejaVu Sans",
            "text.color": TEKST,
            "axes.edgecolor": LINJEGRA,
            "axes.labelcolor": TEKST,
            "xtick.color": DEMPET,
            "ytick.color": DEMPET,
        })


        def _ny_side():
            return plt.figure(figsize=(A4_BREDDE, A4_HOYDE))


        def _kort_tekst(tekst, maks=30):
            if tekst is None:
                return "-"
            return tekst if len(tekst) <= maks else tekst[: maks - 1] + "…"


        def _sidehode(fig, tittel, undertittel=""):

            fig.patches.append(
                Rectangle(
                    (0, HODE_Y), 1, HODE_H,
                    transform=fig.transFigure,
                    facecolor=NAVY,
                    edgecolor="none",
                    zorder=0,
                )
            )

            fig.text(
                0.065, HODE_Y + HODE_H * 0.62,
                tittel,
                fontsize=15,
                fontweight="bold",
                color="white",
                va="center",
            )

            if undertittel:
                fig.text(
                    0.065, HODE_Y + HODE_H * 0.24,
                    undertittel,
                    fontsize=9,
                    color=LYSBLA,
                    va="center",
                )


        def _sidefot(fig, gridnavn, dato, sidetall):

            fig.add_artist(
                Line2D(
                    [0.065, 0.935], [FOT_LINJE_Y, FOT_LINJE_Y],
                    transform=fig.transFigure,
                    color=LINJEGRA,
                    linewidth=0.8,
                )
            )

            fig.text(
                0.065, FOT_LINJE_Y - 0.017,
                f"Kraftsystemanalyse  ·  {gridnavn}",
                fontsize=7.5,
                color=DEMPET,
            )

            fig.text(
                0.935, FOT_LINJE_Y - 0.017,
                f"Side {sidetall} av {TOTALT_SIDER}   ·   Generert {dato}",
                fontsize=7.5,
                color=DEMPET,
                ha="right",
            )


        def _side_med_innramming(pdf, fig, gridnavn, dato, sidetall):
            _sidefot(fig, gridnavn, dato, sidetall)
            pdf.savefig(fig)
            plt.close(fig)


        def _seksjonstittel(fig, x, y, tekst):

            fig.text(
                x, y, tekst,
                fontsize=11,
                fontweight="bold",
                color=NAVY,
            )

            fig.add_artist(
                Line2D(
                    [x, x + 0.34], [y - 0.010, y - 0.010],
                    transform=fig.transFigure,
                    color=BLUE,
                    linewidth=1.6,
                )
            )


        def _rad(fig, x, y, etikett, verdi, farge=TEKST, storrelse=9.3):
            fig.text(x, y, etikett, fontsize=9.3, color=DEMPET)
            fig.text(x + 0.235, y, verdi, fontsize=storrelse, color=farge, fontweight="bold")


        def _beregn_ramme(bus_pos, marg=0.15, topp_ekstra=0.12):
            """Finn xlim/ylim for nettdiagrammet, med ekstra plass øverst til generatorsymboler."""

            xs = [p[0] for p in bus_pos.values()]
            ys = [p[1] for p in bus_pos.values()]

            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)

            dx = (x_max - x_min) or 1.0
            dy = (y_max - y_min) or 1.0

            x_pad = dx * marg
            y_pad = dy * marg
            y_topp = dy * topp_ekstra

            xlim = (x_min - x_pad, x_max + x_pad)
            ylim = (y_min - y_pad, y_max + y_pad + y_topp)

            return xlim, ylim, (xlim[1] - xlim[0]), (ylim[1] - ylim[0])


        def _velg_side_og_rute(dx_tot, dy_tot):
            """Velg A4-portrett eller A4-landskap for enlinjeskjemaet – hva som gir best
            plassutnyttelse for nettets faktiske høyde/bredde-forhold – og gi tilbake
            figurstørrelsen og aksens plassering. Akseforholdet holdes likt (1:1) i
            begge tilfeller, slik at busser/transformatorsirkler ikke blir ovale."""

            x0, bw = 0.07, 0.86
            bh = INNHOLD_TOPP - INNHOLD_BUNN

            def _fyll(side_bredde, side_hoyde):
                bw_tomm = bw * side_bredde
                bh_tomm = bh * side_hoyde
                if dy_tot / dx_tot * bw_tomm <= bh_tomm:
                    w_tomm = bw_tomm
                    h_tomm = w_tomm * dy_tot / dx_tot
                else:
                    h_tomm = bh_tomm
                    w_tomm = h_tomm * dx_tot / dy_tot
                return w_tomm, h_tomm

            beste = None
            for side_bredde, side_hoyde in ((A4_BREDDE, A4_HOYDE), (A4_HOYDE, A4_BREDDE)):
                w_tomm, h_tomm = _fyll(side_bredde, side_hoyde)
                areal = w_tomm * h_tomm
                if beste is None or areal > beste[0]:
                    beste = (areal, side_bredde, side_hoyde, w_tomm, h_tomm)

            _, side_bredde, side_hoyde, w_tomm, h_tomm = beste

            w_frac = w_tomm / side_bredde
            h_frac = h_tomm / side_hoyde

            x = x0 + (bw - w_frac) / 2
            y = INNHOLD_BUNN + (bh - h_frac) / 2

            return side_bredde, side_hoyde, [x, y, w_frac, h_frac]


        def _kpi_kort(fig, x, y, w, h, etikett, verdi):

            fig.patches.append(
                FancyBboxPatch(
                    (x, y), w, h,
                    boxstyle="round,pad=0.0015,rounding_size=0.010",
                    transform=fig.transFigure,
                    facecolor=GRABAKGRUNN,
                    edgecolor=LINJEGRA,
                    linewidth=0.8,
                )
            )

            fig.text(
                x + w / 2, y + h * 0.62,
                verdi,
                fontsize=17,
                fontweight="bold",
                color=NAVY,
                ha="center",
                va="center",
            )

            fig.text(
                x + w / 2, y + h * 0.22,
                etikett.upper(),
                fontsize=7.3,
                color=DEMPET,
                ha="center",
                va="center",
            )
    Design_av_utsende()


    #------------Skjematisk plassering av bussene (ikke geografisk)---------
    def _beregn_skjematisk_pos(grid):
        """Rutenett-plassering av bussene til enlinjeskjemaet: hver buss får
        en heltallsrad (nivå = korteste avstand fra en rot-buss) og en
        heltallskolonne innad i raden. Busser havner dermed alltid symmetrisk
        på linje med hverandre – enten på samme rad eller samme kolonne –
        i stedet for en fri, fysikk-basert plassering."""

        graf = nx.Graph()
        for bus in grid.bus:
            graf.add_node(bus.busNumber)
        for line in grid.line:
            if line.Frombus in graf and line.Tobus in graf:
                graf.add_edge(line.Frombus, line.Tobus)
        for trafo in grid.trafo:
            if trafo.Frombus in graf and trafo.Tobus in graf:
                graf.add_edge(trafo.Frombus, trafo.Tobus)

        if graf.number_of_nodes() == 0:
            return {}

        grader = dict(graf.degree())

        # Nivå (rad) = antall hopp fra en rot-buss (bussen med flest forbindelser
        # i hver sammenhengende del av nettet). Fungerer også med masker/looper,
        # siden det bare er korteste-vei-avstanden som brukes, ikke et spenntre.
        nivaa = {}
        for komponent in nx.connected_components(graf):
            delgraf = graf.subgraph(komponent)
            lokal_rot = max(komponent, key=lambda n: grader[n])
            nivaa.update(nx.shortest_path_length(delgraf, lokal_rot))

        rader = {}
        for busnr, niva in nivaa.items():
            rader.setdefault(niva, []).append(busnr)

        # Barysenter-heuristikk: sorter hver rad etter gjennomsnittlig kolonne
        # til naboene i raden over, slik at antall kryssende linjer minimeres
        # og relaterte busser havner rett over/under hverandre.
        kolonne = {}
        for niva in sorted(rader):
            buss_i_rad = rader[niva]

            if niva == 0:
                buss_i_rad.sort()
            else:
                def _barysenter(busnr):
                    naboer_over = [
                        n for n in graf.neighbors(busnr)
                        if nivaa.get(n, -1) < niva and n in kolonne
                    ]
                    if not naboer_over:
                        return float(busnr)
                    return sum(kolonne[n] for n in naboer_over) / len(naboer_over)

                buss_i_rad.sort(key=_barysenter)

            n = len(buss_i_rad)
            for i, busnr in enumerate(buss_i_rad):
                kolonne[busnr] = i - (n - 1) / 2

        return {
            busnr: (float(kolonne[busnr]), -float(niva))
            for busnr, niva in nivaa.items()
        }


    def _rett_vinkel_bane(x1, y1, x2, y2, knekk_y=None, tol=1e-6):
        """Finn punktene i en forbindelse som alltid går rett ut av bussen
        (loddrett, siden samleskinnene er vannrette) før den eventuelt
        knekker 90° og fortsetter vannrett inn mot den andre bussen."""

        if abs(y1 - y2) < tol or abs(x1 - x2) < tol:
            return [(x1, y1), (x2, y2)]

        ym = knekk_y if knekk_y is not None else (y1 + y2) / 2
        return [(x1, y1), (x1, ym), (x2, ym), (x2, y2)]


    def _tildel_pinner(grid, bus_pos, bar_w):
        """Gi hver linje/transformator et lite sideveis avvik fra bussens
        senter der den går ut. Uten dette ville flere loddrette forbindelser
        fra samme buss startet i akkurat samme punkt og ligget oppå
        hverandre helt til de knekker hver sin vei. Pinnene fordeles jevnt
        langs samleskinnen, sortert etter hvilken kant forbindelsen går mot,
        slik at de også unngår å krysse hverandre rett ved bussen."""

        tilkoblinger = {}

        for line in grid.line:
            if line.Frombus in bus_pos and line.Tobus in bus_pos:
                xa, xb = bus_pos[line.Frombus][0], bus_pos[line.Tobus][0]
                tilkoblinger.setdefault(line.Frombus, []).append((("line", line.lineNumber, "A"), xb))
                tilkoblinger.setdefault(line.Tobus, []).append((("line", line.lineNumber, "B"), xa))

        for i, trafo in enumerate(grid.trafo):
            if trafo.Frombus in bus_pos and trafo.Tobus in bus_pos:
                xa, xb = bus_pos[trafo.Frombus][0], bus_pos[trafo.Tobus][0]
                tilkoblinger.setdefault(trafo.Frombus, []).append((("trafo", i, "A"), xb))
                tilkoblinger.setdefault(trafo.Tobus, []).append((("trafo", i, "B"), xa))

        pin_x = {}

        for liste in tilkoblinger.values():
            n = len(liste)
            if n <= 1:
                for nokkel, _ in liste:
                    pin_x[nokkel] = 0.0
                continue

            liste.sort(key=lambda t: t[1])
            bredde_total = min(bar_w * 0.30 * (n - 1), bar_w * 0.9)
            steg = bredde_total / (n - 1)
            start = -bredde_total / 2

            for i, (nokkel, _) in enumerate(liste):
                pin_x[nokkel] = start + i * steg

        return pin_x


    def _beregn_alle_baner(grid, bus_pos):
        """Beregn den (evt. knekkede) banen for hver linje og transformator på
        forhånd. Flere forbindelser som krysser det samme rad-mellomrommet får
        hver sin vannrette 'kanal' fordelt mellom radene, og flere forbindelser
        fra samme buss får hver sin 'pinne' langs samleskinnen, slik at
        loddrette linjer aldri ligger oppå hverandre."""

        xs = [p[0] for p in bus_pos.values()]
        ys = [p[1] for p in bus_pos.values()]
        span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
        bar_w = 0.16 * span

        pin_x = _tildel_pinner(grid, bus_pos, bar_w)

        rader_data = []
        nokler = []

        for line in grid.line:
            if line.Frombus in bus_pos and line.Tobus in bus_pos:
                x1, y1 = bus_pos[line.Frombus]
                x2, y2 = bus_pos[line.Tobus]
                x1 += pin_x.get(("line", line.lineNumber, "A"), 0.0)
                x2 += pin_x.get(("line", line.lineNumber, "B"), 0.0)
                rader_data.append((x1, y1, x2, y2))
                nokler.append(("line", line.lineNumber))

        for i, trafo in enumerate(grid.trafo):
            if trafo.Frombus in bus_pos and trafo.Tobus in bus_pos:
                x1, y1 = bus_pos[trafo.Frombus]
                x2, y2 = bus_pos[trafo.Tobus]
                x1 += pin_x.get(("trafo", i, "A"), 0.0)
                x2 += pin_x.get(("trafo", i, "B"), 0.0)
                rader_data.append((x1, y1, x2, y2))
                nokler.append(("trafo", i))

        grupper = {}
        for i, (x1, y1, x2, y2) in enumerate(rader_data):
            if abs(y1 - y2) < 1e-6 or abs(x1 - x2) < 1e-6:
                continue
            nokkel = (min(y1, y2), max(y1, y2))
            grupper.setdefault(nokkel, []).append(i)

        knekk_y = {}
        for (y_lav, y_hoy), indekser in grupper.items():
            indekser.sort(key=lambda i: (rader_data[i][0] + rader_data[i][2]) / 2)
            n = len(indekser)
            for rekkefolge, i in enumerate(indekser):
                knekk_y[i] = y_lav + (rekkefolge + 1) / (n + 1) * (y_hoy - y_lav)

        baner = {}
        for i, (x1, y1, x2, y2) in enumerate(rader_data):
            baner[nokler[i]] = _rett_vinkel_bane(x1, y1, x2, y2, knekk_y=knekk_y.get(i))

        return baner


    def _midtpunkt_pa_bane(bane):
        """Finn punktet halvveis (etter lengde) langs en (evt. knekket) bane,
        og retningsvektoren der – brukes til å plassere transformatorsymboler
        og impedans-etiketter midt på forbindelsen, uansett hvor den knekker."""

        segl = [
            np.hypot(bane[i + 1][0] - bane[i][0], bane[i + 1][1] - bane[i][1])
            for i in range(len(bane) - 1)
        ]
        total = sum(segl)

        if total == 0:
            x, y = bane[0]
            return x, y, 1.0, 0.0

        halv = total / 2
        akkum = 0.0

        for i, d in enumerate(segl):
            if d == 0:
                continue
            if akkum + d >= halv:
                t = (halv - akkum) / d
                (xa, ya), (xb, yb) = bane[i], bane[i + 1]
                return xa + (xb - xa) * t, ya + (yb - ya) * t, (xb - xa) / d, (yb - ya) / d
            akkum += d

        (xa, ya), (xb, yb) = bane[-2], bane[-1]
        d = segl[-1] or 1.0
        return xb, yb, (xb - xa) / d, (yb - ya) / d


    def _generator_busser(grid, bus_pos):
        """Bussnumre som har en generator koblet til seg. gen.bus kan enten
        være selve bussnummeret eller en posisjonsindeks i grid.bus."""

        busser = set()
        for gen in grid.gen:
            busnummer = int(gen.bus)
            if busnummer not in bus_pos and 0 <= busnummer < len(grid.bus):
                busnummer = grid.bus[busnummer].busNumber
            if busnummer in bus_pos:
                busser.add(busnummer)
        return busser
    #------------Skjematisk plassering av bussene (ikke geografisk)---------


    #------------Felles skjelett: linjer, trafoer og generatorer-----------
    def _tegn_underliggende_nett(ax, grid, bus_pos, gen_busser, span, baner):

        SORT = "black"

        for line in grid.line:
            if line.Frombus not in bus_pos or line.Tobus not in bus_pos:
                continue
            bane = baner[("line", line.lineNumber)]
            ax.plot([p[0] for p in bane], [p[1] for p in bane], color=BLUE, linewidth=1.6,
                    zorder=2, solid_capstyle="round", solid_joinstyle="round")

        trafo_r = 0.028 * span

        for i, trafo in enumerate(grid.trafo):
            if trafo.Frombus not in bus_pos or trafo.Tobus not in bus_pos:
                continue

            bane = baner[("trafo", i)]

            ax.plot([p[0] for p in bane], [p[1] for p in bane], color=BLUE, linewidth=1.6,
                    zorder=3, solid_joinstyle="round")

            xm, ym, ux, uy = _midtpunkt_pa_bane(bane)

            avstand = span * 0.05
            x_t1, y_t1 = xm - ux * avstand / 2, ym - uy * avstand / 2
            x_t2, y_t2 = xm + ux * avstand / 2, ym + uy * avstand / 2

            for cx, cy in ((x_t1, y_t1), (x_t2, y_t2)):
                ax.add_patch(Circle((cx, cy), trafo_r, edgecolor=SORT, facecolor="white",
                                     linewidth=1.8, zorder=6))

            ax.text(xm, ym + trafo_r * 2.3, f"{trafo.ratio:.3g}:1", ha="center",
                    fontsize=6.5, color=SORT, zorder=7)

        gen_r = 0.040 * span
        stamme = 0.085 * span

        for busnr in gen_busser:
            if busnr not in bus_pos:
                continue
            x, y = bus_pos[busnr]
            gx, gy = x, y - stamme

            ax.plot([x, gx], [y, gy], color=SORT, linewidth=1.8, zorder=6)
            ax.add_patch(Circle((gx, gy), gen_r, edgecolor=SORT, facecolor="white",
                                 linewidth=1.8, zorder=7))

            tt = np.linspace(-1, 1, 40)
            ax.plot(gx + tt * gen_r * 0.75, gy + np.sin(tt * np.pi * 1.6) * gen_r * 0.4,
                    color=SORT, linewidth=1.2, zorder=8)
    #------------Felles skjelett: linjer, trafoer og generatorer-----------


    #---------Forklaring til enlinjeskjemaet---------------
    def _diagramlegende_skjema(ax):

        handler = [
            Line2D([0], [0], color=BLUE, linewidth=2.2, label="Linje"),
            Line2D([0], [0], marker="o", linestyle="none", markersize=8,
                   markerfacecolor="white", markeredgecolor="black", markeredgewidth=1.8,
                   label="Transformator (to sirkler)"),
            Line2D([0], [0], marker="o", linestyle="none", markersize=8,
                   markerfacecolor="white", markeredgecolor="black", markeredgewidth=1.8,
                   label="Generator (sirkel m/ sinuskurve)"),
            Line2D([0], [0], color="black", linewidth=1.6, marker=">", markersize=6, label="Last (vinklet pil)"),
            Line2D([0], [0], color=NAVY, linewidth=4.5, label="Buss (samleskinne)"),
        ]

        legende = ax.legend(
            handles=handler,
            loc="upper left",
            fontsize=7.4,
            frameon=True,
            framealpha=0.9,
            edgecolor=LINJEGRA,
            facecolor="white",
            labelcolor=TEKST,
            borderpad=0.7,
        )
        legende.set_zorder(20)
    #---------Forklaring til enlinjeskjemaet---------------


    #------------lager interaktivt (zoombart) enlinjeskjema for store nett---
    def _lag_interaktiv_html(grid, V, angle_deg, bus_pos, gen_busser, html_navn):
        """Lager en zoombar/pannbar HTML-versjon av enlinjeskjemaet, med en
        bryter mellom skjematisk visning og spenningsheatmap. Brukes for
        store nett der en statisk PDF-side blir uleselig."""

        try:
            import plotly.graph_objects as go
        except ImportError:
            print(f"Advarsel: fant ikke pakken «plotly» – hopper over interaktivt diagram ({html_navn}).")
            return

        baner = _beregn_alle_baner(grid, bus_pos)

        linje_x, linje_y = [], []
        for line in grid.line:
            if line.Frombus not in bus_pos or line.Tobus not in bus_pos:
                continue
            bane = baner[("line", line.lineNumber)]
            linje_x += [p[0] for p in bane] + [None]
            linje_y += [p[1] for p in bane] + [None]

        linje_trace = go.Scatter(
            x=linje_x, y=linje_y, mode="lines",
            line=dict(color=BLUE, width=1.4),
            hoverinfo="skip", name="Linjer", showlegend=False,
        )

        trafo_x, trafo_y, trafo_hover = [], [], []
        for i, trafo in enumerate(grid.trafo):
            if trafo.Frombus not in bus_pos or trafo.Tobus not in bus_pos:
                continue
            xm, ym, _, _ = _midtpunkt_pa_bane(baner[("trafo", i)])
            trafo_x.append(xm)
            trafo_y.append(ym)
            trafo_hover.append(
                f"Transformator {trafo.Frombus}-{trafo.Tobus}<br>"
                f"Omsetning: {trafo.ratio:.4g}:1<br>R={trafo.R:.4g} pu, X={trafo.X:.4g} pu"
            )

        trafo_trace = go.Scatter(
            x=trafo_x, y=trafo_y, mode="markers",
            marker=dict(symbol="circle-open", size=14, color="black", line=dict(width=2)),
            hovertext=trafo_hover, hoverinfo="text", name="Transformatorer", showlegend=False,
        )

        gen_x, gen_y, gen_hover = [], [], []
        gen_ved_bus = {b.busNumber: b for b in grid.bus}
        for busnr in gen_busser:
            if busnr not in bus_pos:
                continue
            x, y = bus_pos[busnr]
            bus = gen_ved_bus[busnr]
            gen_x.append(x)
            gen_y.append(y)
            gen_hover.append(f"Generator ved buss {busnr}<br>P_G={bus.P_gen:.4f} pu<br>Q_G={bus.Q_gen:.4f} pu")

        gen_trace = go.Scatter(
            x=gen_x, y=gen_y, mode="markers",
            marker=dict(symbol="circle-open", size=20, color="black", line=dict(width=2.5)),
            hovertext=gen_hover, hoverinfo="text", name="Generatorer", showlegend=False,
        )

        bus_x, bus_y, bus_v, bus_navn_liste, bus_hover = [], [], [], [], []
        for i, bus in enumerate(grid.bus):
            if bus.busNumber not in bus_pos:
                continue
            x, y = bus_pos[bus.busNumber]
            bus_x.append(x)
            bus_y.append(y)
            bus_v.append(V[i])
            bus_navn_liste.append(str(bus.busNumber))
            bus_hover.append(
                f"<b>Buss {bus.busNumber}</b> – {bus.Name}<br>"
                f"V = {V[i]:.4f} pu<br>δ = {angle_deg[i]:.3f}°<br>"
                f"P_gen = {bus.P_gen:.4f} pu, Q_gen = {bus.Q_gen:.4f} pu<br>"
                f"P_last = {bus.P_load:.4f} pu, Q_last = {bus.Q_load:.4f} pu"
            )

        buss_skjema = go.Scatter(
            x=bus_x, y=bus_y, mode="markers+text",
            marker=dict(symbol="square", size=16, color=NAVY, line=dict(width=1, color="white")),
            text=bus_navn_liste, textposition="top center", textfont=dict(size=10, color=NAVY),
            hovertext=bus_hover, hoverinfo="text", name="Busser", visible=True,
        )

        v_min, v_max = float(np.min(V)), float(np.max(V))
        buss_heatmap = go.Scatter(
            x=bus_x, y=bus_y, mode="markers+text",
            marker=dict(
                symbol="square", size=22,
                color=bus_v, colorscale="RdBu_r", cmin=v_min, cmax=v_max,
                colorbar=dict(title="Spenning [pu]"),
                line=dict(width=1.2, color="black"),
            ),
            text=bus_navn_liste, textposition="middle center", textfont=dict(size=9, color="white"),
            hovertext=bus_hover, hoverinfo="text", name="Busser (spenning)", visible=False,
        )

        fig = go.Figure(data=[linje_trace, trafo_trace, gen_trace, buss_skjema, buss_heatmap])

        fig.update_layout(
            title=f"Enlinjeskjema – {grid.Name} (zoombart – rull for å zoome, dra for å panorere)",
            template="plotly_white",
            dragmode="pan",
            hovermode="closest",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
            margin=dict(l=20, r=20, t=70, b=20),
            updatemenus=[dict(
                type="buttons", direction="left", x=0.0, y=1.06, xanchor="left",
                buttons=[
                    dict(label="Enlinjeskjema", method="update",
                         args=[{"visible": [True, True, True, True, False]}]),
                    dict(label="Spenningsheatmap", method="update",
                         args=[{"visible": [True, True, True, False, True]}]),
                ],
            )],
        )

        fig.write_html(html_navn, config={"scrollZoom": True})
        print(f"Interaktivt enlinjeskjema for stort nett ({len(grid.bus)} busser) lagret: {html_navn}")
    #------------lager interaktivt (zoombart) enlinjeskjema for store nett---


    #------------lager enlinjeskjema-----------------------
    def _lag_enlinjeskjema(pdf, grid, V, angle_deg, gridnavn, dato, sidetall, filnavn):

        bus_pos = _beregn_skjematisk_pos(grid)

        if not bus_pos:

            fig = _ny_side()
            _sidehode(fig, "ENLINJESKJEMA", "Ingen busser å tegne")

            ax = fig.add_axes([0.08, INNHOLD_BUNN, 0.84, INNHOLD_TOPP - INNHOLD_BUNN])
            ax.axis("off")
            ax.text(0.5, 0.5, "Nettet har ingen busser.", ha="center", va="center",
                    fontsize=13, color=DEMPET)

            _side_med_innramming(pdf, fig, gridnavn, dato, sidetall)
            return

        gen_busser = _generator_busser(grid, bus_pos)

        xlim, ylim, _, _ = _beregn_ramme(bus_pos, marg=0.30, topp_ekstra=0.0)
        bredde = xlim[1] - xlim[0]
        hoyde = ylim[1] - ylim[0]
        xlim = (xlim[0], xlim[1] + bredde * 0.34)   # plass til tekstboksene til høyre for hver buss
        ylim = (ylim[0] - hoyde * 0.18, ylim[1])    # plass til generatorstammene under bussene
        dx_tot = xlim[1] - xlim[0]
        dy_tot = ylim[1] - ylim[0]

        side_bredde, side_hoyde, rute = _velg_side_og_rute(dx_tot, dy_tot)

        fig = plt.figure(figsize=(side_bredde, side_hoyde))
        _sidehode(fig, "ENLINJESKJEMA", "Skjematisk enlinjeskjema med lastflytresultater")

        ax = fig.add_axes(rute)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")

        xs = [p[0] for p in bus_pos.values()]
        ys = [p[1] for p in bus_pos.values()]
        span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0

        baner = _beregn_alle_baner(grid, bus_pos)

        _tegn_underliggende_nett(ax, grid, bus_pos, gen_busser, span, baner)

        antall_noder = len(grid.bus)
        vis_verditekst = antall_noder <= 40
        vis_impedanslabel = len(grid.line) <= 60

        if vis_impedanslabel:
            for line in grid.line:
                if line.Frombus not in bus_pos or line.Tobus not in bus_pos:
                    continue
                xm, ym, _, _ = _midtpunkt_pa_bane(baner[("line", line.lineNumber)])
                tekst = f"$Z_{{{line.Frombus}-{line.Tobus}}}$ = {line.R:.4g} + j{line.X:.4g} [pu]"
                ax.text(xm, ym, tekst, ha="center", va="bottom", fontsize=6.2, color=DEMPET, zorder=9,
                        bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.8))

        bar_w = 0.16 * span

        for i, bus in enumerate(grid.bus):
            if bus.busNumber not in bus_pos:
                continue

            x, y = bus_pos[bus.busNumber]

            ax.plot([x - bar_w / 2, x + bar_w / 2], [y, y], color=NAVY, linewidth=4.5,
                    solid_capstyle="butt", zorder=10)
            ax.text(x - bar_w / 2 - 0.012 * span, y, str(bus.busNumber),
                    ha="right", va="center", fontsize=9, fontweight="bold", color=NAVY, zorder=11)

            har_last = abs(bus.P_load) > 1e-9 or abs(bus.Q_load) > 1e-9

            if har_last:
                # Lastsymbol: rett ut av bussen (loddrett), så en knekk på 90°
                # slik at pilspissen peker vannrett – samme retning som bussen.
                x0 = x + bar_w * 0.32
                stubb = 0.07 * span
                vannrett = 0.05 * span
                y_knekk = y - stubb

                ax.plot([x0, x0], [y, y_knekk], color="black", linewidth=1.6, zorder=10)
                ax.annotate(
                    "", xy=(x0 + vannrett, y_knekk), xytext=(x0, y_knekk),
                    arrowprops=dict(arrowstyle="-|>", color="black", linewidth=1.6),
                    zorder=10,
                )

            if vis_verditekst:
                linjer = [f"V = {V[i]:.4f} pu", f"δ = {angle_deg[i]:.3f}°"]
                if bus.busNumber in gen_busser:
                    linjer.append(f"P_G = {bus.P_gen:.4f} pu")
                    if abs(bus.Q_gen) > 1e-9:
                        linjer.append(f"Q_G = {bus.Q_gen:.4f} pu")
                if har_last:
                    linjer.append(f"P_L = {bus.P_load:.4f} pu")
                    linjer.append(f"Q_L = {bus.Q_load:.4f} pu")

                ax.text(
                    x + bar_w / 2 + 0.02 * span, y, "\n".join(linjer),
                    ha="left", va="center", fontsize=7, color=TEKST, zorder=11,
                    bbox=dict(boxstyle="round,pad=0.28", facecolor="white", edgecolor=LINJEGRA, alpha=0.92),
                )

        html_navn = None
        if not vis_verditekst:
            html_navn = (filnavn[:-4] if filnavn.lower().endswith(".pdf") else filnavn) + "_interaktiv.html"
            ax.text(
                0.5, 0.02,
                f"For mange noder til å vise enkeltverdier i diagrammet – se resultattabellen,\n"
                f"eller åpne den zoombare versjonen: {html_navn}",
                ha="center", va="bottom", transform=ax.transAxes, fontsize=9, color=DEMPET,
            )

        _diagramlegende_skjema(ax)

        _side_med_innramming(pdf, fig, gridnavn, dato, sidetall)

        if html_navn is not None:
            _lag_interaktiv_html(grid, V, angle_deg, bus_pos, gen_busser, html_navn)
    #------------lager enlinjeskjema-----------------------


    #------------lager spenningsheatmap---------------------
    def _lag_spenningsheatmap(pdf, grid, V, angle_deg, gridnavn, dato, sidetall):

        bus_pos = _beregn_skjematisk_pos(grid)

        if not bus_pos:

            fig = _ny_side()
            _sidehode(fig, "SPENNINGSHEATMAP", "Ingen busser å tegne")

            ax = fig.add_axes([0.08, INNHOLD_BUNN, 0.84, INNHOLD_TOPP - INNHOLD_BUNN])
            ax.axis("off")
            ax.text(0.5, 0.5, "Nettet har ingen busser.", ha="center", va="center",
                    fontsize=13, color=DEMPET)

            _side_med_innramming(pdf, fig, gridnavn, dato, sidetall)
            return

        gen_busser = _generator_busser(grid, bus_pos)

        xlim, ylim, _, _ = _beregn_ramme(bus_pos, marg=0.28, topp_ekstra=0.0)
        hoyde = ylim[1] - ylim[0]
        ylim = (ylim[0] - hoyde * 0.18, ylim[1])
        dx_tot = xlim[1] - xlim[0]
        dy_tot = ylim[1] - ylim[0]

        side_bredde, side_hoyde, rute = _velg_side_og_rute(dx_tot, dy_tot)
        rute = [rute[0], rute[1], rute[2] * 0.86, rute[3]]  # plass til fargeskala til høyre

        fig = plt.figure(figsize=(side_bredde, side_hoyde))
        _sidehode(fig, "SPENNINGSHEATMAP", "Spenning per node på enlinjeskjemaet")

        ax = fig.add_axes(rute)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.set_aspect("equal", adjustable="box")
        ax.axis("off")

        xs = [p[0] for p in bus_pos.values()]
        ys = [p[1] for p in bus_pos.values()]
        span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0

        baner = _beregn_alle_baner(grid, bus_pos)

        _tegn_underliggende_nett(ax, grid, bus_pos, gen_busser, span, baner)

        v_min, v_max = float(np.min(V)), float(np.max(V))
        senter = 1.0
        if v_min >= senter:
            v_min = senter - 1e-4
        if v_max <= senter:
            v_max = senter + 1e-4
        norm = mcolors.TwoSlopeNorm(vmin=v_min, vcenter=senter, vmax=v_max)
        cmap = plt.cm.RdBu_r

        boks_w = 0.17 * span
        boks_h = 0.11 * span

        for i, bus in enumerate(grid.bus):
            if bus.busNumber not in bus_pos:
                continue

            x, y = bus_pos[bus.busNumber]
            farge = cmap(norm(V[i]))

            ax.add_patch(FancyBboxPatch(
                (x - boks_w / 2, y - boks_h / 2), boks_w, boks_h,
                boxstyle="round,pad=0.002,rounding_size=0.01",
                facecolor=farge, edgecolor="black", linewidth=1.0, zorder=10,
            ))

            lys_bakgrunn = sum(farge[:3]) / 3 > 0.55
            ax.text(
                x, y, f"Bnr: {bus.busNumber}\nV={V[i]:.3f}\nδ°={angle_deg[i]:.3f}",
                ha="center", va="center", fontsize=6.3, fontweight="bold", zorder=11,
                color=(TEKST if lys_bakgrunn else "white"),
            )

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar_ax = fig.add_axes([rute[0] + rute[2] + 0.025, rute[1], 0.025, rute[3]])
        cbar = fig.colorbar(sm, cax=cbar_ax)
        cbar.set_label("Spenning [pu]", fontsize=8.5, color=TEKST)
        cbar.ax.tick_params(labelsize=7.5, colors=DEMPET)

        _side_med_innramming(pdf, fig, gridnavn, dato, sidetall)
    #------------lager spenningsheatmap---------------------


    #----------------------Tegner en generisk tabell--------
    def _teikna_tabell(ax, kolonner, rader):

        if not rader:
            ax.text(0.0, 0.9, "Ingen rader.", fontsize=9, color=DEMPET,
                    transform=ax.transAxes, va="top")
            return

        tabell = ax.table(cellText=rader, colLabels=kolonner, loc="upper center", cellLoc="center")
        tabell.auto_set_font_size(False)
        tabell.set_fontsize(8.2)
        tabell.scale(1, 1.55)
        tabell.auto_set_column_width(col=list(range(len(kolonner))))

        for c in range(len(kolonner)):
            celle = tabell[0, c]
            celle.set_facecolor(NAVY)
            celle.set_text_props(color="white", fontweight="bold")
            celle.set_edgecolor("white")

        for r in range(len(rader)):
            for c in range(len(kolonner)):
                celle = tabell[r + 1, c]
                celle.set_edgecolor(LINJEGRA)
                celle.set_facecolor(GRABAKGRUNN if r % 2 else "white")
    #----------------------Tegner en generisk tabell--------


    #----------------------Lager linjetabell-----------------
    def _lag_linjetabell(pdf, grid, gridnavn, dato, sidetall):

        fig = _ny_side()
        _sidehode(fig, "LINJETABELL", "Linjer og transformatorer")

        total_h = INNHOLD_TOPP - INNHOLD_BUNN
        linje_h = total_h * 0.60
        trafo_h = total_h * 0.28

        fig.text(0.065, INNHOLD_TOPP, "LINJER", fontsize=11, fontweight="bold", color=NAVY, va="top")

        ax1 = fig.add_axes([0.065, INNHOLD_TOPP - linje_h, 0.87, linje_h - 0.03])
        ax1.axis("off")

        kol_linje = ["#", "Fra", "Til", "R [pu]", "X [pu]", "B [pu]", "Lengde"]
        rader_linje = [
            [
                str(i + 1), str(l.Frombus), str(l.Tobus), f"{l.R:.5g}", f"{l.X:.5g}", f"{l.B:.3g}",
                (f"{l.lenght:.0f}" if l.lenght is not None else "-"),
            ]
            for i, l in enumerate(grid.line)
        ]
        _teikna_tabell(ax1, kol_linje, rader_linje)

        trafo_topp = INNHOLD_TOPP - linje_h - 0.06
        fig.text(0.065, trafo_topp, "TRANSFORMATORER", fontsize=11, fontweight="bold", color=NAVY, va="top")

        ax2 = fig.add_axes([0.065, trafo_topp - trafo_h, 0.87, trafo_h - 0.03])
        ax2.axis("off")

        kol_trafo = ["#", "Fra", "Til", "Omsetning", "R [pu]", "X [pu]"]
        rader_trafo = [
            [str(i + 1), str(t.Frombus), str(t.Tobus), f"{t.ratio:.4g}:1", f"{t.R:.5g}", f"{t.X:.5g}"]
            for i, t in enumerate(grid.trafo)
        ]
        _teikna_tabell(ax2, kol_trafo, rader_trafo)

        _side_med_innramming(pdf, fig, gridnavn, dato, sidetall)
    #----------------------Lager linjetabell-----------------


    #----------------------Lager resultattabell------------
    def _lag_resultattabell(pdf, grid, V, angle_deg, P_MW, Q_MVAr, bus_nr, bus_navn, gridnavn, dato, sidetall):

        fig = _ny_side()
        _sidehode(fig, "RESULTATTABELL", "Lastflytresultater per node")

        ax = fig.add_axes([0.065, INNHOLD_BUNN, 0.87, INNHOLD_TOPP - INNHOLD_BUNN])
        ax.axis("off")

        kolonner = ["#", "Buss", "Navn", "V [pu]", "V [kV]", "Vinkel [°]", "P [MW]", "Q [MVAr]"]

        v_min = [b.V_min for b in grid.bus]
        v_max = [b.V_max for b in grid.bus]
        v_base = [b.Vbase for b in grid.bus]

        rader = []
        avvik = []

        for i in range(len(V)):

            utenfor = (
                (v_min[i] is not None and V[i] < v_min[i])
                or (v_max[i] is not None and V[i] > v_max[i])
            )
            avvik.append(utenfor)

            rader.append([
                str(i + 1),
                str(bus_nr[i]),
                _kort_tekst(bus_navn[i], 26),
                f"{V[i]:.4f}",
                f"{V[i] * v_base[i]:.1f}" if v_base[i] else "-",
                f"{angle_deg[i]:.3f}",
                f"{P_MW[i]:.2f}",
                f"{Q_MVAr[i]:.2f}",
            ])

        tabell = ax.table(cellText=rader, colLabels=kolonner, loc="upper center", cellLoc="center")
        tabell.auto_set_font_size(False)
        tabell.set_fontsize(8.3)
        tabell.scale(1, 1.65)
        tabell.auto_set_column_width(col=list(range(len(kolonner))))

        for c in range(len(kolonner)):
            celle = tabell[0, c]
            celle.set_facecolor(NAVY)
            celle.set_text_props(color="white", fontweight="bold")
            celle.set_edgecolor("white")

        for r in range(len(rader)):
            for c in range(len(kolonner)):
                celle = tabell[r + 1, c]
                celle.set_edgecolor(LINJEGRA)

                if avvik[r]:
                    celle.set_facecolor(LYSROD)
                    if c == 3:
                        celle.set_text_props(color=ROD, fontweight="bold")
                else:
                    celle.set_facecolor(GRABAKGRUNN if r % 2 else "white")

        if any(m is not None for m in v_min) or any(m is not None for m in v_max):
            n_brudd = sum(avvik)
            if n_brudd == 0:
                fig.text(0.065, INNHOLD_BUNN - 0.02, "Alle spenninger er innenfor definerte grenseverdier.",
                         fontsize=8.5, color=GRONN)
            else:
                fig.text(0.065, INNHOLD_BUNN - 0.02, f"{n_brudd} node(r) er utenfor definerte spenningsgrenser (markert i rødt).",
                         fontsize=8.5, color=ROD)

        _side_med_innramming(pdf, fig, gridnavn, dato, sidetall)
    #----------------------Lager resultattabell------------


    #---------------lager rapport--------------------------
    # -----------------------------------------------------
    # Gjør om til numpy-arrays og fysiske enheter
    # -----------------------------------------------------

    V = np.asarray(V, dtype=float)
    angle_deg = np.degrees(np.asarray(angle, dtype=float))

    Sbase = grid.Base.Sbase if grid.Base is not None else 1.0

    P_MW = np.asarray(P, dtype=float) * Sbase
    Q_MVAr = np.asarray(Q, dtype=float) * Sbase

    # -----------------------------------------------------
    # Antall noder
    # -----------------------------------------------------

    antall_noder = len(V)

    bus_nr = np.array([b.busNumber for b in grid.bus])
    bus_navn = [b.Name for b in grid.bus]

    # -----------------------------------------------------
    # BEREGN NØKKELTALL
    # -----------------------------------------------------

    idx_min_V = int(np.argmin(V))
    idx_max_V = int(np.argmax(V))

    idx_min_angle = int(np.argmin(angle_deg))
    idx_max_angle = int(np.argmax(angle_deg))

    idx_min_P = int(np.argmin(P_MW))
    idx_max_P = int(np.argmax(P_MW))

    idx_min_Q = int(np.argmin(Q_MVAr))
    idx_max_Q = int(np.argmax(Q_MVAr))

    def _noderef(i, maks=24):
        return f"{_kort_tekst(bus_navn[i], maks)} (buss {bus_nr[i]})"

    dato = datetime.now().strftime("%d.%m.%Y %H:%M")

    losning = getattr(grid, "solution", None)

    # -----------------------------------------------------
    # OPPRETT PDF
    # -----------------------------------------------------

    with PdfPages(filnavn) as pdf:

        d = pdf.infodict()
        d["Title"] = f"Kraftsystemanalyse – {grid.Name}"
        d["Author"] = "GridMaker"
        d["Subject"] = "Lastflytrapport"

        # =================================================
        # SIDE 1 – FORSIDE / SAMMENDRAG
        # =================================================

        fig = _ny_side()
        _sidehode(fig, "KRAFTSYSTEMANALYSE", f"Lastflytrapport  ·  {grid.Name}  ·  {dato}")

        # -------- KPI-kort --------
        kort_y = 0.840
        kort_h = 0.052
        kort_w = 0.192
        mellomrom = 0.0187

        _kpi_kort(fig, 0.065 + 0 * (kort_w + mellomrom), kort_y, kort_w, kort_h, "Antall noder", str(antall_noder))
        _kpi_kort(fig, 0.065 + 1 * (kort_w + mellomrom), kort_y, kort_w, kort_h, "Antall linjer", str(len(grid.line)))
        _kpi_kort(fig, 0.065 + 2 * (kort_w + mellomrom), kort_y, kort_w, kort_h, "Transformatorer", str(len(grid.trafo)))
        _kpi_kort(fig, 0.065 + 3 * (kort_w + mellomrom), kort_y, kort_w, kort_h, "Generatorer", str(len(grid.gen)))

        # -------- Lastflyt-status --------
        y = 0.775
        _seksjonstittel(fig, 0.065, y, "LASTFLYT-STATUS")

        if losning is not None and getattr(losning, "konvergerte", None) is not None:
            konvergerte = bool(losning.konvergerte)
            _rad(
                fig, 0.065, y - 0.038, "Konvergerte:",
                "Ja" if konvergerte else "Nei",
                GRONN if konvergerte else ROD,
            )
            iter_txt = str(getattr(losning, "iterasjoner", "-"))
            _rad(fig, 0.065, y - 0.066, "Iterasjoner:", iter_txt)

            mismatch = getattr(losning, "mismatch", None)
            if isinstance(mismatch, (int, float)):
                mismatch_txt = f"{mismatch:.2e}"
            elif mismatch is not None:
                mismatch_txt = f"{np.max(np.abs(np.asarray(mismatch))):.2e}"
            else:
                mismatch_txt = "-"
            _rad(fig, 0.065, y - 0.094, "Maks. mismatch:", mismatch_txt)
        else:
            _rad(fig, 0.065, y - 0.038, "Status:", "Ikke tilgjengelig", DEMPET)

        # -------- Spenning --------
        y = 0.635
        _seksjonstittel(fig, 0.065, y, "SPENNING")

        _rad(fig, 0.065, y - 0.038, "Minimum:", f"{V[idx_min_V]:.4f} pu")
        _rad(fig, 0.065, y - 0.060, "", _noderef(idx_min_V, 26), DEMPET, 8.3)
        _rad(fig, 0.065, y - 0.096, "Maksimum:", f"{V[idx_max_V]:.4f} pu")
        _rad(fig, 0.065, y - 0.118, "", _noderef(idx_max_V, 26), DEMPET, 8.3)

        # -------- Spenningsvinkel --------
        y = 0.430
        _seksjonstittel(fig, 0.065, y, "SPENNINGSVINKEL")

        _rad(fig, 0.065, y - 0.038, "Minimum:", f"{angle_deg[idx_min_angle]:.3f}°")
        _rad(fig, 0.065, y - 0.060, "", _noderef(idx_min_angle, 26), DEMPET, 8.3)
        _rad(fig, 0.065, y - 0.096, "Maksimum:", f"{angle_deg[idx_max_angle]:.3f}°")
        _rad(fig, 0.065, y - 0.118, "", _noderef(idx_max_angle, 26), DEMPET, 8.3)

        # -------- Effekt --------
        y = 0.775
        _seksjonstittel(fig, 0.545, y, "EFFEKT")

        _rad(fig, 0.545, y - 0.038, "Total aktiv effekt:", f"{np.sum(P_MW):.2f} MW")
        _rad(fig, 0.545, y - 0.062, "Total reaktiv effekt:", f"{np.sum(Q_MVAr):.2f} MVAr")

        _rad(fig, 0.545, y - 0.100, "Minimum P:", f"{P_MW[idx_min_P]:.2f} MW")
        _rad(fig, 0.545, y - 0.122, "", _noderef(idx_min_P, 16), DEMPET, 8.3)
        _rad(fig, 0.545, y - 0.158, "Maksimum P:", f"{P_MW[idx_max_P]:.2f} MW")
        _rad(fig, 0.545, y - 0.180, "", _noderef(idx_max_P, 16), DEMPET, 8.3)

        _rad(fig, 0.545, y - 0.220, "Minimum Q:", f"{Q_MVAr[idx_min_Q]:.2f} MVAr")
        _rad(fig, 0.545, y - 0.242, "", _noderef(idx_min_Q, 16), DEMPET, 8.3)
        _rad(fig, 0.545, y - 0.278, "Maksimum Q:", f"{Q_MVAr[idx_max_Q]:.2f} MVAr")
        _rad(fig, 0.545, y - 0.300, "", _noderef(idx_max_Q, 16), DEMPET, 8.3)

        _side_med_innramming(pdf, fig, grid.Name, dato, 1)

        # =================================================
        # SIDE 2 – ENLINJESKJEMA
        # =================================================

        _lag_enlinjeskjema(pdf, grid, V, angle_deg, grid.Name, dato, 2, filnavn)

        # =================================================
        # SIDE 3 – SPENNINGSHEATMAP
        # =================================================

        _lag_spenningsheatmap(pdf, grid, V, angle_deg, grid.Name, dato, 3)

        # =================================================
        # SIDE 4 – RESULTATTABELL (NODER)
        # =================================================

        _lag_resultattabell(
            pdf, grid, V, angle_deg, P_MW, Q_MVAr, bus_nr, bus_navn,
            grid.Name, dato, 4,
        )

        # =================================================
        # SIDE 5 – LINJETABELL
        # =================================================

        _lag_linjetabell(pdf, grid, grid.Name, dato, 5)
    #---------------lager rapport--------------------------
#---------------------Lager rapporten----------------------------------------
