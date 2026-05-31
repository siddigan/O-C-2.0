export default function App() {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "#020509",
        gap: "32px",
      }}
    >
      <svg
        viewBox="0 0 400 400"
        width="400"
        height="400"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          {/* Main gradient — shared across all mark elements */}
          <linearGradient
            id="mainGrad"
            x1="30"
            y1="30"
            x2="370"
            y2="370"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0%" stopColor="#00EEC8" />
            <stop offset="48%" stopColor="#1A7AFF" />
            <stop offset="100%" stopColor="#9B30FF" />
          </linearGradient>

          {/* Accent gradient for 2.0 label */}
          <linearGradient
            id="accentGrad"
            x1="228"
            y1="300"
            x2="312"
            y2="300"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0%" stopColor="#FF9A3C" />
            <stop offset="100%" stopColor="#FFE44D" />
          </linearGradient>

          {/* Tile background gradient */}
          <linearGradient
            id="bgGrad"
            x1="0"
            y1="0"
            x2="400"
            y2="400"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0%" stopColor="#09131F" />
            <stop offset="100%" stopColor="#060A14" />
          </linearGradient>

          {/* Outer glow filter */}
          <filter id="glow" x="-35%" y="-35%" width="170%" height="170%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" />
            <feColorMatrix
              in="blur"
              type="matrix"
              values="0 0 0 0 0.05  0 0 0 0 0.5  0 0 0 0 1  0 0 0 0.65 0"
              result="coloredBlur"
            />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Soft glow for accent dots */}
          <filter id="softGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="3.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Clip to tile boundary */}
          <clipPath id="tileClip">
            <rect x="16" y="16" width="368" height="368" rx="72" />
          </clipPath>
        </defs>

        {/* ── Tile background ── */}
        <rect x="16" y="16" width="368" height="368" rx="72" fill="url(#bgGrad)" />

        {/* ── Subtle dot grid ── */}
        <g clipPath="url(#tileClip)" opacity="0.45">
          {[0, 1, 2, 3, 4, 5].flatMap((row) =>
            [0, 1, 2, 3, 4, 5].map((col) => (
              <circle
                key={`dot-${row}-${col}`}
                cx={55 + col * 59}
                cy={55 + row * 59}
                r="1.4"
                fill="#1B3A62"
              />
            ))
          )}
        </g>

        {/* ── Faint outer ring border ── */}
        <rect
          x="20"
          y="20"
          width="360"
          height="360"
          rx="69"
          fill="none"
          stroke="url(#mainGrad)"
          strokeWidth="0.75"
          opacity="0.2"
        />

        {/* ══════════════ O MARK ══════════════ */}

        {/* O — outer ring (filled circle) */}
        <circle cx="134" cy="200" r="70" fill="url(#mainGrad)" filter="url(#glow)" />

        {/* O — inner hole (reveals dark bg) */}
        <circle cx="134" cy="200" r="44" fill="url(#bgGrad)" />

        {/* O — arrow inside the hole, pointing right */}
        <path
          d="M 108 192 L 148 192 L 148 178 L 170 200 L 148 222 L 148 208 L 108 208 Z"
          fill="url(#mainGrad)"
        />

        {/* ══════════════ C MARK ══════════════ */}

        {/*
          C center: (267, 200), arc path radius: 57, stroke: 26
          Opening ±55° from right (0°)
          Start: (267+57·cos−55°, 200+57·sin−55°) ≈ (300, 153)
          End:   (300, 247)
          large-arc=1, sweep=0 → counterclockwise, left-going arc = C shape ✓
        */}
        <path
          d="M 300 153 A 57 57 0 1 0 300 247"
          fill="none"
          stroke="url(#mainGrad)"
          strokeWidth="26"
          strokeLinecap="round"
          filter="url(#glow)"
        />

        {/* ══════════════ 2.0 LABEL ══════════════ */}

        <text
          x="228"
          y="318"
          fontFamily="'Courier New', Courier, monospace"
          fontSize="21"
          fontWeight="900"
          letterSpacing="4"
          fill="url(#accentGrad)"
        >
          2.0
        </text>

        {/* ── Accent corner dot (top-right) ── */}
        <circle cx="350" cy="50" r="7" fill="#FFB830" filter="url(#softGlow)" />
        <circle cx="334" cy="59" r="3.5" fill="#1A7AFF" opacity="0.65" />

        {/* ── Corner bracket accent (bottom-left) ── */}
        <path
          d="M 46 336 L 46 354 L 64 354"
          stroke="#1B3A62"
          strokeWidth="2"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* ── Thin vertical tick beside version (top-right) ── */}
        <path
          d="M 350 64 L 350 76"
          stroke="#FFB830"
          strokeWidth="1.5"
          fill="none"
          strokeLinecap="round"
          opacity="0.4"
        />
      </svg>

      {/* App name label below */}
      <div
        style={{
          fontFamily: "'Courier New', Courier, monospace",
          fontSize: "13px",
          letterSpacing: "6px",
          color: "#2A4A72",
          textTransform: "uppercase",
          userSelect: "none",
        }}
      >
        OC · Job Search Platform
      </div>
    </div>
  );
}
