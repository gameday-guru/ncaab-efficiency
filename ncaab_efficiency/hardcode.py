west_example =  [
    [["106","195"],None,None,None],
    [None,None,None,None],
    [["276","102"],None,None,None],
    [None,None,None,None],
    [["335","45"],None,None,None],
    [None,None,None,None],
    [["3","167"],None,None,None],
    [None,None,None,None],
    [["114","216"],None,None,None],
    [None,[None,None],None,None],
    [["334","345"],None,None,None],
    [None,None,None,None],
    [["100","215"],None,None,None],
    [None,None,None,None],
    [["253","80"],None,None,None]
]


east_example = [
    [["94","304"],None,None,None],
    [None,[None,None],None,None],
    [["7","145"],None,None,None],
    [None,None,None,None],
    [["26","320"],None,None,None],
    [None,None,None,None],
    [["277","266"],None,None,None],
    [None,None,None,None],
    [["268","63"],None,None,None],
    [None,None,None,None],
    [["112","74"],None,None,None],
    [None,None,None,None],
    [["97","246"],None,None,None],
    [None,None,None,None],
    [["65","15"],None,None,None]
]


south_example = [[["275","292"],None,None,None],[None,None,None,None],[["92","107"],None,None,None],[None,None,None,None],[["212","129"],None,None,None],[None,None,None,None],[["22","283"],None,None,None],[None,None,None,None],[["61","33"],None,None,None],[None,None,None,None],[["108","119"],None,None,None],[None,None,None,None],[["280","220"],None,None,None],[None,None,None,None],[["247","160"],None,None,None]]


midwest_example = [
    [["6","154"],None,None,None],
    [None,[None,None],None,None],
    [["91","279"],None,None,None],
    [None,None,[None,None],None],
    [["23","211"],None,None,None],
    [None,None,None,None],
    [["93","178"],None,None,None],
    [None,None,None,None],
    [["110","28"],None,None,None],
    [None,None,None,None],
    [["59","42"],None,None,None],
    [None,None,None,None],
    [["270","101"],None,None,None],
    [None,None,None,None],
    [["109","261"],None,None,None]
]

full_example = [
    *west_example,
    *[[None]],
    *east_example,
    # *[[None]]
    *[[None]],
    # *[[None]]
    *south_example,
    *[[None]],
    *midwest_example
]