import os, sqlite3, secrets, hmac, json, datetime
from ai import generate
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
app=Flask(__name__)
app.secret_key=os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.getenv('PRODUCTION')=='1')
if os.getenv('PRODUCTION')=='1' and (not os.getenv('SECRET_KEY') or not os.getenv('MENTOR_PASSWORD') or os.getenv('ENABLE_DEMO','1')!='0'):
 raise RuntimeError('Configure SECRET_KEY, MENTOR_PASSWORD and ENABLE_DEMO=0 for production')
DB=os.getenv('DB_PATH',os.path.join(os.path.dirname(__file__),'study.db'))
TRACKS={
'Python':['Variables, types and input/output','Conditions and loops','Strings, lists and dictionaries','Functions and error handling','Files and object-oriented programming','Build a command-line project'],
'DSA':['Arrays and complexity','Strings and hashing','Stacks and queues','Linked lists and recursion','Trees and graphs','Sorting, searching and interview practice'],
'AI & Machine Learning':['Python and NumPy','Statistics and linear algebra','Regression and classification','Model evaluation and validation','Neural networks and transformers','Build and evaluate an AI project'],
'Web Development':['HTML and accessible layouts','CSS and responsive design','JavaScript and DOM','APIs and asynchronous requests','Backend and databases','Deploy a full-stack application'],
'SQL & Analytics':['Tables and SELECT','Filtering and aggregation','Joins and subqueries','Window functions','Data cleaning and dashboards','Build a business analysis project']}
def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT); CREATE TABLE IF NOT EXISTS plans(user_id INTEGER PRIMARY KEY,track TEXT,level TEXT,hours INTEGER,weeks INTEGER); CREATE TABLE IF NOT EXISTS progress(user_id INTEGER,step INTEGER,PRIMARY KEY(user_id,step)); CREATE TABLE IF NOT EXISTS doubts(id INTEGER PRIMARY KEY,user_id INTEGER,topic TEXT,question TEXT,answer TEXT,mentor TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP);''')
  c.executescript("""CREATE TABLE IF NOT EXISTS ai_plans(user_id INTEGER PRIMARY KEY, steps TEXT); CREATE TABLE IF NOT EXISTS tools(user_id INTEGER, kind TEXT, result TEXT, source TEXT, PRIMARY KEY(user_id,kind)); CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, user_id INTEGER, kind TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE IF NOT EXISTS referrals(user_id INTEGER PRIMARY KEY, inviter INTEGER); CREATE TABLE IF NOT EXISTS reminders(user_id INTEGER PRIMARY KEY, day TEXT, message TEXT);""")
  for name,email,role,pw in [('Demo Student','student@demo.local','student',os.getenv('DEMO_STUDENT_PASSWORD','student123')),('Demo Mentor','mentor@demo.local','mentor',os.getenv('MENTOR_PASSWORD','mentor123'))]:
   if os.getenv('ENABLE_DEMO','1')=='1' or (role=='mentor' and os.getenv('MENTOR_PASSWORD')): c.execute('INSERT OR IGNORE INTO users(name,email,password,role) VALUES(?,?,?,?)',(name,email,generate_password_hash(pw),role))
init()
@app.before_request
def csrf():
 if 'csrf' not in session: session['csrf']=secrets.token_hex(24)
 if request.method=='POST' and not hmac.compare_digest(request.form.get('csrf',''),session['csrf']): abort(400)
def user():
 with db() as c: return c.execute('SELECT * FROM users WHERE id=?',(session.get('uid',0),)).fetchone()
@app.context_processor
def config_context(): return {'demo_enabled':os.getenv('ENABLE_DEMO','1')=='1'}
@app.route('/')
def index():
 u=user()
 if not u and request.args.get('ref','').isdigit(): session['ref']=int(request.args['ref'])
 if not u:return render_template('index.html',u=None,tracks=TRACKS)
 with db() as c:
  p=c.execute('SELECT * FROM plans WHERE user_id=?',(u['id'],)).fetchone(); done={r[0] for r in c.execute('SELECT step FROM progress WHERE user_id=?',(u['id'],))}
  q=c.execute('SELECT doubts.*,users.name FROM doubts JOIN users ON users.id=doubts.user_id '+('WHERE user_id=? ' if u['role']=='student' else '')+'ORDER BY doubts.id DESC', (u['id'],) if u['role']=='student' else ()).fetchall()
 with db() as c:
  ai_plan=c.execute('SELECT steps FROM ai_plans WHERE user_id=?',(u['id'],)).fetchone()
  results={r['kind']:r for r in c.execute('SELECT * FROM tools WHERE user_id=?',(u['id'],))}
  reminder=c.execute('SELECT * FROM reminders WHERE user_id=?',(u['id'],)).fetchone()
  referrals=c.execute('SELECT count(*) FROM referrals WHERE inviter=?',(u['id'],)).fetchone()[0]
  metrics={r[0]:r[1] for r in c.execute('SELECT kind,count(*) FROM events GROUP BY kind')} if u['role']=='mentor' else {}
  active=c.execute("SELECT count(DISTINCT user_id) FROM events WHERE kind='milestone' AND created>=datetime('now','-7 days')").fetchone()[0] if u['role']=='mentor' else 0
 steps=[]
 if p:
  topics=TRACKS[p['track']]; n=p['weeks'];
  for i in range(n):
   if n<=6: text=' / '.join(topics[i*6//n:(i+1)*6//n])
   else: text=topics[i*6//n]+(' — practice and revision' if i and i*6//n==(i-1)*6//n else '')
   steps.append(text)
 if ai_plan and p: steps=json.loads(ai_plan[0])
 return render_template('index.html',u=u,tracks=TRACKS,p=p,done=done,q=q,steps=steps,ai_plan=ai_plan,results=results,reminder=reminder,referrals=referrals,metrics=metrics,active=active,ai_enabled=bool(os.getenv('GEMINI_API_KEY')),today=datetime.date.today().isoformat())
@app.post('/auth')
def auth():
 email=request.form.get('email','').strip().lower(); pw=request.form.get('password',''); name=request.form.get('name','').strip()
 with db() as c:
  if request.form.get('mode')=='register':
   if not name or '@' not in email or len(pw)<8: return render_template('index.html',u=None,tracks=TRACKS,error='Enter a name, valid email and password of at least 8 characters.'),400
   try:c.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',(name,email,generate_password_hash(pw),'student'))
   except sqlite3.IntegrityError:return render_template('index.html',u=None,tracks=TRACKS,error='Account already exists.'),400
  u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
  if request.form.get('mode')=='register' and u:
   c.execute("INSERT INTO events(user_id,kind) VALUES(?,'signup')",(u['id'],))
   ref=session.get('ref')
   if ref and ref!=u['id'] and c.execute("SELECT 1 FROM users WHERE id=? AND role='student'",(ref,)).fetchone(): c.execute('INSERT OR IGNORE INTO referrals VALUES(?,?)',(u['id'],ref)); c.execute("INSERT INTO events(user_id,kind) VALUES(?,'referral_signup')",(u['id'],))
  if not u or not check_password_hash(u['password'],pw):return render_template('index.html',u=None,tracks=TRACKS,error='Incorrect email or password.'),401
 session.clear();session['uid']=u['id'];return redirect('/')
@app.post('/logout')
def logout():session.clear();return redirect('/')
def require(role):
 u=user()
 if not u or u['role']!=role:abort(403)
 return u
@app.post('/plan')
def plan():
 u=require('student'); track=request.form.get('track');level=request.form.get('level');hours=request.form.get('hours',type=int);weeks=request.form.get('weeks',type=int)
 if track not in TRACKS or level not in ['Beginner','Intermediate','Advanced'] or hours not in range(1,41) or weeks not in range(2,13):abort(400)
 with db() as c:c.execute('INSERT OR REPLACE INTO plans VALUES(?,?,?,?,?)',(u['id'],track,level,hours,weeks));c.execute('DELETE FROM progress WHERE user_id=?',(u['id'],))
 text=generate(f'Create a {weeks}-week {level} study roadmap for {track}, {hours} hours per week. Return only a JSON array of exactly {weeks} short strings, each with topic and exercise.')
 with db() as c:
  c.execute('DELETE FROM ai_plans WHERE user_id=?',(u['id'],))
  try:
   items=json.loads((text or '').removeprefix('```json').removesuffix('```').strip())
   if isinstance(items,list) and len(items)==weeks and all(isinstance(i,str) and 0<len(i)<=500 for i in items): c.execute('INSERT INTO ai_plans VALUES(?,?)',(u['id'],json.dumps(items)))
  except (ValueError,TypeError): pass
  c.execute("INSERT INTO events(user_id,kind) VALUES(?,'roadmap')",(u['id'],))
 return redirect('/#roadmap')
@app.post('/progress/<int:step>')
def progress(step):
 u=require('student')
 with db() as c:
  p=c.execute('SELECT weeks FROM plans WHERE user_id=?',(u['id'],)).fetchone()
  if not p or not 0<=step<p[0]:abort(400)
  if c.execute('SELECT 1 FROM progress WHERE user_id=? AND step=?',(u['id'],step)).fetchone():c.execute('DELETE FROM progress WHERE user_id=? AND step=?',(u['id'],step))
  else:
   c.execute('INSERT INTO progress VALUES(?,?)',(u['id'],step));c.execute("INSERT INTO events(user_id,kind) VALUES(?,'milestone')",(u['id'],))
 return redirect('/#roadmap')
@app.post('/ask')
def ask():
 u=require('student');topic=request.form.get('topic','');question=request.form.get('question','').strip()
 if topic not in TRACKS or not 5<=len(question)<=3000:abort(400)
 with db() as c:
  c.execute('INSERT INTO doubts(user_id,topic,question) VALUES(?,?,?)',(u['id'],topic,question));c.execute("INSERT INTO events(user_id,kind) VALUES(?,'mentor_question')",(u['id'],))
 return redirect('/#doubts')
@app.post('/answer/<int:id>')
def answer(id):
 u=require('mentor');a=request.form.get('answer','').strip()
 if not 2<=len(a)<=5000:abort(400)
 with db() as c:
  c.execute('UPDATE doubts SET answer=?,mentor=? WHERE id=?',(a,u['name'],id));c.execute("INSERT INTO events(user_id,kind) VALUES(?,'mentor_reply')",(u['id'],))
 return redirect('/#doubts')
@app.post('/tool/<kind>')
def tool(kind):
 role='mentor' if kind=='content' else 'student'; u=require(role)
 if kind not in ('doubt','quiz','content'): abort(404)
 topic=request.form.get('topic','Python'); question=request.form.get('question','').strip()[:1500]
 if topic not in TRACKS: abort(400)
 prompts={'doubt':f'Explain this educational doubt in simple language, with an example. If uncertain say so: {question}', 'quiz':f'Create five practice questions for {topic}, with answers and explanations at the end.', 'content':f'Create a 3-post organic social campaign for a student learning platform about {topic}. Include hook, caption, CTA and experiment metric. No invented claims.'}
 result=generate(prompts[kind]); source='Gemini' if result else 'Offline fallback'
 if not result:
  result={'doubt':'AI is unavailable. Use the mentor form below to submit your question to a human.', 'quiz':'Practice: '+ '\n'.join(f'{i+1}. Explain {t} and give an example.' for i,t in enumerate(TRACKS[topic][:5])), 'content':f'Post 1: What to learn first in {topic}? CTA: Build a free roadmap. Metric: clicks.\nPost 2: One study mistake to avoid. CTA: Share with a friend. Metric: shares.\nPost 3: Weekly study challenge. CTA: Complete a milestone. Metric: activations.'}[kind]
 with db() as c:
  c.execute('INSERT OR REPLACE INTO tools VALUES(?,?,?,?)',(u['id'],kind,result,source));c.execute('INSERT INTO events(user_id,kind) VALUES(?,?)',(u['id'],kind))
 return redirect('/#extras')
@app.post('/reminder')
def reminder():
 u=require('student'); day=request.form.get('day',''); message=request.form.get('message','').strip()[:300]
 try: datetime.date.fromisoformat(day)
 except ValueError: abort(400)
 if not message: abort(400)
 with db() as c:c.execute('INSERT OR REPLACE INTO reminders VALUES(?,?,?)',(u['id'],day,message))
 return redirect('/#extras')
if __name__=='__main__':app.run(debug=False,port=int(os.getenv('PORT',5000)))
