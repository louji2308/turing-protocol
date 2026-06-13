import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Network, X, AlertTriangle } from 'lucide-react';

const HPS_COLOR_SCALE = d3.scaleLinear()
  .domain([0, 4000, 7000, 10000])
  .range(['#ff4d6d', '#fbbf24', '#84cc16', '#2ee6a0']);

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

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d) => d.id).distance(64))
      .force('charge', d3.forceManyBody().strength(-140))
      .force('center', d3.forceCenter(width / 2, height / 2));

    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', 'rgba(139,124,255,0.28)')
      .attr('stroke-width', 1.4);

    const node = svg.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', (d) => (d.isCoordinator ? 13 : 6))
      .attr('fill', (d) => HPS_COLOR_SCALE(d.hps))
      .attr('stroke', (d) => (d.isCoordinator ? '#fff' : 'rgba(255,255,255,0.25)'))
      .attr('stroke-width', (d) => (d.isCoordinator ? 2.5 : 1))
      .style('cursor', 'pointer')
      .style('filter', (d) => `drop-shadow(0 0 ${d.isCoordinator ? 8 : 4}px ${HPS_COLOR_SCALE(d.hps)})`)
      .on('click', (_, d) => setSelected(d))
      .call(
        d3.drag()
          .on('start', (event, d) => { d.fx = d.x; d.fy = d.y; })
          .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
          .on('end', (event, d) => { d.fx = null; d.fy = null; }),
      );

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
          <span className="badge badge-red"><Network size={10} /> Threat Graph</span>
        </div>
        <div className="panel-subtitle">
          Each node is a wallet · color = Human Probability Score · large ringed nodes are suspected funding coordinators
        </div>
      </div>

      {empty ? (
        <div style={{
          height: 340, display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', gap: 12, color: 'var(--text-muted)', textAlign: 'center',
          border: '1px dashed var(--border-subtle)', borderRadius: 'var(--radius-lg)',
        }}>
          <Network size={32} color="var(--text-disabled)" />
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-tertiary)' }}>No Sybil clusters detected yet</div>
          <div style={{ fontSize: 'var(--text-2xs)', maxWidth: 360, lineHeight: 1.6 }}>
            When coordinated wallet clusters are flagged by the detector, their funding topology will be visualized here in real time.
          </div>
        </div>
      ) : (
        <div style={{ position: 'relative' }}>
          <svg ref={svgRef} style={{ width: '100%', height: 460 }} />

          <div style={{
            position: 'absolute', bottom: 8, left: 8, display: 'flex', gap: 14,
            padding: '6px 12px', borderRadius: 20,
            background: 'rgba(14,16,25,0.7)', border: '1px solid var(--border-subtle)',
            backdropFilter: 'blur(8px)',
          }}>
            {[['Bot', 'var(--signal-agent)'], ['Uncertain', 'var(--signal-uncertain)'], ['Human', 'var(--signal-human)']].map(([l, c]) => (
              <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: c, boxShadow: `0 0 6px ${c}` }} />
                <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-tertiary)' }}>{l}</span>
              </div>
            ))}
          </div>

          {selected && (
            <div style={{
              position: 'absolute', top: 12, right: 12, width: 240,
              background: 'rgba(14,16,25,0.92)', border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)', padding: 'var(--space-4)',
              backdropFilter: 'blur(16px)', boxShadow: 'var(--shadow-lg)',
              animation: 'fade-in-up 200ms var(--ease-out) both',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', wordBreak: 'break-all' }}>
                  {selected.id.slice(0, 10)}…{selected.id.slice(-6)}
                </span>
                <button onClick={() => setSelected(null)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', flexShrink: 0 }}>
                  <X size={14} />
                </button>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[
                  ['HPS', selected.hps?.toLocaleString()],
                  ['Cluster', selected.clusterId],
                  ['Sybil prob.', `${(selected.sybilProbability * 100).toFixed(1)}%`],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase' }}>{k}</span>
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
    </div>
  );
}
