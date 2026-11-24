import os,tempfile,unittest
from pathlib import Path
folder=tempfile.TemporaryDirectory();os.environ['DB_PATH']=str(Path(folder.name)/'test.db');os.environ['ENABLE_DEMO']='1';os.environ.pop('GEMINI_API_KEY',None);os.environ.pop('PRODUCTION',None)
from app import app,db
class Flow(unittest.TestCase):
 def test_flow(self):
  c=app.test_client()
  def post(client,path,**data):
   client.get('/')
   with client.session_transaction() as s: data['csrf']=s['csrf']
   return client.post(path,data=data)
  self.assertEqual(post(c,'/auth',mode='register',name='Test',email='test@example.com',password='testing123').status_code,302)
  self.assertEqual(post(c,'/plan',track='Python',level='Beginner',hours=7,weeks=6).status_code,302)
  self.assertEqual(post(c,'/progress/0').status_code,302)
  self.assertEqual(post(c,'/tool/quiz',topic='Python').status_code,302)
  self.assertEqual(post(c,'/tool/doubt',question='What is Python?').status_code,302)
  self.assertEqual(post(c,'/reminder',day='2027-01-01',message='Practice').status_code,302)
  self.assertEqual(post(c,'/ask',topic='Python',question='What is a list?').status_code,302)
  self.assertEqual(c.get('/').status_code,200)
  m=app.test_client();self.assertEqual(post(m,'/auth',mode='login',email='mentor@demo.local',password='mentor123').status_code,302)
  with db() as conn: q=conn.execute('SELECT id FROM doubts').fetchone()[0]
  self.assertEqual(post(m,f'/answer/{q}',answer='A mutable sequence').status_code,302)
  self.assertIn(b'A mutable sequence',c.get('/').data)
  self.assertEqual(post(m,'/tool/content',topic='Python').status_code,302)
  self.assertEqual(m.get('/').status_code,200)
if __name__=='__main__':unittest.main()
