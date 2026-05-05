import os, sqlite3, uuid, shutil
from flask import Flask, request, jsonify, redirect, session, send_from_directory
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'photowall-secret-2024')

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DB_PATH      = os.path.join(BASE_DIR, 'photos.db')
ALLOWED_EXT  = {'png','jpg','jpeg','gif','webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ── DB helpers ────────────────────────────────────────────
def get_db():
    db = sqlite3.connect(DB_PATH); db.row_factory = sqlite3.Row; return db

def init_db():
    with get_db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS photos(
            id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL,
            original_name TEXT, status TEXT DEFAULT 'pending',
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        db.execute('''CREATE TABLE IF NOT EXISTS config(key TEXT PRIMARY KEY, value TEXT)''')
        defaults = [
            ('event_name',  os.environ.get('EVENT_NAME',  'Photo Wall')),
            ('mod_password',os.environ.get('MOD_PASSWORD','admin123')),
            ('theme',       os.environ.get('EVENT_THEME', 'fiesta')),
            ('font',        os.environ.get('EVENT_FONT',  'grande')),
        ]
        for k,v in defaults:
            db.execute('INSERT OR IGNORE INTO config(key,value) VALUES(?,?)',(k,v))
        db.commit()

def gc(key, default=''):
    try:
        with get_db() as db:
            r = db.execute('SELECT value FROM config WHERE key=?',(key,)).fetchone()
            return r['value'] if r else default
    except: return default

def sc(key, value):
    with get_db() as db:
        db.execute('INSERT OR REPLACE INTO config(key,value) VALUES(?,?)',(key,value)); db.commit()

def allowed(f): return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED_EXT

def login_required(f):
    @wraps(f)
    def d(*a,**k):
        if not session.get('logged_in'): return redirect('/moderador/login')
        return f(*a,**k)
    return d

init_db()

# ══════════════════════════════════════════════════════════
# THEME + FONT DEFINITIONS
# ══════════════════════════════════════════════════════════
FONTS = {
    'elegante':   ('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600&display=swap', 'Cormorant Garamond, serif'),
    'divertida':  ('https://fonts.googleapis.com/css2?family=Fredoka+One&display=swap', 'Fredoka One, cursive'),
    'minimalista':('https://fonts.googleapis.com/css2?family=Inter:wght@200;400;700&display=swap', 'Inter, sans-serif'),
    'grande':     ('https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap', 'Bebas Neue, sans-serif'),
    'calida':     ('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&display=swap', 'Playfair Display, serif'),
}

def get_font(key):
    return FONTS.get(key, FONTS['grande'])

# Each theme returns (css_vars, bg_css, particles_js, overlay_html)
def get_theme_parts(theme):

    if theme == 'boda':
        css_vars = '--c1:#D4AF37;--c2:#f5f0e8;--c3:#b8860b;--dark:#1a1510;'
        bg_css = '''
body{background:#1a1510}
body::before{content:'';position:fixed;inset:0;
  background:radial-gradient(ellipse at 30% 40%,rgba(212,175,55,.18) 0%,transparent 55%),
             radial-gradient(ellipse at 70% 60%,rgba(184,134,11,.12) 0%,transparent 55%);
  pointer-events:none}'''
        particles_js = '''
function makeParticles(){
  const c=document.getElementById('pts');if(!c)return;
  const items=['💍','✨','🌸','💐','⭐','🕊️'];
  for(let i=0;i<22;i++){
    const p=document.createElement('div');
    p.style.cssText=`position:absolute;font-size:${14+Math.random()*18}px;left:${Math.random()*100}%;
      animation:riseUp ${10+Math.random()*14}s linear ${Math.random()*12}s infinite;opacity:0;`;
    p.textContent=items[Math.floor(Math.random()*items.length)];
    c.appendChild(p);
  }
}'''
        overlay_html = '''
<svg style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;opacity:.07;z-index:0" viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice">
  <text x="400" y="280" text-anchor="middle" font-size="320" fill="#D4AF37" font-family="serif">💍</text>
</svg>'''

    elif theme == 'cumple':
        css_vars = '--c1:#FF6B6B;--c2:#FFE66D;--c3:#4ECDC4;--dark:#0d0d1a;'
        bg_css = '''
body{background:#0d0d1a}
body::before{content:'';position:fixed;inset:0;
  background:radial-gradient(ellipse at 20% 50%,rgba(255,107,107,.2) 0%,transparent 50%),
             radial-gradient(ellipse at 80% 30%,rgba(78,205,196,.15) 0%,transparent 50%),
             radial-gradient(ellipse at 50% 80%,rgba(255,230,109,.1) 0%,transparent 50%);
  pointer-events:none}'''
        particles_js = '''
function makeParticles(){
  const c=document.getElementById('pts');if(!c)return;
  const items=['🎂','🎉','🎈','🥳','⭐','🎁','✨','🎊','😄'];
  const colors=['#FF6B6B','#FFE66D','#4ECDC4','#FF9F43','#A29BFE'];
  for(let i=0;i<35;i++){
    const p=document.createElement('div');
    const isEmoji=Math.random()>.45;
    if(isEmoji){
      p.style.cssText=`position:absolute;font-size:${12+Math.random()*20}px;left:${Math.random()*100}%;
        animation:riseUp ${7+Math.random()*10}s linear ${Math.random()*8}s infinite;opacity:0;`;
      p.textContent=items[Math.floor(Math.random()*items.length)];
    } else {
      const s=4+Math.random()*8;
      p.style.cssText=`position:absolute;width:${s}px;height:${s}px;border-radius:2px;
        background:${colors[Math.floor(Math.random()*colors.length)]};
        left:${Math.random()*100}%;
        animation:riseUp ${6+Math.random()*9}s linear ${Math.random()*8}s infinite;opacity:0;`;
    }
    c.appendChild(p);
  }
}'''
        overlay_html = ''

    elif theme == 'quince':
        css_vars = '--c1:#C084FC;--c2:#F472B6;--c3:#818CF8;--dark:#0d0a1a;'
        bg_css = '''
body{background:#0d0a1a}
body::before{content:'';position:fixed;inset:0;
  background:radial-gradient(ellipse at 25% 45%,rgba(192,132,252,.25) 0%,transparent 55%),
             radial-gradient(ellipse at 75% 55%,rgba(244,114,182,.2) 0%,transparent 55%),
             radial-gradient(ellipse at 50% 20%,rgba(129,140,248,.15) 0%,transparent 50%);
  pointer-events:none}'''
        particles_js = '''
function makeParticles(){
  const c=document.getElementById('pts');if(!c)return;
  const items=['⭐','✨','💫','🌟','💜','🌸','👑'];
  for(let i=0;i<40;i++){
    const p=document.createElement('div');
    const isEmoji=Math.random()>.4;
    if(isEmoji){
      p.style.cssText=`position:absolute;font-size:${10+Math.random()*16}px;left:${Math.random()*100}%;
        animation:riseUp ${8+Math.random()*12}s linear ${Math.random()*10}s infinite;opacity:0;`;
      p.textContent=items[Math.floor(Math.random()*items.length)];
    } else {
      const s=2+Math.random()*5;
      p.style.cssText=`position:absolute;width:${s}px;height:${s}px;border-radius:50%;
        background:${['#C084FC','#F472B6','#818CF8','#fff'][Math.floor(Math.random()*4)]};
        left:${Math.random()*100}%;
        animation:riseUp ${8+Math.random()*12}s linear ${Math.random()*10}s infinite;opacity:0;`;
    }
    c.appendChild(p);
  }
}'''
        overlay_html = '''
<svg style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;opacity:.06;z-index:0" viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice">
  <text x="400" y="310" text-anchor="middle" font-size="380" fill="#C084FC" font-family="serif">15</text>
</svg>'''

    elif theme == 'empresarial':
        css_vars = '--c1:#38BDF8;--c2:#e2e8f0;--c3:#0EA5E9;--dark:#020817;'
        bg_css = '''
body{background:#020817}
body::before{content:'';position:fixed;inset:0;
  background:radial-gradient(ellipse at 20% 50%,rgba(56,189,248,.12) 0%,transparent 55%),
             radial-gradient(ellipse at 80% 30%,rgba(14,165,233,.1) 0%,transparent 55%);
  pointer-events:none}'''
        particles_js = '''
function makeParticles(){
  const c=document.getElementById('pts');if(!c)return;
  const colors=['#38BDF8','#0EA5E9','#7DD3FC','rgba(255,255,255,.4)'];
  for(let i=0;i<20;i++){
    const p=document.createElement('div');
    const s=2+Math.random()*5;
    p.style.cssText=`position:absolute;width:${s}px;height:${s}px;border-radius:50%;
      background:${colors[Math.floor(Math.random()*colors.length)]};
      left:${Math.random()*100}%;
      animation:riseUp ${10+Math.random()*14}s linear ${Math.random()*12}s infinite;opacity:0;`;
    c.appendChild(p);
  }
}'''
        overlay_html = '''
<svg style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;opacity:.04;z-index:0" viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice">
  <line x1="0" y1="250" x2="800" y2="250" stroke="#38BDF8" stroke-width="1"/>
  <line x1="400" y1="0" x2="400" y2="500" stroke="#38BDF8" stroke-width="1"/>
  <circle cx="400" cy="250" r="180" stroke="#38BDF8" stroke-width="1" fill="none"/>
  <circle cx="400" cy="250" r="100" stroke="#38BDF8" stroke-width="1" fill="none"/>
</svg>'''

    else:  # fiesta (default)
        css_vars = '--c1:#FF3CAC;--c2:#784BA0;--c3:#2B86C5;--dark:#0a0a0f;'
        bg_css = '''
body{background:#0a0a0f}
body::before{content:'';position:fixed;inset:0;
  background:radial-gradient(ellipse at 20% 50%,rgba(120,75,160,.3) 0%,transparent 50%),
             radial-gradient(ellipse at 80% 20%,rgba(255,60,172,.2) 0%,transparent 50%),
             radial-gradient(ellipse at 60% 80%,rgba(43,134,197,.2) 0%,transparent 50%);
  animation:bgpulse 12s ease-in-out infinite alternate;pointer-events:none}
@keyframes bgpulse{0%{opacity:.8}100%{opacity:1;filter:hue-rotate(25deg)}}'''
        particles_js = '''
function makeParticles(){
  const c=document.getElementById('pts');if(!c)return;
  const colors=['#FF3CAC','#784BA0','#2B86C5','#FFD700'];
  for(let i=0;i<25;i++){
    const p=document.createElement('div');
    const s=2+Math.random()*5;
    p.style.cssText=`position:absolute;width:${s}px;height:${s}px;border-radius:50%;
      background:${colors[Math.floor(Math.random()*colors.length)]};
      left:${Math.random()*100}%;
      animation:riseUp ${8+Math.random()*12}s linear ${Math.random()*10}s infinite;opacity:0;`;
    c.appendChild(p);
  }
}'''
        overlay_html = ''

    return css_vars, bg_css, particles_js, overlay_html

# ══════════════════════════════════════════════════════════
# UPLOAD PAGE
# ══════════════════════════════════════════════════════════
@app.route('/')
@app.route('/upload')
def upload_page():
    event  = gc('event_name','Photo Wall')
    theme  = gc('theme','fiesta')
    font_k = gc('font','grande')
    font_url, font_family = get_font(font_k)
    css_vars, bg_css, particles_js, _ = get_theme_parts(theme)

    # pick gradient colors from theme
    grad = {'boda':'#D4AF37,#f5f0e8','cumple':'#FF6B6B,#FFE66D',
            'quince':'#C084FC,#F472B6','empresarial':'#38BDF8,#e2e8f0',
            'fiesta':'#FF3CAC,#FFD700'}.get(theme,'#FF3CAC,#FFD700')
    btn_grad = {'boda':'#D4AF37,#b8860b','cumple':'#FF6B6B,#4ECDC4',
                'quince':'#C084FC,#818CF8','empresarial':'#38BDF8,#0EA5E9',
                'fiesta':'#FF3CAC,#784BA0'}.get(theme,'#FF3CAC,#784BA0')

    return f'''<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>📸 Photo Wall</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{{css_vars}}}
{bg_css}
body{{font-family:'DM Sans',sans-serif;min-height:100dvh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;overflow-x:hidden}}
.pts{{position:fixed;inset:0;pointer-events:none;z-index:0}}
.wrap{{position:relative;z-index:1;width:100%;max-width:460px;text-align:center}}
.logo{{font-family:Bebas Neue,sans-serif;font-size:clamp(1.8rem,9vw,3.2rem);background:linear-gradient(135deg,{grad});-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1.15;margin-bottom:4px}}
.sub{{color:rgba(255,255,255,.45);font-size:.82rem;letter-spacing:.18em;text-transform:uppercase;margin-bottom:28px}}
.card{{background:rgba(255,255,255,.05);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.1);border-radius:22px;padding:26px}}
.drop{{border:2px dashed rgba(255,255,255,.2);border-radius:14px;padding:34px 16px;cursor:pointer;transition:all .3s;position:relative;overflow:hidden;margin-bottom:14px}}
.drop:hover,.drop.over{{border-color:var(--c1);background:rgba(255,255,255,.04);transform:scale(1.01)}}
.drop input{{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}}
.drop-icon{{font-size:2.6rem;margin-bottom:8px;display:block}}
.drop-txt{{color:rgba(255,255,255,.65);font-size:.92rem}}
.drop-hint{{color:rgba(255,255,255,.25);font-size:.72rem;margin-top:4px}}
.prev-wrap{{display:none;margin-bottom:14px;position:relative}}
.prev-wrap img{{width:100%;max-height:250px;object-fit:cover;border-radius:10px;border:2px solid rgba(255,255,255,.15)}}
.prev-x{{position:absolute;top:7px;right:7px;background:rgba(0,0,0,.7);border:1px solid rgba(255,255,255,.2);color:#fff;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:.85rem}}
.btn{{width:100%;padding:14px;font-family:Bebas Neue,sans-serif;font-size:1.25rem;letter-spacing:.06em;border:none;border-radius:11px;cursor:pointer;transition:all .3s;background:linear-gradient(135deg,{btn_grad});color:#fff;position:relative;overflow:hidden}}
.btn:hover{{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.4)}}
.btn:disabled{{opacity:.45;cursor:not-allowed;transform:none}}
.btn span{{position:relative;z-index:1}}
.bar{{height:4px;background:rgba(255,255,255,.08);border-radius:2px;margin-top:10px;overflow:hidden;display:none}}
.bar-fill{{height:100%;background:linear-gradient(90deg,{btn_grad});width:0%;transition:width .3s}}
.msg{{margin-top:13px;padding:11px;border-radius:9px;font-size:.88rem;display:none}}
.msg.ok{{background:rgba(0,255,150,.08);border:1px solid rgba(0,255,150,.28);color:#00ff96}}
.msg.err{{background:rgba(255,60,60,.08);border:1px solid rgba(255,60,60,.28);color:#ff6b6b}}
@keyframes riseUp{{0%{{transform:translateY(100vh) rotate(0deg);opacity:0}}10%{{opacity:.6}}90%{{opacity:.25}}100%{{transform:translateY(-10vh) rotate(360deg);opacity:0}}}}
</style></head>
<body>
<div class="pts" id="pts"></div>
<div class="wrap">
  <div class="logo">Photo Wall</div>
  <div class="sub">Compartí tu momento en la pantalla</div>
  <div class="card">
    <div class="drop" id="drop">
      <input type="file" id="file" accept="image/*" capture="environment">
      <span class="drop-icon">📸</span>
      <div class="drop-txt">Tocá para sacar o elegir una foto</div>
      <div class="drop-hint">JPG · PNG · GIF · WebP &nbsp;·&nbsp; máx 16MB</div>
    </div>
    <div class="prev-wrap" id="pw">
      <img id="prev" src="" alt="">
      <button class="prev-x" onclick="clr()">✕</button>
    </div>
    <button class="btn" id="btn" onclick="up()" disabled><span id="bt">🚀 ENVIAR A LA PANTALLA</span></button>
    <div class="bar" id="bar"><div class="bar-fill" id="fill"></div></div>
    <div class="msg" id="msg"></div>
  </div>
</div>
<script>
{particles_js}
makeParticles();
const fi=document.getElementById('file'),drop=document.getElementById('drop'),pw=document.getElementById('pw'),prev=document.getElementById('prev'),btn=document.getElementById('btn');
fi.addEventListener('change',e=>{{if(e.target.files[0])show(e.target.files[0]);}});
drop.addEventListener('dragover',e=>{{e.preventDefault();drop.classList.add('over');}});
drop.addEventListener('dragleave',()=>drop.classList.remove('over'));
drop.addEventListener('drop',e=>{{e.preventDefault();drop.classList.remove('over');const f=e.dataTransfer.files[0];if(f&&f.type.startsWith('image/')){{fi.files=e.dataTransfer.files;show(f);}}}});
function show(f){{const r=new FileReader();r.onload=e=>{{prev.src=e.target.result;pw.style.display='block';drop.style.display='none';btn.disabled=false;}};r.readAsDataURL(f);}}
function clr(){{fi.value='';pw.style.display='none';drop.style.display='block';btn.disabled=true;document.getElementById('msg').style.display='none';}}
async function up(){{
  const f=fi.files[0];if(!f)return;
  btn.disabled=true;document.getElementById('bt').textContent='⏳ ENVIANDO...';
  document.getElementById('bar').style.display='block';document.getElementById('fill').style.width='65%';
  const fd=new FormData();fd.append('photo',f);
  try{{
    const r=await fetch('/api/upload',{{method:'POST',body:fd}});const d=await r.json();
    document.getElementById('fill').style.width='100%';
    const m=document.getElementById('msg');
    if(r.ok){{m.className='msg ok';m.textContent='✅ ¡Foto enviada! Pronto aparecerá en la pantalla 🎉';m.style.display='block';setTimeout(clr,3500);}}
    else{{m.className='msg err';m.textContent='❌ '+(d.error||'Error al subir');m.style.display='block';}}
  }}catch(e){{const m=document.getElementById('msg');m.className='msg err';m.textContent='❌ Sin conexión. Intentá de nuevo.';m.style.display='block';}}
  finally{{btn.disabled=false;document.getElementById('bt').textContent='🚀 ENVIAR A LA PANTALLA';setTimeout(()=>{{document.getElementById('bar').style.display='none';document.getElementById('fill').style.width='0%';}},800);}}
}}
</script>
</body></html>'''

# ══════════════════════════════════════════════════════════
# UPLOAD API
# ══════════════════════════════════════════════════════════
@app.route('/api/upload', methods=['POST'])
def api_upload():
    if 'photo' not in request.files: return jsonify({'error':'No se encontró archivo'}),400
    file = request.files['photo']
    if not file or file.filename=='': return jsonify({'error':'Archivo vacío'}),400
    if not allowed(file.filename): return jsonify({'error':'Tipo no permitido'}),400
    ext = file.filename.rsplit('.',1)[1].lower()
    fn  = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))
    with get_db() as db:
        db.execute('INSERT INTO photos(filename,original_name) VALUES(?,?)',(fn,secure_filename(file.filename)))
        db.commit()
    return jsonify({'ok':True}),200

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ══════════════════════════════════════════════════════════
# MODERATOR LOGIN
# ══════════════════════════════════════════════════════════
@app.route('/moderador/login', methods=['GET','POST'])
def mod_login():
    error=''
    if request.method=='POST':
        if request.form.get('password')==gc('mod_password','admin123'):
            session['logged_in']=True; return redirect('/moderador')
        error='Contraseña incorrecta'
    return f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moderador</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',sans-serif;background:#0a0a0f;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
body::before{{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 50% 50%,rgba(120,75,160,.3) 0%,transparent 60%);pointer-events:none}}
.card{{background:rgba(255,255,255,.05);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.1);border-radius:22px;padding:38px;width:100%;max-width:350px;text-align:center;position:relative;z-index:1;color:#fff}}
h1{{font-family:'Bebas Neue',sans-serif;font-size:1.9rem;margin-bottom:5px}}
p{{color:rgba(255,255,255,.4);font-size:.85rem;margin-bottom:24px}}
input{{width:100%;padding:12px 14px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.14);border-radius:9px;color:#fff;font-size:.95rem;font-family:'DM Sans',sans-serif;margin-bottom:11px;outline:none;transition:border-color .2s}}
input:focus{{border-color:#FF3CAC}}
button{{width:100%;padding:12px;font-family:'Bebas Neue',sans-serif;font-size:1.25rem;letter-spacing:.1em;border:none;border-radius:9px;cursor:pointer;background:linear-gradient(135deg,#FF3CAC,#784BA0);color:#fff;transition:all .3s}}
button:hover{{transform:translateY(-2px);box-shadow:0 6px 20px rgba(255,60,172,.4)}}
.err{{background:rgba(255,60,60,.1);border:1px solid rgba(255,60,60,.3);color:#ff6b6b;padding:9px;border-radius:7px;margin-bottom:11px;font-size:.85rem}}
</style></head>
<body><div class="card">
  <h1>🎛️ MODERADOR</h1><p>Panel de control de fotos</p>
  {"<div class='err'>"+error+"</div>" if error else ""}
  <form method="POST"><input type="password" name="password" placeholder="Contraseña" autofocus><button type="submit">INGRESAR</button></form>
</div></body></html>'''

@app.route('/moderador/logout')
def mod_logout():
    session.clear(); return redirect('/moderador/login')

# ══════════════════════════════════════════════════════════
# MODERATOR PANEL (with config as 3rd tab)
# ══════════════════════════════════════════════════════════
@app.route('/moderador', methods=['GET','POST'])
@login_required
def moderador():
    saved=False; cleared=False
    if request.method=='POST':
        action=request.form.get('action')
        if action=='save':
            n=request.form.get('event_name','').strip()
            p=request.form.get('mod_password','').strip()
            t=request.form.get('theme','fiesta')
            f=request.form.get('font','grande')
            if n: sc('event_name',n)
            if p: sc('mod_password',p)
            sc('theme',t); sc('font',f); saved=True
        elif action=='clear':
            for fn in os.listdir(UPLOAD_FOLDER):
                try: os.remove(os.path.join(UPLOAD_FOLDER,fn))
                except: pass
            with get_db() as db: db.execute('DELETE FROM photos'); db.commit()
            cleared=True

    event=gc('event_name','Photo Wall'); pwd=gc('mod_password','admin123')
    cur_theme=gc('theme','fiesta'); cur_font=gc('font','grande')
    with get_db() as db:
        total   =db.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
        approved_count=db.execute("SELECT COUNT(*) FROM photos WHERE status='approved'").fetchone()[0]
        pending_count =db.execute("SELECT COUNT(*) FROM photos WHERE status='pending'").fetchone()[0]

    themes = [
        ('fiesta',    '🎊 Fiesta General', 'Rosa neón y violeta con partículas de colores'),
        ('boda',      '💍 Boda',           'Dorado elegante con anillos y flores'),
        ('cumple',    '🎂 Cumpleaños',     'Colores vibrantes con confetti y emojis de festejo'),
        ('quince',    '👑 15 Años',        'Lila y rosa con estrellas y el número 15'),
        ('empresarial','💼 Empresarial',   'Azul corporativo con partículas sutiles'),
    ]
    fonts = [
        ('grande',    'Bebas Neue',         'GRANDE Y LLAMATIVA'),
        ('elegante',  'Cormorant Garamond', 'Elegante y fina'),
        ('divertida', 'Fredoka One',        'Divertida y redondeada'),
        ('minimalista','Inter',             'Moderna y minimalista'),
        ('calida',    'Playfair Display',   'Cálida y sofisticada'),
    ]
    themes_html = ''
    for val, label, desc in themes:
        sel = 'on' if val==cur_theme else ''
        themes_html += f'<div class="opt {sel}" onclick="selOpt(this,\'theme\',\'{val}\')"><div class="opt-title">{label}</div><div class="opt-desc">{desc}</div></div>'

    fonts_html = ''
    font_links = ''
    for val, fname, label in fonts:
        fu, ff = get_font(val)
        font_links += f'<link href="{fu}" rel="stylesheet">\n'
        sel = 'on' if val==cur_font else ''
        fonts_html += f'<div class="opt {sel}" onclick="selOpt(this,\'font\',\'{val}\')" style="font-family:{ff}"><div class="opt-title" style="font-family:{ff}">{label}</div><div class="opt-desc">{fname}</div></div>'

    open_tab = 'config' if (saved or cleared) else 'pending'
    flash = ''
    if saved:   flash = "<div class='flash-ok'>✅ Configuración guardada correctamente</div>"
    if cleared: flash = "<div class='flash-warn'>🗑️ Todas las fotos fueron eliminadas</div>"

    return f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Panel · {event}</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
{font_links}
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',sans-serif;background:#0a0a0f;color:#fff;min-height:100vh}}
body::before{{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 0% 0%,rgba(120,75,160,.2) 0%,transparent 50%);pointer-events:none;z-index:0}}
header{{position:relative;z-index:1;padding:14px 18px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.07);background:rgba(255,255,255,.02)}}
.ht{{font-family:'Bebas Neue',sans-serif;font-size:1.4rem;background:linear-gradient(135deg,#FF3CAC,#FFD700);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.hr{{display:flex;gap:7px;align-items:center}}
.badge{{background:rgba(255,60,172,.15);border:1px solid rgba(255,60,172,.3);color:#FF3CAC;padding:3px 10px;border-radius:18px;font-size:.78rem;font-weight:500}}
.bs{{padding:6px 13px;border-radius:7px;border:1px solid rgba(255,255,255,.1);font-size:.8rem;font-weight:500;cursor:pointer;transition:all .2s;background:rgba(255,255,255,.05);color:rgba(255,255,255,.5);font-family:'DM Sans',sans-serif;text-decoration:none;display:inline-block}}
.bs:hover{{color:#fff;background:rgba(255,255,255,.1)}}
.tabs{{position:relative;z-index:1;display:flex;gap:3px;padding:12px 18px 0;border-bottom:1px solid rgba(255,255,255,.07)}}
.tab{{padding:8px 16px;border-radius:7px 7px 0 0;font-size:.85rem;font-weight:500;cursor:pointer;color:rgba(255,255,255,.35);background:transparent;border:none;transition:all .2s}}
.tab.on{{color:#fff;background:rgba(255,60,172,.12);border-bottom:2px solid #FF3CAC}}
.tab:hover:not(.on){{color:rgba(255,255,255,.6)}}
.content{{position:relative;z-index:1;padding:18px}}
/* photo grid */
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px}}
.pc{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:12px;overflow:hidden;transition:transform .2s,border-color .2s}}
.pc:hover{{transform:translateY(-3px);border-color:rgba(255,60,172,.25)}}
.pc img{{width:100%;aspect-ratio:1;object-fit:cover;display:block}}
.pcb{{padding:10px}}
.pct{{font-size:.7rem;color:rgba(255,255,255,.3);margin-bottom:8px}}
.acts{{display:flex;gap:6px}}
.bapp{{flex:1;padding:6px;background:rgba(0,255,150,.07);border:1px solid rgba(0,255,150,.25);color:#00ff96;border-radius:6px;cursor:pointer;font-size:.8rem;font-weight:500;transition:all .2s}}
.bapp:hover{{background:rgba(0,255,150,.16)}}
.brej{{flex:1;padding:6px;background:rgba(255,60,60,.07);border:1px solid rgba(255,60,60,.25);color:#ff6b6b;border-radius:6px;cursor:pointer;font-size:.8rem;font-weight:500;transition:all .2s}}
.brej:hover{{background:rgba(255,60,60,.16)}}
.abadge{{display:inline-block;background:rgba(0,255,150,.1);border:1px solid rgba(0,255,150,.25);color:#00ff96;padding:3px 8px;border-radius:5px;font-size:.68rem;margin-bottom:8px}}
.empty{{text-align:center;padding:46px 20px;color:rgba(255,255,255,.2);grid-column:1/-1}}
.empty-i{{font-size:2.6rem;margin-bottom:8px;display:block}}
/* config tab */
.cfg{{max-width:640px}}
.section{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:20px;margin-bottom:16px}}
.section h2{{font-family:'Bebas Neue',sans-serif;font-size:1.15rem;letter-spacing:.06em;margin-bottom:14px}}
label{{display:block;font-size:.8rem;color:rgba(255,255,255,.42);margin-bottom:5px;margin-top:12px}}
label:first-of-type{{margin-top:0}}
input[type=text],input[type=password]{{width:100%;padding:10px 13px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:9px;color:#fff;font-size:.9rem;font-family:'DM Sans',sans-serif;outline:none;transition:border-color .2s}}
input:focus{{border-color:#FF3CAC}}
.hint{{font-size:.7rem;color:rgba(255,255,255,.2);margin-top:3px}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:9px;margin-top:4px}}
.opt{{background:rgba(255,255,255,.04);border:2px solid rgba(255,255,255,.08);border-radius:10px;padding:11px;cursor:pointer;transition:all .2s}}
.opt:hover{{border-color:rgba(255,60,172,.35);background:rgba(255,60,172,.05)}}
.opt.on{{border-color:#FF3CAC;background:rgba(255,60,172,.1)}}
.opt-title{{font-size:.88rem;font-weight:500;margin-bottom:2px}}
.opt-desc{{font-size:.7rem;color:rgba(255,255,255,.32)}}
.bsave{{margin-top:14px;padding:11px 24px;font-family:'Bebas Neue',sans-serif;font-size:1.1rem;letter-spacing:.08em;border:none;border-radius:9px;cursor:pointer;background:linear-gradient(135deg,#FF3CAC,#784BA0);color:#fff;transition:all .3s}}
.bsave:hover{{transform:translateY(-2px);box-shadow:0 5px 16px rgba(255,60,172,.35)}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-bottom:14px}}
.stat{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:10px;padding:12px;text-align:center}}
.stat-n{{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;background:linear-gradient(135deg,#FF3CAC,#2B86C5);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.stat-l{{font-size:.7rem;color:rgba(255,255,255,.3);margin-top:2px}}
.danger{{border-color:rgba(255,60,60,.18)}}
.danger h2{{color:#ff6b6b}}
.bclear{{margin-top:4px;padding:11px 24px;font-family:'Bebas Neue',sans-serif;font-size:1.1rem;letter-spacing:.08em;border:none;border-radius:9px;cursor:pointer;background:rgba(255,60,60,.1);border:1px solid rgba(255,60,60,.28);color:#ff6b6b;transition:all .3s}}
.bclear:hover{{background:rgba(255,60,60,.2)}}
.flash-ok{{background:rgba(0,255,150,.07);border:1px solid rgba(0,255,150,.25);color:#00ff96;padding:10px 13px;border-radius:8px;margin-bottom:14px;font-size:.86rem}}
.flash-warn{{background:rgba(255,200,0,.07);border:1px solid rgba(255,200,0,.25);color:#ffd700;padding:10px 13px;border-radius:8px;margin-bottom:14px;font-size:.86rem}}
.tc{{display:none}}.tc.on{{display:block}}
/* bulk upload */
.upload-bar{{display:flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap}}
.bupload{{padding:9px 18px;font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:.08em;border:none;border-radius:8px;cursor:pointer;background:linear-gradient(135deg,#FF3CAC,#784BA0);color:#fff;transition:all .3s;position:relative;overflow:hidden}}
.bupload:hover{{transform:translateY(-2px);box-shadow:0 5px 16px rgba(255,60,172,.35)}}
.bupload input{{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}}
.uprog{{flex:1;min-width:160px;display:none}}
.uprog-bar{{height:5px;background:rgba(255,255,255,.08);border-radius:3px;overflow:hidden;margin-top:4px}}
.uprog-fill{{height:100%;background:linear-gradient(90deg,#FF3CAC,#2B86C5);border-radius:3px;transition:width .2s}}
.uprog-txt{{font-size:.75rem;color:rgba(255,255,255,.4)}}
</style></head>
<body>
<header>
  <div class="ht">🎛️ {event}</div>
  <div class="hr">
    <span class="badge" id="cnt">…</span>
    <a href="/moderador/logout" class="bs">Salir</a>
  </div>
</header>
<div class="tabs">
  <button class="tab {'on' if open_tab=='pending' else ''}" onclick="sw('pending',this)">⏳ Pendientes</button>
  <button class="tab {'on' if open_tab=='approved' else ''}" onclick="sw('approved',this)">✅ En pantalla</button>
  <button class="tab {'on' if open_tab=='config' else ''}" onclick="sw('config',this)">⚙️ Configuración</button>
</div>
<div class="content">
  <div class="tc {'on' if open_tab=='pending' else ''}" id="tc-pending">
    <div class="upload-bar">
      <div class="bupload">
        📁 SUBIR FOTOS
        <input type="file" id="bulkInput" accept="image/*" multiple onchange="bulkUpload(this)">
      </div>
      <div class="uprog" id="uprog">
        <div class="uprog-txt" id="uprogTxt">Subiendo...</div>
        <div class="uprog-bar"><div class="uprog-fill" id="uprogFill"></div></div>
      </div>
    </div>
    <div class="grid" id="g-pending"></div>
  </div>
  <div class="tc {'on' if open_tab=='approved' else ''}" id="tc-approved"><div class="grid" id="g-approved"></div></div>
  <div class="tc cfg {'on' if open_tab=='config' else ''}" id="tc-config">
    {flash}
    <div class="section">
      <h2>📊 Estado del evento</h2>
      <div class="stats">
        <div class="stat"><div class="stat-n">{total}</div><div class="stat-l">Total fotos</div></div>
        <div class="stat"><div class="stat-n">{approved_count}</div><div class="stat-l">En pantalla</div></div>
        <div class="stat"><div class="stat-n">{pending_count}</div><div class="stat-l">Pendientes</div></div>
      </div>
    </div>
    <form method="POST">
      <input type="hidden" name="action" value="save">
      <input type="hidden" name="theme" id="htheme" value="{cur_theme}">
      <input type="hidden" name="font"  id="hfont"  value="{cur_font}">
      <div class="section">
        <h2>🎉 Datos del evento</h2>
        <label>Nombre del evento</label>
        <input type="text" name="event_name" value="{event}" placeholder="Ej: Boda Juan y Ana">
        <div class="hint">Aparece en el proyector y en la página de subida de fotos</div>
        <label>Nueva contraseña del moderador</label>
        <input type="password" name="mod_password" placeholder="Dejá vacío para no cambiar (actual: {pwd})">
      </div>
      <div class="section">
        <h2>🎨 Tema visual de la pantalla</h2>
        <div class="grid2" id="themes">{themes_html}</div>
      </div>
      <div class="section">
        <h2>✍️ Tipografía del nombre</h2>
        <div class="grid2" id="fonts">{fonts_html}</div>
      </div>
      <button type="submit" class="bsave">💾 GUARDAR TODOS LOS CAMBIOS</button>
    </form>
    <div class="section danger" style="margin-top:16px">
      <h2>🗑️ Borrar todo al terminar</h2>
      <p style="color:rgba(255,255,255,.4);font-size:.84rem;margin-bottom:12px">Elimina todas las fotos y limpia la base de datos. No se puede deshacer.</p>
      <form method="POST" onsubmit="return confirm('¿Seguro? Se borrarán TODAS las fotos.')">
        <input type="hidden" name="action" value="clear">
        <button type="submit" class="bclear">🗑️ BORRAR TODAS LAS FOTOS</button>
      </form>
    </div>
  </div>
</div>
<script>
let cur='pending';
function sw(tab,el){{
  cur=tab;
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));el.classList.add('on');
  document.querySelectorAll('.tc').forEach(t=>t.classList.remove('on'));
  document.getElementById('tc-'+tab).classList.add('on');
  if(tab==='pending'||tab==='approved') load();
}}
function fmt(s){{return new Date(s+'Z').toLocaleTimeString('es-AR',{{hour:'2-digit',minute:'2-digit'}})+' hs';}}
function card(p,tab){{return `<div class="pc" id="c${{p.id}}"><img src="/uploads/${{p.filename}}" loading="lazy"><div class="pcb"><div class="pct">📷 ${{fmt(p.uploaded_at)}}</div>${{tab==='approved'?'<span class="abadge">✓ En carrusel</span>':''}}<div class="acts">${{tab==='pending'?`<button class="bapp" onclick="act(${{p.id}},'approve')">✓ Aprobar</button><button class="brej" onclick="act(${{p.id}},'reject')">✗ Rechazar</button>`:`<button class="brej" onclick="act(${{p.id}},'reject')" style="flex:1">✗ Quitar</button>`}}</div></div></div>`;}}
async function load(){{
  const r=await fetch('/api/photos?status='+cur);const photos=await r.json();
  if(cur==='pending')document.getElementById('cnt').textContent=photos.length+' pendientes';
  const g=document.getElementById('g-'+cur);
  g.innerHTML=photos.length?photos.map(p=>card(p,cur)).join(''):`<div class="empty"><span class="empty-i">${{cur==='pending'?'🎉':'📸'}}</span>${{cur==='pending'?'No hay fotos pendientes':'Ninguna foto aprobada aún'}}</div>`;
}}
async function bulkUpload(input){{
  const files=[...input.files];
  if(!files.length)return;
  const prog=document.getElementById('uprog');
  const fill=document.getElementById('uprogFill');
  const txt=document.getElementById('uprogTxt');
  prog.style.display='block';
  let done=0;
  for(const f of files){{
    txt.textContent=`Subiendo ${{done+1}} de ${{files.length}}...`;
    fill.style.width=Math.round((done/files.length)*100)+'%';
    const fd=new FormData();fd.append('photo',f);
    try{{await fetch('/api/upload',{{method:'POST',body:fd}});}}catch(e){{}}
    done++;
  }}
  fill.style.width='100%';
  txt.textContent=`✅ ${{done}} foto${{done>1?'s':''}} subida${{done>1?'s':''}}`;
  setTimeout(()=>{{prog.style.display='none';fill.style.width='0%';input.value='';}},2500);
  load();
}}
function selOpt(el,group,val){{
  document.querySelectorAll('#'+(group==='theme'?'themes':'fonts')+' .opt').forEach(o=>o.classList.remove('on'));
  el.classList.add('on');document.getElementById('h'+group).value=val;
}}
load();setInterval(load,60000);
</script></body></html>'''

# ══════════════════════════════════════════════════════════
# CONFIGURATION (redirect to moderador#config tab)
# ══════════════════════════════════════════════════════════
@app.route('/configuracion')
@login_required
def configuracion():
    return redirect('/moderador')

# ══════════════════════════════════════════════════════════
# PHOTOS API
# ══════════════════════════════════════════════════════════
@app.route('/api/photos')
@login_required
def api_photos():
    status=request.args.get('status','pending')
    with get_db() as db:
        photos=db.execute('SELECT * FROM photos WHERE status=? ORDER BY uploaded_at DESC',(status,)).fetchall()
    return jsonify([dict(p) for p in photos])

@app.route('/api/photos/approved-display')
def api_approved_display():
    with get_db() as db:
        photos=db.execute('SELECT * FROM photos WHERE status="approved" ORDER BY uploaded_at ASC').fetchall()
    return jsonify([dict(p) for p in photos])

@app.route('/api/photos/<int:pid>/approve', methods=['POST'])
@login_required
def approve_photo(pid):
    with get_db() as db: db.execute('UPDATE photos SET status="approved" WHERE id=?',(pid,)); db.commit()
    return jsonify({'ok':True})

@app.route('/api/photos/<int:pid>/reject', methods=['POST'])
@login_required
def reject_photo(pid):
    with get_db() as db:
        photo=db.execute('SELECT filename FROM photos WHERE id=?',(pid,)).fetchone()
        if photo:
            fp=os.path.join(app.config['UPLOAD_FOLDER'],photo['filename'])
            if os.path.exists(fp): os.remove(fp)
        db.execute('DELETE FROM photos WHERE id=?',(pid,)); db.commit()
    return jsonify({'ok':True})

# ══════════════════════════════════════════════════════════
# DISPLAY — 16:10, themes, fonts
# ══════════════════════════════════════════════════════════
@app.route('/display')
def display():
    event  = gc('event_name','Photo Wall')
    theme  = gc('theme','fiesta')
    font_k = gc('font','grande')
    font_url, font_family = get_font(font_k)
    css_vars, bg_css, particles_js, overlay_html = get_theme_parts(theme)

    host       = request.host_url.rstrip('/')
    upload_url = host + '/upload'
    qr_url     = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={upload_url}&bgcolor=0a0a0f&color=FF3CAC&margin=2"

    grad = {'boda':'#D4AF37,#f5f0e8','cumple':'#FF6B6B,#FFE66D',
            'quince':'#C084FC,#F472B6','empresarial':'#38BDF8,#e2e8f0',
            'fiesta':'#FF3CAC,#FFD700'}.get(theme,'#FF3CAC,#FFD700')

    return f'''<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>📸 {event}</title>
<link href="{font_url}" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{{css_vars}}}
{bg_css}
html,body{{width:100%;height:100%;overflow:hidden;color:#fff}}
.stage{{position:fixed;inset:0;display:flex;align-items:center;justify-content:center}}
.canvas{{position:relative;width:100vw;height:calc(100vw * 10 / 16);max-height:100vh;max-width:calc(100vh * 16 / 10)}}
.pts{{position:absolute;inset:0;pointer-events:none;z-index:1;overflow:hidden}}
@keyframes riseUp{{0%{{transform:translateY(110%) rotate(0deg);opacity:0}}10%{{opacity:.65}}90%{{opacity:.25}}100%{{transform:translateY(-10%) rotate(360deg);opacity:0}}}}
.empty{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:3}}
.empty.hide{{display:none}}
.empty-title{{font-family:{font_family};font-size:clamp(2.5rem,8vw,7rem);background:linear-gradient(135deg,{grad});-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1.1;text-align:center;animation:breathe 3.5s ease-in-out infinite}}
@keyframes breathe{{0%,100%{{transform:scale(1);opacity:1}}50%{{transform:scale(.97);opacity:.85}}}}
.empty-sub{{color:rgba(255,255,255,.3);font-size:clamp(.7rem,1.6vw,1.1rem);letter-spacing:.2em;text-transform:uppercase;margin-top:10px}}
.sw-wrap{{position:absolute;inset:0;z-index:2;display:none}}
.swiper,.swiper-slide{{width:100%;height:100%}}
.swiper-slide{{display:flex;align-items:center;justify-content:center;overflow:hidden}}
.swiper-slide img{{width:100%;height:100%;object-fit:contain;animation:kb 9s ease-in-out forwards}}
@keyframes kb{{from{{transform:scale(1)}}to{{transform:scale(1.05)}}}}
.topbar{{position:absolute;top:0;left:0;right:0;height:clamp(42px,6vh,62px);z-index:5;display:flex;align-items:center;justify-content:space-between;padding:0 clamp(10px,2vw,22px);background:linear-gradient(to bottom,rgba(0,0,0,.7),transparent);pointer-events:none}}
.topbar-name{{font-family:{font_family};font-size:clamp(1rem,2.4vw,1.9rem);background:linear-gradient(135deg,{grad});-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:.06em}}
.topbar-count{{font-size:clamp(.6rem,1.1vw,.85rem);color:rgba(255,255,255,.32);letter-spacing:.1em}}
.qr{{position:absolute;right:0;bottom:0;width:clamp(130px,15vw,220px);background:rgba(0,0,0,.88);backdrop-filter:blur(20px);border-top-left-radius:clamp(12px,2vw,20px);border:1px solid rgba(255,255,255,.12);border-right:none;border-bottom:none;padding:clamp(10px,1.4vw,18px);text-align:center;z-index:10;animation:slideqr 1.2s ease-out}}
@keyframes slideqr{{from{{transform:translate(100%,100%);opacity:0}}to{{transform:translate(0,0);opacity:1}}}}
.qr-lbl{{font-family:{font_family};font-size:clamp(.7rem,1.2vw,1rem);background:linear-gradient(135deg,{grad});-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:.06em;margin-bottom:clamp(5px,.9vw,10px);line-height:1.3}}
.qr img{{width:100%;max-width:clamp(80px,11vw,155px);border-radius:clamp(5px,.9vw,10px);border:2px solid rgba(255,255,255,.15)}}
.qr-url{{margin-top:clamp(3px,.5vw,7px);font-size:clamp(.45rem,.75vw,.65rem);color:rgba(255,255,255,.25);word-break:break-all}}
.toast{{position:absolute;top:clamp(46px,7vh,68px);left:50%;transform:translateX(-50%) translateY(-14px);background:rgba(0,0,0,.8);backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,.15);color:#fff;padding:clamp(6px,.9vh,10px) clamp(14px,1.8vw,24px);border-radius:28px;font-size:clamp(.7rem,1.1vw,.9rem);font-weight:500;z-index:20;opacity:0;transition:all .4s;pointer-events:none;white-space:nowrap}}
.toast.show{{opacity:1;transform:translateX(-50%) translateY(0)}}
</style></head>
<body>
<div class="stage">
 <div class="canvas">
  <!-- background overlay (theme graphic) -->
  {overlay_html}
  <!-- particles -->
  <div class="pts" id="pts"></div>
  <!-- topbar -->
  <div class="topbar">
    <div class="topbar-name">{event}</div>
    <div class="topbar-count" id="cnt"></div>
  </div>
  <!-- toast -->
  <div class="toast" id="toast"></div>
  <!-- empty state -->
  <div class="empty" id="empty">
    <div class="empty-title">{event}</div>
    <div class="empty-sub">Las fotos aparecerán aquí</div>
  </div>
  <!-- carousel -->
  <div class="sw-wrap" id="swWrap">
    <div class="swiper" id="sw">
      <div class="swiper-wrapper" id="swSlides"></div>
      <div class="swiper-pagination"></div>
    </div>
  </div>
  <!-- qr -->
  <div class="qr">
    <div class="qr-lbl">COMPARTÍ<br>TU FOTO</div>
    <img src="{qr_url}" alt="QR" onerror="this.style.display='none'">
    <div class="qr-url">{upload_url}</div>
  </div>
 </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
<script>
{particles_js}
makeParticles();
let sw=null,known=new Set(),ready=false;
function initSw(){{if(sw)return;sw=new Swiper('#sw',{{loop:true,autoplay:{{delay:5000,disableOnInteraction:false}},speed:1200,effect:'fade',fadeEffect:{{crossFade:true}},pagination:{{el:'.swiper-pagination'}}}});}}
function toast(msg){{const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3500);}}
async function load(){{
  try{{
    const r=await fetch('/api/photos/approved-display');const photos=await r.json();
    document.getElementById('cnt').textContent=photos.length>0?photos.length+' fotos':'';
    if(!photos.length){{document.getElementById('empty').classList.remove('hide');document.getElementById('swWrap').style.display='none';return;}}
    document.getElementById('empty').classList.add('hide');document.getElementById('swWrap').style.display='block';
    const news=photos.filter(p=>!known.has(p.id));
    if(news.length&&ready)toast('📸 '+news.length+' foto'+(news.length>1?'s nuevas':'  nueva')+' agregada'+(news.length>1?'s':''));
    if(news.length||!ready){{
      const wrap=document.getElementById('swSlides');wrap.innerHTML='';
      photos.forEach(p=>{{known.add(p.id);const s=document.createElement('div');s.className='swiper-slide';s.innerHTML=`<img src="/uploads/${{p.filename}}" alt="">`;wrap.appendChild(s);}});
      if(!ready){{initSw();ready=true;}}else{{sw.update();}}
    }}
  }}catch(e){{console.error(e);}}
}}
load();setInterval(load,60000);
</script>
</body></html>'''

# ══════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════
if __name__=='__main__':
    port=int(os.environ.get('PORT',5000))
    app.run(debug=False,host='0.0.0.0',port=port)
