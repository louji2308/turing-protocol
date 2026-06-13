import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

const HPS_COLOR_SCALE = d3.scaleLinear()
  .domain([0, 4000, 7000, 10000])
  .range(['#ef4444', '#f59e0b', '#84cc16', '#22c55e']);

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

    const width = 800, height = 500;
    const svg = d3.select(svgRef.current)
      .attr('viewBox', `0 0 ${width} ${height}`);
    svg.selectAll('*').remove();

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d) => d.id).distance(60))
      .force('charge', d3.forceManyBody().strength(-120))
      .force('center', d3.forceCenter(width / 2, height / 2));

    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', '#475569')
      .attr('stroke-width', 1.5);

    const node = svg.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', (d) => (d.isCoordinator ? 12 : 6))
      .attr('fill', (d) => HPS_COLOR_SCALE(d.hps))
      .attr('stroke', (d) => (d.isCoordinator ? '#fff' : 'none'))
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
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

  if (!clusters || Object.keys(clusters).length === 0) {
    return (
      <div className="sybil-graph-panel bg-slate-900 rounded-xl p-4">
        <h3 className="text-lg font-semibold text-white mb-2">Sybil Cluster Map</h3>
        <p className="text-sm text-slate-400">No Sybil clusters detected yet.</p>
      </div>
    );
  }

  return (
    <div className="sybil-graph-panel bg-slate-900 rounded-xl p-4 relative">
      <h3 className="text-lg font-semibold text-white mb-2">Sybil Cluster Map</h3>
      <p className="text-sm text-slate-400 mb-3">
        Each node is a wallet. Color = Human Probability Score (red = likely bot,
        green = likely human). Large ringed nodes are suspected funding coordinators.
      </p>
      <svg ref={svgRef} className="w-full h-[500px]" />
      {selected && (
        <div className="absolute top-4 right-4 bg-slate-800 border border-slate-700 rounded-lg p-4 text-sm text-white">
          <div className="font-mono text-xs mb-1">{selected.id}</div>
          <div>HPS: {selected.hps}</div>
          <div>Cluster: {selected.clusterId}</div>
          <div>Sybil probability: {(selected.sybilProbability * 100).toFixed(1)}%</div>
          {selected.isCoordinator && <div className="text-amber-400 mt-1">{'\u26A0'} Suspected funding coordinator</div>}
          <button className="text-slate-400 mt-2 underline" onClick={() => setSelected(null)}>close</button>
        </div>
      )}
    </div>
  );
}
