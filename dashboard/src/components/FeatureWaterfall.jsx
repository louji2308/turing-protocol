import { useEffect, useState } from 'react';

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

export default function FeatureWaterfall({ contributions = [], maxFeatures = 10, apiAvailable = true }) {
  const [mounted, setMounted] = useState(false);
  const [hoveredFeature, setHoveredFeature] = useState(null);

  useEffect(() => {
    setMounted(false);
    const t = setTimeout(() => setMounted(true), 50);
    return () => clearTimeout(t);
  }, [contributions]);

  if (!contributions || contributions.length === 0) {
    return (
      <div style={{
        padding: 'var(--space-4)',
        textAlign: 'center',
        color: 'var(--text-muted)',
        fontSize: 'var(--text-sm)',
        fontFamily: 'var(--font-mono)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
      }}>
        {apiAvailable === false ? (
          <span style={{ color: 'var(--signal-uncertain-text)' }}>
            Oracle unreachable — retrying...
          </span>
        ) : (
          <>
            <span style={{ width: 16, height: 16, border: '2px solid var(--border-subtle)', borderTopColor: 'var(--accent-purple)', borderRadius: '50%', animation: 'spin 800ms linear infinite', display: 'inline-block' }} />
            Waiting for SHAP analysis...
          </>
        )}
      </div>
    );
  }

  const displayed = contributions.slice(0, maxFeatures);
  const maxContrib = Math.max(...displayed.map(f => Math.abs(f.contribution)), 0.01);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '150px 1fr 52px',
        gap: 8,
        paddingBottom: 6,
        borderBottom: '1px solid var(--border-subtle)',
        marginBottom: 2,
      }}>
        <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase' }}>Feature</span>
        <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase', textAlign: 'center' }}>{'\u2190'} Agent {'\u00B7'} Human {'\u2192'}</span>
        <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase', textAlign: 'right' }}>SHAP</span>
      </div>

      {displayed.map((feat, idx) => {
        const isHuman = feat.contribution > 0;
        const absContrib = Math.abs(feat.contribution);
        const barWidthPct = mounted ? (absContrib / maxContrib) * 50 : 0;
        const label = FEATURE_LABELS[feat.feature] || feat.feature.replace(/_/g, ' ');
        const isHovered = hoveredFeature === feat.feature;

        return (
          <div
            key={feat.feature}
            style={{
              display: 'grid',
              gridTemplateColumns: '150px 1fr 52px',
              gap: 8,
              alignItems: 'center',
              padding: '3px 6px',
              borderRadius: 'var(--radius-sm)',
              background: isHovered ? 'var(--surface-02)' : 'transparent',
              transition: 'background var(--duration-fast) ease',
              cursor: 'default',
              animation: `fade-in-up ${200 + idx * 40}ms var(--ease-out) both`,
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

            <div style={{ position: 'relative', height: 8 }}>
              <div style={{
                position: 'absolute',
                left: '50%',
                top: 0,
                bottom: 0,
                width: 1,
                background: 'var(--border-default)',
                transform: 'translateX(-50%)',
              }} />

              <div style={{
                position: 'absolute',
                inset: 0,
                background: 'var(--bg-elevated)',
                borderRadius: 4,
              }} />

              <div style={{
                position: 'absolute',
                top: 1,
                bottom: 1,
                borderRadius: 3,
                background: isHuman ? 'var(--signal-human)' : 'var(--signal-agent)',
                ...(isHuman
                  ? { left: '50%', width: `${barWidthPct}%` }
                  : { right: '50%', width: `${barWidthPct}%` }
                ),
                boxShadow: `0 0 4px ${isHuman ? 'var(--signal-human)' : 'var(--signal-agent)'}44`,
                transition: `width ${400 + idx * 30}ms var(--ease-out)`,
              }} />
            </div>

            <div style={{
              fontSize: 'var(--text-xs)',
              color: isHuman ? 'var(--signal-human-text)' : 'var(--signal-agent-text)',
              textAlign: 'right',
              fontFamily: 'var(--font-mono)',
              fontVariantNumeric: 'tabular-nums',
            }}>
              {feat.contribution > 0 ? '+' : ''}{(feat.contribution * 100).toFixed(1)}
            </div>
          </div>
        );
      })}

      <div style={{
        display: 'flex',
        justifyContent: 'center',
        gap: 20,
        paddingTop: 8,
        borderTop: '1px solid var(--border-subtle)',
        marginTop: 4,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 24, height: 4, background: 'var(--signal-agent)', borderRadius: 2 }} />
          <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase' }}>Agent Signal</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 24, height: 4, background: 'var(--signal-human)', borderRadius: 2 }} />
          <span style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-muted)', letterSpacing: '1px', textTransform: 'uppercase' }}>Human Signal</span>
        </div>
      </div>

      {hoveredFeature && FEATURE_DESCRIPTIONS[hoveredFeature] && (
        <div style={{
          padding: '8px 10px',
          background: 'var(--surface-02)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          fontSize: 'var(--text-xs)',
          color: 'var(--text-secondary)',
          marginTop: 4,
          animation: 'fade-in-up 150ms var(--ease-out) both',
        }}>
          {FEATURE_DESCRIPTIONS[hoveredFeature]}
        </div>
      )}
    </div>
  );
}
