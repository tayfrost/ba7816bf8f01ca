import Button from "./Button";

export default function LandingHeader() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/10 backdrop-blur-md border-b border-white/20">
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        
        <div className="hidden md:flex items-center gap-8 text-brand-deep/80 font-medium">
          <a href="#features" className="hover:text-brand-deep transition-colors">Features</a>
          <a href="#pricing" className="hover:text-brand-deep transition-colors">Pricing</a>
          <a href="#security" className="hover:text-brand-deep transition-colors">Security</a>
        </div>

        <div className="flex items-center gap-4">
          <button className="text-brand-deep font-bold px-4 hover:opacity-70 transition-opacity">
            Login
          </button>
          <div className="w-32">
            <Button variant="primary">Join Now</Button>
          </div>
        </div>
      </div>
    </nav>
  );
}