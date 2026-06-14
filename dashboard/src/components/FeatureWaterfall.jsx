import { useEffect, useState, useRef } from 'react';

const FEATURE_LABELS = {
  'temp_0_log_mean_delta': 'Mean reaction time',
  'temp_1_log_std_delta': 'Reaction time spread',
  'temp_2_skewness': 'Timing skewness',
  'temp_3_kurtosis': 'Timing kurtosis',
  'temp_4_cv': 'Timing variability (CV)',
  'temp_5_fast_reaction_ratio': 'Fast reaction rate',
  'temp_6_autocorr': 'Timing autocorrelation',
  'temp_7_hour_gini': 'Hourly activity Gini',
  'gas_0_price_cv': 'Gas price variability',
  'gas_1_round_fraction': 'Round gas prices',
  'gas_2_nice_number_fraction': 'Nice gas numbers',
  'gas_3_percentile_variance': 'Gas percentile spread',
  'gas_4_overpay_ratio': 'Gas overpayment rate',
  'gas_5_mean_efficiency': 'Gas efficiency (mean)',
  'gas_6_efficiency_std': 'Gas efficiency spread',
  'div_0_unique_contract_ratio': 'Contract diversity',
  'div_1_unique_protocols': 'Unique protocols',
  'div_2_method_diversity': 'Method diversity',
  'div_3_protocol_hhi': 'Protocol concentration',
  'div_4_exploration_ratio': 'Exploration rate',
  'div_5_weekend_ratio': 'Weekend activity',
  'port_0_size_cv': 'Trade size variability',
  'port_1_size_skew': 'Trade size skewness',
  'port_2_size_kurtosis': 'Trade size kurtosis',
  'port_3_overconfidence_score': 'Overconfidence signal',
  'port_4_streak_size_correlation': 'Streak-size correlation',
  'port_5_round_value_ratio': 'Round value bias',
  'port_6_lognormal_fit': 'Log-normal fit quality',
  'port_7_activity_consistency': 'Activity consistency',
  'port_8_max_to_mean_ratio': 'Max / mean ratio',
  'event_0_burstiness': 'Activity burstiness',
  'event_1_memory': 'Temporal memory',
  'event_2_clustering': 'Activity clustering',
  'event_3_avg_session_txs': 'Avg session length',
  'event_4_session_gap_cv': 'Session gap regularity',
  'consist_0_stress_variance_ratio': 'Stress variance ratio',
  'consist_1_timing_early_cv': 'Early timing CV',
  'consist_2_timing_late_cv': 'Late timing CV',
  'consist_3_cv_evolution': 'Timing evolution',
  'consist_4_failure_rate': 'TX failure rate',
  'consist_5_method_evolution': 'Method evolution',
  'net_0_unique_recipient_ratio': 'Recipient diversity',
  'net_1_top1_concentration': 'Top-1 concentration',
  'net_2_top3_concentration': 'Top-3 concentration',
  'net_3_wallet_age_blocks_log': 'Wallet age (blocks)',
  'net_4_total_volume_log': 'Total volume',
  'net_5_contract_ratio': 'Contract call ratio',
};

const FEATURE_DESCRIPTIONS = {
  'temp_4_cv': 'Humans have high timing variability (CV > 1.0). Agents are precise.',
  'temp_5_fast_reaction_ratio': 'Agents react in milliseconds. Humans take seconds.',
  'temp_7_hour_gini': 'Humans concentrate activity in waking hours. Agents are 24/7.',
  'gas_0_price_cv': 'Humans choose gas inconsistently. Agents use exact calculations.',
  'gas_1_round_fraction': 'Humans prefer round Gwei values (1, 2, 5, 10). Agents do not.',
  'div_3_protocol_hhi': 'Agents focus on 1-2 protocols. Humans explore many.',
  'consist_4_failure_rate': 'Only humans make mistakes. Agents never fail transactions.',
  'event_0_burstiness': 'Human activity is bursty (news-driven). Agents are regular.',
  'port_5_round_value_ratio': 'Humans prefer round amounts (0.1, 0.5, 1.0 MNT).',
  'port_0_size_cv': 'Human trade sizes vary dramatically. Agents use fixed sizes.',
};

function getCategoryPrefix(featureName) {
  const map = { temp: 'TIMING', gas: 'GAS', div: 'DIVERSITY', port: 'PORTFOLIO', event: 'EVENT', consist: 'CONSISTENCY', net: 'NETWORK' };
  const prefix = featureName.split('_')[0];
  return map[prefix] || 'OTHER';
}

const CATEGORY_ORDER = ['TIMING', 'GAS', 'DIVERSITY', 'PORTFOLIO', 'EVENT', 'CONSISTENCY', 'NETWORK', 'OTHER'];

export default function FeatureWaterfall({ contributions = [], maxFeatures = 12, apiAvailable = true }) {
  const [mounted, setMounted] = useState(false);
  const [hoveredFeature, setHoveredFeature] = useState(null);
  const tooltipRef = useRef(null);

  useEffect(() => {
    setMounted(false);
    const t = setTimeout(() => setMounted(true), 50);
    return () => clearTimeout(t);
  }, [contributions]);

  if (!contributions || contributions.length === 0) {
    return (
      <div style={{
        padding: 'var(--space-6)',
        textAlign: 'center',
        color: 'var(--text-muted)',
        fontSize: 'var(--text-sm)',
        fontFamily: 'var(--font-mono)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12,
      }}>
        {apiAvailable === false ? (
          <span style={{ color: 'var(--signal-uncertain-text)' }}>
            Oracle unreachable — retrying...
          </span>
        ) : (
          <>
            <div style={{ width: 20, height: 20, border: '2px solid var(--border-subtle)', borderTopColor: 'var(--accent-purple)', borderRadius: '50%', animation: 'spin 800ms linear infinite' }} />
            <span style={{ color: 'var(--text-tertiary)', letterSpacing: '1px', textTransform: 'uppercase', fontSize: 'var(--text-2xs)' }}>
              Waiting for SHAP analysis...
            </span>
          </>
        )}
      </div>
    );
  }

  const sorted = [...contributions].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));
  const displayed = sorted.slice(0, maxFeatures);

  const grouped = {};
  displayed.forEach((f) => {
    const cat = getCategoryPrefix(f.feature);
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(f);
  });

  const orderedGroups = CATEGORY_ORDER.filter((c) => grouped[c]).map((c) => ({ category: c, items: grouped[c] }));

  let globalIdx = 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 60px 44px',
        gap: 8,
        paddingBottom: 8,
        borderBottom: '1px solid var(--border-subtle)',
        marginBottom: 4,
      }}>
        <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '2px', textTransform: 'uppercase', fontWeight: 700 }}>Feature</span>
        <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '2px', textTransform: 'uppercase', fontWeight: 700, textAlign: 'center' }}>
          {'\u2190'} A &middot; H {'\u2192'}
        </span>
        <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '2px', textTransform: 'uppercase', fontWeight: 700, textAlign: 'right' }}>SHAP</span>
      </div>

      {orderedGroups.map(({ category, items }) => (
        <div key={category}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '6px 4px 4px',
            marginTop: 4,
          }}>
            <span style={{
              fontSize: '8px', letterSpacing: '3px', color: 'var(--text-disabled)',
              fontWeight: 700, textTransform: 'uppercase',
            }}>
              {category}
            </span>
            <div style={{ flex: 1, height: 1, background: 'linear-gradient(90deg, var(--border-subtle), transparent)' }} />
          </div>

          {items.map((feat) => {
            const idx = globalIdx++;
            const isHuman = feat.contribution > 0;
            const absContrib = Math.abs(feat.contribution);
            const barWidthPct = mounted ? Math.min(absContrib * 50, 50) : 0;
            const label = FEATURE_LABELS[feat.feature] || feat.feature.replace(/_/g, ' ');
            const isHovered = hoveredFeature === feat.feature;

            return (
              <div
                key={feat.feature}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 60px 44px',
                  gap: 8,
                  alignItems: 'center',
                  padding: '4px 6px',
                  borderRadius: 'var(--radius-sm)',
                  background: isHovered ? 'var(--surface-02)' : 'transparent',
                  border: isHovered ? '1px solid var(--border-subtle)' : '1px solid transparent',
                  transition: 'background var(--duration-fast) ease, border-color var(--duration-fast) ease, transform var(--duration-fast) ease',
                  cursor: 'default',
                  animation: `fade-in-up ${200 + idx * 45}ms var(--ease-out) both`,
                  position: 'relative',
                }}
                onMouseEnter={() => setHoveredFeature(feat.feature)}
                onMouseLeave={() => setHoveredFeature(null)}
              >
                <div style={{
                  fontSize: 'var(--text-xs)',
                  color: isHovered ? 'var(--text-secondary)' : 'var(--text-tertiary)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  transition: 'color var(--duration-fast) ease',
                  fontFamily: 'var(--font-mono)',
                }}
                  title={FEATURE_DESCRIPTIONS[feat.feature] || label}
                >
                  {label}
                </div>

                <div style={{ position: 'relative', height: 10 }}>
                  <div style={{
                    position: 'absolute',
                    left: '50%',
                    top: 0,
                    bottom: 0,
                    width: 1,
                    background: 'var(--border-subtle)',
                    transform: 'translateX(-50%)',
                  }} />

                  <div style={{
                    position: 'absolute',
                    inset: 0,
                    background: 'rgba(255,255,255,0.04)',
                    borderRadius: 4,
                  }} />

                  {/* Glow layer */}
                  <div style={{
                    position: 'absolute',
                    top: -2,
                    bottom: -2,
                    borderRadius: 6,
                    background: isHuman
                      ? `linear-gradient(90deg, rgba(0,255,163,0.15), transparent)`
                      : `linear-gradient(270deg, rgba(255,51,85,0.15), transparent)`,
                    filter: 'blur(4px)',
                    opacity: isHovered ? 0.4 : 0.15,
                    transition: 'opacity var(--duration-fast) ease',
                    ...(isHuman
                      ? { left: '50%', width: `${Math.min(barWidthPct * 2, 100)}%` }
                      : { right: '50%', width: `${Math.min(barWidthPct * 2, 100)}%` }
                    ),
                  }} />

                  {/* Main bar */}
                  <div style={{
                    position: 'absolute',
                    top: 1,
                    bottom: 1,
                    borderRadius: 3,
                    background: isHuman
                      ? `linear-gradient(90deg, rgba(0,255,163,0.6), rgba(0,255,163,0.9))`
                      : `linear-gradient(270deg, rgba(255,51,85,0.6), rgba(255,51,85,0.9))`,
                    boxShadow: isHuman
                      ? '0 0 6px rgba(0,255,163,0.3)'
                      : '0 0 6px rgba(255,51,85,0.3)',
                    transition: `width ${400 + idx * 30}ms var(--ease-out), filter var(--duration-fast) ease`,
                    ...(isHuman
                      ? { left: '50%', width: `${barWidthPct}%` }
                      : { right: '50%', width: `${barWidthPct}%` }
                    ),
                    filter: isHovered ? 'brightness(1.3) saturate(1.2)' : 'none',
                  }} />
                </div>

                <div style={{
                  fontSize: 'var(--text-xs)',
                  color: isHuman ? 'var(--signal-human-text)' : 'var(--signal-agent-text)',
                  textAlign: 'right',
                  fontFamily: 'var(--font-mono)',
                  fontVariantNumeric: 'tabular-nums',
                  fontWeight: 600,
                }}>
                  {feat.contribution > 0 ? '+' : ''}{(feat.contribution * 100).toFixed(1)}
                </div>
              </div>
            );
          })}
        </div>
      ))}

      <div style={{
        display: 'flex',
        justifyContent: 'center',
        gap: 24,
        paddingTop: 10,
        borderTop: '1px solid var(--border-subtle)',
        marginTop: 6,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: 'var(--signal-agent)',
            boxShadow: '0 0 6px var(--signal-agent)',
          }} />
          <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1.5px', textTransform: 'uppercase', fontWeight: 700 }}>
            {'\u2190'} AGENT SIGNALS
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: 'var(--signal-human)',
            boxShadow: '0 0 6px var(--signal-human)',
          }} />
          <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1.5px', textTransform: 'uppercase', fontWeight: 700 }}>
            HUMAN SIGNALS {'\u2192'}
          </span>
        </div>
      </div>

      {hoveredFeature && FEATURE_DESCRIPTIONS[hoveredFeature] && (
        <div
          ref={tooltipRef}
          style={{
            padding: '10px 12px',
            background: 'var(--bg-panel-solid)',
            border: '1px solid var(--border-accent)',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--text-xs)',
            color: 'var(--text-secondary)',
            marginTop: 4,
            animation: 'fade-in-up 150ms var(--ease-out) both',
            lineHeight: 1.6,
            boxShadow: 'var(--shadow-purple)',
            position: 'relative',
          }}
        >
          <div style={{
            position: 'absolute', top: -1, left: '20%', right: '20%',
            height: 1,
            background: 'linear-gradient(90deg, transparent, var(--accent-purple-border), transparent)',
          }} />
          {FEATURE_DESCRIPTIONS[hoveredFeature]}
        </div>
      )}
    </div>
  );
}
