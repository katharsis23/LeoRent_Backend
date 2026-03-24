from pytest import mark


def test_healthcheck(client):
    response = client.get("/healthcheck/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Server is running"}


@mark.skip("""
    You can toggle this integration test for local development,
    but dont enable it in CI/CD
    """)
def test_healthcheck_db(client):
    response = client.get("/healthcheck/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Database is running"}
