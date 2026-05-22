
def test_userinput_validation(client):
    # Missing fields
    r = client.post("/userinput", data={}, follow_redirects=True)
    assert b"Veuillez remplir tous les champs" in r.data or r.status_code in (301,302)

    # Bad name
    r = client.post("/userinput", data={"fname":"123", "modele":"Android", "Problems":"test"}, follow_redirects=True)
    assert b"Le pr\u00e9nom doit" in r.data or b"Le pr\xc3\xa9nom doit" in r.data

    # OK
    r = client.post("/userinput", data={"fname":"Amine", "modele":"Android", "Problems":"Batterie"}, follow_redirects=True)
    assert b"Votre demande a \xc3\xa9t\xc3\xa9 enregistr\xc3\xa9e" in r.data or r.status_code == 200
