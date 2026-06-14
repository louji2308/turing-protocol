import { useEffect, useRef, useState } from 'react';

export default function AnimatedNumber({ value, duration = 800, className, style }) {
  const [prevValue, setPrevValue] = useState(value);
  const [animating, setAnimating] = useState(false);
  const [displayDigits, setDisplayDigits] = useState(() => {
    const str = value.toLocaleString();
    return str.split('').map((char) => ({
      char,
      prevChar: char,
      isAnimating: false,
      direction: 0,
    }));
  });
  const prevDigitsRef = useRef([]);

  useEffect(() => {
    const current = value;
    const prev = prevValue;
    if (current === prev) return;

    const currentStr = current.toLocaleString();
    const prevStr = prev.toLocaleString();
    const maxLen = Math.max(currentStr.length, prevStr.length);

    const curDigits = currentStr.padStart(maxLen, ' ').split('');
    const prevDigits = prevStr.padStart(maxLen, ' ').split('');

    setAnimating(true);
    setDisplayDigits(curDigits.map((d, i) => ({
      char: d,
      prevChar: prevDigits[i],
      isAnimating: d !== prevDigits[i],
      direction: d > prevDigits[i] ? -1 : 1,
    })));
    setPrevValue(current);

    const t = setTimeout(() => setAnimating(false), duration);
    return () => clearTimeout(t);
  }, [value]);

  return (
    <span className={className} style={{
      display: 'inline-flex',
      fontVariantNumeric: 'tabular-nums',
      ...style,
    }}>
      {displayDigits.map((d, i) => {
        if (d.char === ' ' && d.prevChar === ' ') {
          return <span key={i} style={{ width: '0.5em' }}>&nbsp;</span>;
        }
        if (d.char === ',') {
          return <span key={i} style={{ width: '0.3em', textAlign: 'center' }}>,</span>;
        }
        if (d.char === ' ') {
          return <span key={i} style={{ width: '0.5em' }}>&nbsp;</span>;
        }
        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              overflow: 'hidden',
              height: '1em',
              width: '0.6em',
              textAlign: 'center',
              verticalAlign: 'middle',
            }}
          >
            <span
              style={{
                display: 'inline-block',
                transform: animating && d.isAnimating
                  ? `translateY(${d.direction * 100}%)`
                  : 'translateY(0)',
                transition: animating && d.isAnimating
                  ? `transform ${duration}ms cubic-bezier(0.34, 1.56, 0.64, 1)`
                  : 'none',
              }}
            >
              {d.char}
            </span>
          </span>
        );
      })}
    </span>
  );
}
