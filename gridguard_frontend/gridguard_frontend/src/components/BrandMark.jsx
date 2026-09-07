export default function BrandMark({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 2 L21 6 V12 C21 17 17.5 20.5 12 22 C6.5 20.5 3 17 3 12 V6 Z"
        stroke="var(--copper)"
        strokeWidth="1.6"
        fill="none"
      />
      <path d="M13 7 L8.5 13.2 H11.6 L10.6 18 L16 11.2 H12.9 Z" fill="var(--cyan)" />
    </svg>
  );
}
