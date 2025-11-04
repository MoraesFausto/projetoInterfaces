from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
import serial
import threading
import uvicorn

app = FastAPI()
umidade = 0
lock = threading.Lock()

# Configura a porta serial
try:
    ser = serial.Serial('/dev/ttyUSB1', 115200)
    print("Porta serial aberta com sucesso.")
except serial.SerialException as e:
    print(f"Erro ao abrir a porta serial: {e}")
    ser = None

def ler_serial():
    global umidade
    if ser:
        while True:
            if ser.in_waiting > 0:
                leitura = ser.readline().decode('utf-8').strip()
                print(f"Leitura da porta serial: {leitura}")
                with lock:
                    umidade = leitura
                print(f"Umidade atualizada: {umidade}")

@app.on_event("startup")
def startup_event():
    serial_thread = threading.Thread(target=ler_serial, daemon=True)
    serial_thread.start()

@app.get("/", response_class=HTMLResponse)
async def index():
    return '''
        <!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Monitor de Umidade</title>
  <style>
    :root{
      --bg:#0f172a; /* slate-900 */
      --card:#0b1220;
      --muted:#9aa4b2;
      --accent:#60a5fa; /* default blue */
      --glass: rgba(255,255,255,0.04);
      --radius:18px;
    }
    *{box-sizing:border-box}
    html,body{height:100%}
    body{
      margin:0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
      background: radial-gradient(1200px 600px at 10% 10%, rgba(96,165,250,0.08), transparent 5%), radial-gradient(900px 400px at 90% 90%, rgba(236,72,153,0.04), transparent 10%), var(--bg);
      color:#e6eef8;
      display:flex;
      align-items:center;
      justify-content:center;
      padding:32px;
    }

    .card{
      width:min(520px,96vw);
      background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(0,0,0,0.02));
      border-radius:var(--radius);
      padding:22px;
      box-shadow: 0 10px 30px rgba(2,6,23,0.6);
      border: 1px solid rgba(255,255,255,0.04);
      display:flex;
      gap:20px;
      align-items:center;
    }

    .left{
      display:flex;
      flex-direction:column;
      gap:10px;
      flex:1 1 220px;
    }

    h1{
      margin:0;
      font-size:20px;
      letter-spacing:0.2px;
    }
    p.lead{margin:0;color:var(--muted);font-size:13px}

    .gauge-wrap{display:flex;align-items:center;gap:20px}

    .gauge{
      --pct: 0%;
      width:150px;height:150px;border-radius:50%;
      display:grid;place-items:center;
      padding:14px;
      background: conic-gradient(var(--accent) var(--pct), #e6e6e6 0%);
      box-shadow: inset 0 -6px 18px rgba(0,0,0,0.45), 0 6px 22px rgba(2,6,23,0.6);
      position:relative;
    }
    .gauge::after{
      content:"";
      position:absolute;inset:12px;border-radius:50%;background:var(--card);z-index:0;
      box-shadow: 0 2px 8px rgba(2,6,23,0.6);
    }
    .gauge-inner{
      position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
      width:100%;height:100%;border-radius:50%;
      color:inherit;
    }
    .value{
      font-weight:700;font-size:32px;line-height:1;transition:all 400ms cubic-bezier(.2,.9,.26,1);
    }
    .unit{font-size:12px;color:var(--muted);margin-left:6px}

    .meta{display:flex;flex-direction:column;gap:8px}
    .meta .row{display:flex;gap:8px;align-items:center}
    .muted{color:var(--muted);font-size:13px}

    .controls{display:flex;gap:8px;margin-top:6px}
    button{background:var(--glass);color:inherit;border:1px solid rgba(255,255,255,0.04);padding:8px 12px;border-radius:10px;cursor:pointer;font-weight:600}
    button:active{transform:translateY(1px)}

    .small{font-size:12px;color:var(--muted)}

    /* responsive */
    @media (max-width:520px){
      .card{flex-direction:column;align-items:stretch}
      .gauge{width:132px;height:132px}
    }

  </style>
</head>
<body>
  <main class="card" role="main" aria-labelledby="titulo">
    <section class="left">
      <div>
        <h1 id="titulo">Monitor de Umidade</h1>
        <p class="lead">Leitura em tempo real da umidade do sensor. Atualiza automaticamente a cada 2 segundos.</p>
      </div>

      <div class="meta">
        <div class="row"><span class="muted">Última leitura:</span> <span id="last">—</span></div>
        <div class="row"><span class="muted">Status:</span> <span id="status">Conectando...</span></div>

        <div class="controls">
          <button id="refresh" title="Atualizar agora">🔄 Atualizar</button>
          <button id="pause" title="Pausar atualizações">⏸️ Pausar</button>
        </div>
      </div>
    </section>

    <aside class="gauge-wrap">
      <div class="gauge" role="img" aria-label="Indicador de umidade" id="gauge" style="--pct:0%">
        <div class="gauge-inner">
          <div style="display:flex;align-items:baseline">
            <div id="umidade" class="value">—</div>
            <div class="unit">%</div>
          </div>
          <div class="small" id="trend">—</div>
        </div>
      </div>
    </aside>
  </main>

  <script>
    (function(){
      const umidadeEl = document.getElementById('umidade');
      const gauge = document.getElementById('gauge');
      const lastEl = document.getElementById('last');
      const statusEl = document.getElementById('status');
      const trendEl = document.getElementById('trend');
      const refreshBtn = document.getElementById('refresh');
      const pauseBtn = document.getElementById('pause');

      let intervalId = null;
      let paused = false;
      let previous = null;

      function setAccentFor(value){
        // define cor conforme o nível
        let color = '#60a5fa'; // azul
        if (value >= 75) color = '#fb7185'; // vermelho suave
        else if (value >= 55) color = '#f59e0b'; // amarelo
        else if (value <= 30) color = '#34d399'; // verde
        document.documentElement.style.setProperty('--accent', color);
      }

      function setGauge(value){
        // atualiza texto e gauge visual
        umidadeEl.textContent = (Math.round(value*10)/10).toString();
        gauge.style.setProperty('--pct', value + '%');
        setAccentFor(value);

        // trend
        if (previous === null) trendEl.textContent = '—';
        else if (value > previous) trendEl.textContent = 'Subindo ↑';
        else if (value < previous) trendEl.textContent = 'Descendo ↓';
        else trendEl.textContent = 'Estável —';

        previous = value;
      }

      async function atualizarUmidade(){
        try{
          const res = await fetch('/umidade', {cache:'no-store'});
          if (!res.ok) throw new Error('Resposta não OK: ' + res.status);
          const data = await res.json();
          const value = Number(data.umidade);
          if (Number.isFinite(value)){
            setGauge(value);
            const now = new Date();
            lastEl.textContent = now.toLocaleString();
            statusEl.textContent = 'Online';
            statusEl.style.color = '';
          } else {
            throw new Error('Valor inválido recebido');
          }
        }catch(err){
          console.error('Erro ao buscar a umidade:', err);
          statusEl.textContent = 'Erro ao conectar';
          statusEl.style.color = '#fb7185';
          umidadeEl.textContent = '—';
          trendEl.textContent = '—';
        }
      }

      function startInterval(){
        if (intervalId) clearInterval(intervalId);
        intervalId = setInterval(()=>{ if(!paused) atualizarUmidade(); }, 2000);
      }

      refreshBtn.addEventListener('click', () => { atualizarUmidade(); });
      pauseBtn.addEventListener('click', () => {
        paused = !paused;
        pauseBtn.textContent = paused ? '▶️ Retomar' : '⏸️ Pausar';
        pauseBtn.title = paused ? 'Retomar atualizações' : 'Pausar atualizações';
      });

      // primeira leitura imediata
      atualizarUmidade();
      startInterval();

      // acessibilidade: permitir atualizar com tecla R
      window.addEventListener('keydown', (e) => {
        if (e.key.toLowerCase() === 'r') atualizarUmidade();
      });
    })();
  </script>
</body>
</html>

    '''

@app.get('/umidade')
async def umidade_api():
    with lock:
        current_umidade = umidade
    return {'umidade': current_umidade}

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5000)