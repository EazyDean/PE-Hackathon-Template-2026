from app.models import ShortUrl, UrlEvent, User
from app.seed.loader import load_seed_data


def test_load_seed_data_from_csv(app):
    load_seed_data(seed_directory=app.config["SEED_DIRECTORY"], reset=True)

    assert User.select().count() == 400
    assert ShortUrl.select().count() == 2000
    assert UrlEvent.select().count() == 3422


def test_load_seed_data_is_repeatable_without_duplicates(app):
    load_seed_data(seed_directory=app.config["SEED_DIRECTORY"], reset=True)
    load_seed_data(seed_directory=app.config["SEED_DIRECTORY"], reset=False)

    assert User.select().count() == 400
    assert ShortUrl.select().count() == 2000
    assert UrlEvent.select().count() == 3422


def test_load_seed_data_preserves_known_relationships(app):
    load_seed_data(seed_directory=app.config["SEED_DIRECTORY"], reset=True)

    user = User.get_by_id(1)
    short_url = ShortUrl.get_by_id(1)
    event = UrlEvent.get_by_id(1)

    assert user.email == "livelyvalley00@opswise.net"
    assert short_url.user_id == user.id
    assert short_url.short_code == "trXjXP"
    assert event.url_id == short_url.id
    assert event.user_id == user.id
    assert event.event_type == "created"
    assert event.details["short_code"] == short_url.short_code
    assert event.details["original_url"] == short_url.original_url
