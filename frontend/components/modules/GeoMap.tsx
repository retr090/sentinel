'use client'

import { useEffect, useRef } from 'react'

interface GeoItem {
  id: string | number
  title: string
  description?: string
  latitude: number
  longitude: number
  item_type: string
  severity: string
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: '#ef4444', HIGH: '#f59e0b', MEDIUM: '#3b82f6', LOW: '#10b981', INFO: '#64748b',
}

const TYPE_ICONS: Record<string, string> = {
  threat: '☠', news: '📰', incident: '⚠', flight: '✈', ship: '⚓', default: '📍',
}

export default function GeoMap({ items }: { items: GeoItem[] }) {
  const mapRef = useRef<any>(null)
  const mapInstanceRef = useRef<any>(null)
  const markersRef = useRef<any[]>([])

  useEffect(() => {
    if (typeof window === 'undefined' || mapInstanceRef.current) return

    import('leaflet').then((L) => {
      const map = L.map(mapRef.current, {
        center: [7.8731, 80.7718], // Sri Lanka
        zoom: 7,
        zoomControl: true,
      })

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18,
      }).addTo(map)

      // Dark tile override with CSS
      const style = document.createElement('style')
      style.textContent = '.leaflet-tile { filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%); }'
      document.head.appendChild(style)

      mapInstanceRef.current = map
    })

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!mapInstanceRef.current) return

    import('leaflet').then((L) => {
      // Clear old markers
      markersRef.current.forEach((m) => m.remove())
      markersRef.current = []

      items.forEach((item) => {
        if (!item.latitude || !item.longitude) return
        const color = SEVERITY_COLORS[item.severity] || '#64748b'
        const icon = TYPE_ICONS[item.item_type] || TYPE_ICONS.default

        const marker = L.circleMarker([item.latitude, item.longitude], {
          radius: item.severity === 'CRITICAL' ? 10 : item.severity === 'HIGH' ? 8 : 6,
          fillColor: color,
          color: color,
          weight: 2,
          opacity: 0.8,
          fillOpacity: 0.4,
        })
          .bindPopup(`
            <div style="font-family: monospace; font-size: 12px; min-width: 180px;">
              <strong>${item.title}</strong><br/>
              <span style="color: ${color}">${item.severity}</span> · ${item.item_type}<br/>
              ${item.description ? `<span style="font-size: 11px; opacity: 0.7">${item.description.substring(0, 100)}</span>` : ''}
            </div>
          `)
          .addTo(mapInstanceRef.current)

        markersRef.current.push(marker)
      })
    })
  }, [items])

  return <div ref={mapRef} style={{ width: '100%', height: '100%', background: '#0a0d0f' }} />
}
