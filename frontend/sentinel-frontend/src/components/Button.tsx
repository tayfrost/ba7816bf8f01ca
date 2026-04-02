import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  children: React.ReactNode;
}

const Button = ({ variant = 'primary', children, className = '', ...props }: ButtonProps) => {
  const baseStyles = `w-full py-4 font-bold rounded-2xl transition-all duration-300 ${
    props.disabled ? 'saturate-40 opacity-30 cursor-not-allowed' : 'cursor-pointer active:scale-95'
  }`;
  
  const variants = {
    primary: "bg-brand-deep text-white shadow-lg hover:bg-brand-deep/90",
    secondary: "bg-white/40 text-brand-deep border border-brand-deep/10 hover:bg-white/60",
    ghost: "border-2 border-transparent text-brand-deep hover:bg-white/20 hover:shadow-lg hover:shadow-black/10",
    danger: "bg-[#ef592c] text-white shadow-lg hover:saturate-110" 
  };

  return (
    <button 
      className={`${baseStyles} ${variants[variant]} ${className}`} 
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;