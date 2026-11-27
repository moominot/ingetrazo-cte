# SPDX-License-Identifier: GPL-3.0-or-later
"""The extension's words: English in the code, Catalan and Spanish here."""
from __future__ import annotations

LANGUAGE = lambda: "en"  # noqa: E731 - setup() points it at IngeTrazo's

#: English -> (Catalan, Spanish)
_TABLE = {
    "Stairs": ("Escales", "Escaleras"),
    "CTE Stairs and ramps": ("CTE Escales i rampes",
                             "CTE Escaleras y rampas"),
    "CTE Stairs and ramps…": ("CTE Escales i rampes…",
                              "CTE Escaleras y rampas…"),
    "Show the tab: stairs and ramps raised from a plan drawing.": (
        "Mostra la pestanya: escales i rampes aixecades des del dibuix en "
        "planta.",
        "Muestra la pestaña: escaleras y rampas levantadas desde el dibujo "
        "en planta."),
    # ramps
    "Stair": ("Escala", "Escalera"),
    "Ramp": ("Rampa", "Rampa"),
    "Slope": ("Pendent", "Pendiente"),
    "Automatic: the ramp fills the plan. With a slope, it runs only as far "
    "as that slope needs.": (
        "Automàtic: la rampa omple la planta. Amb un pendent, només arriba "
        "fins on cal.",
        "Automático: la rampa llena la planta. Con una pendiente, solo llega "
        "hasta donde hace falta."),
    "Use": ("Ús", "Uso"),
    "Landings in long runs and warnings, after CTE DB SUA 1, 4.3 (Spain). "
    "Lengths in plan.": (
        "Replans als trams llargs i avisos, segons el CTE DB SUA 1, 4.3. "
        "Longituds en planta.",
        "Rellanos en tramos largos y avisos, según el CTE DB SUA 1, 4.3. "
        "Longitudes en planta."),
    "Accessible": ("Accessible", "Accesible"),
    "People": ("Vianants", "Peatones"),
    "Cars": ("Cotxes", "Coches"),
    "Accessible route: 10 % up to 3 m, 8 % up to 6 m, then 6 %; flights of "
    "9 m at most.": (
        "Itinerari accessible: 10 % fins a 3 m, 8 % fins a 6 m i després 6 %; "
        "trams de 9 m com a màxim.",
        "Itinerario accesible: 10 % hasta 3 m, 8 % hasta 6 m y después 6 %; "
        "tramos de 9 m como máximo."),
    "12 % at most; flights up to 15 m.": (
        "12 % com a màxim; trams de 15 m com a màxim.",
        "12 % como máximo; tramos de 15 m como máximo."),
    "Car park ramps also walked on: 16 % at most.": (
        "Rampes d'aparcament per on també passen persones: 16 % com a màxim.",
        "Rampas de aparcamiento por donde también pasan personas: 16 % como "
        "máximo."),
    "Sloping": ("En pendent", "En pendiente"),
    "The slope goes on round the turn.": (
        "El pendent continua pel gir.", "La pendiente sigue por el giro."),
    "Landings in long runs": ("Replans als trams llargs",
                              "Rellanos en tramos largos"),
    "A flight longer than the use allows is cut by a landing.": (
        "Un tram més llarg del que l'ús permet es parteix amb un replà.",
        "Un tramo más largo de lo que el uso permite se parte con un "
        "rellano."),
    "Landing length": ("Llarg del replà", "Largo del rellano"),
    "Sloping length": ("Longitud en pendent", "Longitud en pendiente"),
    "Flights": ("Trams", "Tramos"),
    "Longest flight": ("Tram més llarg", "Tramo más largo"),
    "The plan has {m} m to spare.": ("A la planta li sobren {m} m.",
                                     "A la planta le sobran {m} m."),
    "Over {p} % for a flight of {m} m.": (
        "Passa del {p} % per a un tram de {m} m.",
        "Supera el {p} % para un tramo de {m} m."),
    "Up to 4 % the code does not call it a ramp.": (
        "Fins al 4 % la norma no la considera rampa.",
        "Hasta el 4 % la norma no la considera rampa."),
    "Accessible route: flights must be straight, or have a radius of 30 m "
    "or more.": (
        "Itinerari accessible: els trams han de ser rectes o tenir 30 m de "
        "radi com a mínim.",
        "Itinerario accesible: los tramos deben ser rectos o tener 30 m de "
        "radio como mínimo."),
    "Landings in line need 1.50 m or more.": (
        "Els replans en línia han de fer 1,50 m com a mínim.",
        "Los rellanos en línea deben medir 1,50 m como mínimo."),
    "{m} m of run missing for {p} %: the plan is filled.": (
        "Falten {m} m de recorregut per al {p} %: s'omple la planta.",
        "Faltan {m} m de recorrido para el {p} %: se llena la planta."),
    "A flight over {m} m.": ("Hi ha un tram de més de {m} m.",
                             "Hay un tramo de más de {m} m."),
    "Narrower than {m} m.": ("Fa menys de {m} m d'amplada.",
                             "Tiene menos de {m} m de anchura."),
    "At the least favourable side: {p} % (it is the one that counts).": (
        "Al costat més desfavorable: {p} % (és el que compta).",
        "En el lado más desfavorable: {p} % (es el que cuenta)."),
    "Turns {a}°.": ("Gira {a}°.", "Gira {a}°."),
    "Deck thickness": ("Gruix tauler", "Grosor tablero"),
    "Deck": ("Tauler", "Tablero"),
    "Raise the ramp": ("Aixeca la rampa", "Levantar la rampa"),
    "Slope {p} %": ("Pendent {p} %", "Pendiente {p} %"),
    "Type the slope in % (e.g. 8) or a height (e.g. 0.60) · Ctrl = reverse": (
        "Escriu el pendent en % (p. ex. 8) o una alçada (p. ex. 0,60) · Ctrl "
        "= inverteix",
        "Escribe la pendiente en % (p. ej. 8) o una altura (p. ej. 0,60) · "
        "Ctrl = invertir"),
    "Solid ramp": ("Rampa massissa", "Rampa maciza"),
    "Concrete ramp": ("Rampa de formigó", "Rampa de hormigón"),
    "Steel ramp": ("Rampa de platines", "Rampa de pletinas"),
    ".": (",", ","),
    # DB SUA verdict
    "Restricted use": ("Ús restringit", "Uso restringido"),
    "General use": ("Ús general", "Uso general"),
    "Public or no lift": ("Públic o sense ascensor",
                          "Público o sin ascensor"),
    "Complies": ("Compleix", "Cumple"),
    "Does not comply": ("No compleix", "No cumple"),
    "Sizes only. Not checked: the width of table 4.1 and DB SI, handrails, "
    "guards, closed risers, headroom, doors by the landings.": (
        "Només mides. No es comprova: l'amplada de la taula 4.1 i del DB SI, "
        "passamans, baranes, davanters, alçada lliure, portes als replans.",
        "Solo medidas. No se comprueba: la anchura de la tabla 4.1 y del DB "
        "SI, pasamanos, barandillas, tabicas, altura libre, puertas en las "
        "mesetas."),
    "db_riser_max": ("Davanter de {v} cm (màxim {m}).",
                     "Contrahuella de {v} cm (máximo {m})."),
    "db_riser_min": ("Davanter de {v} cm (mínim 13).",
                     "Contrahuella de {v} cm (mínimo 13)."),
    "db_going_min": ("Petjada de {v} cm (mínim {m}).",
                     "Huella de {v} cm (mínimo {m})."),
    "db_relation": ("2C + H = {v} cm (ha de ser entre 54 i 70).",
                    "2C + H = {v} cm (debe estar entre 54 y 70)."),
    "db_curve_inner": (
        "Corba: {v} cm de petjada a 50 cm de la vora interior (mínim 28).",
        "Curva: {v} cm de huella a 50 cm del borde interior (mínimo 28)."),
    "db_curve_walking": (
        "Corba: {v} cm de petjada a la línia de mesura (mínim {m}).",
        "Curva: {v} cm de huella en la línea de medida (mínimo {m})."),
    "db_curve_narrow": ("Corba: {v} cm al costat estret (mínim 5).",
                        "Curva: {v} cm en el lado estrecho (mínimo 5)."),
    "db_curve_wide": ("Corba: {v} cm al costat ample (màxim 44).",
                      "Curva: {v} cm en el lado ancho (máximo 44)."),
    "db_width": ("Amplada útil de {v} m (mínim 0,80).",
                 "Anchura útil de {v} m (mínimo 0,80)."),
    "db_uneven": ("Les petjades dels trams rectes no són iguals.",
                  "Las huellas de los tramos rectos no son iguales."),
    "db_mixed": (
        "A la part corba, la petjada a l'eix és menor que a la recta.",
        "En la parte curva, la huella en el eje es menor que en la recta."),
    "db_few_steps": ("Un tram de {v} graons (mínim 3).",
                     "Un tramo de {v} peldaños (mínimo 3)."),
    "db_flight_height": ("Un tram salva {v} m (màxim {m}).",
                         "Un tramo salva {v} m (máximo {m})."),
    "db_landing": ("Replà en línia de {v} m (mínim 1,00).",
                   "Meseta en línea de {v} m (mínimo 1,00)."),
    "db_no_treads": ("No hi ha cap petjada.", "No hay ninguna huella."),
    "Not checked: widths off accessible routes, the level 1.20 m at the "
    "ends of flights, landings at turns, doors, cross slope, handrails, "
    "kerbs, DB SUA 7.": (
        "No es comprova: l'amplada fora d'itinerari accessible, els 1,20 m "
        "horitzontals als extrems dels trams, els replans de gir, les "
        "portes, el pendent transversal, passamans, sòcols ni el DB SUA 7.",
        "No se comprueba: la anchura fuera de itinerario accesible, los "
        "1,20 m horizontales en los extremos de los tramos, las mesetas de "
        "giro, las puertas, la pendiente transversal, pasamanos, zócalos ni "
        "el DB SUA 7."),
    # the plan
    "Plan": ("Planta", "Planta"),
    "Take the selected plan": ("Agafa la planta seleccionada",
                               "Tomar la planta seleccionada"),
    "No plan taken": ("Cap planta agafada", "Ninguna planta tomada"),
    "Contour": ("Contorn", "Contorno"),
    "Contour with {n} drawn steps": ("Contorn amb {n} línies de graó",
                                     "Contorno con {n} líneas de peldaño"),
    "Open line": ("Línia oberta", "Línea abierta"),
    "Circle (helical stair)": ("Cercle (helicoidal)", "Círculo (helicoidal)"),
    "Width": ("Amplada", "Anchura"),
    "The line is": ("La línia és", "La línea es"),
    "Left": ("Esquerra", "Izquierda"),
    "Centre": ("Eix", "Eje"),
    "Right": ("Dreta", "Derecha"),
    "As seen going up": ("Mirant cap amunt de l'escala",
                         "Mirando hacia arriba de la escalera"),
    "Total turn": ("Gir total", "Giro total"),
    "Start at": ("Arrencada", "Arranque"),
    "Turns the first step about the centre.": (
        "Gira el primer graó al voltant del centre.",
        "Gira el primer peldaño alrededor del centro."),
    "Post radius": ("Radi del pilar", "Radio del pilar"),
    "Reverse": ("Inverteix", "Invertir"),
    "Climb from the other end (Ctrl).": (
        "Puja des de l'altre extrem (Ctrl).",
        "Subir desde el otro extremo (Ctrl)."),
    "Other ends": ("Altres extrems", "Otros extremos"),
    "When the contour could start somewhere else: tries the next pair of "
    "ends.": (
        "Quan el contorn pot arrencar per un altre lloc: prova la parella "
        "d'extrems següent.",
        "Cuando el contorno puede arrancar por otro sitio: prueba el "
        "siguiente par de extremos."),
    # the steps
    "Steps": ("Graons", "Peldaños"),
    "Height": ("Alçada", "Altura"),
    "Risers": ("Davanters", "Contrahuellas"),
    "Automatic": ("Automàtic", "Automático"),
    "Number of risers. Automatic: by the rule 2 risers + 1 going = 60–65 "
    "cm.": (
        "Nombre d'alçades. Automàtic: segons la regla 2 davanters + 1 "
        "petjada = 60–65 cm.",
        "Número de alturas. Automático: según la regla 2 contrahuellas + 1 "
        "huella = 60–65 cm."),
    "At the turns": ("Als girs", "En los giros"),
    "Landing": ("Replà", "Rellano"),
    "Winders": ("Compensats", "Compensados"),
    "A flat landing at each turn.": ("Un replà pla a cada gir.",
                                     "Un rellano plano en cada giro."),
    "Balanced winders: the narrowing is shared with the steps around the "
    "turn.": (
        "Graons compensats: l'estretament es reparteix amb els graons del "
        "voltant del gir.",
        "Peldaños compensados: el estrechamiento se reparte con los "
        "peldaños que rodean el giro."),
    "Follow the drawn steps": ("Segueix els graons dibuixats",
                               "Seguir los peldaños dibujados"),
    "Riser": ("Davanter", "Contrahuella"),
    "Going": ("Petjada", "Huella"),
    "2 risers + going": ("2 davanters + petjada", "2 contrahuellas + huella"),
    "{n} landing": ("{n} replà", "{n} rellano"),
    "{n} landings": ("{n} replans", "{n} rellanos"),
    "Outside the rule (60–65).": ("Fora de la regla (60–65).",
                                  "Fuera de la regla (60–65)."),
    "The drawn goings are uneven.": (
        "Les petjades dibuixades són desiguals.",
        "Las huellas dibujadas son desiguales."),
    "Over one turn: check the headroom.": (
        "Més d'una volta: comprova l'alçada lliure.",
        "Más de una vuelta: comprueba la altura libre."),
    "A solid stair over one turn would run into itself: use slab or "
    "plates.": (
        "Una escala massissa de més d'una volta es trepitja: fes llosa o "
        "platines.",
        "Una escalera maciza de más de una vuelta se pisa: usa losa o "
        "pletinas."),
    # building
    "Construction": ("Construcció", "Construcción"),
    "Solid": ("Massissa", "Maciza"),
    "Slab": ("Llosa", "Losa"),
    "Plates": ("Platines", "Pletinas"),
    "Everything under the steps, down to the floor.": (
        "Tot massís sota els graons, fins al terra.",
        "Todo macizo bajo los peldaños, hasta el suelo."),
    "A sloping concrete slab under the steps.": (
        "Llosa de formigó inclinada sota els graons.",
        "Losa de hormigón inclinada bajo los peldaños."),
    "Steel stringers at the sides, with treads between them.": (
        "Platines d'acer als costats, amb les petjades entre elles.",
        "Pletinas de acero a los lados, con las huellas entre ellas."),
    "Slab thickness": ("Gruix de llosa", "Grosor de losa"),
    "Measured square to the slope.": (
        "Mesurat perpendicular al pendent.",
        "Medido perpendicular a la pendiente."),
    "Closed risers": ("Amb davanter", "Con contrahuella"),
    "Stringers": ("Platines", "Pletinas"),
    "Both": ("Totes dues", "Las dos"),
    "Tread thickness": ("Gruix petjada", "Grosor huella"),
    "Plate thickness": ("Gruix xapa", "Grosor chapa"),
    "Thickness of the stringers and the riser plates.": (
        "Gruix de les platines i dels davanters.",
        "Grosor de las pletinas y las contrahuellas."),
    "Stringer height": ("Cantell platina", "Canto pletina"),
    "Measured upright; made taller when the steps need it.": (
        "Mesurat en vertical; creix si els graons ho necessiten.",
        "Medido en vertical; crece si los peldaños lo necesitan."),
    # the foot
    "Raise the stair": ("Aixeca l'escala", "Levantar la escalera"),
    "Click the title to fold or unfold this group": (
        "Clic al títol per plegar o desplegar el grup",
        "Clic en el título para plegar o desplegar el grupo"),
    # the tool
    "Select one group: the one with the plan.": (
        "Selecciona un sol grup: el de la planta.",
        "Selecciona un solo grupo: el de la planta."),
    "Click the group that holds the plan.": (
        "Clica el grup que té la planta.",
        "Haz clic en el grupo que tiene la planta."),
    "Click the group that holds the plan": (
        "Clica el grup que té la planta",
        "Haz clic en el grupo que tiene la planta"),
    "That is a stair already: click its plan.": (
        "Això ja és una escala: clica la seva planta.",
        "Eso ya es una escalera: haz clic en su planta."),
    "The plan is not flat: its lowest height is the floor.": (
        "La planta no és plana: la cota més baixa és el terra.",
        "La planta no es plana: la cota más baja es el suelo."),
    "Click a point above the plan, or type the height (Enter: the panel's).": (
        "Clica un punt per damunt de la planta o escriu l'alçada (Intro: la "
        "del tauler).",
        "Haz clic en un punto por encima de la planta o escribe la altura "
        "(Intro: la del panel)."),
    "Click the top point or type the height (Enter: the panel's) · Ctrl = "
    "reverse": (
        "Clica el punt d'arribada o escriu l'alçada (Intro: la del tauler) "
        "· Ctrl = inverteix",
        "Haz clic en el punto de llegada o escribe la altura (Intro: la del "
        "panel) · Ctrl = invertir"),
    "Type the risers (e.g. 16) or a height (e.g. 2.90) · Ctrl = reverse": (
        "Escriu els davanters (p. ex. 16) o una alçada (p. ex. 2,90) · Ctrl "
        "= inverteix",
        "Escribe las contrahuellas (p. ej. 16) o una altura (p. ej. 2,90) · "
        "Ctrl = invertir"),
    " · click an end = start there": (" · clic a un extrem = arrenca allà",
                                      " · clic en un extremo = arranca ahí"),
    " · click beside the line = that side": (
        " · clic al costat de la línia = per aquell costat",
        " · clic al lado de la línea = por ese lado"),
    " · Enter = done": (" · Intro = fet", " · Intro = listo"),
    "Climbs the other way": ("Puja en sentit contrari",
                             "Sube en sentido contrario"),
    "{n} risers": ("{n} davanters", "{n} contrahuellas"),
    # reading the plan
    "empty": ("El grup no té línies que facin una planta.",
              "El grupo no tiene líneas que formen una planta."),
    "open_outline": (
        "No he pogut seguir el contorn de la planta.",
        "No he podido seguir el contorno de la planta."),
    "touching_outline": (
        "El contorn es toca amb si mateix. En una escala en U, deixa un ull "
        "(encara que sigui d'1 cm) entre els dos trams.",
        "El contorno se toca consigo mismo. En una escalera en U, deja un "
        "ojo (aunque sea de 1 cm) entre los dos tramos."),
    "not_closed": (
        "El contorn no està tancat: uneix els dos extrems.",
        "El contorno no está cerrado: une los dos extremos."),
    "no_ends": (
        "No trobo els dos extrems del contorn (arrencada i arribada).",
        "No encuentro los dos extremos del contorno (arranque y llegada)."),
    "all_landing": (
        "Els trams són massa curts per fer replans: prova amb graons "
        "compensats.",
        "Los tramos son demasiado cortos para rellanos: prueba con "
        "peldaños compensados."),
    "no_height": ("Falta l'alçada.", "Falta la altura."),
    "narrow": ("La planta és massa petita per a una escala.",
               "La planta es demasiado pequeña para una escalera."),
    # the made groups
    "Solid stair": ("Escala massissa", "Escalera maciza"),
    "Concrete stair": ("Escala de formigó", "Escalera de hormigón"),
    "Steel stair": ("Escala de platines", "Escalera de pletinas"),
    "Body": ("Cos", "Cuerpo"),
    "Column": ("Pilar", "Pilar"),
    "Left stringer": ("Platina esquerra", "Pletina izquierda"),
    "Right stringer": ("Platina dreta", "Pletina derecha"),
    "Tread {n}": ("Petjada {n}", "Huella {n}"),
    "Riser {n}": ("Davanter {n}", "Contrahuella {n}"),
}

#: The keys that are codes, not English sentences.
_CODES = {
    "db_riser_max": "Riser of {v} cm (at most {m}).",
    "db_riser_min": "Riser of {v} cm (at least 13).",
    "db_going_min": "Going of {v} cm (at least {m}).",
    "db_relation": "2R + G = {v} cm (must be 54 to 70).",
    "db_curve_inner": "Curve: {v} cm of going 50 cm from the inner edge "
                      "(at least 28).",
    "db_curve_walking": "Curve: {v} cm of going where measured (at least "
                        "{m}).",
    "db_curve_narrow": "Curve: {v} cm at the narrow side (at least 5).",
    "db_curve_wide": "Curve: {v} cm at the wide side (at most 44).",
    "db_width": "Useful width {v} m (at least 0.80).",
    "db_uneven": "The straight flights' goings are not equal.",
    "db_mixed": "In the curve, the going on the axis is under the straight "
                "one.",
    "db_few_steps": "A flight of {v} steps (at least 3).",
    "db_flight_height": "A flight rises {v} m (at most {m}).",
    "db_landing": "Landing in line {v} m long (at least 1.00).",
    "db_no_treads": "There is no tread.",
    "empty": "The group has no lines that make a plan.",
    "open_outline": "The plan's contour could not be followed.",
    "touching_outline": "The contour touches itself. For a U stair, leave a "
                        "well (even 1 cm) between the two flights.",
    "no_ends": "The two ends of the contour (start and arrival) were not "
               "found.",
    "all_landing": "The flights are too short for landings: try winders.",
    "not_closed": "The contour is not closed: join its two ends.",
    "no_height": "The height is missing.",
    "narrow": "The plan is too small for a stair.",
}


def tr(text: str, **values) -> str:
    try:
        lang = str(LANGUAGE() or "en").lower()[:2]
    except Exception:  # noqa: BLE001
        lang = "en"
    entry = _TABLE.get(text)
    if entry is not None and lang in ("ca", "es"):
        text = entry[0 if lang == "ca" else 1]
    else:
        text = _CODES.get(text, text)
    return text.format(**values) if values else text
