import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, BarChart, Bar, PieChart, Pie, Cell } from 'recharts'

function usePoll<T>(fn:()=>Promise<T>, ms:number, deps:any[]=[]){
  const [data,setData]=useState<T|null>(null)
  const [err,setErr]=useState<string|null>(null)
  useEffect(()=>{
    let alive=true, timer:any
    async function tick(){ try{ const d=await fn(); if(alive){setData(d); setErr(null)} }catch(e:any){ if(alive) setErr(String(e?.message||e)) } }
    tick(); timer=setInterval(tick,ms)
    return()=>{ alive=false; clearInterval(timer)}
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },deps)
  return {data, err}
}

export default function App(){
  const status = usePoll(()=>api.status(), 4000)
  const portfolio = usePoll(()=>api.portfolio(), 5000)
  const openPositions = usePoll(()=>api.openPositions(), 5000)
  const capital = usePoll(()=>api.capital(), 5000)
  const market = usePoll(()=>api.market(), 5000)
  const perf = usePoll(()=>api.performance(), 7000)
  const exp = usePoll(()=>api.experiment(), 6000)
  const health = usePoll(()=>api.health(), 8000)
  const alerts = usePoll(()=>api.alerts(), 8000)
  const [tradesFilter,setTradesFilter]=useState<'all'|'open'|'closed'>('all')
  const trades = usePoll(()=>api.trades(tradesFilter), 6000, [tradesFilter])
  const [logLevel,setLogLevel]=useState<'all'|'error'|'warning'>('all')
  const [paused,setPaused]=useState(false)
  const logs = usePoll(()=> paused ? Promise.resolve({logs: [] as string[]}) : api.logs(180, logLevel), 4000, [paused, logLevel])
  const logRef=useRef<HTMLDivElement>(null)
  useEffect(()=>{ if(!paused) logRef.current?.scrollTo({top: logRef.current.scrollHeight}) },[logs.data])

  // market filter for Live Market Data
  const [marketFilter,setMarketFilter]=useState<'all'|'AL'|'SAT'|'BEKLE'>('all')

  const marketFiltered = useMemo(()=>{
    const pairs = (market.data as any)?.pairs || []
    if(marketFilter==='all') return pairs
    return pairs.filter((p:any)=> p.signal===marketFilter)
  },[market.data, marketFilter])

  const buyCount = (market.data as any)?.buys ?? (market.data as any)?.pairs?.filter((p:any)=>p.signal==='AL').length ?? 0
  const sellCount = (market.data as any)?.sells ?? 0
  const totalScanned = (market.data as any)?.count ?? (market.data as any)?.pairs?.length ?? 0

  // Live ticker WebSocket — dinamik universe, son 60s, gorsel (500ms throttle)
  const [liveMap, setLiveMap] = useState<Record<string,{price:number, history:{t:number,p:number}[], change:number, changePct:number, dir:'up'|'down'|null}>>({})
  // derive universe symbols for WS
  const wsSymbols = useMemo(()=>{
    const pairs = (market.data as any)?.pairs || []
    return pairs.slice(0,30).map((p:any)=> (p.pair as string).replace('/','').toLowerCase())
  },[market.data])
  const wsPairs = useMemo(()=>{
    const pairs = (market.data as any)?.pairs || []
    return pairs.slice(0,30).map((p:any)=> p.pair as string)
  },[market.data])

  useEffect(()=>{
    if(wsSymbols.length===0) return
    let ws: WebSocket | null = null
    let retry: any = null
    let fallback: any = null
    let alive = true
    const streams = wsSymbols.map((s:string)=> `${s}@trade`).join('/')
    const url = `wss://stream.binance.com:9443/stream?streams=${streams}`
    const pairBySym: Record<string,string> = {}
    wsSymbols.forEach((sym:string,i:number)=>{
      const pair = wsPairs[i]
      if(pair) pairBySym[sym.toUpperCase()] = pair
    })
    const buffer: Record<string,{price:number,t:number}[]> = {}
    let lastFlush = 0
    function flush(){
      const now = Date.now()
      if(now - lastFlush < 500) return
      lastFlush = now
      if(Object.keys(buffer).length===0) return
      setLiveMap(prev=>{
        const next = {...prev}
        for(const pair of Object.keys(buffer)){
          const q = buffer[pair]
          if(!q || q.length===0) continue
          const last = q[q.length-1]
          const price = last.price
          const prevEntry = prev[pair] || {price, history:[], change:0, changePct:0, dir: null as any}
          const prevPrice = prevEntry.price
          const dir = price > prevPrice ? 'up' as const : price < prevPrice ? 'down' as const : (prevEntry.dir || 'up' as const)
          const hist = [...prevEntry.history]
          for(const pt of q) hist.push({t: pt.t, p: pt.price})
          const filtered = hist.filter(h=> now - h.t < 60000)
          const trimmed = filtered.length>60 ? filtered.slice(-60) : filtered
          const base = trimmed[0]?.p ?? price
          const change = price - base
          const changePct = base ? (change / base * 100) : 0
          next[pair] = {price, history: trimmed, change, changePct, dir}
          buffer[pair]=[]
        }
        return next
      })
    }
    const flushInt = setInterval(flush, 500)
    function connect(){
      try{
        ws = new WebSocket(url)
        ws.onmessage = (ev)=>{
          try{
            const msg = JSON.parse(ev.data)
            const d = msg.data
            if(!d || !d.p) return
            const sym = d.s as string
            const pair = pairBySym[sym] || null
            if(!pair) return
            const price = parseFloat(d.p)
            const now = Date.now()
            if(!buffer[pair]) buffer[pair]=[]
            buffer[pair].push({price, t: now})
          }catch{}
        }
        ws.onclose = ()=>{ if(alive) retry = setTimeout(connect, 3000) }
        ws.onerror = ()=>{ try{ ws?.close() }catch{} }
      }catch{
        if(alive) retry = setTimeout(connect, 3000)
      }
    }
    connect()
    fallback = setInterval(()=>{
      if(!ws || ws.readyState !== 1){
        ;(async()=>{
          for(const pair of wsPairs.slice(0,6)){
            try{
              const j = await api.price(pair)
              const price = j.price
              if(!price) continue
              const now = Date.now()
              if(!buffer[pair]) buffer[pair]=[]
              buffer[pair].push({price, t: now})
            }catch{}
          }
        })()
      }
    }, 1500)
    return ()=>{ alive=false; try{ ws?.close() }catch{}; clearTimeout(retry); clearInterval(fallback); clearInterval(flushInt) }
  },[wsSymbols.join(','), wsPairs.join(',')])

  const tfData = usePoll(()=> (fetch('/api/market/timeframes?limit=6').then(r=>r.json()) as Promise<any>), 30000)

  const equity = perf.data?.equity || []
  const drawdown = perf.data?.drawdown || []
  const daily = perf.data?.daily || []
  const stats = perf.data?.stats

  const pnlBuckets = useMemo(()=>{
    const tr = trades.data?.trades?.filter((t:any)=>t.close_profit_abs!=null) || []
    if(!tr.length) return []
    const vals = tr.map((t:any)=>Number(t.close_profit_abs))
    const min=Math.min(...vals), max=Math.max(...vals)
    const bins=8; const step=(max-min)/bins || 1
    const buckets=Array.from({length:bins},(_,i)=>({range:`${(min+i*step).toFixed(2)}-${(min+(i+1)*step).toFixed(2)}`, count:0}))
    vals.forEach((v:number)=>{ const idx=Math.min(bins-1, Math.max(0, Math.floor((v-min)/step))); buckets[idx].count++ })
    return buckets
  },[trades.data])

  const winLoss = useMemo(()=>[
    {name:'Win', value: stats?.winning||0, color:'#2dd4a0'},
    {name:'Loss', value: stats?.losing||0, color:'#ff5a68'},
  ],[stats])

  const filteredTrades = useMemo(()=>{
    let t = trades.data?.trades || []
    return t
  },[trades.data])

  const uptimeHours = status.data?.uptime_seconds ? (status.data.uptime_seconds / 3600).toFixed(1) : null
  const fmtDurH = (s:number)=> (s/3600).toFixed(1)
  const fmtDurM = (s:number)=> (s/60).toFixed(0)

  async function ctrl(a:string){
    try{ const r=await api.control(a); alert(`${a}: ${JSON.stringify(r).slice(0,800)}`) }catch(e:any){ alert(e.message)}
  }

  return (
    <div>
      <div className="header">
        <div style={{display:'flex',alignItems:'center',gap:12}}>
          <div style={{width:10,height:10,borderRadius:999, background: status.data?.bot_status==='RUNNING'?'#2dd4a0':'#ff5a68', boxShadow: status.data?.bot_status==='RUNNING'?'0 0 8px rgba(45,212,160,.6)':''}} />
          <div>
            <div style={{fontWeight:800,letterSpacing:.02+'em'}}>ZEN-GENIE <span style={{color:'#8aa0b8',fontWeight:600}}>FAZ-1 TERMINAL</span></div>
            <div style={{fontSize:11,color:'#8aa0b8'}} className="mono">{status.data?.strategy||'BaselineStrategy'} · {status.data?.exchange?.toUpperCase()||'BINANCE'} · {status.data?.trading_mode||'DRY-RUN'}</div>
          </div>
          <span className={status.data?.bot_status==='RUNNING'?'badge badge-run':'badge badge-stop'} style={{marginLeft:8}}>{status.data?.bot_status||'...'}</span>
          {status.data?.bot_status!=='RUNNING' && <span style={{marginLeft:8, color:'#ff5a68', fontWeight:700, fontSize:12, border:'1px solid rgba(255,90,104,.4)', padding:'4px 8px', borderRadius:999}}>BOT STOPPED — CHECK HEALTH</span>}
        </div>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <span className="badge" style={{borderColor:'#243548',background:'#0f1a26',color:'#8aa0b8'}}>LIVE TRADING: DISABLED</span>
          <span className="mono" style={{fontSize:11,color:'#8aa0b8'}}>hb: {status.data?.heartbeat||'—'} · up {uptimeHours ? `${uptimeHours}h` : '—'}</span>
          <button className="btn" onClick={()=>location.reload()}>Refresh</button>
        </div>
      </div>

      <div className="layout">
        <div className="card" style={{borderColor: exp.data?.locked? 'rgba(45,212,160,.35)' : '#1e2d3d', background: exp.data?.locked? 'linear-gradient(180deg, rgba(45,212,160,.06), #111820)' : undefined}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',flexWrap:'wrap',gap:10}}>
            <div>
              <div style={{fontSize:11,letterSpacing:.12+'em',color:'#8aa0b8',fontWeight:700}}>EXPERIMENT STATUS</div>
              <div style={{fontSize:18,fontWeight:800,marginTop:4}}>{exp.data?.phase||'PHASE 1 — DRY RUN'} <span style={{fontSize:12,marginLeft:8,padding:'3px 8px',borderRadius:999,border:'1px solid rgba(45,212,160,.35)',color:'#2dd4a0'}}>{exp.data?.lock_text||'Phase 1 → LOCKED'}</span> <span className={exp.data?.status==='RUNNING'?'badge badge-run':'badge badge-stop'} style={{marginLeft:6}}>{exp.data?.status||'RUNNING'}</span></div>
              <div className="mono" style={{fontSize:11,color:'#8aa0b8',marginTop:4}}>start: {exp.data?.started_at||'—'} · elapsed: {exp.data?.elapsed_human||'—'} · required: 7 days · verify: {exp.data?.verification?.passed}/{exp.data?.verification?.total}</div>
            </div>
            <div style={{minWidth:360, flex:1, maxWidth:520}}>
              <div style={{display:'flex',justifyContent:'space-between',fontSize:11,color:'#8aa0b8',marginBottom:6}}><span>{exp.data?.observation||'0 / 7 days'}</span><span>{(exp.data?.progress_pct||0).toFixed(2)}%</span></div>
              <div className="progress"><div style={{width:`${Math.min(100, exp.data?.progress_pct||0)}%`}} /></div>
              <div style={{fontSize:11,color:'#5e758d',marginTop:6}}>Faz 1 7 gun dolmadan Faz 2-3 gelistirme kapali.</div>
            </div>
          </div>
        </div>

        <div className="grid" style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(170px, 1fr))', gap:12}}>
          <div className="card kpi" style={{padding:'12px'}}>
            <div className="label mono" style={{fontSize:10, color:'#8aa0b8', letterSpacing:.08+'em', fontWeight:700}}>PORTFÖY DEĞERİ</div>
            <div className="mono" style={{fontSize:11, color:'#5e758d', marginTop:6}}>Başlangıç: <span style={{color:'#e6eef6', fontWeight:700}}>${portfolio.data?.starting_balance?.toFixed(2) ?? '—'}</span></div>
            <div className="mono" style={{fontSize:13, fontWeight:800, marginTop:2}}>Güncel: <span style={{color:'#e6eef6'}}>${portfolio.data?.current_value?.toFixed(2) ?? '—'}</span></div>
            <div className="mono" style={{fontSize:12, fontWeight:800, marginTop:6, color: (portfolio.data?.total_pnl||0)>=0 ? '#2dd4a0' : '#ff5a68'}}>
              {(portfolio.data?.total_pnl||0)>=0?'+':''}${(portfolio.data?.total_pnl||0).toFixed(2)} <span style={{fontSize:11}}>({(portfolio.data?.return_pct||0).toFixed(2)}%)</span>
            </div>
            <div className="mono" style={{fontSize:9, color:'#5e758d', marginTop:2}}>toplam P/L • { (portfolio.data?.realized_pnl||0).toFixed(2)} realized / {(portfolio.data?.unrealized_pnl||0).toFixed(2)} unrealized</div>
          </div>
          <div className="card kpi" style={{padding:'12px', borderColor: openPositions.data?.count>0 ? 'rgba(45,212,160,.25)' : '#1e2d3d', background: openPositions.data?.count>0 ? 'linear-gradient(180deg, rgba(45,212,160,.06), #111820)' : undefined}}>
            <div className="label mono" style={{fontSize:10, color:'#8aa0b8', letterSpacing:.08+'em', fontWeight:700}}>AÇIK POZİSYONLAR</div>
            <div className="mono" style={{fontWeight:800, fontSize:22, marginTop:6}}>{openPositions.data?.summary?.open_count ?? portfolio.data?.open_trades_count ?? 0}<span style={{color:'#5e758d', fontSize:14}}>/{openPositions.data?.summary?.max_open_trades ?? 3}</span></div>
            <div style={{display:'flex', gap:4, flexWrap:'wrap', marginTop:6, minHeight:22}}>
              {(openPositions.data?.positions||[]).slice(0,5).map((p:any)=>(
                <span key={p.pair} className="pill" style={{background:'rgba(45,212,160,.12)', color:'#2dd4a0', border:'1px solid rgba(45,212,160,.25)', fontSize:10, fontWeight:700, padding:'2px 6px'}}>{p.pair.split('/')[0]}</span>
              ))}
              {(!openPositions.data?.positions || openPositions.data.positions.length===0) && <span className="mono" style={{fontSize:11, color:'#5e758d'}}>{portfolio.data?.open_trades_count===0 ? '— Ne aldım? Henüz yok' : 'Yükleniyor...'}</span>}
              {(openPositions.data?.positions||[]).length>5 && <span className="mono" style={{fontSize:10, color:'#8aa0b8'}}>+{openPositions.data.positions.length-5}</span>}
            </div>
            <div className="mono" style={{fontSize:9, color:'#5e758d', marginTop:4}}>Ne aldım? • kâr/zarar aşağıda</div>
          </div>
          <div className="card kpi" style={{padding:'12px'}}>
            <div className="label mono" style={{fontSize:10, color:'#8aa0b8', letterSpacing:.08+'em', fontWeight:700}}>YATIRILAN</div>
            <div className="mono" style={{fontWeight:800, fontSize:18, marginTop:6}}>${openPositions.data?.summary?.total_invested?.toFixed(2) ?? '—'}</div>
            <div className="mono" style={{fontSize:10, color:'#8aa0b8', marginTop:2}}>Toplam stake • bağlı dolar</div>
            <div className="mono" style={{fontSize:9, color:'#5e758d', marginTop:4}}>{openPositions.data?.summary?.open_count||0} pozisyon • avg ${openPositions.data?.summary?.total_invested && openPositions.data.summary.open_count ? (openPositions.data.summary.total_invested/openPositions.data.summary.open_count).toFixed(2) : '—'}/poz</div>
          </div>
          <div className="card kpi" style={{padding:'12px'}}>
            <div className="label mono" style={{fontSize:10, color:'#8aa0b8', letterSpacing:.08+'em', fontWeight:700}}>SERBEST BAKİYE</div>
            <div className="mono" style={{fontWeight:800, fontSize:18, marginTop:6}}>${openPositions.data?.summary?.free_balance?.toFixed(2) ?? (portfolio.data?.starting_balance!=null && portfolio.data?.realized_pnl!=null && openPositions.data?.summary?.total_invested!=null ? ((portfolio.data.starting_balance + portfolio.data.realized_pnl) * (openPositions.data.summary.tradable_ratio ?? 0.99) - openPositions.data.summary.total_invested).toFixed(2) : '—')}</div>
            <div className="mono" style={{fontSize:10, color:'#8aa0b8', marginTop:2}}>kullanılabilir USDT</div>
            <div className="mono" style={{fontSize:9, color:'#5e758d', marginTop:4}}>wallet ${openPositions.data?.summary?.wallet?.toFixed(2) ?? (portfolio.data?.starting_balance!=null && portfolio.data?.realized_pnl!=null ? (portfolio.data.starting_balance + portfolio.data.realized_pnl).toFixed(2) : portfolio.data?.starting_balance?.toFixed(2) ?? '—')} • {(openPositions.data?.summary?.tradable_ratio||0.99)*100}% tradable</div>
          </div>
          <div className="card kpi" style={{padding:'12px'}}>
            <div className="label mono" style={{fontSize:10, color:'#8aa0b8', letterSpacing:.08+'em', fontWeight:700}}>POZİSYON DEĞERİ</div>
            <div className="mono" style={{fontWeight:800, fontSize:18, marginTop:6}}>${openPositions.data?.summary?.total_value?.toFixed(2) ?? '—'}</div>
            <div className="mono" style={{fontSize:10, color:'#8aa0b8', marginTop:2}}>güncel toplam piyasa değeri</div>
            <div className="mono" style={{fontSize:9, color: (openPositions.data?.summary?.total_unrealized_abs||0)>=0 ? '#2dd4a0' : '#ff5a68', marginTop:4}}>{(openPositions.data?.summary?.total_unrealized_abs||0)>=0?'+':''}${(openPositions.data?.summary?.total_unrealized_abs||0).toFixed(2)} ({(openPositions.data?.summary?.total_unrealized_pct||0).toFixed(2)}%) unrealized</div>
          </div>
        </div>

        {/* CORE CAPITAL & USDT REZERV — strateji bağımsız risk katmanı */}
        <div className="card" style={{background:'linear-gradient(180deg, rgba(245,200,110,.08), #111820)', borderColor:'rgba(245,200,110,.30)', borderWidth:1}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12, flexWrap:'wrap', gap:8}}>
            <div>
              <h3 style={{margin:0, display:'flex', alignItems:'center', gap:8}}>
                <span style={{background:'#f5c86e', color:'#1a1200', fontSize:10, padding:'2px 6px', borderRadius:4, fontWeight:800, letterSpacing:'.06em'}}>RISK</span>
                CORE CAPITAL & REZERV <span style={{color:'#8aa0b8', fontWeight:400, fontSize:13, marginLeft:4}}>USDT Koruma Katmanı</span>
                <span className="mono" style={{fontSize:9, color:'#f5c86e', border:'1px solid rgba(245,200,110,.3)', padding:'2px 6px', borderRadius:999}}>STRATEJİ BAĞIMSIZ</span>
              </h3>
              <div className="mono" style={{fontSize:10,color:'#8aa0b8',marginTop:4}}>Başlangıç sermayesi kilitli • Kâr periyodik olarak rezerve ayrıştırılır • Trading sermayesi korunur</div>
            </div>
            <div style={{display:'flex',alignItems:'center',gap:8}}>
              <span className="badge" style={{background:'rgba(245,200,110,.15)', color:'#f5c86e', borderColor:'rgba(245,200,110,.30)', fontWeight:700}}>
                CORE {capital.data?.core_capital?.toFixed(2) ?? '—'} USDT 🔒
              </span>
              <button className="btn" style={{fontSize:11, padding:'4px 8px', borderColor: capital.data?.harvest?.should_harvest ? '#f5c86e' : '#1e2d3d', background: capital.data?.harvest?.should_harvest ? 'rgba(245,200,110,.15)' : '', color: capital.data?.harvest?.should_harvest ? '#f5c86e' : '#8aa0b8'}} onClick={async()=>{
                try{
                  const r=await api.capitalHarvest(true)
                  alert(`Harvest: +$${r.harvested?.toFixed(2)} → Rezerv $${r.view?.reserve_balance?.toFixed(2)}`)
                }catch(e:any){ alert('Harvest hata: '+String(e.message||e)) }
              }} title="Kârın koruma payını rezerve aktar (dry-run sanal)">
                Hasat Et
              </button>
            </div>
          </div>

          {capital.data && (
            <div className="grid" style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(155px, 1fr))', gap:10, marginBottom:12}}>
              <div style={{background:'#0f1a26', border:'1px solid rgba(245,200,110,.30)', borderRadius:8, padding:'10px'}}>
                <div className="mono" style={{fontSize:9,color:'#f5c86e', letterSpacing:.06+'em', fontWeight:700}}>CORE CAPITAL 🔒</div>
                <div className="mono" style={{fontWeight:800, fontSize:18, marginTop:4}}>${capital.data.core_capital?.toFixed(2)}</div>
                <div className="mono" style={{fontSize:9,color:'#8aa0b8', marginTop:2}}>kilitli {capital.data.core_locked_at?.slice(0,10)} • risk dışı</div>
                <div className="mono" style={{fontSize:9,color: capital.data.core_protected ? '#2dd4a0' : '#ff5a68', marginTop:4}}>{capital.data.core_protected ? '✓ Core korunuyor' : '⚠ Core risk altında'}</div>
              </div>
              <div style={{background:'#0f1a26', border:'1px solid rgba(245,200,110,.35)', borderRadius:8, padding:'10px'}}>
                <div className="mono" style={{fontSize:9,color:'#f5c86e', letterSpacing:.06+'em', fontWeight:700}}>PROTECTION THRESHOLD 🛡️</div>
                <div className="mono" style={{fontWeight:800, fontSize:18, marginTop:4, color:'#f5c86e'}}>${capital.data.protection_threshold?.toFixed(2)}</div>
                <div className="mono" style={{fontSize:9,color:'#8aa0b8', marginTop:2}}>core + locked • trailing</div>
                <div className="mono" style={{fontSize:9, color: capital.data.protection_status==='protected' ? '#2dd4a0' : capital.data.protection_status==='watch' ? '#f5c86e' : '#ff5a68', marginTop:4}}>
                  {capital.data.protection_status==='protected' ? `✓ Korunuyor (+$${capital.data.distance_to_protection?.toFixed(2)})` : capital.data.protection_status==='watch' ? `→ Mesafe $${capital.data.distance_to_protection?.toFixed(2)}` : '⚠ Eşik altı'}
                </div>
              </div>
              <div style={{background:'#0f1a26', border:'1px solid rgba(255,193,7,.25)', borderRadius:8, padding:'10px'}}>
                <div className="mono" style={{fontSize:9,color:'#ffc107', letterSpacing:.06+'em', fontWeight:700}}>KORUMA HAKKI / THEORETICAL LOCK</div>
                <div className="mono" style={{fontWeight:800, fontSize:18, marginTop:4, color:'#ffc107'}}>${capital.data.locked_profit_theoretical?.toFixed(2) ?? capital.data.locked_profit?.toFixed(2)}</div>
                <div className="mono" style={{fontSize:9,color:'#8aa0b8', marginTop:2}}>teorik • HWM ${capital.data.high_water_mark?.toFixed(2)} • ${(capital.data.protection?.lock_ratio??0.5)*100}%</div>
                <div className="mono" style={{fontSize:9,color:'#5e758d', marginTop:4}}>henüz ayrışmadı • realized bekler</div>
              </div>
              <div style={{background:'#0f1a26', border: capital.data.actual_reserve>0 ? '1px solid rgba(45,212,160,.30)' : '1px solid #13202e', borderRadius:8, padding:'10px'}}>
                <div className="mono" style={{fontSize:9,color: capital.data.actual_reserve>0 ? '#2dd4a0' : '#5e758d', letterSpacing:.06+'em', fontWeight:700}}>GERÇEK REZERV / ACTUAL RESERVE</div>
                <div className="mono" style={{fontWeight:800, fontSize:18, marginTop:4, color: capital.data.actual_reserve>0 ? '#2dd4a0' : '#8aa0b8'}}>${capital.data.actual_reserve?.toFixed(2) ?? capital.data.reserve_balance?.toFixed(2)}</div>
                <div className="mono" style={{fontSize:9,color:'#8aa0b8', marginTop:2}}>USDT • fiilen ayrışmış • realized tabanlı</div>
                <div className="mono" style={{fontSize:9,color: capital.data.actual_reserve>0 ? '#2dd4a0' : '#5e758d', marginTop:4}}>{capital.data.actual_reserve>0 ? `✓ ${capital.data.actual_reserve.toFixed(2)} USDT korundu` : '— Henüz ayrışma yok (realized=0)'}</div>
              </div>
              <div style={{background:'#0f1a26', border:'1px solid #13202e', borderRadius:8, padding:'10px'}}>
                <div className="mono" style={{fontSize:9,color:'#8aa0b8', letterSpacing:.06+'em', fontWeight:700}}>GERÇEKLEŞMİŞ KÂR</div>
                <div className="mono" style={{fontWeight:800, fontSize:16, marginTop:4, color: (capital.data.realized_profit||0)>=0 ? '#2dd4a0' : '#ff5a68'}}>
                  {(capital.data.realized_profit||0)>=0?'+':''}${capital.data.realized_profit?.toFixed(2)}
                </div>
                <div className="mono" style={{fontSize:9,color:'#8aa0b8', marginTop:2}}>kümülatif • unharvested ${capital.data.unharvested_profit?.toFixed(2)}</div>
                <div className="mono" style={{fontSize:9, color: capital.data.net_positive ? '#2dd4a0' : '#5e758d', marginTop:4}}>{capital.data.net_positive ? '✓ Net pozitif > CORE' : '→ Hedef: equity > CORE'}</div>
              </div>
              <div style={{background:'#0f1a26', border:'1px solid #13202e', borderRadius:8, padding:'10px'}}>
                <div className="mono" style={{fontSize:9,color:'#8aa0b8', letterSpacing:.06+'em', fontWeight:700}}>TOPLAM ÖZKAYNAK</div>
                <div className="mono" style={{fontWeight:800, fontSize:18, marginTop:4}}>${capital.data.total_equity?.toFixed(2)}</div>
                <div className="mono" style={{fontSize:9, color: (capital.data.equity_vs_core_pct||0)>=0 ? '#2dd4a0' : '#ff5a68', marginTop:2}}>
                  {(capital.data.equity_vs_core_pct||0)>=0?'+':''}{capital.data.equity_vs_core_pct?.toFixed(2)}% vs CORE
                </div>
                <div className="mono" style={{fontSize:9,color:'#5e758d', marginTop:4}}>core + realized + unrealized ${capital.data.unrealized_pnl?.toFixed(2)}</div>
              </div>
              <div style={{background:'#0f1a26', border:'1px solid #13202e', borderRadius:8, padding:'10px'}}>
                <div className="mono" style={{fontSize:9,color:'#8aa0b8', letterSpacing:.06+'em', fontWeight:700}}>TRADING SERMAYESİ</div>
                <div className="mono" style={{fontWeight:800, fontSize:15, marginTop:4}}>${capital.data.trading_capital?.toFixed(2)}</div>
                <div className="mono" style={{fontSize:9,color:'#8aa0b8', marginTop:2}}>core + unharvested</div>
                <div className="mono" style={{fontSize:9,color:'#5e758d', marginTop:4}}>unharvested ${capital.data.unharvested_profit?.toFixed(2)} • unreal ${capital.data.unrealized_pnl?.toFixed(2)}</div>
              </div>
            </div>
          )}
          {capital.data?.protection && (
            <div className="mono" style={{fontSize:10, color:'#8aa0b8', background:'#0f1a26', border:'1px solid rgba(245,200,110,.20)', borderRadius:8, padding:'8px 10px', display:'flex', justifyContent:'space-between', flexWrap:'wrap', gap:8}}>
              <span>Protection: <b style={{color:'#f5c86e'}}>Lock {capital.data.protection.lock_ratio*100}%</b> • {capital.data.protection.mode} • Trailing {capital.data.protection.trailing?'evet':'hayır'}</span>
              <span>HWM: <b>${capital.data.protection.high_water_mark?.toFixed(2)}</b> • Threshold: <b style={{color:'#f5c86e'}}>${capital.data.protection.threshold?.toFixed(2)}</b> • Mesafe: <b style={{color: (capital.data.protection.distance||0)>=0 ? '#2dd4a0' : '#ff5a68'}}>${capital.data.protection.distance?.toFixed(2)}</b></span>
              <span>Status: <b style={{color: capital.data.protection.status==='protected' ? '#2dd4a0' : capital.data.protection.status==='watch' ? '#f5c86e' : '#ff5a68'}}>{capital.data.protection.status==='protected'?'✓ Korunuyor':capital.data.protection.status==='watch'?'→ İzleniyor':'⚠ Core risk'}</b> • {capital.data.core_protected?'Core güvende':'Core risk'}</span>
            </div>
          )}
          {capital.data?.harvest && (
            <div className="mono" style={{fontSize:9, color:'#5e758d', background:'#0a121c', border:'1px solid #13202e', borderRadius:6, padding:'6px 8px', display:'flex', justifyContent:'space-between', flexWrap:'wrap', gap:8, marginTop:6}}>
              <span>Harvest: {capital.data.harvest.period} • {capital.data.harvest.ratio*100}% • eşik ${capital.data.harvest.threshold} {capital.data.harvest.auto_enabled?'• auto':''}</span>
              <span>Son: {capital.data.harvest.last_harvest_at ? String(capital.data.harvest.last_harvest_at).slice(0,19).replace('T',' ') : '—'} {capital.data.harvest.last_harvest_amount ? `(+$${capital.data.harvest.last_harvest_amount.toFixed(2)})` : ''}</span>
            </div>
          )}
          {!capital.data && <div className="mono" style={{fontSize:11,color:'#5e758d', textAlign:'center', padding:12}}>Rezerv yükleniyor...</div>}
          {capital.err && <div style={{color:'#ff5a68', fontSize:11, marginTop:8}}>capital error: {capital.err}</div>}
        </div>

        {/* AÇIK POZİSYONLAR — ilk ekranda görünür: Balance/Summary sonrası, Live Market Data üstü */}
        <div className="card" style={{background:'linear-gradient(180deg, rgba(45,212,160,.04), #111820)', borderColor: openPositions.data?.count>0 ? 'rgba(45,212,160,.25)' : '#1e2d3d'}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12, flexWrap:'wrap', gap:8}}>
            <div>
              <h3 style={{margin:0}}>AÇIK POZİSYONLAR <span style={{color:'#5e758d', fontWeight:400, fontSize:13}}> / OPEN POSITIONS</span></h3>
              <div className="mono" style={{fontSize:10,color:'#8aa0b8',marginTop:2}}>Doğrudan Freqtrade DB (is_open=1) + Binance güncel fiyat — dashboard tahmini değil</div>
            </div>
            <div style={{display:'flex',alignItems:'center',gap:8}}>
              <span className="badge" style={{background: openPositions.data?.count>0 ? 'rgba(45,212,160,.15)' : 'rgba(245,200,110,.12)', color: openPositions.data?.count>0 ? '#2dd4a0' : '#f5c86e', borderColor: openPositions.data?.count>0 ? 'rgba(45,212,160,.35)' : 'rgba(245,200,110,.3)'}}>
                {openPositions.data?.summary?.open_label || `${portfolio.data?.open_trades_count||0}/3`} AÇIK
              </span>
              <span className="mono" style={{fontSize:10,color:'#5e758d'}}>dry-run • {openPositions.data?.positions?.length||0} pozisyon • 5sn polling</span>
            </div>
          </div>

          {openPositions.data?.summary && (
            <div className="grid cols-4" style={{gap:8, marginBottom:14, gridTemplateColumns:'repeat(auto-fit, minmax(150px, 1fr))'}}>
              <div style={{background:'#0f1a26', border: openPositions.data.summary.open_count>=openPositions.data.summary.max_open_trades ? '1px solid rgba(255,90,104,.3)' : '1px solid #13202e', borderRadius:8, padding:'10px'}}>
                <div className="mono" style={{fontSize:9,color:'#5e758d', letterSpacing:.06+'em'}}>AÇIK POZİSYON</div>
                <div className="mono" style={{fontWeight:800, fontSize:18, marginTop:4}}>{openPositions.data.summary.open_count}/{openPositions.data.summary.max_open_trades}</div>
                <div className="mono" style={{fontSize:10,color: openPositions.data.summary.open_count>=openPositions.data.summary.max_open_trades ? '#ff5a68' : '#8aa0b8'}}>{openPositions.data.summary.open_count>=openPositions.data.summary.max_open_trades ? 'Limit dolu — yeni AL kuyrukta' : 'Yeni sinyal alınabilir'}</div>
              </div>
              <div style={{background:'#0f1a26', border:'1px solid #13202e', borderRadius:8, padding:'10px'}}>
                <div className="mono" style={{fontSize:9,color:'#5e758d', letterSpacing:.06+'em'}}>TOPLAM YATIRILAN</div>
                <div className="mono" style={{fontWeight:800, fontSize:15, marginTop:4}}>${openPositions.data.summary.total_invested?.toFixed(2) ?? '0.00'}</div>
                <div className="mono" style={{fontSize:10,color:'#8aa0b8'}}>stake toplam</div>
              </div>
              <div style={{background:'#0f1a26', border:'1px solid #13202e', borderRadius:8, padding:'10px'}}>
                <div className="mono" style={{fontSize:9,color:'#5e758d', letterSpacing:.06+'em'}}>GÜNCEL DEĞER</div>
                <div className="mono" style={{fontWeight:800, fontSize:15, marginTop:4}}>${openPositions.data.summary.total_value?.toFixed(2) ?? '0.00'}</div>
                <div className="mono" style={{fontSize:10,color:'#8aa0b8'}}>amount × güncel fiyat</div>
              </div>
              <div style={{background:'#0f1a26', border:'1px solid #13202e', borderRadius:8, padding:'10px'}}>
                <div className="mono" style={{fontSize:9,color:'#5e758d', letterSpacing:.06+'em'}}>UNREALIZED P/L</div>
                <div className="mono" style={{fontWeight:800, fontSize:15, marginTop:4, color: (openPositions.data.summary.total_unrealized_abs||0)>=0 ? '#2dd4a0' : '#ff5a68'}}>
                  {(openPositions.data.summary.total_unrealized_abs||0)>=0?'+':''}${(openPositions.data.summary.total_unrealized_abs||0).toFixed(2)} <span style={{fontSize:11}}>({(openPositions.data.summary.total_unrealized_pct||0).toFixed(2)}%)</span>
                </div>
                <div className="mono" style={{fontSize:10,color:'#8aa0b8'}}>gerçekleşmemiş</div>
              </div>
              <div style={{background:'#0f1a26', border:'1px solid #13202e', borderRadius:8, padding:'10px'}}>
                <div className="mono" style={{fontSize:9,color:'#5e758d', letterSpacing:.06+'em'}}>SERBEST BAKİYE</div>
                <div className="mono" style={{fontWeight:800, fontSize:15, marginTop:4}}>${openPositions.data.summary.free_balance?.toFixed(2) ?? '—'}</div>
                <div className="mono" style={{fontSize:10,color:'#8aa0b8'}}>wallet ${openPositions.data.summary.wallet?.toFixed(2)} • tradable {openPositions.data.summary.tradable_ratio*100}%</div>
              </div>
            </div>
          )}

          {(!openPositions.data || openPositions.data.count===0) ? (
            <div style={{height:140,display:'grid',placeItems:'center',color:'#5e758d',border:'1px dashed #1e2d3d',borderRadius:8, background:'#0f1a26'}}>
              <div style={{textAlign:'center'}}>
                <div style={{fontSize:13, fontWeight:700}}>Açık pozisyon yok</div>
                <div className="mono" style={{fontSize:11, marginTop:4}}>AL sinyali geldiğinde sanal pozisyon burada görünecek (dry-run)</div>
                <div className="mono" style={{fontSize:10,color:'#5e758d', marginTop:6}}>Kapanan pozisyon otomatik olarak TRADE HISTORY'e taşınır</div>
              </div>
            </div>
          ) : (
            <div style={{display:'grid', gap:12, gridTemplateColumns:'repeat(auto-fill, minmax(340px, 1fr))'}}>
              {(openPositions.data.positions||[]).map((pos:any)=>{
                const pnlUp = (pos.unrealized_abs||0) >=0
                const base = pos.base_currency || pos.pair.split('/')[0]
                const side = pos.side || 'LONG'
                return (
                  <div key={pos.id} className="card" style={{background:'#0f1a26', borderColor: pnlUp ? 'rgba(45,212,160,.25)' : 'rgba(255,90,104,.25)', padding:'12px'}}>
                    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center', marginBottom:10, paddingBottom:8, borderBottom:'1px solid #1e2d3d'}}>
                      <div className="mono" style={{fontSize:14, fontWeight:800}}>{pos.pair} <span style={{color:'#5e758d', fontWeight:400}}>· {side}</span></div>
                      <span className="mono" style={{fontWeight:800, fontSize:13, color: pnlUp ? '#2dd4a0' : '#ff5a68'}}>
                        {pnlUp?'+':''}${pos.unrealized_abs?.toFixed(2)} ({pnlUp?'+':''}{pos.unrealized_pct?.toFixed(2)}%)
                      </span>
                    </div>
                    <div style={{display:'grid', gap:6}}>
                      <div style={{display:'flex',justifyContent:'space-between', fontSize:12}}>
                        <span className="mono" style={{color:'#8aa0b8'}}>Miktar:</span>
                        <span className="mono" style={{fontWeight:700}}>{pos.amount} {base}</span>
                      </div>
                      <div style={{display:'flex',justifyContent:'space-between', fontSize:12}}>
                        <span className="mono" style={{color:'#8aa0b8'}}>Giriş:</span>
                        <span className="mono" style={{fontWeight:700}}>${pos.open_rate?.toLocaleString(undefined,{maximumFractionDigits:2})}</span>
                      </div>
                      <div style={{display:'flex',justifyContent:'space-between', fontSize:12}}>
                        <span className="mono" style={{color:'#8aa0b8'}}>Güncel:</span>
                        <span className="mono" style={{fontWeight:700, color: pnlUp ? '#2dd4a0' : '#ff5a68'}}>${pos.current_price?.toLocaleString(undefined,{maximumFractionDigits:2})}</span>
                      </div>
                      <div style={{display:'flex',justifyContent:'space-between', fontSize:12}}>
                        <span className="mono" style={{color:'#8aa0b8'}}>Kullanılan:</span>
                        <span className="mono" style={{fontWeight:600}}>${pos.stake_amount?.toFixed(2)}</span>
                      </div>
                      <div style={{display:'flex',justifyContent:'space-between', fontSize:12}}>
                        <span className="mono" style={{color:'#8aa0b8'}}>Güncel Değer:</span>
                        <span className="mono" style={{fontWeight:700}}>${pos.value?.toFixed(2)}</span>
                      </div>
                      <div style={{display:'flex',justifyContent:'space-between', fontSize:12, background: pnlUp ? 'rgba(45,212,160,.08)' : 'rgba(255,90,104,.08)', padding:'6px 8px', borderRadius:6, border: `1px solid ${pnlUp ? 'rgba(45,212,160,.18)' : 'rgba(255,90,104,.18)'}`}}>
                        <span className="mono" style={{color: pnlUp ? '#2dd4a0' : '#ff5a68', fontWeight:800}}>P/L:</span>
                        <span className="mono" style={{fontWeight:800, color: pnlUp ? '#2dd4a0' : '#ff5a68'}}>
                          {pnlUp?'+':''}${pos.unrealized_abs?.toFixed(2)} ({pnlUp?'+':''}{pos.unrealized_pct?.toFixed(2)}%)
                        </span>
                      </div>
                      <div style={{display:'flex',justifyContent:'space-between', fontSize:11}}>
                        <span className="mono" style={{color:'#5e758d'}}>Açılış:</span>
                        <span className="mono" style={{fontSize:10, color:'#cbd9ea'}}>{String(pos.open_date).slice(0,19).replace('T',' ')}</span>
                      </div>
                      <div style={{display:'flex',justifyContent:'space-between', fontSize:11}}>
                        <span className="mono" style={{color:'#5e758d'}}>Süre:</span>
                        <span className="mono" style={{fontSize:10}}>{pos.duration_seconds ? `${fmtDurH(pos.duration_seconds)}h` : '—'} • #{pos.id}</span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
          {openPositions.err && <div style={{color:'#ff5a68', fontSize:11, marginTop:8}}>open_positions error: {openPositions.err}</div>}
        </div>

        <div className="card" style={{background: 'linear-gradient(180deg, rgba(59,130,246,.05), #111820)', borderColor: 'rgba(59,130,246,.3)'}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:10, flexWrap:'wrap', gap:8}}>
            <div style={{display:'flex',alignItems:'center',gap:10, flexWrap:'wrap'}}>
              <h3 style={{margin:0}}>Live Market Data</h3>
              <span className="badge" style={{background:'rgba(59,130,246,.15)',color:'#3b82f6',borderColor:'rgba(59,130,246,.3)'}}>{(market.data as any)?.watched || `İzlenen Pariteler: ${totalScanned||2}`}</span>
              <span className="mono" style={{fontSize:10,color:'#8aa0b8'}}>taranan {totalScanned} · AL {buyCount} · SAT {sellCount} · BEKLE {totalScanned-buyCount-sellCount}</span>
              {(market.data as any)?.last_refresh && <span className="mono" style={{fontSize:9,color:'#5e758d'}}>refresh {(market.data as any).last_refresh.slice(11,19)} UTC</span>}
            </div>
            <div style={{display:'flex',gap:6, alignItems:'center', flexWrap:'wrap'}}>
              {(['all','AL','SAT','BEKLE'] as const).map(f=>(
                <button key={f} className="btn" style={{padding:'4px 10px', fontSize:11, borderColor: marketFilter===f? '#3b82f6':'#1e2d3d', background: marketFilter===f?'rgba(59,130,246,.18)':'', color: marketFilter===f?'#3b82f6':'#8aa0b8'}} onClick={()=>setMarketFilter(f)}>
                  {f==='all' ? `TÜMÜ (${totalScanned})` : `${f} (${f==='AL'?buyCount: f==='SAT'?sellCount: totalScanned-buyCount-sellCount})`}
                </button>
              ))}
            </div>
          </div>

          {buyCount>0 && (
            <div style={{background:'linear-gradient(180deg, rgba(45,212,160,.12), rgba(45,212,160,.04))', border:'1px solid rgba(45,212,160,.35)', borderRadius:10, padding:'10px 12px', marginBottom:12}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center', flexWrap:'wrap', gap:8}}>
                <div style={{display:'flex',alignItems:'center',gap:8}}>
                  <span style={{background:'#2dd4a0', color:'#081410', fontWeight:800, fontSize:11, padding:'3px 8px', borderRadius:999}}>AL SİNYALLERİ</span>
                  <span className="mono" style={{fontSize:12, fontWeight:700, color:'#2dd4a0'}}>{buyCount} paritede AL</span>
                  <span className="mono" style={{fontSize:10,color:'#8aa0b8'}}>Freqtrade max_open_trades={(status as any).data?.config_safe?.max_open_trades ?? 3} — fazla sinyalde risk limitine göre seçim</span>
                </div>
                <span className="mono" style={{fontSize:10,color:'#5e758d'}}>strateji: RSI(14)&lt;30 & SMA50&gt;SMA200 — kapalı 5m mum</span>
              </div>
              <div style={{display:'flex',gap:6,flexWrap:'wrap', marginTop:8}}>
                {((market.data as any)?.buy_pairs || (market.data as any)?.pairs?.filter((p:any)=>p.signal==='AL').map((p:any)=>p.pair) || []).map((pair:string)=>(
                  <span key={pair} className="pill" style={{background:'rgba(45,212,160,.18)', color:'#2dd4a0', border:'1px solid rgba(45,212,160,.4)', fontWeight:800, fontSize:11}}>{pair} ● AL</span>
                ))}
              </div>
            </div>
          )}

          {marketFiltered.length===0 && (market.data as any)?.pairs?.length>0 && (
            <div className="mono" style={{textAlign:'center', padding:20, color:'#8aa0b8', border:'1px dashed #1e2d3d', borderRadius:8, marginBottom:12}}>
              {marketFilter} sinyali yok — {marketFilter==='AL' ? 'Tümü BEKLE/SAT durumunda' : `${marketFilter} filtresi boş`}
            </div>
          )}

          <div className="grid cols-2" style={{gap:12}}>
            {marketFiltered.map((p:any)=>(
              <div key={p.pair} className="card" style={{background:'#0f1a26', borderColor: p.signal==='AL'?'rgba(45,212,160,.5)': p.signal==='SAT'?'rgba(255,90,104,.45)':'#1e2d3d', boxShadow: p.signal==='AL'?'0 0 12px rgba(45,212,160,.12)':''}}>
                <div style={{display:'flex',justifyContent:'space-between',alignItems:'baseline',marginBottom:8}}>
                  <div className="mono" style={{fontSize:17,fontWeight:800}}>{p.pair}</div>
                  <span className="pill" style={{
                    background: p.signal==='AL'?'rgba(45,212,160,.2)': p.signal==='SAT'?'rgba(255,90,104,.2)':'rgba(59,130,246,.15)',
                    color: p.signal==='AL'?'#2dd4a0': p.signal==='SAT'?'#ff5a68':'#3b82f6',
                    fontSize:12, fontWeight:700
                  }}>{p.signal || 'BEKLE'}</span>
                </div>
                <div style={{display:'flex',alignItems:'baseline',gap:10,marginBottom:6}}>
                  <div className="mono" style={{fontSize:22,fontWeight:800}}>${p.price?.toLocaleString(undefined,{maximumFractionDigits:2}) ?? '—'}</div>
                  <span className="pill" style={{background: (p.change_24h||0)>=0? 'rgba(45,212,160,.15)':'rgba(255,90,104,.15)', color:(p.change_24h||0)>=0?'#2dd4a0':'#ff5a68'}}>{(p.change_24h||0).toFixed(2)}% 24h</span>
                </div>
                <div className="mono" style={{fontSize:11,color:'#8aa0b8',display:'flex',gap:10,marginBottom:8,flexWrap:'wrap'}}>
                  <span>5m {p.change_5m!=null? `${p.change_5m.toFixed(2)}%`:'—'}</span>
                  <span>15m {p.change_15m!=null? `${p.change_15m.toFixed(2)}%`:'—'}</span>
                  <span>1h {p.change_1h!=null? `${p.change_1h.toFixed(2)}%`:'—'}</span>
                  <span>Vol {p.volume?.toLocaleString()??'—'}</span>
                  {p.quoteVolume!=null && <span>QVol {(p.quoteVolume/1e6).toFixed(1)}M</span>}
                </div>
                {(()=>{
                  const live = (liveMap as any)[p.pair]
                  const hasLive = live && live.history && live.history.length>1
                  return (
                    <div style={{background:'#0a121c',border:'1px solid #1e2d3d',borderRadius:8,padding:'8px',marginTop:8}}>
                      <div style={{display:'flex',justifyContent:'space-between',fontSize:9,color:'#5e758d'}}>
                        <span>Live Price · Son 60 saniye</span>
                        <span style={{color: !hasLive ? '#5e758d' : live.dir==='up' ? '#2dd4a0' : '#ff5a68', fontWeight:700}}>
                          {!hasLive ? '● baglaniyor...' : `${live.dir==='up'?'▲':'▼'} ${live.change>=0?'+':''}${live.change.toFixed(2)} (${live.changePct>=0?'+':''}${live.changePct.toFixed(3)}%)`}
                        </span>
                      </div>
                      <div style={{display:'flex',alignItems:'baseline',gap:8,marginTop:4}}>
                        <span className="mono" style={{fontSize:17,fontWeight:800,color: !hasLive ? '#e6eef6' : live.dir==='up' ? '#2dd4a0' : live.dir==='down' ? '#ff5a68' : '#e6eef6', transition:'color 0.15s'}}>{hasLive ? `$${live.price.toLocaleString(undefined,{maximumFractionDigits:2})}` : `$${p.price?.toLocaleString(undefined,{maximumFractionDigits:2}) ?? '—'}`}</span>
                        <span className="mono" style={{fontSize:9,color:'#5e758d'}}>{hasLive ? 'ticker · WebSocket' : 'ticker · polling'}</span>
                      </div>
                      <div style={{height:42,marginTop:6}}>
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart data={hasLive ? live.history : [{t:Date.now(),p:p.price||0}]}>
                            <Tooltip contentStyle={{background:'#0f1a26',border:'1px solid #1e2d3d',fontSize:10}} formatter={(v:any)=>[`$${Number(v).toFixed(2)}`,'fiyat']} labelFormatter={()=>''} />
                            <Area type="monotone" dataKey="p" stroke={hasLive ? (live.dir==='up'?'#2dd4a0':'#ff5a68') : '#3b82f6'} fill={hasLive ? (live.dir==='up'?'rgba(45,212,160,.14)':'rgba(255,90,104,.14)') : 'rgba(59,130,246,.12)'} strokeWidth={1.5} dot={false} isAnimationActive={false} />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )
                })()}
                <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:8,marginTop:8}}>
                  <div style={{background:'#0a121c',border:'1px solid #1e2d3d',borderRadius:8,padding:'8px'}}>
                    <div className="label mono" style={{fontSize:9,color:'#5e758d'}}>RSI</div>
                    <div className="mono" style={{fontWeight:700,fontSize:16,color: (p.rsi!==null && p.rsi!==undefined && p.rsi<30)?'#2dd4a0':(p.rsi!==null && p.rsi!==undefined && p.rsi>70)?'#ff5a68':'#e6eef6'}}>{p.rsi?.toFixed(1) ?? '—'}</div>
                    <div className="mono" style={{fontSize:9,color:'#5e758d'}}>14p</div>
                  </div>
                  <div style={{background:'#0a121c',border:'1px solid #1e2d3d',borderRadius:8,padding:'8px'}}>
                    <div className="label mono" style={{fontSize:9,color:'#5e758d'}}>SMA50</div>
                    <div className="mono" style={{fontWeight:700,fontSize:14}}>{p.sma50?.toLocaleString(undefined,{maximumFractionDigits:2}) ?? '—'}</div>
                    <div className="mono" style={{fontSize:9,color:'#5e758d'}}>50p</div>
                  </div>
                  <div style={{background:'#0a121c',border:'1px solid #1e2d3d',borderRadius:8,padding:'8px'}}>
                    <div className="label mono" style={{fontSize:9,color:'#5e758d'}}>SMA200</div>
                    <div className="mono" style={{fontWeight:700,fontSize:14}}>{p.sma200?.toLocaleString(undefined,{maximumFractionDigits:2}) ?? '—'}</div>
                    <div className="mono" style={{fontSize:9,color:'#5e758d'}}>200p</div>
                  </div>
                </div>
                <div style={{display:'flex',justifyContent:'space-between',fontSize:10,marginTop:8,padding:'6px 8px',background:'#0a121c',border:'1px solid #1e2d3d',borderRadius:6}}>
                  <span>SİNYAL: <b style={{color: p.signal==='AL'?'#2dd4a0':p.signal==='SAT'?'#ff5a68':'#3b82f6'}}>{p.signal}</b></span>
                  <span>POZİSYON: <b style={{color: p.position==='YOK'?'#8aa0b8':'#f5c86e'}}>{p.position}</b></span>
                </div>
                <div className="mono" style={{fontSize:9,color:'#5e758d',marginTop:6,display:'flex',justifyContent:'space-between'}}>
                  <span>Son: {p.last_evaluation || '—'}</span>
                  <span>Sonraki: {p.next_evaluation || 'sonraki 5m candle'}</span>
                </div>
                <div className="mono" style={{fontSize:8,color:'#3b82f6',marginTop:2,opacity:0.8}}>TA-Lib Wilder RSI — Freqtrade ile birebir · kapalı mum</div>
                <div style={{display:'flex',justifyContent:'space-between',fontSize:9,color:'#5e758d',marginTop:8}}>
                  <span>5m Strateji (kapalı mumlar)</span>
                  <span className="mono" style={{fontSize:8}}>sinyal kaynagi</span>
                </div>
                <div style={{marginTop:4, height:80}}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={(p.klines||[]).slice(-48).map((k:any,i:number)=>({i,c:k.c}))}>
                      <Tooltip contentStyle={{background:'#0f1a26',border:'1px solid #1e2d3d',fontSize:11}} />
                      <Area type="monotone" dataKey="c" stroke="#3b82f6" fill="rgba(59,130,246,.18)" strokeWidth={1.6} dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ))}
          </div>
          {!market.data && <div className="mono" style={{textAlign:'center', padding:20, color:'#5e758d'}}>Yükleniyor — Binance USDT universe keşfediliyor...</div>}
          {market.data && marketFiltered.length===0 && <div className="mono" style={{textAlign:'center', padding:12, color:'#5e758d'}}>Filtre boş</div>}
        </div>

        <div className="card">
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:10}}>
            <h3 style={{margin:0}}>Piyasa — Çoklu Zaman Dilimi</h3>
            <span className="mono" style={{fontSize:10,color:'#5e758d'}}>1S · 1G · 1H · 1Ay · 1Y · sadece gorsel · ilk {tfData.data?.count ?? 6}/{totalScanned} parite</span>
          </div>
          {(tfData.data?.pairs||[]).map((g:any)=>(
            <div key={g.pair} style={{marginBottom:14}}>
              <div className="mono" style={{fontSize:12,fontWeight:700,color:'#cbd9ea',marginBottom:8}}>{g.pair}</div>
              <div style={{display:'grid',gridTemplateColumns:'repeat(5,1fr)',gap:8}}>
                {(g.timeframes||[]).map((tf:any)=>(
                  <div key={tf.label} style={{background:'#0a121c',border:'1px solid #1e2d3d',borderRadius:8,padding:'10px'}}>
                    <div style={{display:'flex',justifyContent:'space-between',fontSize:10,color:'#8aa0b8'}}>
                      <span style={{fontWeight:700,color:'#cbd9ea'}}>{tf.label}</span><span>{tf.desc}</span>
                    </div>
                    <div className="mono" style={{fontSize:14,fontWeight:700,color:(tf.change||0)>=0?'#2dd4a0':'#ff5a68',marginTop:4}}>
                      {tf.change!=null ? `${tf.change>=0?'▲':''} ${tf.change.toFixed(2)}%` : '—'}
                    </div>
                    <div className="mono" style={{fontSize:10,color:'#5e758d'}}>{tf.last?.toLocaleString(undefined,{maximumFractionDigits:2}) ?? '—'}</div>
                    <div style={{height:36,marginTop:6}}>
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={tf.klines||[]}>
                          <Area type="monotone" dataKey="c" stroke={(tf.change||0)>=0?'#2dd4a0':'#ff5a68'} fill={(tf.change||0)>=0?'rgba(45,212,160,.12)':'rgba(255,90,104,.12)'} dot={false} strokeWidth={1.2} isAnimationActive={false} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {!tfData.data && <div className="mono" style={{fontSize:11,color:'#5e758d',textAlign:'center',padding:12}}>Yukleniyor...</div>}
        </div>

<div className="grid cols-2">
          <div className="card">
            <h3>Equity Curve</h3>
            <div style={{height:180}}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={equity.length? equity : [{date:'start',equity: portfolio.data?.starting_balance||10}]}>
                  <CartesianGrid stroke="#13202e" vertical={false}/>
                  <XAxis dataKey="date" hide />
                  <YAxis width={50} tick={{fontSize:10, fill:'#8aa0b8'}} domain={['auto','auto']} />
                  <Tooltip contentStyle={{background:'#0f1a26',border:'1px solid #1e2d3d',fontSize:11}} />
                  <Area type="monotone" dataKey="equity" stroke="#2dd4a0" fill="rgba(45,212,160,.15)" strokeWidth={1.8} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="mono" style={{fontSize:11,color:'#5e758d',marginTop:6}}>{'N/A before first closed trade - curve updates on trade close.'}</div>
          </div>
          <div className="card">
            <h3>Drawdown</h3>
            <div style={{height:180}}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={drawdown.length? drawdown: [{date:'start',drawdown:0}]}>
                  <CartesianGrid stroke="#13202e" vertical={false}/>
                  <XAxis dataKey="date" hide /><YAxis width={50} tick={{fontSize:10,fill:'#8aa0b8'}} unit="%" />
                  <Tooltip contentStyle={{background:'#0f1a26',border:'1px solid #1e2d3d',fontSize:11}} />
                  <Area type="monotone" dataKey="drawdown" stroke="#ff5a68" fill="rgba(255,90,104,.15)" strokeWidth={1.6} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="grid cols-3">
          <div className="card">
            <h3>PnL Distribution</h3>
            <div style={{height:160}}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={pnlBuckets.length? pnlBuckets : [{range:'no trades',count:0}]}>
                  <CartesianGrid stroke="#13202e" vertical={false}/>
                  <XAxis dataKey="range" hide /><YAxis width={30} tick={{fontSize:10,fill:'#8aa0b8'}} />
                  <Tooltip contentStyle={{background:'#0f1a26',border:'1px solid #1e2d3d',fontSize:11}}/>
                  <Bar dataKey="count" fill="#3b82f6" radius={[6,6,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="card">
            <h3>{'Win / Loss'}</h3>
            <div style={{height:160, display:'grid', placeItems:'center'}}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={winLoss} dataKey="value" innerRadius={45} outerRadius={70} paddingAngle={4}>
                    {winLoss.map((e,i)=><Cell key={i} fill={e.color} />)}
                  </Pie>
                  <Tooltip contentStyle={{background:'#0f1a26',border:'1px solid #1e2d3d',fontSize:11}} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mono" style={{fontSize:11,color:'#8aa0b8',textAlign:'center'}}>{stats?.win_rate!=null? `${(stats.win_rate*100).toFixed(1)}% win` : 'N/A'} · {stats?.total_trades||0} trades</div>
          </div>
          <div className="card">
            <h3>Daily Return</h3>
            <div style={{height:160}}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={daily.length? daily : [{date:'—',pnl:0}]}>
                  <CartesianGrid stroke="#13202e" vertical={false}/>
                  <XAxis dataKey="date" tick={{fontSize:9,fill:'#8aa0b8'}} hide={daily.length>8} />
                  <YAxis width={40} tick={{fontSize:10,fill:'#8aa0b8'}} />
                  <Tooltip contentStyle={{background:'#0f1a26',border:'1px solid #1e2d3d',fontSize:11}}/>
                  <Bar dataKey="pnl" fill="#f5c86e" radius={[6,6,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="card">
          <h3>Trading Statistics</h3>
          <div className="grid cols-4" style={{gap:8}}>
            {[
              ['Total Trades', stats?.total_trades],
              ['Winning', stats?.winning],
              ['Losing', stats?.losing],
              ['Win Rate', stats?.win_rate!=null? `${(stats.win_rate*100).toFixed(1)}%` : 'N/A'],
              ['Profit Factor', stats?.profit_factor!=null? (Number.isFinite(stats.profit_factor)? stats.profit_factor.toFixed(2):'∞') : 'N/A'],
              ['Avg Win', stats?.avg_win!=null? stats.avg_win.toFixed(4):'N/A'],
              ['Avg Loss', stats?.avg_loss!=null? stats.avg_loss.toFixed(4):'N/A'],
              ['Largest Win', stats?.largest_win!=null? stats.largest_win.toFixed(4):'N/A'],
              ['Largest Loss', stats?.largest_loss!=null? stats.largest_loss.toFixed(4):'N/A'],
              ['Avg Trade', stats?.avg_trade!=null? stats.avg_trade.toFixed(4):'N/A'],
              ['Total Fees', stats?.total_fees ?? 'N/A'],
              ['Max Drawdown', stats?.max_drawdown!=null? `${stats.max_drawdown.toFixed(2)}%`:'N/A'],
              ['Sharpe', stats?.sharpe!=null? stats.sharpe.toFixed(2):'N/A'],
              ['Sortino', stats?.sortino!=null? stats.sortino.toFixed(2):'N/A'],
              ['Turnover', stats?.turnover ?? 'N/A'],
            ].map(([k,v])=>(
              <div key={k} style={{background:'#0f1a26',border:'1px solid #13202e',borderRadius:8,padding:'10px'}}>
                <div style={{fontSize:10,letterSpacing:.06+'em',color:'#5e758d',textTransform:'uppercase'}}>{k}</div>
                <div className="mono" style={{fontWeight:700,marginTop:4}}>{v as any}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}>
            <h3 style={{margin:0}}>Trade History</h3>
            <div style={{display:'flex',gap:6}}>
              {(['all','open','closed'] as const).map(f=>(
                <button key={f} className="btn" style={{borderColor: tradesFilter===f? '#3b82f6':'#1e2d3d', background: tradesFilter===f?'rgba(59,130,246,.15)':''}} onClick={()=>setTradesFilter(f)}>{f.toUpperCase()}</button>
              ))}
            </div>
          </div>
          <div className="scroll">
            <table className="table">
              <thead><tr>{['Time','Pair','Side','Entry','Exit','Amount','Gross PnL','Fee','Net PnL','Duration','Exit'].map((h,i)=><th key={i}>{h}</th>)}</tr></thead>
              <tbody>
                {(filteredTrades.length? filteredTrades: []).map((t:any)=>(
                  <tr key={t.id}>
                    <td className="mono" style={{fontSize:11}}>{(t.close_date||t.open_date||'').slice(0,19).replace('T',' ')}</td>
                    <td className="mono">{t.pair}</td>
                    <td><span className="pill pill-green">{t.side}</span></td>
                    <td className="mono">{t.open_rate}</td>
                    <td className="mono">{t.close_rate ?? '—'}</td>
                    <td className="mono">{t.amount}</td>
                    <td className="mono" style={{color:(t.gross_pnl||0)>=0?'#2dd4a0':'#ff5a68'}}>{t.gross_pnl!=null? t.gross_pnl.toFixed(4):'—'}</td>
                    <td className="mono">{t.fee!=null? t.fee.toFixed(4):'—'}</td>
                    <td className="mono" style={{color:(t.net_pnl||0)>=0?'#2dd4a0':'#ff5a68'}}>{t.net_pnl!=null? t.net_pnl.toFixed(4):'—'}</td>
                    <td className="mono">{t.duration_seconds? `${fmtDurM(t.duration_seconds)}m` : '—'}</td>
                    <td style={{fontSize:11,color:'#8aa0b8'}}>{t.exit_reason|| (t.is_open?'OPEN':'—')}</td>
                  </tr>
                ))}
                {!filteredTrades.length && <tr><td colSpan={11} style={{textAlign:'center',color:'#5e758d',padding:18}}>No trades yet — Faz 1 just started.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid cols-2">
          <div className="card">
            <h3>System Health</h3>
            <div style={{display:'grid',gap:6}}>
              {(health.data?.items||[]).map((it:any)=>(
                <div key={it.name} style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'8px 10px',borderRadius:8,background:'#0f1a26',border:'1px solid #13202e'}}>
                  <span style={{fontSize:12, color:'#cbd9ea'}}>{it.name}</span>
                  <span style={{display:'flex',alignItems:'center',gap:8}}>
                    <span className="mono" style={{fontSize:11,color:'#8aa0b8'}}>{it.detail?.slice(0,64)}</span>
                    <span className="pill" style={{background: it.status==='Healthy'?'rgba(45,212,160,.15)': it.status==='Warning'?'rgba(245,200,110,.15)':'rgba(255,90,104,.15)', color: it.status==='Healthy'?'#2dd4a0': it.status==='Warning'?'#f5c86e':'#ff5a68'}}>{it.status}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}>
              <h3 style={{margin:0}}>Alerts</h3>
              <span className="mono" style={{fontSize:11,color:'#5e758d'}}>{alerts.data?.alerts?.length||0} events</span>
            </div>
            <div style={{display:'grid',gap:6,maxHeight:260,overflow:'auto'}}>
              {(alerts.data?.alerts||[]).map((a:any,i:number)=>(
                <div key={i} style={{padding:'8px 10px',borderRadius:8,background:'#0f1a26',border:'1px solid #13202e',display:'flex',justifyContent:'space-between'}}>
                  <span style={{fontSize:12}}>{a.msg}</span><span className="mono" style={{fontSize:10,color:'#5e758d'}}>{String(a.time).slice(0,19)}</span>
                </div>
              ))}
              {!(alerts.data?.alerts||[]).length && <div style={{color:'#5e758d',padding:12,textAlign:'center'}}>No alerts</div>}
            </div>
            <div style={{display:'flex',gap:8,marginTop:10,flexWrap:'wrap'}}>
              <button className="btn btn-primary" onClick={()=>ctrl('restart')}>Restart bot</button>
              <button className="btn" onClick={()=>ctrl('stop')}>Stop bot</button>
              <button className="btn" onClick={()=>ctrl('start')}>Start bot</button>
              <button className="btn" disabled title="LIVE TRADING DISABLED" style={{opacity:.5}}>LIVE TRADING: DISABLED</button>
            </div>
          </div>
        </div>

        <div className="card">
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}>
            <h3 style={{margin:0}}>Freqtrade Logs</h3>
            <div style={{display:'flex',gap:6,alignItems:'center'}}>
              <select value={logLevel} onChange={e=>setLogLevel(e.target.value as any)} className="btn" style={{padding:'6px 8px'}}>
                <option value="all">All</option><option value="error">Error</option><option value="warning">Warning</option>
              </select>
              <button className="btn" onClick={()=>setPaused(p=>!p)}>{paused?'Resume':'Pause'}</button>
              <button className="btn" onClick={()=>{const el=logRef.current; if(el) el.innerHTML=''}}>Clear view</button>
            </div>
          </div>
          <div ref={logRef} className="log">{(logs.data?.logs||[]).slice(-180).join('\n') || '— no logs yet —'}</div>
          {status.err && <div style={{color:'#ff5a68',fontSize:11,marginTop:6}}>status error: {status.err}</div>}
        </div>

        <div style={{textAlign:'center',color:'#5e758d',fontSize:11,padding:'8px'}} className="mono">
          Zen-Genie - Faz 1 locked - backend 8001 - frontend 5173 - live_trading DISABLED - universe TOP {(status as any).data?.universe?.count || totalScanned} USDT · strategy BaselineStrategy (RSI 30/70 SMA50/200) · data: SQLite + Binance public REST
        </div>
      </div>
    </div>
  )
}
