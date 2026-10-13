import { ParticleVideo } from './ParticleFilm';

export default function LivingBackground({ motion }) {
  return <div className="living-background scene-background particle" aria-hidden="true"><ParticleVideo motion={motion} className="particle-atmosphere particle-film-bg"/><div className="background-vignette"/></div>;
}
