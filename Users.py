import sqlite3

connection = sqlite3.connect('testedatabase.db') #det er en databse
cursor = connection.cursor()

#vi skal ha firma, firmapassord, firmabrukernavn

#python språket fungerer ikke med sql, det må være sql språket

#SÅ kommandoer er er tekst string, men så da sql leser
#VARCHAR er en variable som tar string med maks antall tegn
sql_command = """ CREATE TABLE sample (
vid_firma VARCHAR(30),
passord VARCHAR(100),
brukernavn VARCHAR(100),
firmaopprettet Date
)
"""

cursor.execute(sql_command)

#connection.close() #Veldig viktig, fordi vi må ikke ha en åpen kontakt

liste = [["test",3,4], [2,3,3]]

for i in range(len(liste)):
   vid_firma = liste[i,0]
   passord = liste[i,1]

cursor.execute("INSERT INTO sample VALUES (?,?,?)", (vid_firma, passord)

#det er veldig viktig å commite lagre hvis man endrer en db
connection.commit()
connection.close()

#Hvis man skal oppdatere noe som er i en db. Kan lete etter spesifikke navn eller verdier
cursor.execute('''UPDATE sample SET vid_firma="nye navnet" WHERE vid_firma="et gitt navn den leter etter" ''')
connection.commit()#må alltid med hvis man endrer data i db
connection.close()
#hvis man skal slette, så endrer man bare UPDATE til DELETE
