import fitz

# ###Auslesen des Textes
# doc = pymupdf.open("Organigramme/Organigramm_Inneren.pdf")
# page = doc[0]
# text = page.get_text(sort=True)

# ### Worte mit nur einem Leerzeichen anordnen
# words = text.split()
# non_empty_words = [word for word in words if word]
# new_text = " ".join(non_empty_words)

# ###Liste mancher Jobbetitelungen
# keywords = ["Referat", "Abteilung", "Unterabteilung", "Beauftragter der Bundesregierung für Sucht- und Drogenfragen",
#             "Parlamentarischer Staatssekretär", "Parlamentarische Staatssekretärin", "Staatssekretär", "Staatssekretärin",
#             "evollmächtigte der Bundesregierung für Pflege",
#             "Beauftragter der Bundesregierung für die Belange der Patientinnen und Patienten"]

# ###Austauschen der Keywords mit Leerzeilen
# for keyword in keywords:
#     # new_text = text.replace("Referat", "\n\nReferat")
#     new_text = text.replace(keyword, f"\n\n{keyword}")
# ---------------------------------------------------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------------------------------------------------

# Auslesen des Textes
doc = fitz.open("example_orgcharts/org_finanz.pdf")
page = doc[0]
paths = page.get_drawings()

outpdf = fitz.open()
outpage = outpdf.new_page(width=page.rect.width, height=page.rect.height)
shape = outpage.new_shape()

rectangle_list = []
lines_list = []

for path in paths:
    print(path)
    print("----")
    for item in path["items"]:
        if item[0] == "re":  # rectangle
            shape.draw_rect(item[1])
            rectangle_list.append(item)
        elif item[0] == "l":  # line
            shape.draw_line(item[1], item[2])
            lines_list.append(item)
        # elif item[0] == "qu":  # quad
        #     shape.draw_quad(item[1])
        # elif item[0] == "c":  # curve
        #     shape.draw_bezier(item[1], item[2], item[3], item[4])
        # else:
            # raise ValueError("unhandled drawing", item)

print("#################")
# shape.finish(
#     fill=path["fill"],  # fill color
#     color=path["color"],  # line color
#     dashes=path["dashes"],  # line dashing
#     even_odd=path.get("even_odd", True),  # control color of overlaps
#     closePath=path["closePath"],  # whether to connect last and first point
#     lineJoin=path["lineJoin"],  # how line joins should look like
#     lineCap=path["lineCap"],  # how line ends should look like
#     width=path["width"],  # line width
#     stroke_opacity=path.get("stroke_opacity", 1),  # same value for both
#     fill_opacity=path.get("fill_opacity", 1),  # opacity parameters
#     )

shape.finish(
    fill=path["fill"],  # fill color
    # color=path["color"],  # line color
)

text = page.get_text("blocks", sort=False)
number_of_text_blocks = len(text)
text_as_string = str(text)

words = text_as_string.split()
non_empty_words = [word for word in words if word]
new_text = " ".join(non_empty_words)

modified_text = new_text.replace("),", "),\n\n")
final_modified_text = modified_text.replace(r"\n", "")
# print(final_modified_text)
# print("----------------------------------------------------------------------")
# print("----------------------------------------------------------------------")
# print(f"---------------- Number of extracted text blocks: {number_of_text_blocks} ----------------")
# print("----------------------------------------------------------------------")
# print("----------------------------------------------------------------------")

for rect in rectangle_list:
    print(rect)
    print("-----")

for line in lines_list:
    print(line)
    print("-----")

shape.commit()
outpdf.save("example_orgcharts/org_shapes.pdf")
