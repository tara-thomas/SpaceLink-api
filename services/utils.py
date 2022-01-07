# 1027 convert hms / dms to degree
def hms2degree(ra_hms: list, dec_dms: list):
    len_ra = len(ra_hms)
    len_dec = len(dec_dms)
    if len_ra != 0:
        ra_symbol = -1 if float(ra_hms[0]) < 0 else 1
    if len_dec != 0:
        dec_symbol = -1 if float(dec_dms[0]) < 0 else 1

    # transfer the unit of ra/dec from hms/dms to degrees
    if len_ra == 1:
        ra_degree = float(ra_hms[0]) * 15
    elif len_ra == 2:
        ra_degree = (float(ra_hms[0]) + ra_symbol*float(ra_hms[1])/60) * 15
    else:
        ra_degree = (float(ra_hms[0]) + ra_symbol*float(ra_hms[1])/60 + ra_symbol*float(ra_hms[2])/3600) * 15

    if len_dec == 1:
        dec_degree = float(dec_dms[0])
    elif len_dec == 2:
        dec_degree = float(dec_dms[0]) + dec_symbol*float(dec_dms[1])/60
    else:
        dec_degree = float(dec_dms[0]) + dec_symbol*float(dec_dms[1])/60 + dec_symbol*float(dec_dms[2])/3600

    return ra_degree, dec_degree

# 0107 convet degree to hms / dms
def degree2hms(ra='', dec='', _round=False):
    RA, DEC, rs, ds = '', '', '', ''
    if dec:
        if str(dec)[0] == '-':
            ds, dec = '-', abs(dec)
        degree = int(dec)
        decM = abs(int((dec-degree) * 60))
        if _round:
            decS = round((abs((dec-degree) * 60)-decM) * 60, 2)
        else:
            decS = (abs((dec-degree)*60)-decM) * 60
        DEC = '{0}{1} {2} {3}'.format(ds, degree, decM, decS)

    if ra:
        if str(ra)[0] == '-':
            rs, ra = '-', abs(ra)
        raH = int(ra/15)
        raM = int(((ra/15)-raH) * 60)
        if _round:
            raS = round(((((ra/15)-raH) * 60)-raM) * 60, 2)
        else:
            raS = ((((ra/15)-raH) * 60)-raM) * 60
        RA = '{0}{1} {2} {3}'.format(rs, raH, raM, raS)

    if ra and dec:
        return (RA, DEC)
    else:
        return RA or DEC