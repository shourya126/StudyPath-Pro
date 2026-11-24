import os,json,urllib.request

def generate(prompt):
    key=os.getenv('GEMINI_API_KEY')
    if not key: return None
    try:
        model=os.getenv('GEMINI_MODEL','gemini-2.5-flash')
        req=urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent',data=json.dumps({'contents':[{'parts':[{'text':prompt}]}]}).encode(),headers={'Content-Type':'application/json','x-goog-api-key':key})
        with urllib.request.urlopen(req,timeout=25) as r: data=json.load(r)
        return ''.join(p.get('text','') for p in data['candidates'][0]['content']['parts']).strip() or None
    except Exception: return None
