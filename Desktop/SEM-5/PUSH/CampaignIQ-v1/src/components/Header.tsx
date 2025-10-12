import { BarChart3 } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Header = () => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/80 backdrop-blur-lg">
      <div className="container mx-auto px-6 h-20 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 hover:opacity-70 transition-opacity">
          <BarChart3 className="w-6 h-6" />
          <span className="text-xl font-semibold tracking-tight">CampaignIQ</span>
        </Link>
        
        <nav className="flex items-center gap-8">
          <Link 
            to="/"
            className="text-sm font-medium hover:text-foreground/70 transition-colors"
          >
            Home
          </Link>
          <Link 
            to="/about-creators"
            className="text-sm font-medium hover:text-foreground/70 transition-colors"
          >
            About Creators
          </Link>
          
        </nav>
      </div>
    </header>
  );
};
