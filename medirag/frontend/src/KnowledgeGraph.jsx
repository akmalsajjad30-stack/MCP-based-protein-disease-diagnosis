// KnowledgeGraph.jsx — D3 force-directed knowledge graph visualization
import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

const NODE_COLORS = {
  Condition: '#f87171',
  Symptom: '#6ee7b7',
  Drug: '#fbbf24',
  Gene: '#a78bfa',
  Protein: '#60a5fa',
  ClinicalTrial: '#34d399',
  Community: '#f472b6',
}

export default function KnowledgeGraph({ graphData }) {
  const svgRef = useRef()

  useEffect(() => {
    if (!graphData || !graphData.nodes?.length) return

    const container = svgRef.current.parentElement
    const W = container.clientWidth || 600
    const H = 320

    const svg = d3.select(svgRef.current)
      .attr('width', W)
      .attr('height', H)

    svg.selectAll('*').remove()

    // Defs — arrow markers
    const defs = svg.append('defs')
    defs.append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 18).attr('refY', 0)
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', 'rgba(110,231,183,0.4)')

    const g = svg.append('g')

    // Zoom
    svg.call(d3.zoom().scaleExtent([0.3, 4]).on('zoom', e => g.attr('transform', e.transform)))

    const sim = d3.forceSimulation(graphData.nodes)
      .force('link', d3.forceLink(graphData.edges || []).id(d => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide(30))

    // Links
    const link = g.append('g')
      .selectAll('line')
      .data(graphData.edges || [])
      .join('line')
      .attr('stroke', 'rgba(110,231,183,0.25)')
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#arrow)')

    // Link labels
    const linkLabel = g.append('g')
      .selectAll('text')
      .data(graphData.edges || [])
      .join('text')
      .attr('font-size', 9)
      .attr('fill', 'rgba(139,148,158,0.7)')
      .attr('text-anchor', 'middle')
      .text(d => d.type || d.label || '')

    // Node groups
    const node = g.append('g')
      .selectAll('g')
      .data(graphData.nodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(d3.drag()
        .on('start', (event, d) => { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
        .on('end', (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null })
      )

    // Circle
    node.append('circle')
      .attr('r', d => (d.type || d.label) === 'Condition' ? 14 : 10)
      .attr('fill', d => (NODE_COLORS[d.type || d.label] || '#8b949e') + '22')
      .attr('stroke', d => NODE_COLORS[d.type || d.label] || '#8b949e')
      .attr('stroke-width', 1.5)

    // Label
    node.append('text')
      .attr('font-size', 9)
      .attr('fill', 'var(--text-secondary)')
      .attr('text-anchor', 'middle')
      .attr('dy', 24)
      .text(d => d.name?.length > 14 ? d.name.slice(0, 14) + '…' : d.name)

    // Tooltip
    node.append('title').text(d => `${d.type || d.label || 'Node'}: ${d.name}`)

    sim.on('tick', () => {
      link
        .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
      linkLabel
        .attr('x', d => (d.source.x + d.target.x) / 2)
        .attr('y', d => (d.source.y + d.target.y) / 2)
      node.attr('transform', d => `translate(${d.x},${d.y})`)
    })

    return () => sim.stop()
  }, [graphData])

  return (
    <div className="graph-viz">
      <div className="scan-line" />
      <svg ref={svgRef} />
      {/* Legend */}
      <div style={{
        position: 'absolute', bottom: 8, left: 8,
        display: 'flex', flexWrap: 'wrap', gap: 6,
      }}>
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.65rem', color: 'var(--text-muted)' }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
            {type}
          </div>
        ))}
      </div>
    </div>
  )
}
