"""
tests/test_watchlist.py — CineLog

Tests for the watchlist service.
Follows the patterns from test_collection.py.
"""

import pytest
from app import create_app   # <-- removed db import
from database import db      # <-- added import from database
from models import User, Film, WatchlistEntry
from services.watchlist_service import (
    add_to_watchlist,
    remove_from_watchlist,
    get_watchlist,
    update_watchlist_visibility,
    FilmNotFoundError,
    AlreadyInWatchlistError,
    NotInWatchlistError,
)


@pytest.fixture
def app():
    """Create an isolated test app with an in-memory database."""
    app = create_app(config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def sample_user(app):
    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_film(app):
    with app.app_context():
        film = Film(title="Dune", year=2021, genre="Sci-Fi")
        db.session.add(film)
        db.session.commit()
        return film.id


# ── Basic add ───────────────────────────────────────────────────────────────

def test_add_to_watchlist_creates_entry(app, sample_user, sample_film):
    with app.app_context():
        entry = add_to_watchlist(user_id=sample_user, film_id=sample_film)
        assert entry is not None
        assert entry.user_id == sample_user
        assert entry.film_id == sample_film
        assert entry.public is True  # default

        in_db = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).first()
        assert in_db is not None


def test_add_to_watchlist_with_public_false(app, sample_user, sample_film):
    with app.app_context():
        entry = add_to_watchlist(user_id=sample_user, film_id=sample_film, public=False)
        assert entry.public is False


# ── Deduplication ────────────────────────────────────────────────────────────

def test_add_to_watchlist_duplicate_raises(app, sample_user, sample_film):
    with app.app_context():
        add_to_watchlist(user_id=sample_user, film_id=sample_film)
        with pytest.raises(AlreadyInWatchlistError):
            add_to_watchlist(user_id=sample_user, film_id=sample_film)

        count = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).count()
        assert count == 1


# ── Nonexistent film (required by Comment 3) ──────────────────────────────

def test_add_to_watchlist_nonexistent_film_raises(app, sample_user):
    with app.app_context():
        fake_film_id = "00000000-0000-0000-0000-000000000000"
        with pytest.raises(FilmNotFoundError):
            add_to_watchlist(user_id=sample_user, film_id=fake_film_id)


# ── get_watchlist sort order ──────────────────────────────────────────────

def test_get_watchlist_returns_newest_first(app, sample_user):
    with app.app_context():
        from datetime import datetime, timezone, timedelta

        film_a = Film(title="Arrival", year=2016, genre="Sci-Fi")
        film_b = Film(title="Interstellar", year=2014, genre="Sci-Fi")
        db.session.add_all([film_a, film_b])
        db.session.commit()

        earlier = datetime.now(timezone.utc) - timedelta(days=5)
        later = datetime.now(timezone.utc)

        entry_a = WatchlistEntry(user_id=sample_user, film_id=film_a.id, date_added=earlier)
        entry_b = WatchlistEntry(user_id=sample_user, film_id=film_b.id, date_added=later)
        db.session.add_all([entry_a, entry_b])
        db.session.commit()

        watchlist = get_watchlist(sample_user)
        titles = [f["title"] for f in watchlist]
        assert titles[0] == "Interstellar"
        assert titles[1] == "Arrival"


# ── Remove from watchlist ──────────────────────────────────────────────────

def test_remove_from_watchlist_removes_entry(app, sample_user, sample_film):
    with app.app_context():
        add_to_watchlist(user_id=sample_user, film_id=sample_film)
        result = remove_from_watchlist(user_id=sample_user, film_id=sample_film)
        assert result is True

        entry = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).first()
        assert entry is None


def test_remove_from_watchlist_not_in_list_raises(app, sample_user):
    with app.app_context():
        fake_film_id = "00000000-0000-0000-0000-000000000000"
        with pytest.raises(NotInWatchlistError):
            remove_from_watchlist(user_id=sample_user, film_id=fake_film_id)


# ── Visibility toggle (stretch) ────────────────────────────────────────────

def test_update_watchlist_visibility(app, sample_user, sample_film):
    with app.app_context():
        entry = add_to_watchlist(user_id=sample_user, film_id=sample_film, public=True)
        assert entry.public is True

        updated = update_watchlist_visibility(user_id=sample_user, film_id=sample_film, public=False)
        assert updated.public is False

        # Verify in DB
        in_db = WatchlistEntry.query.filter_by(
            user_id=sample_user, film_id=sample_film
        ).first()
        assert in_db.public is False


def test_update_watchlist_visibility_not_in_list_raises(app, sample_user):
    with app.app_context():
        fake_film_id = "00000000-0000-0000-0000-000000000000"
        with pytest.raises(NotInWatchlistError):
            update_watchlist_visibility(user_id=sample_user, film_id=fake_film_id, public=False)