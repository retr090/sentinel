'use client'

import { useEffect, useState } from 'react'
import AppLayout from '@/components/layout/AppLayout'
import api from '@/lib/api'
import { MapPin, Plane, Plus } from 'lucide-react'
import dynamic from 'next/dynamic'

// Leaflet must be loaded client-side only
const GeoMap = dynamic(() => import('@/components/modules/GeoMap'), { ssr: false, loading: () => (
  <div className="h-96 flex items-center justify-center text-text-muted font-mono text-xs bg-background rounded">LOADING MAP...</div>
) })

export default function GeoIntPage() {
  const [geoItems, setGeoItems] = useState<any[]>([])
  const [flights, setFlights] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [activeLayer, setActiveLayer] = useState<string[]>(['threat', 'news', 'incident'])

  useEffect(() => {
    api.get('/geoint/items?since_hours=168').then(({ data }) => setGeoItems(data)).catch(() => {})
    api.get('/geoint/flights').then(({ data }) => setFlights(data.flights || [])).catch(() => {})
    api.get('/geoint/stats').then(({ data }) => setStats(data)).catch(() => {})
  }, [])

  const allMapItems = [
    ...geoItems.map((g: any) => ({ ...g, _source: 'geo' })),
    ...flights.map((f: any) => ({
      id: f.icao24,
      title: f.callsign || f.icao24,
      description: `${f.origin_country} | Alt: ${f.altitude}m | ${f.velocity} m/s`,
      latitude: f.latitude,
      longitude: f.longitude,
      item_type: 'flight',
      severity: 'INFO',
      _source: 'flight',
    })),
  ].filter((item) => activeLayer.includes(item.item_type))

  return (
    <AppLayout title="SENTINEL / GEOINT">
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              <MapPin className="w-5 h-5 text-warning" /> Geo Intelligence
            </h1>
            <p className="text-xs text-text-muted mt-0.5">Map-based intelligence visualization with live flight and incident tracking</p>
          </div>
        </div>

        {stats && (
          <div className="grid grid-cols-3 gap-3">
            <div className="sentinel-card text-center">
              <div className="text-xl font-bold font-mono text-warning">{stats.total_items}</div>
              <div className="text-xs text-text-muted mt-0.5">Intel Pins</div>
            </div>
            <div className="sentinel-card text-center">
              <div className="text-xl font-bold font-mono text-accent-blue">{flights.length}</div>
              <div className="text-xs text-text-muted mt-0.5">Live Flights</div>
            </div>
            <div className="sentinel-card text-center">
              <div className="text-xl font-bold font-mono text-accent-green">{stats.active_aoi}</div>
              <div className="text-xs text-text-muted mt-0.5">Areas of Interest</div>
            </div>
          </div>
        )}

        {/* Layer toggles */}
        <div className="flex gap-2 flex-wrap">
          {['threat', 'news', 'incident', 'flight', 'ship'].map((layer) => (
            <button
              key={layer}
              onClick={() => setActiveLayer(l => l.includes(layer) ? l.filter(x => x !== layer) : [...l, layer])}
              className={`text-xs px-3 py-1.5 rounded font-mono transition-colors border ${
                activeLayer.includes(layer) ? 'bg-accent-green/20 text-accent-green border-accent-green/30' : 'border-border text-text-muted'
              }`}
            >
              {layer.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Map */}
        <div className="sentinel-card p-0 overflow-hidden rounded-lg" style={{ height: '500px' }}>
          <GeoMap items={allMapItems} />
        </div>

        {/* Intel pins table */}
        <div className="sentinel-card">
          <h2 className="text-sm font-semibold mb-3 font-mono">INTEL PINS ({geoItems.length})</h2>
          <table className="sentinel-table">
            <thead><tr><th>Title</th><th>Type</th><th>Severity</th><th>Coordinates</th><th>Source</th></tr></thead>
            <tbody>
              {geoItems.slice(0, 20).map((item: any) => (
                <tr key={item.id}>
                  <td><span className="text-xs">{item.title}</span></td>
                  <td><span className="text-xs font-mono text-text-muted">{item.item_type}</span></td>
                  <td><span className={`text-xs font-mono font-bold ${
                    item.severity === 'CRITICAL' ? 'text-danger' :
                    item.severity === 'HIGH' ? 'text-warning' : 'text-text-muted'
                  }`}>{item.severity}</span></td>
                  <td><code className="text-xs font-mono text-text-muted">{item.latitude?.toFixed(4)}, {item.longitude?.toFixed(4)}</code></td>
                  <td><span className="text-xs text-text-muted font-mono">{item.module_source || '—'}</span></td>
                </tr>
              ))}
              {geoItems.length === 0 && (
                <tr><td colSpan={5} className="text-center py-8 text-text-muted font-mono text-xs">NO GEO ITEMS — ADD PINS FROM OTHER MODULES</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AppLayout>
  )
}
