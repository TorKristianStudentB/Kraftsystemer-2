#-----------En test som bare leter etter linjer med null i verdi------------
def test_finner_linje_med_null_impedans(grid_g):
    g = grid_g

    null_linjer = [
        line.Name
        for line in g.line
        if line.R == 0 and line.X == 0
    ]

    assert not null_linjer, f"Fant linjer med R = X = 0: {null_linjer}"
#-----------En test som bare leter etter linjer med null i verdi------------

#-------En test som leter etter linjer med svært lav impedans, som kan føre til numeriske problemer i lastflytanalysen---
def test_finner_linje_med_naer_null_impedans(grid_g):
    g = grid_g
    toleranse = 1e-6  # pu

    svake_linjer = [
        (line.Name, abs(complex(line.R, line.X)))
        for line in g.line
        if abs(complex(line.R, line.X)) <= toleranse
    ]

    assert not svake_linjer, (
        f"Fant linjer med impedans <= {toleranse} pu: {svake_linjer}"
    )
#-------En test som leter etter linjer med svært lav impedans, som kan føre til numeriske problemer i lastflytanalysen---

