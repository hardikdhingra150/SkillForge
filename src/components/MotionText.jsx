/** Word-sized animation layers keep long titles responsive and cheap to composite. */
export default function MotionText({ text, className = '' }) {
  return <span className={`motion-text ${className}`} aria-label={text}>{text.split(' ').map((word, index) => <span className="motion-word" key={`${word}-${index}`} style={{ '--word': index }} aria-hidden="true"><span>{word}</span>{' '}</span>)}</span>;
}
