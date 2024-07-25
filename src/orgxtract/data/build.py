import csv
from importlib import resources
import itertools
import locale

from orgxtract import data

path = resources.files(data)
data = set()
bases = set()
posts = set()

with open(path / "Funktionsbezeichnungen.csv", "r", encoding="utf-8") as fun_file:
    reader = csv.DictReader(fun_file)

    for row in reader:
        data.add((row["Funktionsbezeichnung"], row["Zusatz"]))

with open(path / "Besoldungsgruppen.csv", "r", encoding="utf-8") as amt_file:
    reader = csv.DictReader(amt_file)

    for row in reader:
        data.add((row["Amtsbezeichnung"], row["Zusatz"]))

for (bezeichnung, zusatz) in data:
    bezeichnung_split = bezeichnung.split("/")

    for b in bezeichnung_split:
        bases.add(b.lower())
        posts.add(b)

    if len(zusatz) == 0:
        continue

    # #1 Oberrat + Regierungs- = Oberregierungsrat
    # #2 Oberrat + Technischer Regierungs- = Technischer Oberregierungsrat
    is_zusatz_inside = zusatz[-1].isdigit()

    if is_zusatz_inside:
        zusatz = zusatz[:-1]

    zusatz_split = zusatz.strip("\"").split("/")

    for (b, z) in zip(bezeichnung_split, itertools.cycle(zusatz_split)):
        b_modifier = ""
        b_base = b

        index = b.find(" ")
        if index != -1:
            b_modifier = b[:index + 1]
            b_base = b[index + 1:]
        elif is_zusatz_inside:
            for b in bases:
                if len(b) < len(b_base) and b_base.endswith(b):
                    b_modifier = b_base[:len(b_base) - len(b)]
                    b_base = b
                    break

        if z[-1] == "-":
            z = z[:-1]

            if is_zusatz_inside:
                index = z.rfind(" ")

                if index != -1:
                    posts.add(f"{z[:index + 1]}{b_modifier}{z[index + 1:].lower()}{b_base}")
                else:
                    posts.add(f"{b_modifier}{z.lower()}{b_base}")
            else:
                posts.add(f"{b_modifier}{z}{b_base.lower()}")
        else:
            index = z.find("...")
            if index != -1:
                if z[index - 1] == "-":
                    posts.add(f"{b_modifier}{z[:index - 1]}{b_base.lower()}{z[index + 3:]}")
                else:
                    posts.add(f"{b_modifier}{z[:index]}{b_base}{z[index + 3:]}")
            else:
                if z.rfind("ORG") != -1:
                    posts.add(f"{b_modifier}{b_base} {z.rstrip(" ORG")}")
                    pass
                else:
                    if z.istitle():
                        posts.add(f"{b_modifier}{z} {b_base}")
                    else:
                        posts.add(f"{b_modifier}{b_base} {z}")

locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")
posts = sorted(posts, key=locale.strxfrm)
locale.setlocale(locale.LC_ALL, "")

with open(path / "per_posts", "w", encoding="utf-8") as terminology_file:
    for term in posts:
        terminology_file.write(term)
        terminology_file.write("\n")