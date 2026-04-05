import app as app_module


def test_flag_helper_parses_truthy_and_falsy_values():
    assert app_module._flag("true") is True
    assert app_module._flag("On") is True
    assert app_module._flag("0") is False
    assert app_module._flag(None, default=True) is True


def test_create_app_runs_optional_startup_hooks(monkeypatch):
    calls = {"init_db": 0, "create_tables": 0, "register_routes": 0, "load_seed_data": 0}

    monkeypatch.setattr(app_module, "init_db", lambda app: calls.__setitem__("init_db", calls["init_db"] + 1))
    monkeypatch.setattr(
        app_module,
        "create_tables",
        lambda safe=True: calls.__setitem__("create_tables", calls["create_tables"] + 1),
    )
    monkeypatch.setattr(
        app_module,
        "register_routes",
        lambda app: calls.__setitem__("register_routes", calls["register_routes"] + 1),
    )

    import app.seed.loader as loader_module

    monkeypatch.setattr(
        loader_module,
        "load_seed_data",
        lambda seed_directory, reset: calls.__setitem__("load_seed_data", calls["load_seed_data"] + 1),
    )

    created_app = app_module.create_app(
        {
            "TESTING": True,
            "AUTO_CREATE_TABLES": True,
            "AUTO_LOAD_SEED_DATA": True,
            "RESET_DATABASE_ON_STARTUP": True,
            "SEED_DIRECTORY": "app/seed",
        }
    )

    assert calls == {
        "init_db": 1,
        "create_tables": 1,
        "register_routes": 1,
        "load_seed_data": 1,
    }
    assert created_app.test_client().get("/health").get_json() == {"status": "ok"}
