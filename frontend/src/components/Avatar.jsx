// Preset "pick an avatar" tiles, Netflix-style. The chosen avatar is stored as
// its emoji (e.g. "taco"); Google sign-ins may instead store a photo URL, which
// renders as an image. Anything else falls back to the person's initial.
export const AVATARS = [
  { id: '\u{1F35C}', bg: '#F4B740' }, // ramen
  { id: '\u{1F32E}', bg: '#E8703A' }, // taco
  { id: '\u{1F355}', bg: '#E24E42' }, // pizza
  { id: '\u{1F363}', bg: '#6FB07F' }, // sushi
  { id: '\u{1F354}', bg: '#C9822E' }, // burger
  { id: '\u{1F957}', bg: '#8FA94C' }, // salad
  { id: '\u{1F35B}', bg: '#E0A458' }, // curry
  { id: '\u{1F969}', bg: '#C0504D' }, // steak
  { id: '\u{1F95F}', bg: '#5AA9A3' }, // dumpling
  { id: '\u{1F35D}', bg: '#D65DB1' }, // spaghetti
  { id: '\u{1F9C1}', bg: '#EC9EC0' }, // cupcake
  { id: '\u{2615}',  bg: '#9C6B3F' }, // coffee
];

const isUrl = (v) => typeof v === 'string' && /^https?:\/\//.test(v);

export function Avatar({ value, name, size = 28, className = '' }) {
  const px = `${size}px`;
  const base =
    'inline-flex flex-shrink-0 items-center justify-center rounded-full border-2 border-ink overflow-hidden';

  if (isUrl(value)) {
    return (
      <img
        src={value}
        alt=""
        style={{ width: px, height: px }}
        className={`${base} object-cover ${className}`}
      />
    );
  }

  const preset = AVATARS.find((a) => a.id === value);
  if (preset) {
    return (
      <span
        style={{ width: px, height: px, background: preset.bg, fontSize: `${size * 0.52}px` }}
        className={`${base} ${className}`}
      >
        {preset.id}
      </span>
    );
  }

  return (
    <span
      style={{ width: px, height: px, fontSize: `${size * 0.42}px` }}
      className={`${base} bg-wash font-bold uppercase text-gray ${className}`}
    >
      {(name || '?').trim().charAt(0)}
    </span>
  );
}
