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

connection.close() #Veldig viktig, fordi vi må ikke ha en åpen kontakt
