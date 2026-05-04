import os
import sqlite3
import uuid
import shutil
from flask import Flask, request, jsonify, redirect, session, send_from_directory

from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'photowall-secret-2024')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DB_PATH = os.path.join(BASE_DIR, 'photos.db')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT,
            status TEXT DEFAULT 'pending',
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        defaults = [('event_name', 'Photo Wall'), ('mod_password', 'admin123')]
        for k, v in defaults:
            db.execute('INSERT OR IGNORE INTO config (key,value) VALUES (?,?)', (k, v))
        db.commit()

def get_config(key, default=''):
    try:
        with get_db() as db:
            row = db.execute('SELECT value FROM config WHERE key=?', (key,)).fetchone()
            return row['value'] if row else default
    except:
        return default

def set_config(key, value):
    with get_db() as db:
        db.execute('INSERT OR REPLACE INTO config (key,value) VALUES (?,?)', (key, value))
        db.commit()

def allowed_file(f):
    return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect('/moderador/login')
        return f(*args, **kwargs)
    return decorated

init_db()

# ══════════════════════════════════════════════════════════
#  UPLOAD PAGE
# ══════════════════════════════════════════════════════════
@app.route('/')
@app.route('/upload')
def upload_page():
    event = get_config('event_name', 'Photo Wall')
    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📸 {event}</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{--neon:#FF3CAC;--neon2:#784BA0;--neon3:#2B86C5;--gold:#FFD700;--dark:#0a0a0f}}
body{{font-family:'DM Sans',sans-serif;background:var(--dark);min-height:100dvh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;overflow-x:hidden}}
body::before{{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 20% 50%,rgba(120,75,160,.3) 0%,transparent 50%),radial-gradient(ellipse at 80% 20%,rgba(255,60,172,.2) 0%,transparent 50%),radial-gradient(ellipse at 60% 80%,rgba(43,134,197,.2) 0%,transparent 50%);pointer-events:none;z-index:0}}
.wrap{{position:relative;z-index:1;width:100%;max-width:460px;text-align:center}}
.logo{{font-family:'Bebas Neue',sans-serif;font-size:clamp(2rem,9vw,3.5rem);background:linear-gradient(135deg,var(--neon),var(--gold));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1.1;margin-bottom:4px}}
.sub{{color:rgba(255,255,255,.45);font-size:.85rem;letter-spacing:.18em;text-transform:uppercase;margin-bottom:32px}}
.card{{background:rgba(255,255,255,.05);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.1);border-radius:24px;padding:28px}}
.drop{{border:2px dashed rgba(255,60,172,.4);border-radius:14px;padding:36px 16px;cursor:pointer;transition:all .3s;position:relative;overflow:hidden;margin-bottom:16px}}
.drop:hover,.drop.over{{border-color:var(--neon);background:rgba(255,60,172,.07);transform:scale(1.01)}}
.drop input{{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}}
.drop-icon{{font-size:2.8rem;margin-bottom:10px;display:block}}
.drop-txt{{color:rgba(255,255,255,.7);font-size:.95rem}}
.drop-hint{{color:rgba(255,255,255,.28);font-size:.75rem;margin-top:5px}}
.prev-wrap{{display:none;margin-bottom:16px;position:relative}}
.prev-wrap img{{width:100%;max-height:260px;object-fit:cover;border-radius:12px;border:2px solid rgba(255,60,172,.4)}}
.prev-x{{position:absolute;top:8px;right:8px;background:rgba(0,0,0,.7);border:1px solid rgba(255,255,255,.2);color:#fff;border-radius:50%;width:30px;height:30px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:.9rem}}
.btn{{width:100%;padding:15px;font-family:'Bebas Neue',sans-serif;font-size:1.35rem;letter-spacing:.1em;border:none;border-radius:12px;cursor:pointer;transition:all .3s;background:linear-gradient(135deg,var(--neon),var(--neon2));color:#fff;position:relative;overflow:hidden}}
.btn::before{{content:'';position:absolute;inset:0;background:linear-gradient(135deg,var(--neon2),var(--neon3));opacity:0;transition:opacity .3s}}
.btn:hover::before{{opacity:1}}
.btn:hover{{transform:translateY(-2px);box-shadow:0 8px 28px rgba(255,60,172,.4)}}
.btn:disabled{{opacity:.45;cursor:not-allowed;transform:none}}
.btn span{{position:relative;z-index:1}}
.bar{{height:4px;background:rgba(255,255,255,.08);border-radius:2px;margin-top:10px;overflow:hidden;display:none}}
.bar-fill{{height:100%;background:linear-gradient(90deg,var(--neon),var(--neon3));width:0%;transition:width .3s}}
.msg{{margin-top:14px;padding:12px;border-radius:10px;font-size:.9rem;display:none}}
.msg.ok{{background:rgba(0,255,150,.08);border:1px solid rgba(0,255,150,.3);color:#00ff96}}
.msg.err{{background:rgba(255,60,60,.08);border:1px solid rgba(255,60,60,.3);color:#ff6b6b}}
.particles{{position:fixed;inset:0;pointer-events:none;z-index:0}}
.p{{position:absolute;border-radius:50%;animation:rise linear infinite;opacity:0}}
@keyframes rise{{0%{{transform:translateY(100vh);opacity:0}}10%{{opacity:.5}}90%{{opacity:.2}}100%{{transform:translateY(-10vh);opacity:0}}}}
</style>
</head>
<body>
<div class="particles" id="pts"></div>
<div class="wrap">
  <div class="logo">📸 {event}</div>
  <div class="sub">Compartí tu momento en la pantalla</div>
  <div class="card">
    <div class="drop" id="drop">
      <input type="file" id="file" accept="image/*" capture="environment">
      <span class="drop-icon">🌟</span>
      <div class="drop-txt">Tocá para sacar o elegir una foto</div>
      <div class="drop-hint">JPG · PNG · GIF · WebP &nbsp;·&nbsp; máx 16MB</div>
    </div>
    <div class="prev-wrap" id="pw">
      <img id="prev" src="" alt="">
      <button class="prev-x" onclick="clear()">✕</button>
    </div>
    <button class="btn" id="btn" onclick="upload()" disabled><span id="btnTxt">🚀 ENVIAR A LA PANTALLA</span></button>
    <div class="bar" id="bar"><div class="bar-fill" id="fill"></div></div>
    <div class="msg" id="msg"></div>
  </div>
</div>
<script>
const pts=document.getElementById('pts');
for(let i=0;i<20;i++){{const p=document.createElement('div');p.className='p';p.style.cssText=`left:${{Math.random()*100}}%;width:${{2+Math.random()*4}}px;height:${{2+Math.random()*4}}px;animation-duration:${{8+Math.random()*12}}s;animation-delay:${{Math.random()*10}}s;background:${{['#FF3CAC','#784BA0','#2B86C5','#FFD700'][Math.floor(Math.random()*4)]}}`;pts.appendChild(p);}}
const fi=document.getElementById('file'),drop=document.getElementById('drop'),pw=document.getElementById('pw'),prev=document.getElementById('prev'),btn=document.getElementById('btn');
fi.addEventListener('change',e=>{{if(e.target.files[0])show(e.target.files[0]);}});
drop.addEventListener('dragover',e=>{{e.preventDefault();drop.classList.add('over');}});
drop.addEventListener('dragleave',()=>drop.classList.remove('over'));
drop.addEventListener('drop',e=>{{e.preventDefault();drop.classList.remove('over');const f=e.dataTransfer.files[0];if(f&&f.type.startsWith('image/')){{fi.files=e.dataTransfer.files;show(f);}}}});
function show(f){{const r=new FileReader();r.onload=e=>{{prev.src=e.target.result;pw.style.display='block';drop.style.display='none';btn.disabled=false;}};r.readAsDataURL(f);}}
function clear(){{fi.value='';pw.style.display='none';drop.style.display='block';btn.disabled=true;document.getElementById('msg').style.display='none';}}
async function upload(){{
  const f=fi.files[0];if(!f)return;
  btn.disabled=true;document.getElementById('btnTxt').textContent='⏳ ENVIANDO...';
  document.getElementById('bar').style.display='block';document.getElementById('fill').style.width='65%';
  const fd=new FormData();fd.append('photo',f);
  try{{
    const r=await fetch('/api/upload',{{method:'POST',body:fd}});
    const d=await r.json();
    document.getElementById('fill').style.width='100%';
    const msg=document.getElementById('msg');
    if(r.ok){{msg.className='msg ok';msg.textContent='✅ ¡Foto enviada! Pronto aparecerá en la pantalla 🎉';msg.style.display='block';setTimeout(clear,3500);}}
    else{{msg.className='msg err';msg.textContent='❌ '+(d.error||'Error al subir');msg.style.display='block';}}
  }}catch(e){{const msg=document.getElementById('msg');msg.className='msg err';msg.textContent='❌ Sin conexión. Intentá de nuevo.';msg.style.display='block';}}
  finally{{btn.disabled=false;document.getElementById('btnTxt').textContent='🚀 ENVIAR A LA PANTALLA';setTimeout(()=>{{document.getElementById('bar').style.display='none';document.getElementById('fill').style.width='0%';}},800);}}
}}
</script>
</body>
</html>'''

# ══════════════════════════════════════════════════════════
#  UPLOAD API
# ══════════════════════════════════════════════════════════
@app.route('/api/upload', methods=['POST'])
def api_upload():
    if 'photo' not in request.files:
        return jsonify({'error': 'No se encontró archivo'}), 400
    file = request.files['photo']
    if not file or file.filename == '':
        return jsonify({'error': 'Archivo vacío'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Tipo de archivo no permitido'}), 400
    ext = file.filename.rsplit('.',1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    with get_db() as db:
        db.execute('INSERT INTO photos (filename, original_name) VALUES (?,?)',
                   (filename, secure_filename(file.filename)))
        db.commit()
    return jsonify({'ok': True}), 200

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ══════════════════════════════════════════════════════════
#  MODERATOR LOGIN
# ══════════════════════════════════════════════════════════
@app.route('/moderador/login', methods=['GET','POST'])
def mod_login():
    error = ''
    if request.method == 'POST':
        pwd = get_config('mod_password', 'admin123')
        if request.form.get('password') == pwd:
            session['logged_in'] = True
            return redirect('/moderador')
        error = 'Contraseña incorrecta'
    return f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Moderador</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',sans-serif;background:#0a0a0f;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
body::before{{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 50% 50%,rgba(120,75,160,.3) 0%,transparent 60%);pointer-events:none}}
.card{{background:rgba(255,255,255,.05);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.1);border-radius:24px;padding:40px;width:100%;max-width:360px;text-align:center;position:relative;z-index:1}}
h1{{font-family:'Bebas Neue',sans-serif;font-size:2rem;color:#fff;margin-bottom:6px}}
p{{color:rgba(255,255,255,.4);font-size:.88rem;margin-bottom:26px}}
input{{width:100%;padding:13px 16px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.15);border-radius:10px;color:#fff;font-size:1rem;font-family:'DM Sans',sans-serif;margin-bottom:12px;outline:none;transition:border-color .2s}}
input:focus{{border-color:#FF3CAC}}
button{{width:100%;padding:13px;font-family:'Bebas Neue',sans-serif;font-size:1.3rem;letter-spacing:.1em;border:none;border-radius:10px;cursor:pointer;background:linear-gradient(135deg,#FF3CAC,#784BA0);color:#fff;transition:all .3s}}
button:hover{{transform:translateY(-2px);box-shadow:0 6px 20px rgba(255,60,172,.4)}}
.err{{background:rgba(255,60,60,.1);border:1px solid rgba(255,60,60,.3);color:#ff6b6b;padding:10px;border-radius:8px;margin-bottom:12px;font-size:.88rem}}
</style></head>
<body><div class="card">
  <h1>🎛️ MODERADOR</h1>
  <p>Panel de control de fotos</p>
  {"<div class='err'>"+error+"</div>" if error else ""}
  <form method="POST">
    <input type="password" name="password" placeholder="Contraseña" autofocus>
    <button type="submit">INGRESAR</button>
  </form>
</div></body></html>'''

@app.route('/moderador/logout')
def mod_logout():
    session.clear()
    return redirect('/moderador/login')

# ══════════════════════════════════════════════════════════
#  MODERATOR PANEL
# ══════════════════════════════════════════════════════════
@app.route('/moderador')
@login_required
def moderador():
    event = get_config('event_name', 'Photo Wall')
    return f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Panel · {event}</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{--neon:#FF3CAC;--neon2:#784BA0;--neon3:#2B86C5;--dark:#0a0a0f}}
body{{font-family:'DM Sans',sans-serif;background:var(--dark);color:#fff;min-height:100vh}}
body::before{{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 0% 0%,rgba(120,75,160,.2) 0%,transparent 50%);pointer-events:none;z-index:0}}
header{{position:relative;z-index:1;padding:16px 20px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.02)}}
.htitle{{font-family:'Bebas Neue',sans-serif;font-size:1.5rem;background:linear-gradient(135deg,#FF3CAC,#FFD700);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:.05em}}
.hright{{display:flex;gap:8px;align-items:center}}
.badge{{background:rgba(255,60,172,.18);border:1px solid rgba(255,60,172,.35);color:#FF3CAC;padding:3px 11px;border-radius:20px;font-size:.8rem;font-weight:500}}
.bsm{{padding:7px 14px;border-radius:8px;border:none;font-family:'DM Sans',sans-serif;font-size:.82rem;font-weight:500;cursor:pointer;transition:all .2s}}
.blog{{background:rgba(255,255,255,.06);color:rgba(255,255,255,.55);border:1px solid rgba(255,255,255,.1)}}
.blog:hover{{color:#fff;background:rgba(255,255,255,.12)}}
.tabs{{position:relative;z-index:1;display:flex;gap:3px;padding:14px 20px 0;border-bottom:1px solid rgba(255,255,255,.07)}}
.tab{{padding:9px 18px;border-radius:8px 8px 0 0;font-size:.88rem;font-weight:500;cursor:pointer;color:rgba(255,255,255,.38);background:transparent;border:none;transition:all .2s}}
.tab.on{{color:#fff;background:rgba(255,60,172,.13);border-bottom:2px solid var(--neon)}}
.tab:hover:not(.on){{color:rgba(255,255,255,.65)}}
.content{{position:relative;z-index:1;padding:20px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px}}
.pc{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:14px;overflow:hidden;transition:transform .2s,border-color .2s}}
.pc:hover{{transform:translateY(-3px);border-color:rgba(255,60,172,.28)}}
.pc img{{width:100%;aspect-ratio:1;object-fit:cover;display:block}}
.pcb{{padding:10px}}
.pct{{font-size:.72rem;color:rgba(255,255,255,.32);margin-bottom:9px}}
.acts{{display:flex;gap:7px}}
.bapp{{flex:1;padding:7px;background:rgba(0,255,150,.08);border:1px solid rgba(0,255,150,.28);color:#00ff96;border-radius:7px;cursor:pointer;font-size:.82rem;font-weight:500;transition:all .2s}}
.bapp:hover{{background:rgba(0,255,150,.18)}}
.brej{{flex:1;padding:7px;background:rgba(255,60,60,.08);border:1px solid rgba(255,60,60,.28);color:#ff6b6b;border-radius:7px;cursor:pointer;font-size:.82rem;font-weight:500;transition:all .2s}}
.brej:hover{{background:rgba(255,60,60,.18)}}
.abadge{{display:inline-block;background:rgba(0,255,150,.12);border:1px solid rgba(0,255,150,.28);color:#00ff96;padding:3px 9px;border-radius:5px;font-size:.7rem;margin-bottom:9px}}
.empty{{text-align:center;padding:50px 20px;color:rgba(255,255,255,.22);grid-column:1/-1}}
.empty-i{{font-size:2.8rem;margin-bottom:10px;display:block}}
.tc{{display:none}}.tc.on{{display:block}}
</style></head>
<body>
<header>
  <div class="htitle">🎛️ {event}</div>
  <div class="hright">
    <span class="badge" id="cnt">…</span>
    <a href="/configuracion"><button class="bsm blog">⚙️ Config</button></a>
    <a href="/moderador/logout"><button class="bsm blog">Salir</button></a>
  </div>
</header>
<div class="tabs">
  <button class="tab on" onclick="sw('pending',this)">⏳ Pendientes</button>
  <button class="tab" onclick="sw('approved',this)">✅ En pantalla</button>
</div>
<div class="content">
  <div class="tc on" id="tc-pending"><div class="grid" id="g-pending"></div></div>
  <div class="tc" id="tc-approved"><div class="grid" id="g-approved"></div></div>
</div>
<script>
let cur='pending';
function sw(tab,el){{cur=tab;document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));el.classList.add('on');document.querySelectorAll('.tc').forEach(t=>t.classList.remove('on'));document.getElementById('tc-'+tab).classList.add('on');load();}}
function fmt(s){{return new Date(s+'Z').toLocaleTimeString('es-AR',{{hour:'2-digit',minute:'2-digit'}})+' hs';}}
function card(p,tab){{
  return `<div class="pc" id="c${{p.id}}">
    <img src="/uploads/${{p.filename}}" loading="lazy">
    <div class="pcb">
      <div class="pct">📷 ${{fmt(p.uploaded_at)}}</div>
      ${{tab==='approved'?'<span class="abadge">✓ En carrusel</span>':''}}
      <div class="acts">
        ${{tab==='pending'
          ?`<button class="bapp" onclick="act(${{p.id}},'approve')">✓ Aprobar</button><button class="brej" onclick="act(${{p.id}},'reject')">✗ Rechazar</button>`
          :`<button class="brej" onclick="act(${{p.id}},'reject')" style="flex:1">✗ Quitar</button>`
        }}
      </div>
    </div>
  </div>`;
}}
async function load(){{
  const r=await fetch('/api/photos?status='+cur);
  const photos=await r.json();
  if(cur==='pending') document.getElementById('cnt').textContent=photos.length+' pendientes';
  const g=document.getElementById('g-'+cur);
  g.innerHTML=photos.length
    ?photos.map(p=>card(p,cur)).join('')
    :`<div class="empty"><span class="empty-i">${{cur==='pending'?'🎉':'📸'}}</span>${{cur==='pending'?'No hay fotos pendientes':'Ninguna foto aprobada aún'}}</div>`;
}}
async function act(id,a){{
  const c=document.getElementById('c'+id);
  if(c){{c.style.opacity='.3';c.style.pointerEvents='none';}}
  await fetch('/api/photos/'+id+'/'+a,{{method:'POST'}});
  load();
}}
load();
setInterval(load,60000);
</script>
</body></html>'''

# ══════════════════════════════════════════════════════════
#  CONFIGURATION PAGE
# ══════════════════════════════════════════════════════════
@app.route('/configuracion', methods=['GET','POST'])
@login_required
def configuracion():
    saved = False
    cleared = False

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'save':
            new_name = request.form.get('event_name','').strip()
            new_pass = request.form.get('mod_password','').strip()
            if new_name:
                set_config('event_name', new_name)
            if new_pass:
                set_config('mod_password', new_pass)
            saved = True
        elif action == 'clear':
            # Delete all photos from disk
            for fn in os.listdir(UPLOAD_FOLDER):
                fp = os.path.join(UPLOAD_FOLDER, fn)
                try:
                    os.remove(fp)
                except:
                    pass
            # Delete all photo records from DB
            with get_db() as db:
                db.execute('DELETE FROM photos')
                db.commit()
            cleared = True

    event = get_config('event_name', 'Photo Wall')
    pwd   = get_config('mod_password', 'admin123')

    with get_db() as db:
        total    = db.execute("SELECT COUNT(*) FROM photos").fetchone()[0]
        approved = db.execute("SELECT COUNT(*) FROM photos WHERE status='approved'").fetchone()[0]
        pending  = db.execute("SELECT COUNT(*) FROM photos WHERE status='pending'").fetchone()[0]

    return f'''<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Configuración · {event}</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{--neon:#FF3CAC;--neon2:#784BA0;--neon3:#2B86C5;--dark:#0a0a0f}}
body{{font-family:'DM Sans',sans-serif;background:var(--dark);color:#fff;min-height:100vh}}
body::before{{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 80% 20%,rgba(255,60,172,.15) 0%,transparent 50%);pointer-events:none}}
header{{position:relative;z-index:1;padding:16px 20px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.02)}}
.htitle{{font-family:'Bebas Neue',sans-serif;font-size:1.5rem;background:linear-gradient(135deg,#FF3CAC,#FFD700);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.bsm{{padding:7px 14px;border-radius:8px;border:none;font-size:.82rem;font-weight:500;cursor:pointer;transition:all .2s;background:rgba(255,255,255,.06);color:rgba(255,255,255,.55);border:1px solid rgba(255,255,255,.1);font-family:'DM Sans',sans-serif;text-decoration:none;display:inline-block}}
.bsm:hover{{color:#fff;background:rgba(255,255,255,.12)}}
.page{{position:relative;z-index:1;max-width:600px;margin:0 auto;padding:24px 20px}}
.section{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:18px;padding:24px;margin-bottom:20px}}
.section h2{{font-family:'Bebas Neue',sans-serif;font-size:1.3rem;letter-spacing:.06em;margin-bottom:18px;color:#fff}}
label{{display:block;font-size:.85rem;color:rgba(255,255,255,.5);margin-bottom:6px;margin-top:14px}}
label:first-of-type{{margin-top:0}}
input[type=text],input[type=password]{{width:100%;padding:12px 14px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.14);border-radius:10px;color:#fff;font-size:.95rem;font-family:'DM Sans',sans-serif;outline:none;transition:border-color .2s}}
input:focus{{border-color:var(--neon)}}
.hint{{font-size:.75rem;color:rgba(255,255,255,.25);margin-top:4px}}
.bsave{{margin-top:18px;padding:13px 28px;font-family:'Bebas Neue',sans-serif;font-size:1.2rem;letter-spacing:.08em;border:none;border-radius:10px;cursor:pointer;background:linear-gradient(135deg,var(--neon),var(--neon2));color:#fff;transition:all .3s}}
.bsave:hover{{transform:translateY(-2px);box-shadow:0 6px 20px rgba(255,60,172,.4)}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:18px}}
.stat{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:14px;text-align:center}}
.stat-n{{font-family:'Bebas Neue',sans-serif;font-size:2rem;background:linear-gradient(135deg,var(--neon),var(--neon3));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.stat-l{{font-size:.75rem;color:rgba(255,255,255,.35);margin-top:2px}}
.danger{{border-color:rgba(255,60,60,.2)}}
.danger h2{{color:#ff6b6b}}
.bclear{{margin-top:4px;padding:13px 28px;font-family:'Bebas Neue',sans-serif;font-size:1.2rem;letter-spacing:.08em;border:none;border-radius:10px;cursor:pointer;background:rgba(255,60,60,.12);border:1px solid rgba(255,60,60,.3);color:#ff6b6b;transition:all .3s}}
.bclear:hover{{background:rgba(255,60,60,.22)}}
.flash-ok{{background:rgba(0,255,150,.08);border:1px solid rgba(0,255,150,.28);color:#00ff96;padding:12px 16px;border-radius:10px;margin-bottom:18px;font-size:.9rem}}
.flash-warn{{background:rgba(255,200,0,.08);border:1px solid rgba(255,200,0,.28);color:#ffd700;padding:12px 16px;border-radius:10px;margin-bottom:18px;font-size:.9rem}}
</style></head>
<body>
<header>
  <div class="htitle">⚙️ CONFIGURACIÓN</div>
  <a href="/moderador" class="bsm">← Volver al panel</a>
</header>
<div class="page">
  {"<div class='flash-ok'>✅ Configuración guardada correctamente</div>" if saved else ""}
  {"<div class='flash-warn'>🗑️ Todas las fotos fueron eliminadas</div>" if cleared else ""}

  <!-- Stats -->
  <div class="section">
    <h2>📊 Estado del evento</h2>
    <div class="stats">
      <div class="stat"><div class="stat-n">{total}</div><div class="stat-l">Total fotos</div></div>
      <div class="stat"><div class="stat-n">{approved}</div><div class="stat-l">En pantalla</div></div>
      <div class="stat"><div class="stat-n">{pending}</div><div class="stat-l">Pendientes</div></div>
    </div>
  </div>

  <!-- Event config -->
  <div class="section">
    <h2>🎉 Datos del evento</h2>
    <form method="POST">
      <input type="hidden" name="action" value="save">
      <label>Nombre del evento</label>
      <input type="text" name="event_name" value="{event}" placeholder="Ej: Boda Juan y Ana">
      <div class="hint">Aparece en la pantalla del proyector y en la página de subida</div>
      <label>Nueva contraseña del moderador</label>
      <input type="password" name="mod_password" placeholder="Dejá vacío para no cambiarla">
      <div class="hint">Contraseña actual: {pwd}</div>
      <button type="submit" class="bsave">💾 GUARDAR CAMBIOS</button>
    </form>
  </div>

  <!-- Danger zone -->
  <div class="section danger">
    <h2>🗑️ Borrar todo al terminar</h2>
    <p style="color:rgba(255,255,255,.45);font-size:.88rem;margin-bottom:16px">Elimina todas las fotos del servidor y limpia la base de datos. Usalo cuando termine el evento. Esta acción no se puede deshacer.</p>
    <form method="POST" onsubmit="return confirm('¿Estás seguro? Se borrarán TODAS las fotos permanentemente.')">
      <input type="hidden" name="action" value="clear">
      <button type="submit" class="bclear">🗑️ BORRAR TODAS LAS FOTOS</button>
    </form>
  </div>
</div>
</body></html>'''

# ══════════════════════════════════════════════════════════
#  PHOTOS API
# ══════════════════════════════════════════════════════════
@app.route('/api/photos')
@login_required
def api_photos():
    status = request.args.get('status', 'pending')
    with get_db() as db:
        photos = db.execute(
            'SELECT * FROM photos WHERE status=? ORDER BY uploaded_at DESC', (status,)
        ).fetchall()
    return jsonify([dict(p) for p in photos])

@app.route('/api/photos/approved-display')
def api_approved_display():
    with get_db() as db:
        photos = db.execute(
            'SELECT * FROM photos WHERE status="approved" ORDER BY uploaded_at ASC'
        ).fetchall()
    return jsonify([dict(p) for p in photos])

@app.route('/api/photos/<int:pid>/approve', methods=['POST'])
@login_required
def approve_photo(pid):
    with get_db() as db:
        db.execute('UPDATE photos SET status="approved" WHERE id=?', (pid,))
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/photos/<int:pid>/reject', methods=['POST'])
@login_required
def reject_photo(pid):
    with get_db() as db:
        photo = db.execute('SELECT filename FROM photos WHERE id=?', (pid,)).fetchone()
        if photo:
            fp = os.path.join(app.config['UPLOAD_FOLDER'], photo['filename'])
            if os.path.exists(fp):
                os.remove(fp)
        db.execute('DELETE FROM photos WHERE id=?', (pid,))
        db.commit()
    return jsonify({'ok': True})

# ══════════════════════════════════════════════════════════
#  DISPLAY (PROJECTOR) — 16:10 optimized
# ══════════════════════════════════════════════════════════
@app.route('/display')
def display():
    event = get_config('event_name', 'Photo Wall')
    host = request.host_url.rstrip('/')
    upload_url = host + '/upload'
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={upload_url}&bgcolor=0a0a0f&color=FF3CAC&margin=2"

    return f'''<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📸 {event}</title>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{--neon:#FF3CAC;--neon2:#784BA0;--neon3:#2B86C5;--gold:#FFD700;--dark:#0a0a0f}}

html,body{{width:100%;height:100%;overflow:hidden;background:var(--dark);color:#fff;font-family:'DM Sans',sans-serif}}

/* 16:10 stage — always fills the screen without distortion */
.stage{{
  position:fixed;inset:0;
  display:flex;align-items:center;justify-content:center;
  background:var(--dark);
}}
.stage::before{{
  content:'';position:absolute;inset:0;
  background:
    radial-gradient(ellipse at 15% 30%,rgba(255,60,172,.15) 0%,transparent 50%),
    radial-gradient(ellipse at 85% 70%,rgba(120,75,160,.15) 0%,transparent 50%),
    radial-gradient(ellipse at 50% 50%,rgba(43,134,197,.08) 0%,transparent 60%);
  animation:bgpulse 12s ease-in-out infinite alternate;
}}
@keyframes bgpulse{{0%{{opacity:.8}}100%{{opacity:1;filter:hue-rotate(25deg)}}}}

.canvas{{
  position:relative;
  width:100vw;
  height:calc(100vw * 10 / 16);
  max-height:100vh;
  max-width:calc(100vh * 16 / 10);
}}

/* ── Empty state ── */
.empty{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:2}}
.empty.hide{{display:none}}
.empty-title{{font-family:'Bebas Neue',sans-serif;font-size:clamp(3rem,9vw,8rem);background:linear-gradient(135deg,var(--neon),var(--gold));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1;text-align:center;animation:breathe 3s ease-in-out infinite}}
@keyframes breathe{{0%,100%{{transform:scale(1);opacity:1}}50%{{transform:scale(.97);opacity:.85}}}}
.empty-sub{{color:rgba(255,255,255,.35);font-size:clamp(.8rem,1.8vw,1.3rem);letter-spacing:.2em;text-transform:uppercase;margin-top:12px}}

/* ── Swiper ── */
.sw-wrap{{position:absolute;inset:0;z-index:1;display:none}}
.swiper,.swiper-slide{{width:100%;height:100%}}
.swiper-slide{{display:flex;align-items:center;justify-content:center;overflow:hidden}}
.swiper-slide img{{width:100%;height:100%;object-fit:contain;animation:kenburns 9s ease-in-out forwards}}
@keyframes kenburns{{from{{transform:scale(1)}}to{{transform:scale(1.06)}}}}

/* ── Top bar ── */
.topbar{{position:absolute;top:0;left:0;right:0;height:clamp(44px,6vh,64px);z-index:5;display:flex;align-items:center;justify-content:space-between;padding:0 clamp(12px,2vw,24px);background:linear-gradient(to bottom,rgba(10,10,15,.85),transparent);pointer-events:none}}
.topbar-name{{font-family:'Bebas Neue',sans-serif;font-size:clamp(1.1rem,2.5vw,2rem);background:linear-gradient(135deg,var(--neon),var(--gold));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:.08em}}
.topbar-count{{font-size:clamp(.65rem,1.2vw,.9rem);color:rgba(255,255,255,.35);letter-spacing:.1em}}

/* ── QR panel ── */
.qr{{position:absolute;right:0;bottom:0;width:clamp(140px,16vw,240px);background:rgba(10,10,15,.93);backdrop-filter:blur(20px);border-top-left-radius:clamp(14px,2vw,22px);border:1px solid rgba(255,60,172,.22);border-right:none;border-bottom:none;padding:clamp(12px,1.5vw,20px);text-align:center;z-index:10;animation:slideqr 1.2s ease-out}}
@keyframes slideqr{{from{{transform:translate(100%,100%);opacity:0}}to{{transform:translate(0,0);opacity:1}}}}
.qr-lbl{{font-family:'Bebas Neue',sans-serif;font-size:clamp(.75rem,1.3vw,1.1rem);background:linear-gradient(135deg,var(--neon),var(--gold));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:.08em;margin-bottom:clamp(6px,1vw,12px);line-height:1.3}}
.qr img{{width:100%;max-width:clamp(90px,12vw,170px);border-radius:clamp(6px,1vw,12px);border:2px solid rgba(255,60,172,.3)}}
.qr-url{{margin-top:clamp(4px,.6vw,8px);font-size:clamp(.5rem,.8vw,.7rem);color:rgba(255,255,255,.28);word-break:break-all}}

/* ── Toast ── */
.toast{{position:absolute;top:clamp(48px,7vh,72px);left:50%;transform:translateX(-50%) translateY(-16px);background:linear-gradient(135deg,rgba(255,60,172,.92),rgba(120,75,160,.92));backdrop-filter:blur(16px);color:#fff;padding:clamp(7px,1vh,11px) clamp(16px,2vw,26px);border-radius:30px;font-size:clamp(.75rem,1.2vw,.95rem);font-weight:500;z-index:20;opacity:0;transition:all .4s;pointer-events:none;white-space:nowrap}}
.toast.show{{opacity:1;transform:translateX(-50%) translateY(0)}}
</style></head>
<body>
<div class="stage">
  <div class="canvas">
    <!-- top bar -->
    <div class="topbar">
      <div class="topbar-name">✨ {event}</div>
      <div class="topbar-count" id="cnt"></div>
    </div>

    <!-- toast -->
    <div class="toast" id="toast"></div>

    <!-- empty -->
    <div class="empty" id="empty">
      <div class="empty-title">📸<br>{event}</div>
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
      <div class="qr-lbl">📸 COMPARTÍ<br>TU FOTO</div>
      <img src="{qr_url}" alt="QR" onerror="this.style.display='none'">
      <div class="qr-url">{upload_url}</div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js"></script>
<script>
let sw=null, known=new Set(), ready=false;

function initSw(){{
  if(sw)return;
  sw=new Swiper('#sw',{{loop:true,autoplay:{{delay:5000,disableOnInteraction:false}},speed:1200,effect:'fade',fadeEffect:{{crossFade:true}},pagination:{{el:'.swiper-pagination'}}}});
}}

function toast(msg){{
  const t=document.getElementById('toast');
  t.textContent=msg;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),3500);
}}

async function load(){{
  try{{
    const r=await fetch('/api/photos/approved-display');
    const photos=await r.json();
    document.getElementById('cnt').textContent=photos.length>0?photos.length+' fotos':'';

    if(!photos.length){{
      document.getElementById('empty').classList.remove('hide');
      document.getElementById('swWrap').style.display='none';
      return;
    }}
    document.getElementById('empty').classList.add('hide');
    document.getElementById('swWrap').style.display='block';

    const news=photos.filter(p=>!known.has(p.id));
    if(news.length&&ready) toast('📸 '+news.length+' foto'+(news.length>1?'s nuevas':'  nueva')+' agregada'+(news.length>1?'s':''));

    if(news.length||!ready){{
      const wrap=document.getElementById('swSlides');
      wrap.innerHTML='';
      photos.forEach(p=>{{
        known.add(p.id);
        const s=document.createElement('div');
        s.className='swiper-slide';
        s.innerHTML=`<img src="/uploads/${{p.filename}}" alt="">`;
        wrap.appendChild(s);
      }});
      if(!ready){{initSw();ready=true;}}
      else{{sw.update();}}
    }}
  }}catch(e){{console.error(e);}}
}}

load();
setInterval(load,60000);
</script>
</body></html>'''

# ══════════════════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════════════════
if __name__=='__main__':
    port=int(os.environ.get('PORT',5000))
    app.run(debug=False,host='0.0.0.0',port=port)
