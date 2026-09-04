const BASE = (import.meta as any).env?.VITE_API_URL || '/api'
async function j<T>(p:string):Promise<T>{ const r=await fetch(`${BASE}${p}`); if(!r.ok) throw new Error(r.statusText); return r.json() as Promise<T>}
export const api = {
  status: ()=>j<any>('/status'),
  portfolio: ()=>j<any>('/portfolio'),
  openPositions: ()=>j<any>('/open_positions'),
  capital: ()=>j<any>('/capital'),
  capitalHarvest: async (force=false, amount?:number)=>{
    const q = new URLSearchParams()
    if(force) q.set('force','true')
    if(amount!=null) q.set('amount', String(amount))
    const r=await fetch(`${BASE}/capital/harvest?${q}`,{method:'POST'})
    if(!r.ok) throw new Error(r.statusText)
    return r.json()
  },
  capitalHistory: ()=>j<any>('/capital/history'),
  price: (pair="BTC/USDT")=>j<any>(`/price?pair=${encodeURIComponent(pair)}`),
  market: ()=>j<any>('/market'),
  universe: ()=>j<any>('/universe'),
  timeframes: (limit=6)=>j<any>(`/market/timeframes?limit=${limit}`),
  trades: (q="all")=>j<any>(`/trades?status=${q}&limit=100`),
  performance: ()=>j<any>('/performance'),
  experiment: ()=>j<any>('/experiment'),
  health: ()=>j<any>('/health'),
  logs: (n=200, lvl="all")=>j<any>(`/logs?lines=${n}&level=${lvl}`),
  alerts: ()=>j<any>('/alerts'),
  control: async (a:string)=>{ const r=await fetch(`${BASE}/control/${a}`,{method:'POST'}); return r.json()}
}
