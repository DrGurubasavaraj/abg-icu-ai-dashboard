def interpret_abg(ph, pco2, hco3):
    if ph < 7.35 and pco2 > 45:
        return {"primary": "Respiratory Acidosis"}
    elif ph < 7.35 and hco3 < 22:
        return {"primary": "Metabolic Acidosis"}
    elif ph > 7.45 and pco2 < 35:
        return {"primary": "Respiratory Alkalosis"}
    elif ph > 7.45 and hco3 > 26:
        return {"primary": "Metabolic Alkalosis"}
    else:
        return {"primary": "Mixed/Compensated"}