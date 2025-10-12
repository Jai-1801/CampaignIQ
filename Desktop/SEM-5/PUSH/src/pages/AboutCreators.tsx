import { Header } from '@/components/Header';
import { BarChart3, Linkedin } from 'lucide-react';
import { Button } from '@/components/ui/button';
import frontendImg from '@/assets/frontend-dev.jpg';
import backendImg from '@/assets/backend-dev.jpg';
import mlImg from '@/assets/ml-engineer.jpg';
import dataImg from '@/assets/data-engineer.jpg';

const creators = [
  {
    name: 'Jai Surya R',
    role: 'Frontend Developer',
    linkedin: 'https://www.linkedin.com/in/jai-surya-1801abc',
    image: frontendImg,
    alt: 'Frontend developer working on responsive web design'
  },
  {
    name: 'Mohamed Ahsan S',
    role: 'Backend Developer',
    linkedin: 'https://www.linkedin.com/in/mohamedahsan037/',
    image: backendImg,
    alt: 'Backend developer managing servers and databases'
  },
  {
    name: 'Abishai KC',
    role: 'ML Engineer',
    linkedin: 'https://www.linkedin.com/in/abishai-k-c-6a5288271/',
    image: mlImg,
    alt: 'Machine learning engineer working with AI models'
  },
  {
    name: 'Vasanthi',
    role: 'Data Engineer',
    linkedin: 'https://www.linkedin.com/in/vasanthi-sivasankar-98b3b4290/',
    image: dataImg,
    alt: 'Data engineer analyzing data pipelines'
  }
];

const AboutCreators = () => {
  return (
    <div className="min-h-screen">
      <Header />
      
      <section className="relative overflow-hidden bg-background">
        <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/2 left-1/2 w-[1200px] h-[1200px] -translate-x-1/2 -translate-y-1/2 bg-gradient-radial from-foreground/5 via-foreground/2 to-transparent blur-[150px]" />
        </div>
        
        <div className="relative z-10 container mx-auto px-6 py-20 lg:py-32">
          <div className="max-w-5xl mx-auto space-y-16">
            {/* Header */}
            <div className="text-center space-y-6 animate-fade-in-up">
              <h1 className="leading-[1.05]">
                Meet the Creators
              </h1>
              <p className="text-muted-foreground max-w-2xl mx-auto leading-relaxed">
                The talented team behind CampaignIQ, combining expertise in frontend, backend, machine learning, and data engineering to deliver powerful campaign analytics.
              </p>
            </div>

            {/* Team Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 animate-scale-in">
              {creators.map((creator, index) => (
                <div
                  key={index}
                  className="glass rounded-2xl p-8 space-y-6 hover-lift group"
                >
                  {/* Profile Image */}
                  <div className="relative w-full aspect-square rounded-xl overflow-hidden mb-6">
                    <img 
                      src={creator.image} 
                      alt={creator.alt}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent opacity-60" />
                  </div>
                  
                  <div className="space-y-2">
                    <h3 className="text-2xl font-semibold">{creator.name}</h3>
                    <p className="text-muted-foreground">{creator.role}</p>
                  </div>
                  
                  <Button
                    variant="outline"
                    className="w-full gap-2 group-hover:bg-primary/10 group-hover:text-primary transition-smooth"
                    asChild
                  >
                    <a
                      href={creator.linkedin}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Linkedin className="w-4 h-4" />
                      Connect on LinkedIn
                    </a>
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/40 mt-24">
        <div className="container mx-auto px-6 py-12">
          <div className="text-center space-y-4">
            <div className="flex items-center justify-center gap-2">
              <BarChart3 className="w-6 h-6" />
              <span className="text-xl font-semibold">CampaignIQ</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Powered by advanced causal inference and AI
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default AboutCreators;
