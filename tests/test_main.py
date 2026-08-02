from src.main import prompt_user_profile


def test_prompt_user_profile_returns_expected_dict_for_valid_input(monkeypatch):
    answers = iter(["lofi", "chill", "0.6", "y"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    profile = prompt_user_profile()

    assert profile == {"genre": "lofi", "mood": "chill", "energy": 0.6, "likes_acoustic": True}


def test_prompt_user_profile_reprompts_on_invalid_energy(monkeypatch, capsys):
    answers = iter(["pop", "happy", "not-a-number", "0.8", "n"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    profile = prompt_user_profile()

    assert profile["energy"] == 0.8
    assert profile["likes_acoustic"] is False
    captured = capsys.readouterr()
    assert "Please enter a number" in captured.out


def test_prompt_user_profile_maps_acoustic_yes_and_variants_to_true(monkeypatch):
    for answer in ("y", "Y", "yes", "YES"):
        answers = iter(["pop", "happy", "0.5", answer])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
        assert prompt_user_profile()["likes_acoustic"] is True


def test_prompt_user_profile_maps_acoustic_no_and_variants_to_false(monkeypatch):
    for answer in ("n", "N", "no", "NO"):
        answers = iter(["pop", "happy", "0.5", answer])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
        assert prompt_user_profile()["likes_acoustic"] is False


def test_prompt_user_profile_maps_blank_acoustic_answer_to_none(monkeypatch):
    answers = iter(["pop", "happy", "0.5", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    assert prompt_user_profile()["likes_acoustic"] is None


def test_prompt_user_profile_allows_skipping_genre_and_mood(monkeypatch):
    answers = iter(["", "", "0.5", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))

    profile = prompt_user_profile()

    assert profile["genre"] == ""
    assert profile["mood"] == ""
