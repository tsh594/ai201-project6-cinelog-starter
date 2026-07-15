# PR Response Doc — CineLog Watchlist Feature

## AI Usage

During this project, I used AI tools in two specific ways:

1. **Codebase orientation:** I provided the content of `collection_service.py` and `test_collection.py` to an AI and asked for a summary of the deduplication pattern and test structure. This helped me understand how the existing code handles duplicate entries and how tests are organised. I used that knowledge to implement `add_to_watchlist` with a similar deduplication check and to structure `test_watchlist.py` in the same style.

2. **Commit message validation:** After rewriting my commit history, I asked the AI to check if my messages followed the Conventional Commits format and if each commit represented a single logical change. The AI flagged that my “fix: update UUID” commit was bundled with an unrelated whitespace change, so I split them into separate commits. The final history (shown below) reflects that feedback.

I did **not** use AI to write any code or design decisions for Comments 4 and 5; those arguments are my own, rooted in CineLog’s specific user context.

---

## Comment 1 — Rename

**What I did:**  
I renamed `save_to_watchlist()` to `add_to_watchlist()` in `services/watchlist_service.py` and updated its call site in `routes/watchlist.py` (the `add_film` endpoint). I also updated any references in the docstring and comments.

**How I verified:**  
I used `grep -r "save_to_watchlist" --include="*.py" .` from the project root to find all occurrences. The search returned only the function definition and the one call in the route file. After renaming, I ran the test suite (`pytest tests/ -v`) to confirm everything still passes, ensuring I didn’t miss any references (if I had, tests would have failed with `NameError`).

---

## Comment 2 — Deduplication

**What I did:**  
I added a deduplication check inside `add_to_watchlist()` before creating a new entry. The function now queries the database for an existing `WatchlistEntry` with the same `user_id` and `film_id`. If found, it raises `AlreadyInWatchlistError` with a descriptive message. This mirrors exactly what `add_to_collection()` does in `collection_service.py`.

**How I verified:**  
I wrote a test (`test_add_to_watchlist_duplicate_raises`) that calls `add_to_watchlist` twice with the same user and film, and asserts that the second call raises `AlreadyInWatchlistError`. I also confirmed that only one entry remains in the database. The test passes.

**Reference to existing pattern:**  
The deduplication logic is a direct copy of the pattern from `add_to_collection()`: check for an existing entry using `filter_by(user_id=..., film_id=...)`, raise a custom exception if it exists, otherwise create the new entry. This ensures consistency across the codebase.

---

## Comment 3 — Missing test

**What I did:**  
I created `tests/test_watchlist.py` and added a test called `test_add_to_watchlist_nonexistent_film_raises`. It uses the same fixture (`sample_user`) and a fake UUID to call `add_to_watchlist`, and asserts that `FilmNotFoundError` is raised.

**How I verified:**  
The test passes when run with `pytest tests/test_watchlist.py -v`. I modelled it after `test_add_to_collection_nonexistent_film_raises` in `test_collection.py`, using the same structure: a fixture for the user, a fake film ID, and a `pytest.raises` check.

---

## Comment 4 — Default visibility

**My position:**  
The default visibility for watchlist entries should be **public (True)**.

**Reasoning:**  
CineLog is a community film tracking app, not a private journal. The core value proposition is discovery and sharing — users add films to their watchlist to show others what they’re interested in, spark conversations, and get recommendations. In a social context, “public by default” encourages engagement: other users can see what’s trending in their network, which drives more interaction and makes the platform more vibrant. Additionally, the existing `CollectionEntry` model does not have a visibility field, meaning it is implicitly public (since the collection endpoint is publicly accessible). Aligning the watchlist with this implicit default keeps the UX consistent and reduces user confusion.

**Tradeoff acknowledged:**  
The alternative — private by default — would prioritise user privacy and control, which is valuable for users who want to plan their viewing privately before making a decision. However, CineLog’s design leans toward social discovery; if users want privacy, they can explicitly set `public=False` when adding a film. The tradeoff is that some users might be surprised that their watchlist is public, but we can mitigate this with clear UI labels and a one-time prompt explaining the default. In this context, encouraging community activity outweighs the privacy risk.

---

## Comment 5 — Sort order

**My position:**  
The watchlist should be sorted by **date added descending (newest first)**.

**Reasoning:**  
A watchlist is dynamic — users add films over time, and their immediate concern is usually “what did I just add?” when planning what to watch next. Sorting by newest first puts the most recent additions at the top, reducing scroll time and matching the mental model of a to-do list. This is also consistent with how the collection feature works (`get_collection()` already sorts by `date_added.desc()`). Users familiar with the collection interface will expect the watchlist to behave similarly, and maintaining consistent behaviour reduces cognitive load.

**Engagement with the maintainer's point:**  
The maintainer (@dev-lead) argued that “Most users want to see what they added recently.” I agree with this observation, and I’ve built the sort order around it. While alphabetical order is useful for finding a specific film, it doesn’t serve the primary use case of “what’s next?” — the watchlist is a queue, not a catalogue. Users can always use the film search endpoint (`/films/`) to find a particular film if needed. By adopting the maintainer’s preferred order, we also align with the existing collection behaviour, making the feature feel more integrated.

---

## Comment 6 — Rebase

**What conflicted:**  
While my `feature/watchlist` branch was open, the `main` branch was refactored to change all film IDs from integers to UUIDs (commit `refactor: migrate film IDs from integer to UUID`). My watchlist code initially used integer IDs for the `film_id` column in `WatchlistEntry`, and the foreign key constraint expected integer. When I rebased, Git flagged conflicts in the migration scripts and in the model definition because the types didn’t match.

**How I resolved it:**  
I edited `models.py` to change the `film_id` column from `db.Integer` to `db.String(36)`, and updated the foreign key reference accordingly. I also revised `add_to_watchlist` to expect a string UUID and removed any integer conversions. After resolving the conflict, I ran `git add .` and `git rebase --continue`. I then ran the full test suite to ensure the UUID changes didn’t break any other parts of the watchlist feature.

**How I verified no conflict remains:**  
I ran `git log --oneline --graph` to confirm that my branch is now directly on top of `origin/main` with no merge commits. The final commit that addresses this conflict is `fix: update watchlist film_id to UUID after main refactor`. All tests pass, and I manually tested the endpoints with real UUIDs.

---

## PR Description

**What the watchlist feature does:**  
The watchlist allows users to curate a list of films they plan to watch. They can add films (with an optional public/private flag), view their list sorted by most recently added, remove films, and toggle visibility of individual entries. This is separate from the collection (already watched), giving users a place to track their future viewing plans.

**Design decisions:**
- **Default visibility:** `public=True` – encourages social discovery and aligns with CineLog’s community focus.
- **Sort order:** `date_added desc` – prioritises recent additions, matching user expectations and the behaviour of the collection feature.

**Manual testing instructions:**
1. Ensure you have a user and at least one film in the database (you can seed via the Flask shell).
2. Start the app (`python app.py`) and use `curl` or any REST client.
3. **Add a film to watchlist:**

POST /watchlist/<user_id>/add
{ "film_id": "<UUID>", "public": false } (public optional)

Expected: 201 Created with the entry details.
4. **View watchlist:**

GET /watchlist/<user_id>

Expected: JSON array of films with `date_added` and `public` fields, newest first.
5. **Remove a film:**

DELETE /watchlist/<user_id>/remove
{ "film_id": "<UUID>" }

Expected: 200 OK with a success message.
6. **Toggle visibility:**

PATCH /watchlist/<user_id>/<film_id>/visibility
{ "public": false }

Expected: 200 OK with the updated entry.
7. Test error cases: duplicate add (409 Conflict), nonexistent film (404 Not Found), remove not-in-list (404 Not Found).

---

## Commit History

Below is the final commit history after rebasing and rewriting with `git rebase -i`. All commits follow Conventional Commits, are single-logical-change, and there are no merge commits.

$ git log --oneline origin/main..HEAD
66812b1 (HEAD -> feature/watchlist, origin/feature/watchlist) docs: add PR response doc and update README
ffa29db fix: update watchlist film_id to UUID after main refactor
72fc6fc fix: rename save_to_watchlist to add_to_watchlist
3766983 test: add watchlist test suite
d66864f feat: add watchlist service and routes
436efd3 feat: add watchlist model and database`

*(A screenshot of this output is included as `commit_history.png` in the repo.)*

---

## Stretch Features

### remove_from_watchlist()
I implemented `remove_from_watchlist()` in `services/watchlist_service.py`, following the same pattern as `remove_from_collection()`. It queries for an existing `WatchlistEntry`; if none exists, it raises `NotInWatchlistError`; otherwise, it deletes the entry. This is consistent with the project's error‑handling approach. I also added `test_remove_from_watchlist_removes_entry` and `test_remove_from_watchlist_not_in_list_raises` to cover both the happy path and the error case.

### Second Test (public flag default)
I added `test_add_to_watchlist_with_public_false` to verify that the `public` parameter is respected and that the default is `True`. I chose this edge case because the visibility default is a critical design decision; testing it ensures that the default is correctly applied and that a caller can override it.

### Visibility Toggle Endpoint
I added a `PATCH /watchlist/<user_id>/<film_id>/visibility` endpoint that accepts a JSON body with a `public` boolean. The endpoint calls `update_watchlist_visibility()`, which updates the `public` field of the entry. The default for new entries is `True` (public), and callers can change it at any time by sending `{ "public": false }` or `{ "public": true }`.

**End of PR Response Doc**

