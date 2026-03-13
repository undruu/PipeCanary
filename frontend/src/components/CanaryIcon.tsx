interface CanaryIconProps {
  className?: string;
}

function CanaryIcon({ className = "w-8 h-8" }: CanaryIconProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Body */}
      <ellipse cx="30" cy="38" rx="16" ry="14" fill="currentColor" opacity="0.9" />
      {/* Head */}
      <circle cx="38" cy="22" r="10" fill="currentColor" />
      {/* Eye */}
      <circle cx="41" cy="20" r="2" fill="white" />
      <circle cx="41.5" cy="19.5" r="1" fill="#1a1a1a" />
      {/* Beak */}
      <polygon points="48,21 56,19 48,23" fill="#e85d04" />
      {/* Wing */}
      <ellipse cx="24" cy="36" rx="11" ry="8" fill="currentColor" opacity="0.7" transform="rotate(-15 24 36)" />
      <path d="M16 32 C10 38, 8 44, 12 42 C14 40, 18 38, 16 32Z" fill="currentColor" opacity="0.5" />
      {/* Tail */}
      <path d="M14 42 C8 48, 6 52, 10 50 L16 44Z" fill="currentColor" opacity="0.8" />
      <path d="M16 44 C10 52, 8 56, 14 52 L18 46Z" fill="currentColor" opacity="0.6" />
      {/* Legs */}
      <line x1="26" y1="50" x2="24" y2="58" stroke="#e85d04" strokeWidth="2" strokeLinecap="round" />
      <line x1="24" y1="58" x2="20" y2="60" stroke="#e85d04" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="24" y1="58" x2="26" y2="60" stroke="#e85d04" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="34" y1="50" x2="36" y2="58" stroke="#e85d04" strokeWidth="2" strokeLinecap="round" />
      <line x1="36" y1="58" x2="33" y2="60" stroke="#e85d04" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="36" y1="58" x2="39" y2="60" stroke="#e85d04" strokeWidth="1.5" strokeLinecap="round" />
      {/* Crest */}
      <path d="M34 13 C36 6, 42 4, 40 12" fill="currentColor" opacity="0.8" />
    </svg>
  );
}

export default CanaryIcon;
