import Button from './Button';

interface SubscriptionProps {
  title: string;
  price: string;
  period: string; // "mo", "yr", or "" for free
  features: string[];
}

export default function SubscriptionCard({ title, price, period, features }: SubscriptionProps) {

  const buttonVariant = (period === "mo" || period === "yr") ? "primary" : "secondary";

  return (
    <div className="relative max-w-sm w-full bg-white/20 backdrop-blur-3xl rounded-[2.5rem] shadow-2xl overflow-hidden transition-transform hover:scale-[1.02]">

      <div className="p-8 pb-0 text-center">
        <h2 className="text-3xl font-serif font-black text-brand-deep mt-4">{title}</h2>
        <div className="flex items-baseline justify-center mt-3">
          <span className="text-4xl font-bold text-brand-deep">{price}</span>
          
          {period !== "" && (
            <span className="text-brand-deep/60 ml-1">/{period}</span>
          )}
        </div>
      </div>

      <div className="p-8 space-y-4 ">
        <ul className="space-y-4"> 
          {features.map((item, index) => (

            <li key={index} className="flex items-center gap-3 text-lg font-medium text-brand-deep/90">

              <svg className="w-6 h-6 text-brand-deep/50 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
              </svg>
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div className="p-8 pt-0 ">
        <Button variant={buttonVariant}>
          Get Started
        </Button>
      </div>
    </div>
  );
}