import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Network, X, AlertTriangle } from 'lucide-react';

const HPS_COLOR_SCALE = d3.scaleLinear()
  .domain([0, 4000, 7000, 10000])
  .range(['#ff3355', '#f59e0b', '#4ade80', '#00ffa3']);

export function SybilGraph({ clusters }) {
  const svgRef = useRef(null);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    if (!clusters || Object.keys(clusters).length === 0) return;

    const nodes = [];
    const links = [];

    Object.entries(clusters).forEach(([clusterId, cluster]) => {
      cluster.members.forEach((m) => {
        nodes.push({
          id: m.address,
          hps: m.hps,
          clusterId,
          isCoordinator: m.address === cluster.coordinator,
          sybilProbability: cluster.sybil_probability,
        });
      });
      const hub = cluster.coordinator || cluster.members[0]?.address;
      cluster.members.forEach((m) => {
        if (m.address !== hub) links.push({ source: hub, target: m.address });
      });
    });

    const width = 900, height = 460;
    const svg = d3.select(svgRef.current).attr('viewBox', `0 0 ${width} ${height}`);
    svg.selectAll('*').remove();

    // Background
    svg.append('rect')
      .attr('width', width)
      .attr('height', height)
      .attr('fill', 'rgba(0,0,4,0.6)')
      .attr('rx', 12);

    // Radial grid
    const gridGroup = svg.append('g').attr('opacity', 0.15);
    [60, 120, 180, 240].forEach((r) => {
      gridGroup.append('circle')
        .attr('cx', width / 2)
        .attr('cy', height / 2)
        .attr('r', r)
        .attr('fill', 'none')
        .attr('stroke', 'rgba(139,124,255,0.15)')
        .attr('stroke-width', 0.5);
    });

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d) => d.id).distance(72))
      .force('charge', d3.forceManyBody().strength(-160))
      .force('center', d3.forceCenter(width / 2, height / 2));

    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', 'rgba(139,124,255,0.2)')
      .attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '4 4')
      .style('animation', 'dash-flow 2s linear infinite');

    const node = svg.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', (d) => (d.isCoordinator ? 16 : 6))
      .attr('fill', (d) => HPS_COLOR_SCALE(d.hps))
      .attr('stroke', (d) => (d.isCoordinator ? '#ffffff' : 'rgba(255,255,255,0.25)'))
      .attr('stroke-width', (d) => (d.isCoordinator ? 2.5 : 1))
      .style('cursor', 'pointer')
      .style('filter', (d) => `drop-shadow(0 0 ${d.isCoordinator ? 12 : 4}px ${HPS_COLOR_SCALE(d.hps)})`)
      .on('click', (_, d) => setSelected(d))
      .call(
        d3.drag()
          .on('start', (event, d) => { d.fx = d.x; d.fy = d.y; })
          .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
          .on('end', () => { /* keep position */ }),
      );

    node.append('title').text((d) => `${d.id}\nHPS: ${d.hps}\n${d.isCoordinator ? 'Coordinator' : 'Member'}`);

    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x).attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x).attr('y2', (d) => d.target.y);
      node.attr('cx', (d) => d.x).attr('cy', (d) => d.y);
    });

    return () => simulation.stop();
  }, [clusters]);

  const empty = !clusters || Object.keys(clusters).length === 0;

  return (
    <div className="panel">
      <div className="panel-header">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="panel-title">SYBIL CLUSTER MAP</div>
          <span className="badge badge-red"><Network size={10} />{' '}Threat Graph</span>
        </div>
        <div className="panel-subtitle">
          Each node is a wallet &middot; color = HPS &middot; large ringed nodes are suspected funding coordinators
        </div>
      </div>

      {empty ? (
        <div style={{
          height: 400, display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', gap: 12, color: 'var(--text-muted)', textAlign: 'center',
          border: '1px dashed var(--border-subtle)', borderRadius: 'var(--radius-lg)',
        }}>
          <Network size={32} color="var(--text-disabled)" />
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)' }}>No Sybil clusters detected yet</div>
          <div style={{ fontSize: 'var(--text-2xs)', maxWidth: 360, lineHeight: 1.6, color: 'var(--text-muted)' }}>
            When coordinated wallet clusters are flagged by the detector, their funding topology will be visualized here in real time.
          </div>
        </div>
      ) : (
        <div style={{ position: 'relative' }}>
          <svg ref={svgRef} style={{ width: '100%', height: 460 }} />

          <div style={{
            position: 'absolute', bottom: 12, left: 12, display: 'flex', gap: 16,
            padding: '8px 14px', borderRadius: 20,
            background: 'rgba(8,10,20,0.85)', border: '1px solid var(--border-subtle)',
            backdropFilter: 'blur(12px)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ width: 12, height: 12, borderRadius: '50%', border: '2px solid #fff', background: HPS_COLOR_SCALE(2000), boxShadow: '0 0 8px currentColor' }} />
              <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-tertiary)', fontWeight: 600 }}>Coordinator</span>
            </div>
            {[['Bot', '#ff3355'], ['Mixed', '#f59e0b'], ['Human', '#00ffa3']].map(([l, c]) => (
              <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: c, boxShadow: `0 0 6px ${c}` }} />
                <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-tertiary)', fontWeight: 600 }}>{l}</span>
              </div>
            ))}
          </div>

          {selected && (
            <div style={{
              position: 'absolute', top: 12, right: 12, width: 240,
              background: 'rgba(8,10,20,0.95)', border: `1px solid ${HPS_COLOR_SCALE(selected.hps)}44`,
              borderRadius: 'var(--radius-md)', padding: 'var(--space-4)',
              backdropFilter: 'blur(16px)', boxShadow: 'var(--shadow-lg)',
              animation: 'fade-in-scale 200ms var(--ease-out) both',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', wordBreak: 'break-all' }}>
                  {selected.id.slice(0, 10)}&hellip;{selected.id.slice(-6)}
                </span>
                <button onClick={() => setSelected(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', flexShrink: 0 }}>
                  <X size={14} />
                </button>
              </div>
              <div style={{
                width: '100%', height: 4, borderRadius: 2,
                background: `linear-gradient(90deg, var(--signal-agent), var(--signal-human))`,
                marginBottom: 10,
              }}>
                <div style={{
                  height: '100%', width: `${(selected.hps / 10000) * 100}%`,
                  background: HPS_COLOR_SCALE(selected.hps),
                  borderRadius: 2,
                  boxShadow: `0 0 8px ${HPS_COLOR_SCALE(selected.hps)}`,
                }} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[
                  ['HPS', selected.hps?.toLocaleString()],
                  ['Cluster', selected.clusterId],
                  ['Sybil prob.', `${(selected.sybilProbability * 100).toFixed(1)}%`],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase', fontWeight: 700 }}>{k}</span>
                    <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontWeight: 600 }}>{v}</span>
                  </div>
                ))}
              </div>
              {selected.isCoordinator && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 6, marginTop: 10, paddingTop: 10,
                  borderTop: '1px solid var(--border-subtle)',
                  fontSize: 'var(--text-2xs)', color: 'var(--signal-uncertain-text)',
                }}>
                  <AlertTriangle size={12} /> Suspected funding coordinator
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes dash-flow {
          to { stroke-dashoffset: -8; }
        }
      `}</style>
    </div>
  );
}
