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
