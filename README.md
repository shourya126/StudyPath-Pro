# StudyPath Pro
Independent EdTech / GTM portfolio MVP. Flask + SQLite + optional Gemini REST API.

## Windows PowerShell
Open this folder in VS Code. Run:
```
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:GEMINI_API_KEY="YOUR_KEY"
.\.venv\Scripts\python.exe app.py
```
API key optional; get one at https://aistudio.google.com/apikey. Never commit it. Set GEMINI_MODEL if default gemini-2.5-flash is unavailable. The AI sends study prompts to Google; avoid personal information. Offline mode is explicitly labeled. The quiz fallback is practice prompts, not AI-generated answers.
Open http://127.0.0.1:5000. Demo student: student@demo.local / student123; mentor: mentor@demo.local / mentor123. New database study.db is created beside app.py unless DB_PATH is set. To migrate previous data locally, stop old app and copy study.db into this folder. Do not use a demo database in production.

## Test
Register a new student, generate a plan, complete a milestone, ask AI, generate a quiz, save a reminder, submit a human mentor question, and use a separate incognito mentor login to answer. Register a second student through the referral link. Check mentor analytics and campaign generator. Run `python -m unittest discover -v` for automated offline tests. Live Gemini requires a real key. In-app reminders appear when visiting the dashboard; no background delivery. Campaigns are drafts, not auto-posted. Mentor role also sees aggregate growth metrics.

## Render deployment
Create a GitHub repository, upload project files (not database, keys or venv). Create a Python Web Service on Render. Build `pip install -r requirements.txt`, start `gunicorn app:app`. Set environment variables PRODUCTION=1, ENABLE_DEMO=0, SECRET_KEY (random long secret), MENTOR_PASSWORD (strong unique password), GEMINI_API_KEY (optional). Mentor email is mentor@demo.local. Use a fresh database. Attach a persistent disk at /var/data if your hosting plan supports it and set DB_PATH=/var/data/study.db. Without persistent storage data can disappear on redeploy. Run a single service instance with SQLite. Public launch needs additional abuse prevention, account verification, privacy policy and mentor onboarding. Do not advertise a live mentor service unless actual mentors are available.

## GTM
Audience: placement aspirants. Acquisition: content and referrals. Activation: first roadmap. Retention: milestones and reminders. North star: distinct users recording milestone completion in the last 7 days. Analytics count recorded events (not unique conversions, except North Star). No fabricated traction. Suggested experiment: test roadmap-first vs mentor-first social CTA using actual signups and activation. 
