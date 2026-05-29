
from app1 import db, User

def create_user(email, password, role="user"):
    u = User(email=email); u.set_password(password); u.role = role
    db.session.add(u); db.session.commit()
    return u

def login(client, email, password):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)

def test_stats_requires_admin(client, db):
    # create staff and try
    create_user("staff@test.com", "pw", role="staff")
    rv = login(client, "staff@test.com", "pw")
    r = client.get("/stats", follow_redirects=True)
    assert b"Acc\u00e8s r\u00e9serv\u00e9 aux administrateurs" in r.data or b"Acc\xc3\xa8s r\xc3\xa9serv\xc3\xa9" in r.data

    # create admin and access
    create_user("admin@test.com", "pw", role="admin")
    rv = login(client, "admin@test.com", "pw")
    r = client.get("/stats")
    assert r.status_code == 200
