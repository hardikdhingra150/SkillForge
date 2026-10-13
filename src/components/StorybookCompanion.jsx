import React, { useState } from 'react';
import { Heart, Sparkles } from 'lucide-react';
import { PixelSprite } from './PixelArt';

export default function StorybookCompanion({ onToast }) {
  const [greeting, setGreeting] = useState(0);
  return <div className="storybook-companion">
    <div className="companion-topline"><span><i />YOUR CURIOUS COMPANION</span><span>EST. / ONE GOOD IDEA</span></div>
    <button className={`companion-picture ${greeting ? 'greeted' : ''}`} aria-label="Say hello to the ghost dog" onClick={() => { setGreeting(n => n + 1); onToast('A little courage. A little curiosity. Let’s learn something new.'); }}>
      <img src="/images/ghost-dog.png" alt="An illustrated dachshund in a white ghost costume, carrying an orange pumpkin bucket" fetchPriority="high" />
      <span className="companion-greeting" key={greeting}>{greeting ? 'GOOD IDEAS WELCOME.' : 'A LITTLE BRAVER. EVERY DAY.'}<Heart size={12} /></span>
      <span className="companion-star star-a"><Sparkles size={22} /></span><span className="companion-star star-b">+</span>
    </button>
    <div className="companion-caption"><PixelSprite kind="scout" /><span>BIG IDEAS COME IN SMALL DISGUISES.<small>CLICK THE COMPANION TO SAY HELLO</small></span><span className="companion-signature">↗</span></div>
  </div>;
}
