"""Pareja vs amigo: what each kind unlocks, and who is allowed to decide it."""
from conftest import API, auth


def _befriend(client, a, b, kind="friend", accept_as=None):
    """a asks b; b accepts (optionally lowering the kind). Returns the id."""
    r = client.post(f"{API}/friends", json={"email": b.email, "kind": kind}, headers=auth(a))
    assert r.status_code == 201, r.text
    fid = r.json()["id"]
    body = {"status": "accepted"}
    if accept_as:
        body["kind"] = accept_as
    r = client.patch(f"{API}/friends/{fid}", json=body, headers=auth(b))
    assert r.status_code == 200, r.text
    return fid


# ── The default that used to hand out diary access ──────────────────────────

def test_new_friendship_grants_no_diary_access(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    fid = _befriend(client, ruben, silva)

    r = client.get(f"{API}/friends", headers=auth(ruben))
    f = next(x for x in r.json() if x["id"] == fid)
    assert f["can_add_food"] is False
    assert f["can_add_food_requester"] is False


def _log_for(client, actor, target, product):
    return client.post(
        f"{API}/diary",
        json={
            "product_id": product.id,
            "grams": 100,
            "consumed_at": "2026-07-17T12:00:00Z",
            "meal_type": "lunch",
            "only_for_user_id": target.id,
        },
        headers=auth(actor),
    )


def test_friend_cannot_write_in_my_diary_by_default(client, make_user, make_product):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    _befriend(client, ruben, silva)
    assert _log_for(client, silva, ruben, make_product()).status_code == 403


# ── Diary access is partner-only ────────────────────────────────────────────

def test_a_friend_cannot_be_granted_diary_access(client, make_user):
    """The flag can't even be switched on for a friend — it's a couple thing."""
    ruben, silva = make_user("Ruben"), make_user("Silva")
    fid = _befriend(client, ruben, silva)  # ruben=requester, silva=receiver

    r = client.patch(f"{API}/friends/{fid}", json={"can_add_food": True}, headers=auth(silva))
    assert r.status_code == 403
    assert "pareja" in r.json()["detail"]


def test_a_partner_can_be_granted_and_then_write(client, make_user, make_product):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    fid = _befriend(client, ruben, pilar, kind="partner")  # ruben=req, pilar=receiver
    product = make_product()

    # Nothing granted yet → ruben can't write in pilar's diary.
    assert _log_for(client, ruben, pilar, product).status_code == 403

    # Pilar (receiver) lets ruben write.
    r = client.patch(f"{API}/friends/{fid}", json={"can_add_food": True}, headers=auth(pilar))
    assert r.status_code == 200

    assert _log_for(client, ruben, pilar, product).status_code in (200, 201)


def test_demoting_a_partner_revokes_diary_access(client, make_user, make_product):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    fid = _befriend(client, ruben, pilar, kind="partner")
    product = make_product()
    client.patch(f"{API}/friends/{fid}", json={"can_add_food": True}, headers=auth(pilar))
    assert _log_for(client, ruben, pilar, product).status_code in (200, 201)

    # Break up → the diary flag is cleared and writing is refused again.
    r = client.patch(f"{API}/friends/{fid}", json={"kind": "friend"}, headers=auth(ruben))
    assert r.json()["can_add_food"] is False
    assert _log_for(client, ruben, pilar, product).status_code == 403


def test_partner_shows_in_the_also_log_picker_but_a_friend_does_not(client, make_user):
    ruben, pilar, silva = make_user("Ruben"), make_user("Pilar"), make_user("Silva")
    fp = _befriend(client, ruben, pilar, kind="partner")
    _befriend(client, ruben, silva)  # plain friend
    client.patch(f"{API}/friends/{fp}", json={"can_add_food": True}, headers=auth(pilar))

    names = {u["name"] for u in client.get(f"{API}/users", headers=auth(ruben)).json()}
    assert "Pilar" in names   # partner who granted access
    assert "Silva" not in names  # friend never qualifies


# ── One partner per user ────────────────────────────────────────────────────

def test_partner_request_is_accepted_as_partner(client, make_user):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    fid = _befriend(client, ruben, pilar, kind="partner")

    r = client.get(f"{API}/friends", headers=auth(ruben))
    assert next(x for x in r.json() if x["id"] == fid)["kind"] == "partner"


def test_second_partner_is_rejected(client, make_user):
    ruben, pilar, silva = make_user("Ruben"), make_user("Pilar"), make_user("Silva")
    _befriend(client, ruben, pilar, kind="partner")

    r = client.post(
        f"{API}/friends", json={"email": silva.email, "kind": "partner"}, headers=auth(ruben)
    )
    assert r.status_code == 409
    assert "Ya tienes pareja" in r.json()["detail"]


def test_second_partner_rejected_when_i_am_the_receiver(client, make_user):
    """The gap the partial unique indexes leave: requester of one, receiver of another."""
    ruben, pilar, silva = make_user("Ruben"), make_user("Pilar"), make_user("Silva")
    _befriend(client, ruben, pilar, kind="partner")  # ruben is requester here

    r = client.post(
        f"{API}/friends", json={"email": ruben.email, "kind": "partner"}, headers=auth(silva)
    )
    assert r.status_code == 409
    assert "ya tiene pareja" in r.json()["detail"]


def test_error_does_not_leak_who_someone_elses_partner_is(client, make_user):
    ruben, pilar, silva = make_user("Ruben"), make_user("Pilar"), make_user("Silva")
    _befriend(client, ruben, pilar, kind="partner")

    r = client.post(
        f"{API}/friends", json={"email": ruben.email, "kind": "partner"}, headers=auth(silva)
    )
    assert "Pilar" not in r.json()["detail"]


# ── Accepting can only lower the kind ───────────────────────────────────────

def test_partner_request_can_be_accepted_as_friend_only(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    fid = _befriend(client, ruben, silva, kind="partner", accept_as="friend")

    r = client.get(f"{API}/friends", headers=auth(ruben))
    assert next(x for x in r.json() if x["id"] == fid)["kind"] == "friend"


def test_cannot_accept_a_friend_request_as_partner(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    r = client.post(f"{API}/friends", json={"email": silva.email}, headers=auth(ruben))
    fid = r.json()["id"]

    r = client.patch(
        f"{API}/friends/{fid}", json={"status": "accepted", "kind": "partner"}, headers=auth(silva)
    )
    assert r.status_code == 400


# ── Promotion needs both sides ──────────────────────────────────────────────

def test_promotion_waits_for_the_other_side(client, make_user):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    fid = _befriend(client, ruben, pilar)

    client.patch(f"{API}/friends/{fid}", json={"kind": "partner"}, headers=auth(ruben))
    r = client.get(f"{API}/friends", headers=auth(ruben))
    f = next(x for x in r.json() if x["id"] == fid)
    assert f["kind"] == "friend", "one side asking is not enough"
    assert f["partner_proposed_by"] == ruben.id

    client.patch(f"{API}/friends/{fid}", json={"kind": "partner"}, headers=auth(pilar))
    r = client.get(f"{API}/friends", headers=auth(ruben))
    f = next(x for x in r.json() if x["id"] == fid)
    assert f["kind"] == "partner"
    assert f["partner_proposed_by"] is None


def test_asking_twice_does_not_promote_on_its_own(client, make_user):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    fid = _befriend(client, ruben, pilar)

    client.patch(f"{API}/friends/{fid}", json={"kind": "partner"}, headers=auth(ruben))
    client.patch(f"{API}/friends/{fid}", json={"kind": "partner"}, headers=auth(ruben))

    r = client.get(f"{API}/friends", headers=auth(ruben))
    assert next(x for x in r.json() if x["id"] == fid)["kind"] == "friend"


# ── The household is partners-only ──────────────────────────────────────────

def test_friends_cannot_share_a_household(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    fid = _befriend(client, ruben, silva)

    r = client.patch(
        f"{API}/friends/{fid}", json={"shared_inventory_requester": True}, headers=auth(ruben)
    )
    assert r.status_code == 403
    assert "pareja" in r.json()["detail"]


def test_partners_can_share_a_household(client, make_user):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    fid = _befriend(client, ruben, pilar, kind="partner")

    client.patch(
        f"{API}/friends/{fid}", json={"shared_inventory_requester": True}, headers=auth(ruben)
    )
    r = client.patch(
        f"{API}/friends/{fid}", json={"shared_inventory_receiver": True}, headers=auth(pilar)
    )
    assert r.status_code == 200
    assert r.json()["shared_inventory"] is True


def _share_household(client, fid, a, b):
    client.patch(f"{API}/friends/{fid}", json={"shared_inventory_requester": True}, headers=auth(a))
    client.patch(f"{API}/friends/{fid}", json={"shared_inventory_receiver": True}, headers=auth(b))


def _stock(client, user) -> float:
    r = client.get(f"{API}/inventory", headers=auth(user))
    return sum(i["quantity_g"] for i in r.json())


def test_splitting_a_household_does_not_duplicate_stock(client, make_user, make_product):
    """Merging used to copy personal rows in without deleting them, and the split
    added the shared stock back on top — so 500g became 1000g."""
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    fid = _befriend(client, ruben, pilar, kind="partner")
    product = make_product()

    client.post(
        f"{API}/inventory",
        json={"product_id": product.id, "quantity_base": 500, "unit": "g", "location": "pantry"},
        headers=auth(ruben),
    )
    assert _stock(client, ruben) == 500

    _share_household(client, fid, ruben, pilar)
    assert _stock(client, ruben) == 500, "merging should move the stock, not clone it"
    assert _stock(client, pilar) == 500, "both sides see the same household"

    client.patch(
        f"{API}/friends/{fid}", json={"shared_inventory_requester": False}, headers=auth(ruben)
    )
    assert _stock(client, ruben) == 500, "the split gave back more than went in"


def test_deleting_a_partner_gives_the_household_back(client, make_user, make_product):
    """shared_inventory_items cascades from friendships, so a naive delete used to
    wipe the shared stock instead of returning it."""
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    fid = _befriend(client, ruben, pilar, kind="partner")
    product = make_product()
    client.post(
        f"{API}/inventory",
        json={"product_id": product.id, "quantity_base": 500, "unit": "g", "location": "pantry"},
        headers=auth(ruben),
    )
    _share_household(client, fid, ruben, pilar)

    r = client.delete(f"{API}/friends/{fid}", headers=auth(ruben))
    assert r.status_code == 204
    assert _stock(client, ruben) == 500, "the stock vanished with the cascade"
    # And they really are no longer friends.
    assert all(x["id"] != fid for x in client.get(f"{API}/friends", headers=auth(ruben)).json())


def test_deleting_a_plain_friend_works(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    fid = _befriend(client, ruben, silva)

    r = client.delete(f"{API}/friends/{fid}", headers=auth(silva))
    assert r.status_code == 204
    assert client.get(f"{API}/friends", headers=auth(ruben)).json() == []


def test_demoting_a_partner_splits_the_household(client, make_user, make_product):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    fid = _befriend(client, ruben, pilar, kind="partner")
    product = make_product()
    client.post(
        f"{API}/inventory",
        json={"product_id": product.id, "quantity_base": 500, "unit": "g", "location": "pantry"},
        headers=auth(ruben),
    )
    _share_household(client, fid, ruben, pilar)

    # Breaking up is unilateral — pilar doesn't get asked.
    r = client.patch(f"{API}/friends/{fid}", json={"kind": "friend"}, headers=auth(ruben))
    assert r.status_code == 200
    assert r.json()["kind"] == "friend"
    assert r.json()["shared_inventory"] is False
    assert _stock(client, ruben) == 500, "ruben keeps what he put in"
